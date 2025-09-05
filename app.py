import gradio as gr
from gradio.themes.utils import colors as gr_colors
import requests
import json
import datetime
import os
import re
import fitz  # PyMuPDF for PDF parsing
from typing import Any, Dict, List, Optional, Tuple

# Nebius API configuration (hardcoded)
NEBIUS_API_URL = "https://api.studio.nebius.ai/v1/chat/completions"
NEBIUS_API_KEY = ""

# --- Database / Memory configuration ---
DATABASE_PATH_DEFAULT = "database.json"
DATABASE_FALLBACK_PATH = "json.json"
_DB_CACHE: Dict[str, Any] = {}

# Privacy protection - disable database loading in public deployments
PRIVACY_MODE = os.environ.get("PRIVACY_MODE", "false").lower() == "true"


def _normalize_type_label(label: str) -> List[str]:
    """Normalize a raw type string into internal keys. Supports multi-label via ';', ',', '/'.
    Returns a list of keys among: ['reason', 'framework', 'connection', 'result'] (deduped order-preserving).
    """
    if not label:
        return []
    raw = label.replace("|", ";").replace("/", ";").replace(",", ";")
    parts = [p.strip().lower() for p in raw.split(";") if p.strip()]
    keys: List[str] = []
    for p in parts:
        k = p
        if any(w in p for w in ["reason", "phenomenon", "why", "mechanism", "drivers", "aversion"]):
            k = "reason"
        elif any(w in p for w in ["framework", "model", "formalize", "calibrated"]):
            k = "framework"
        elif any(w in p for w in ["connection", "affects", "impact", "influence", "association", "disconnect", "versus", "no effect"]):
            k = "connection"
        elif any(w in p for w in ["result", "introduce", "consequence", "lead to", "effects"]):
            k = "result"
        # allow typos
        elif "conection" in p:
            k = "connection"
        elif "reasons" in p:
            k = "reason"
        if k not in keys:
            keys.append(k)
    return keys


def _normalize_ui_choice(choice: str) -> Optional[str]:
    c = (choice or "").strip().lower()
    if c.startswith("reason"):
        return "reason"
    if c.startswith("framework") or c.startswith("model"):
        return "framework"
    if c.startswith("connection"):
        return "connection"
    if c.startswith("result"):
        return "result"
    return None


def _ensure_database_loaded(path: Optional[str] = None) -> Dict[str, Any]:
    global _DB_CACHE
    if _DB_CACHE:
        return _DB_CACHE
    
    # Privacy protection: skip database loading in public deployments
    if PRIVACY_MODE:
        _DB_CACHE = {"sources": [], "attempts": []}
        return _DB_CACHE
    
    db_path = path or (DATABASE_PATH_DEFAULT if os.path.exists(DATABASE_PATH_DEFAULT) else DATABASE_FALLBACK_PATH)
    if not os.path.exists(db_path):
        _DB_CACHE = {"sources": [], "attempts": []}
        return _DB_CACHE
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {"sources": [], "attempts": []}

    sources: List[Dict[str, Any]] = data.get("sources", []) or []
    attempts: List[Dict[str, Any]] = data.get("attempts", []) or []

    # Build indices
    id_to_source: Dict[str, Dict[str, Any]] = {}
    for s in sources:
        sid = str(s.get("id", "")).strip()
        if not sid:
            continue
        s_types = _normalize_type_label(str(s.get("type", "")))
        s["_norm_types"] = s_types
        id_to_source[sid] = s

    # Group attempts by source id
    src_to_attempts: Dict[str, List[Dict[str, Any]]] = {sid: [] for sid in id_to_source}
    for at in attempts:
        used_ids = at.get("used_source_ids", []) or []
        for sid in used_ids:
            sid_s = str(sid)
            if sid_s in id_to_source:
                src_to_attempts.setdefault(sid_s, []).append(at)

    # Build examples per type key
    type_to_examples: Dict[str, List[Dict[str, str]]] = {}
    for sid, src in id_to_source.items():
        types = src.get("_norm_types", [])
        if not types:
            continue
        # Prefer final_summary if exists, else last draft
        final_text = None
        drafts: List[Tuple[str, str]] = []  # (draft_summary, comments)
        for at in src_to_attempts.get(sid, []):
            if at.get("final_summary"):
                final_text = at.get("final_summary")
            if at.get("draft_summary") or at.get("comments"):
                drafts.append((at.get("draft_summary", ""), "\n".join(at.get("comments", []) if isinstance(at.get("comments"), list) else [str(at.get("comments") or "")])))
        if not final_text and drafts:
            final_text = drafts[-1][0]
        label = src.get("label", "")
        evo_lines: List[str] = []
        # Keep evolution concise
        for i, (d, cmt) in enumerate(drafts[:4], start=1):
            if d:
                evo_lines.append(f"Draft v{i}: {d}")
            if cmt:
                evo_lines.append(f"Feedback v{i}: {cmt}")
        if final_text:
            evo_lines.append(f"Final: {final_text}")
        evo_text = "\n".join(evo_lines).strip()
        example = {"label": label, "final": final_text or "", "evolution": evo_text}
        for t in types:
            type_to_examples.setdefault(t, []).append(example)

    _DB_CACHE = {
        "raw": data,
        "id_to_source": id_to_source,
        "src_to_attempts": src_to_attempts,
        "type_to_examples": type_to_examples,
    }
    return _DB_CACHE


