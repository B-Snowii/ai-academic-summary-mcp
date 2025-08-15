import gradio as gr
import requests
import json
import datetime
import os

# Nebius API configuration (hardcoded)
NEBIUS_API_URL = "https://api.studio.nebius.ai/v1/chat/completions"
NEBIUS_API_KEY = "eyJhbGciOiJIUzI1NiIsImtpZCI6IlV6SXJWd1h0dnprLVRvdzlLZWstc0M1akptWXBvX1VaVkxUZlpnMDRlOFUiLCJ0eXAiOiJKV1QifQ.eyJzdWIiOiJnb29nbGUtb2F1dGgyfDExMDkwNDYwNzI2NjMxOTY2NDYyMSIsInNjb3BlIjoib3BlbmlkIG9mZmxpbmVfYWNjZXNzIiwiaXNzIjoiYXBpX2tleV9pc3N1ZXIiLCJhdWQiOlsiaHR0cHM6Ly9uZWJpdXMtaW5mZXJlbmNlLmV1LmF1dGgwLmNvbS9hcGkvdjIvIl0sImV4cCI6MTkwNjc4ODk3OSwidXVpZCI6IjBiMDc5OGI4LTdkZjctNDcxMi05ZTY0LTZiNmU5OTk0OWRmNyIsIm5hbWUiOiJNQ1AgU0VSVkVSIiwiZXhwaXJlc19hdCI6IjIwMzAtMDYtMDRUMDc6MzY6MTkrMDAwMCJ9.-RG1eCxfuO9bqmTa00pHCAb6L47IWEFHVxq3xqHrjU8"

# --- MCP Protocol Support ---
def mcp_supported_call(payload, endpoint, headers):
    response = requests.post(endpoint, json=payload, headers=headers)
    return response

def call_nebius_api(query, context_data=""):
    try:
        nebius_payload = {
            "model": "meta-llama/Meta-Llama-3.1-70B-Instruct",
            "messages": [{"role": "user", "content": query}],
            "max_tokens": 1000,
            "temperature": 0.7,
        }
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

def humanize_text(ai_response):
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
            "temperature": 0.9,
        }
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

def gradio_interface(query, context_data, humanize=False, save=False):
    if not query.strip():
        return "Please enter a query.", "", load_history()
    ai_response = call_nebius_api(query, context_data)
    if humanize and not ai_response.startswith("Error:"):
        humanized_response = humanize_text(ai_response)
    else:
        humanized_response = ""
    if save:
        save_conversation(query, ai_response, humanized_response, context_data)
    return ai_response, humanized_response, load_history()

def create_gradio_app():
    with gr.Blocks() as demo:
        gr.Markdown("# MCP-Powered Chatbot with Nebius API & Text Humanization")
        with gr.Row():
            with gr.Column():
                query_input = gr.Textbox(
                    label="Enter your query", placeholder="Ask me anything...", lines=2
                )
                context_input = gr.Textbox(
                    label="Optional context data",
                    placeholder="Enter additional context (optional)",
                    lines=2,
                )
                humanize_checkbox = gr.Checkbox(
                    label="Humanize AI response",
                    value=False,
                    info="Enable this to make the AI response sound more natural and conversational",
                )
                save_checkbox = gr.Checkbox(label="Save this conversation", value=False)
                search_input = gr.Textbox(
                    label="Search History",
                    placeholder="Enter keyword to search history",
                    lines=1,
                )
                submit_button = gr.Button("Submit", variant="primary")
                clear_button = gr.Button("Clear History", variant="secondary")
                export_button = gr.Button("Export History", variant="secondary")
                delete_last_button = gr.Button(
                    "Delete Last Conversation", variant="secondary"
                )
            with gr.Column():
                ai_output = gr.Textbox(
                    label="AI Response",
                    placeholder="AI response will appear here...",
                    lines=10,
                )
                humanized_output = gr.Textbox(
                    label="Humanized Response",
                    placeholder="Humanized response will appear here (when enabled)...",
                    lines=10,
                )
                history_box = gr.Textbox(
                    label="Conversation History",
                    value=load_history(),
                    lines=15,
                    interactive=False,
                )
                search_result = gr.Textbox(
                    label="Search Results", value="", lines=5, interactive=False
                )
        submit_button.click(
            fn=gradio_interface,
            inputs=[query_input, context_input, humanize_checkbox, save_checkbox],
            outputs=[ai_output, humanized_output, history_box],
        )
        clear_button.click(
            fn=lambda: ("", "", clear_history()),
            inputs=[],
            outputs=[ai_output, humanized_output, history_box],
        )
        export_button.click(
            fn=lambda: ("", "", export_history_to_file()),
            inputs=[],
            outputs=[ai_output, humanized_output, history_box],
        )
        delete_last_button.click(
            fn=lambda: ("", "", delete_last_conversation()),
            inputs=[],
            outputs=[ai_output, humanized_output, history_box],
        )

        def do_search(keyword):
            return search_history(keyword)

        search_input.submit(
            fn=do_search,
            inputs=[search_input],
            outputs=[search_result],
        )
        query_input.submit(
            fn=gradio_interface,
            inputs=[query_input, context_input, humanize_checkbox, save_checkbox],
            outputs=[ai_output, humanized_output, history_box],
        )

    return demo

if __name__ == "__main__":
    print("Starting Gradio Interface...")
    try:
        demo = create_gradio_app()
        print("Gradio app created successfully")
        demo.launch(
            server_name="127.0.0.1",
            server_port=7870,
            share=False,
            debug=True,
            show_error=True,
        )
    except Exception as e:
        print(f"Error launching Gradio app: {e}")
        import traceback
        traceback.print_exc()