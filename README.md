# AI Paper Summary Pilot

一个基于Gradio的AI论文摘要工具，支持PDF上传、智能分析和人性化输出。

## 功能特性

- 📄 **PDF文档处理**: 自动提取论文标题、摘要、关键词等关键信息
- 🤖 **AI智能分析**: 使用Nebius API进行深度论文分析
- 💬 **人性化输出**: 将AI回复转换为更自然、对话式的表达
- 📊 **多类型支持**: 支持原因分析、框架模型、关联分析、结果总结等多种类型
- 💾 **历史记录**: 保存对话历史，支持搜索和导出
- 🎛️ **参数调节**: 可调节AI温度和top_p参数

## 技术栈

- **前端**: Gradio
- **AI模型**: Meta-Llama-3.1-70B-Instruct, DeepSeek-R1
- **PDF处理**: PyMuPDF
- **API**: Nebius AI

## 本地运行

1. 克隆仓库：
```bash
git clone <your-repo-url>
cd agentic_Ai_humanizer_mcp
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 运行应用：
```bash
python app.py
```

4. 访问应用：
打开浏览器访问 `http://127.0.0.1:7870`

## 使用说明

1. **上传PDF**: 点击"Upload a PDF"按钮上传论文文件
2. **自动填充**: 点击"Fill from PDF"自动提取论文内容到查询框
3. **选择类型**: 选择合适的分析类型（原因、框架、关联、结果）
4. **调节参数**: 根据需要调整AI温度和top_p参数
5. **人性化**: 勾选"Humanize AI response"获得更自然的输出
6. **提交查询**: 点击"Submit"开始分析

## 部署

### Hugging Face Spaces
本项目已配置为可在Hugging Face Spaces上直接部署。

### 本地部署
确保安装了所有依赖包，然后运行`python app.py`即可。

## 许可证

MIT License

---
license: mit
language:
- en
- zh
base_model:
- deepseek-ai/DeepSeek-R1
- meta-llama/Meta-Llama-3.1-70B-Instruct