def _build_memory_examples_from_db(selected_types_ui: Optional[List[str]], k_per_type: int = 2) -> str:
    """Assemble short examples from DB for the chosen types.
    Falls back to empty string if DB unavailable.
    """
    db = _ensure_database_loaded()
    if not db or not db.get("type_to_examples"):
        return ""
    # Normalize UI choices to internal keys
    keys: List[str] = []
    for ch in (selected_types_ui or []):
        nk = _normalize_ui_choice(ch)
        if nk and nk not in keys:
            keys.append(nk)
    if not keys:
        keys = ["connection"]  # default

    lines: List[str] = []
    for key in keys:
        examples = (db["type_to_examples"].get(key) or [])[:k_per_type]
        for ex in examples:
            if ex.get("final"):
                lines.append(f"- [{key}] {ex.get('final')}")
    return "\n".join(lines).strip()


def _build_cot_like_memory(selected_types_ui: Optional[List[str]], k_sources: int = 1) -> str:
    """Build a CoT-like learning context: show draft->feedback->final evolutions for similar types.
    Keep concise. No hidden chain-of-thought is requested from the model; this is explicit training data.
    """
    db = _ensure_database_loaded()
    if not db or not db.get("type_to_examples"):
        return ""
    keys: List[str] = []
    for ch in (selected_types_ui or []):
        nk = _normalize_ui_choice(ch)
        if nk and nk not in keys:
            keys.append(nk)
    if not keys:
        keys = ["connection"]
    blocks: List[str] = []
    for key in keys:
        examples = (db["type_to_examples"].get(key) or [])[:k_sources]
        for ex in examples:
            evo = ex.get("evolution", "")
            if evo:
                blocks.append(f"[Type: {key}] {ex.get('label','')}:\n{evo}")
    return "\n\n".join(blocks).strip()

# --- MCP Protocol Support ---
def mcp_supported_call(payload, endpoint, headers):
    response = requests.post(endpoint, json=payload, headers=headers)
    return response


# --- PDF utilities (inspired by ChatPaper) ---
def _find_papers_directory() -> str:
    """Find the directory containing PDFs. Prefer 'papers(pdfs)', fallback to 'papers'."""
    base_dir = os.path.dirname(__file__)
    candidates = [
        os.path.join(base_dir, "papers(pdfs)"),
        os.path.join(base_dir, "papers"),
        # Absolute fallback if user keeps exact Windows path
        r"C:\\Users\\HKUBS\\Desktop\\summary\\MCP\\agentic_Ai_humanizer_mcp\\papers(pdfs)",
    ]
    for candidate in candidates:
        if os.path.isdir(candidate):
            return candidate
    # Ensure directory exists even if empty
    default_dir = os.path.join(base_dir, "papers(pdfs)")
    os.makedirs(default_dir, exist_ok=True)
    return default_dir


