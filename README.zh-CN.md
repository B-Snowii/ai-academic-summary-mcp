[ 英文 ](README.md) | [ 中文 ](README.zh-CN.md)

# 学术论文摘要 · MCP 流程

## 任务
每周针对多篇论文产出约 25 词的学术摘要，用于 weekly Research alert。

## 核心成果
- 时间成本：每周 40+ 小时 → ≤ 2 小时
- 质量保障：方法/主题准确、风格一致
- 可复用：MCP 流程化 + 历史修改数据

## 模型与流程
- 模型：Deepseek‑R1、Llama‑3.1
- 流水线：主题/方法识别 → CoT → 草案 → 约束核查 → 风格重写 → 自评打分
- 相关仓库：https://github.com/B-Snowii/research-paper-summary

## 本地运行
git clone <your-repo-url>
cd ai-academic-summary-mcp
pip install -r requirements.txt
python app.py

## 使用说明
1）上传 PDF 自动填充查询  2）选择分析类型与参数  3）提交并获取摘要

## 许可证
MIT License
