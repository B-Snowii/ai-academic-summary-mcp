# AI Paper Summary Pilot

## Task
Produce around 25‑word academic summaries weekly for many papers, used in weekly Research alerts. See the exploration history in `research-paper-summary`.

## Key Outcomes
- Time cost: Before over 40 hrs/week → After ≤2 hrs/week
- Quality assurance: Method/topic accuracy and consistent style
- Reusability: MCP pipeline + edits data

## Models & Pipeline
- Models: Deepseek‑R1, Llama‑3.1
- Pipeline: Topic/Method Identification → CoT → Draft → Constraint Checks → Style Rewrite → Self‑Scoring
- Related repo: `research-paper-summary` (prior attempts before this MCP) — https://github.com/B-Snowii/research-paper-summary

## Local Setup
```bash
git clone <your-repo-url>
cd agentic_Ai_humanizer_mcp
pip install -r requirements.txt
python app.py
```

## Usage
1) Upload a PDF to auto-fill the query
2) Choose analysis type and parameters
3) Submit to get paper summary

## License
MIT License

# 学术论文摘要工具

## 任务
每周针对多篇论文产出约 25 词的学术摘要，用于 weekly Research alert。前序探索见 `research-paper-summary` 仓库。

## 核心成果
- 任务花费时间：由每周 40+ 小时降至 ≤ 2 小时
- 质量保障：方法/主题准确、风格一致
- 可复用：MCP 流程化 + 历史修改过程数据

## 模型与流程
- 模型：Deepseek‑R1、Llama‑3.1
- 流水线：主题/方法识别 → CoT → 草案 → 约束核查 → 风格重写 → 自评打分
- 相关仓库：`research-paper-summary`（该 MCP 之前的所有尝试）— https://github.com/B-Snowii/research-paper-summary

## 本地运行
```bash
git clone <your-repo-url>
cd agentic_Ai_humanizer_mcp
pip install -r requirements.txt
python app.py
```

## 使用说明
1）上传 PDF 自动填充查询
2）选择分析类型与参数
3）提交并获取论文总结

## 许可证
MIT License