def list_pdf_files() -> list:
    papers_dir = _find_papers_directory()
    try:
        files = [
            f for f in os.listdir(papers_dir)
            if f.lower().endswith(".pdf") and os.path.isfile(os.path.join(papers_dir, f))
        ]
        files.sort()
        return files
    except Exception:
        return []


def _extract_title_from_pdf(doc: fitz.Document) -> str:
    """Extract title by taking the largest font spans across pages (approximation)."""
    max_font_size = 0.0
    collected_lines = []
    title_page_index = 0
    try:
        for page_index, page in enumerate(doc):
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue
                lines = block.get("lines", [])
                if not lines:
                    continue
                spans = lines[0].get("spans", [])
                if not spans:
                    continue
                size = spans[0].get("size", 0)
                if size > max_font_size:
                    max_font_size = size
                    collected_lines = []
                    title_page_index = page_index
                # Collect lines that match the largest 1-2 sizes
                if max_font_size and abs(size - max_font_size) < 0.3:
                    text = spans[0].get("text", "").strip()
                    if text and len(text) > 4 and "arXiv" not in text:
                        collected_lines.append(text)
        title = " ".join(collected_lines).replace("\n", " ").strip()
        return title
    except Exception:
        return ""


def _build_section_page_index(doc: fitz.Document) -> dict:
    section_names = [
        "Abstract",
        "Introduction",
        "Related Work",
        "Background",
        "Preliminary",
        "Problem Formulation",
        "Methods",
        "Methodology",
        "Method",
        "Approach",
        "Approaches",
        "Materials and Methods",
        "Experiment Settings",
        "Experiment",
        "Experimental Results",
        "Evaluation",
        "Experiments",
        "Results",
        "Findings",
        "Data Analysis",
        "Discussion",
        "Results and Discussion",
        "Conclusion",
        "Conclusions",
        "Keywords",
        "Index Terms",
    ]
    index_map = {}
    try:
        for page_idx, page in enumerate(doc):
            page_text = page.get_text()
            for sec in section_names:
                if sec == "Abstract" and "Abstract" in page_text:
                    index_map.setdefault("Abstract", page_idx)
                else:
                    if f"{sec}\n" in page_text or f"{sec.upper()}\n" in page_text:
                        index_map.setdefault(sec, page_idx)
    except Exception:
        pass
    return index_map


def _extract_sections(doc: fitz.Document, index_map: dict) -> dict:
    def find_header_index(text: str, header: str) -> int:
        idx = text.find(header)
        if idx == -1:
            idx = text.find(header.upper())
        if idx == -1:
            # Allow optional colon or trailing spaces
            pattern = re.compile(rf"(?im)^\s*{re.escape(header)}\s*:?")
            m = pattern.search(text)
            if m:
                return m.start()
        return idx

    text_pages = [page.get_text() for page in doc]
    sections: dict[str, str] = {}
    # Order sections by page index ascending
    items_sorted = sorted(index_map.items(), key=lambda kv: kv[1])
    try:
        for i, (sec_name, start_page) in enumerate(items_sorted):
            end_page = items_sorted[i + 1][1] if i + 1 < len(items_sorted) else len(text_pages)
            fragments: list[str] = []
            for page_i in range(start_page, end_page):
                page_text = text_pages[page_i]
                # For first page: start at header
                if page_i == start_page:
                    start_i = find_header_index(page_text, sec_name)
                    if start_i == -1:
                        start_i = 0
                    page_text = page_text[start_i:]
                # For last page (just before next section): cut at next header if present
                if page_i == end_page - 1 and i + 1 < len(items_sorted):
                    next_sec = items_sorted[i + 1][0]
                    end_i = find_header_index(page_text, next_sec)
                    if end_i != -1:
                        page_text = page_text[:end_i]
                fragments.append(page_text)
            current_text = "".join(fragments)
            sections[sec_name] = current_text.replace('-\n', '').replace('\n', ' ').strip()
    except Exception:
        pass
    return sections


