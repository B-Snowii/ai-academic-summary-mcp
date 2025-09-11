[ En ](README.md) | [ 中文 ](README.zh-CN.md)

# AI Paper Summary Pilot

## Task
Produce around 25‑word academic summaries weekly for many papers, used in weekly Research alerts.

## Key Outcomes
- Time cost: Before over 40 hrs/week → After ≤2 hrs/week
- Quality assurance: Method/topic accuracy and consistent style
- Reusability: MCP pipeline + edits data

## Models & Pipeline
- Models: Deepseek‑R1, Llama‑3.1
- Pipeline: Topic/Method Identification → CoT → Draft → Constraint Checks → Style Rewrite → Self‑Scoring
- Related repo: https://github.com/B-Snowii/research-paper-summary

## Local Setup
git clone <your-repo-url>
cd ai-academic-summary-mcp
pip install -r requirements.txt
python app.py

## Usage
1. Upload a PDF to auto-fill the query
2. Choose analysis type and parameters
3. Submit to get paper summary

## License
MIT License