def _extract_keywords_from_first_page(doc: fitz.Document) -> str:
    try:
        first_text = doc[0].get_text()
        # Common patterns: "Keywords: xxx" or "Index Terms— xxx"
        m = re.search(r"(?i)(Keywords|Index Terms)\s*[:\u2014\-]\s*(.+)", first_text)
        if m:
            # Stop at line end
            line = m.group(2).splitlines()[0]
            return line.strip().rstrip('.')
        return ""
    except Exception:
        return ""


def extract_paper_fields(pdf_path: str) -> dict:
    doc = fitz.open(pdf_path)
    try:
        title = _extract_title_from_pdf(doc)
        index_map = _build_section_page_index(doc)
        sections = _extract_sections(doc, index_map)
        abstract = sections.get("Abstract", "")
        introduction = (
            sections.get("Introduction")
            or sections.get("Background")
            or sections.get("Preliminary")
            or ""
        )
        conclusion = (
            sections.get("Conclusion")
            or sections.get("Conclusions")
            or sections.get("Discussion")
            or ""
        )
        keywords = (
            sections.get("Keywords", "")
            or sections.get("Index Terms", "")
            or _extract_keywords_from_first_page(doc)
        )
        return {
            "title": title,
            "keywords": keywords,
            "abstract": abstract,
            "introduction": introduction,
            "conclusion": conclusion,
        }
    finally:
        doc.close()


def build_query_from_fields(fields: dict, file_name: str = "") -> str:
    # Return a single paragraph: plain words only, no labels, no newlines, no extra hooks
    ordered_keys = ["title", "keywords", "abstract", "introduction", "conclusion"]
    parts = [str(fields.get(k, "")).strip() for k in ordered_keys if str(fields.get(k, "")).strip()]
    return " ".join(parts).strip()

def call_nebius_api(query, context_data="", temperature: float | None = None, top_p: float | None = None):
    try:
        system_prompt = "You are a helpful research assistant. Keep responses concise and accurate."
        user_content = f"{context_data}\n\n{query}" if context_data else query
        
        # Ensure temperature is a valid float
        temp_value = 0.7
        if temperature is not None:
            try:
                temp_value = float(temperature)
            except (ValueError, TypeError):
                temp_value = 0.7
        
        nebius_payload = {
            "model": "meta-llama/Meta-Llama-3.1-70B-Instruct",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": 1000,
            "temperature": temp_value,
        }
        
        # Ensure top_p is a valid float
        if top_p is not None:
            try:
                nebius_payload["top_p"] = float(top_p)
            except (ValueError, TypeError):
                pass  # Skip top_p if invalid
        
        headers = {
            "Authorization": f"Bearer {NEBIUS_API_KEY}",
            "Content-Type": "application/json",
        }
        response = mcp_supported_call(nebius_payload, NEBIUS_API_URL, headers)
        if response.status_code != 200:
            return f"Error: Nebius API request failed - {response.text}"
        nebius_response = response.json()
        result = (
            nebius_response.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "No response")
        )
        return result
    except Exception as e:
        return f"Error: {str(e)}"

def humanize_text(ai_response, temperature: float | None = None):
    try:
        humanize_prompt = f"""Please rewrite the following AI response to make it sound more natural, conversational, and human-like. 
        Add personality, use casual language where appropriate, include filler words occasionally, and make it feel like it's coming from a real person having a conversation:

        AI Response to humanize:
        {ai_response}

        Humanized version:"""
        nebius_payload = {
            "model": "deepseek-ai/DeepSeek-R1",
            "messages": [{"role": "user", "content": humanize_prompt}],
            "max_tokens": 1200,
        }
        nebius_payload["temperature"] = float(temperature) if temperature is not None else 0.9
        headers = {
            "Authorization": f"Bearer {NEBIUS_API_KEY}",
            "Content-Type": "application/json",
        }
        response = mcp_supported_call(nebius_payload, NEBIUS_API_URL, headers)
        if response.status_code != 200:
            return ai_response
        nebius_response = response.json()
        humanized_result = (
            nebius_response.get("choices", [{}])[0]
            .get("message", {})
            .get("content", ai_response)
        )
        # Remove chain-of-thought or internal reasoning markers like <think> ... </think>
        humanized_result = re.sub(r"(?is)<think>[\s\S]*?</think>", "", humanized_result)
        if "Humanized version:" in humanized_result:
            humanized_result = humanized_result.split("Humanized version:", 1)[-1].strip()
        lines = humanized_result.splitlines()
        filtered_lines = [
            line
            for line in lines
            if not line.strip()
            .lower()
            .startswith(
                (
                    "please",
                    "rewrite",
                    "add personality",
                    "ai response",
                    "humanized version",
                    "as a human",
                    "as an ai",
                    "here's",
                    "sure",
                    "of course",
                )
            )
        ]
        cleaned = "\n".join(filtered_lines).strip()
        return cleaned if cleaned else humanized_result
    except Exception as e:
        return ai_response

def save_conversation(query, ai_response, humanized_response, context_data):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("conversation_history.txt", "a", encoding="utf-8") as f:
        f.write(
            f"[{timestamp}]\nQuery: {query}\nContext: {context_data}\nAI Response: {ai_response}\nHumanized: {humanized_response}\n{'-' * 40}\n"
        )

def clear_history():
    open("conversation_history.txt", "w").close()
    return "History cleared."

def load_history():
    try:
        with open("conversation_history.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "No history found."

def export_history_to_file(filename="conversation_export.txt"):
    try:
        with (
            open("conversation_history.txt", "r", encoding="utf-8") as src,
            open(filename, "w", encoding="utf-8") as dst,
        ):
            dst.write(src.read())
        return f"History exported to {filename}"
    except Exception as e:
        return f"Export failed: {e}"

def search_history(keyword):
    try:
        with open("conversation_history.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
        matches = [line for line in lines if keyword.lower() in line.lower()]
        return "".join(matches) if matches else "No matches found."
    except FileNotFoundError:
        return "No history found."

def delete_last_conversation():
    try:
        with open("conversation_history.txt", "r", encoding="utf-8") as f:
            content = f.read().strip().split("-" * 40)
        if len(content) > 1:
            content = content[:-1]
            with open("conversation_history.txt", "w", encoding="utf-8") as f:
                f.write(("-" * 40).join(content).strip())
            return "Last conversation deleted."
        else:
            clear_history()
            return "History cleared."
    except FileNotFoundError:
        return "No history found."

# --- Original-style chat interface (restore minimal change) ---
def _augment_with_cot_instruction(query: str, enable_cot: bool) -> str:
    if not enable_cot:
        return query
    cot_instruction = (
        "Read the paper excerpts above. Think briefly but DO NOT reveal your reasoning. Then output ONLY in English:\n"
        "1) Key contributions emphasized by the authors (3-5 bullets). Use the original terms/phrases when possible.\n"
        "2) Whether a novel model/framework/algorithm or large-scale data/participants are mentioned. If yes, state the exact name(s) and the number(s); otherwise write 'Not explicitly mentioned'.\n"
        "3) Data and collection method: Specify the data source type (e.g., questionnaire/survey, lab/field/online randomized experiment, administrative records, brokerage/hospital records, public filings, transactions, SEC filings, bank loan data, CRSP/Compustat/Datastream, etc.), how it was obtained (e.g., randomized assignment, field trial, survey administration, scraping/API, matched datasets), the participant/sample size and identities (e.g., startup founders, VCs, bankers, sell-side analysts), and countries/regions (e.g., China, U.S.). If not provided, write 'Not explicitly mentioned'.\n"
        "Output just these three items, nothing else."
    )
    return f"{query}\n\n{cot_instruction}"


def gradio_interface(query, context_data, humanize=False, fewshot_choices=None, ai_temperature=0.7, ai_top_p=1.0, human_temperature=0.9):
    if not str(query).strip():
        return "Please enter a query.", "", ""
    # Always produce both: highlights (CoT) + full response
    full_response = call_nebius_api(query, context_data, temperature=ai_temperature, top_p=ai_top_p)
    cot_query = _augment_with_cot_instruction(query, True)
    cot_response = call_nebius_api(cot_query, context_data, temperature=ai_temperature, top_p=ai_top_p)
    ai_response = f"Highlights:\n{cot_response}\n\n---\nFull response:\n{full_response}"
    final_query = cot_query
    if humanize and not str(ai_response).startswith("Error:"):
        humanized_response = humanize_text(ai_response, temperature=human_temperature)
    else:
        humanized_response = ""
    short_summary = generate_short_summary(full_response, fewshot_choices)
    return ai_response, humanized_response, short_summary


def generate_short_summary(base_text: str, few_shots=None) -> str:
    try:
        prefix = (
            "You are given a model answer below. Produce a compact English output in two parts: "
            "(A) One single-sentence overview (25–40 words), academic yet accessible; "
            "(B) 3–6 bullets with key points. Preserve original key terms when appropriate. "
            "Do not add any headers. Output the sentence first on its own line, then the bullets.\n\n"
        )
        # Build examples from user selection (list of type keys) or raw string, else fallback by detection
        if isinstance(few_shots, list) and len(few_shots) > 0:
            # If labels like "a reason/phenomenon" are passed, normalize to keys
            selected_keys = [str(x).strip().split()[0].lower() for x in few_shots]
            example_list = [_examples_for_type_key(k) for k in selected_keys if _examples_for_type_key(k)]
            examples = "\n".join(example_list).strip()
        elif isinstance(few_shots, str) and few_shots.strip():
            examples = few_shots.strip()
        else:
            examples = _fallback_fewshots_by_type(base_text)
        # Augment with memory from DB (type-prior examples + CoT-like evolution glimpses)
        memory_snippets = _build_memory_examples_from_db(few_shots if isinstance(few_shots, list) else None)
        memory_cot = _build_cot_like_memory(few_shots if isinstance(few_shots, list) else None)
        memory_block = ""
        if memory_snippets:
            memory_block += f"Type-prior exemplars (concise):\n{memory_snippets}\n\n"
        if memory_cot:
            memory_block += f"Learning traces (draft→feedback→final):\n{memory_cot}\n\n"
        prompt = (
            f"{prefix}Few-shot examples (style and brevity to mimic):\n{examples}\n\n"
            f"Use the following memory to improve conciseness, structure, and faithfulness. "
            f"Do NOT copy verbatim; treat it as guidance.\n{memory_block}"
            f"Model Answer:\n{base_text}"
        )
        return call_nebius_api(prompt)
    except Exception:
        return ""


def _detect_paper_type(text: str) -> str:
    t = (text or "").lower()
    # a: reason/phenomenon
    if any(k in t for k in ["why", "because", "drivers", "mechanism", "aversion", "perceptions", "preferences"]):
        return "a"
    # b: framework/model
    if any(k in t for k in ["framework", "model", "quantify", "formalize", "calibrated"]):
        return "b"
    # c: connection
    if any(k in t for k in ["affects", "impact", "influence", "association", "disconnect","disconnection",  "versus", "no effect"]):
        return "c"
    # d: result
    if any(k in t for k in ["result", "results", "introduce", "consequences", "lead to", "effects on"]):
        return "d"
    return "c"


def _fallback_fewshots_by_type(text: str) -> str:
    paper_type = _detect_paper_type(text)
    return _examples_for_type_key(paper_type)


def _examples_for_type_key(key: str) -> str:
    k = (key or "").lower().strip()
    # Normalize human-facing labels back to internal keys
    if k.startswith("reason"):
        k = "a"
    elif k.startswith("framework"):
        k = "b"
    elif k.startswith("connection"):
        k = "c"
    elif k.startswith("result"):
        k = "d"
    if k == "a":
        return (
            "- This paper uses randomized experiments with 409 startup founders and 129 venture capitalists to identify belief- and taste-based drivers of ESG aversion in early-stage collaboration decisions."
        )
    if k == "b":
        return (
            "- Using a calibrated life-cycle model, the study estimates individuals’ willingness to pay for reduced health risks and quantifies resulting impacts on insurance value and government fiscal burden.\n"
            "- This study proposes a model selection framework for AI hiring tools that accounts for real-world operational outcomes rather than relying solely on statistical goodness-of-fit."
        )
    if k == "c":
        return (
            "- Exploiting staggered adoption of U.S. hospital pay transparency laws, this paper assesses how wage transparency among hospital staff affects patient satisfaction outcomes.\n"
            "- This paper analyzes individual investors’ brokerage data to assess how nearing milestone ages (e.g., 30, 40, 50) influences their risk-taking behavior and trading performance in stock markets.\n"
            "- Analyzing U.S. bank loan data and ESG disclosures, the paper documents a disconnect between stated environmental commitments and actual lending to carbon-intensive industries."
        )
    if k == "d":
        return (
            "- This paper investigates placeholder CEOs—non-family executives serving between two family CEOs during leadership transitions when heirs are unavailable—in Japanese family firms, comparing their demographic traits, tenure, and firm performance effects to those of professional CEOs.\n"
            "- Using matched Swedish employer-employee data, this paper investigates how IPOs affect workers’ employment contracts, household financial outcomes, fertility decisions, and geographic mobility."
        )
    return ""

def _get_uploaded_path(file_obj) -> str:
    """Best-effort to obtain filesystem path from Gradio upload item."""
    try:
        if isinstance(file_obj, str):
            return file_obj
        if isinstance(file_obj, dict) and "name" in file_obj:
            return file_obj["name"]
        if hasattr(file_obj, "name"):
            return file_obj.name
    except Exception:
        pass
    return ""


def process_uploaded_pdfs(files, humanize=False, save=False):
    if not files or (isinstance(files, list) and len(files) == 0):
        return "Please upload at least one PDF.", "", load_history()

    ai_agg = []
    human_agg = []
    items = files if isinstance(files, list) else [files]
    for item in items:
        pdf_path = _get_uploaded_path(item)
        if not pdf_path or not os.path.exists(pdf_path):
            ai_agg.append("[Skip] Invalid file input.")
            continue
        try:
            fields = extract_paper_fields(pdf_path)
            query = build_query_from_fields(fields, file_name=os.path.basename(pdf_path))
            ai_response = call_nebius_api(query)
            humanized_response = (
                humanize_text(ai_response) if (humanize and not str(ai_response).startswith("Error:")) else ""
            )
            if save:
                save_conversation(query, ai_response, humanized_response, context_data="uploaded_pdf")

            header = f"===== {os.path.basename(pdf_path)} ====="
            ai_agg.append(f"{header}\n{ai_response}")
            if humanized_response:
                human_agg.append(f"{header}\n{humanized_response}")
        except Exception as e:
            ai_agg.append(f"[Error processing {os.path.basename(pdf_path)}] {e}")

    ai_text = "\n\n".join(ai_agg).strip()
    human_text = "\n\n".join(human_agg).strip()
    return ai_text, human_text, load_history()


def fill_query_from_pdf(file):
    if not file:
        return ""
    try:
        pdf_path = _get_uploaded_path(file)
        if not pdf_path or not os.path.exists(pdf_path):
            return ""
        fields = extract_paper_fields(pdf_path)
        # Plain concatenated text (no labels)
        query_text = build_query_from_fields(fields)
        return query_text
    except Exception as e:
        return f"PDF parse error: {e}"

def create_gradio_app():
    tiffany = gr_colors.Color(
        name="tiffany",
        c50="#F2FBFA",
        c100="#E6F7F6",
        c200="#CFF0EE",
        c300="#B7E8E5",
        c400="#9FE0DB",
        c500="#81D8D0",
        c600="#63C6BE",
        c700="#48B0A8",
        c800="#368F88",
        c900="#276B66",
        c950="#1C4F51",
    )
    theme = gr.themes.Soft(
        primary_hue=tiffany,
        secondary_hue=tiffany,
    )
    with gr.Blocks(theme=theme) as demo:
        gr.Markdown("# AI Paper Summary Pilot")
        with gr.Row():
            with gr.Column():
                # Original query/context inputs
                query_input = gr.Textbox(
                    label="Enter your query", placeholder="Ask me anything...", lines=2
                )
                context_input = gr.Textbox(
                    label="Optional context data",
                    placeholder="Enter additional context (optional)",
                    lines=2,
                )
                # Added: single-file PDF uploader + fill button
                file_uploader = gr.File(label="Upload a PDF to fill query", file_types=[".pdf"])  # ensure English label
                fill_button = gr.Button("Fill from PDF")

                humanize_checkbox = gr.Checkbox(
                    label="Humanize AI response",
                    value=False,
                    info="Enable this to make the AI response sound more natural and conversational",
                )
                # Type selector (labels without a/b/c/d)
                fewshot_choices = gr.CheckboxGroup(
                    label="Type",
                    choices=[
                        "reason",
                        "framework",
                        "connection",
                        "result",
                    ],
                    value=["connection"],
                )
                with gr.Row():
                    ai_temp = gr.Slider(0.0, 1.5, value=0.7, step=0.05, label="AI temperature")
                    ai_top_p = gr.Slider(0.1, 1.0, value=1.0, step=0.05, label="AI top_p")
                human_temp = gr.Slider(0.0, 1.5, value=0.9, step=0.05, label="Humanization temperature")
                submit_button = gr.Button("Submit", variant="primary")
            with gr.Column():
                ai_output = gr.Textbox(
                    label="AI Response",
                    placeholder="AI response will appear here...",
                    lines=10,
                )
                short_summary_output = gr.Textbox(
                    label="Short Summary",
                    placeholder="A very short summary will appear here...",
                    lines=8,
                )
                humanized_output = gr.Textbox(
                    label="Humanized Response",
                    placeholder="Humanized response will appear here (when enabled)...",
                    lines=10,
                )

        # Submit/query interactions (original behavior)
        submit_button.click(
            fn=gradio_interface,
            inputs=[query_input, context_input, humanize_checkbox, fewshot_choices, ai_temp, ai_top_p, human_temp],
            outputs=[ai_output, humanized_output, short_summary_output],
        )
        query_input.submit(
            fn=gradio_interface,
            inputs=[query_input, context_input, humanize_checkbox, fewshot_choices, ai_temp, ai_top_p, human_temp],
            outputs=[ai_output, humanized_output, short_summary_output],
        )

        # Fill query from uploaded PDF (no labels)
        fill_button.click(
            fn=fill_query_from_pdf,
            inputs=[file_uploader],
            outputs=[query_input],
        )
        file_uploader.change(
            fn=fill_query_from_pdf,
            inputs=[file_uploader],
            outputs=[query_input],
        )

    return demo

if __name__ == "__main__":
    print("Starting Gradio Interface...")
    try:
        # Test API connection first
        print("Testing Nebius API connection...")
        test_response = call_nebius_api("Hello", temperature=0.1)
        if test_response.startswith("Error:"):
            print(f"API Test failed: {test_response}")
        else:
            print("API connection successful")
        
        demo = create_gradio_app()
        print("Gradio app created successfully")
        
        # Check if running on Hugging Face Spaces
        import os
        if os.environ.get("SPACE_ID"):
            print("Detected Hugging Face Spaces environment")
            # Hugging Face Spaces deployment - use environment variable for port
            server_port = int(os.environ.get("GRADIO_SERVER_PORT", 7860))
            print(f"Using port: {server_port}")
            demo.launch(
                server_name="0.0.0.0",
                server_port=server_port,
                share=False,
                debug=False,
                show_error=True,
            )
        else:
            print("Running in local environment")
            # Local deployment
            demo.launch(
                server_name="127.0.0.1",
                server_port=7870,
                share=True,
                debug=False,
                show_error=True,
                show_api=False,
            )
    except Exception as e:
        print(f"Error launching Gradio app: {e}")
        import traceback
        traceback.print_exc()
        # Fallback launch for Hugging Face Spaces
        try:
            print("Attempting fallback launch...")
            demo = create_gradio_app()
            demo.launch(
                server_name="0.0.0.0",
                server_port=7860,
                share=False,
                debug=False,
                show_error=True,
                inbrowser=False,
                prevent_thread_lock=True,
                show_api=False,
            )
        except Exception as fallback_e:
            print(f"Fallback launch also failed: {fallback_e}")
            traceback.print_exc()