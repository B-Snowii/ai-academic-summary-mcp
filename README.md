---
title: AI Academic Paper Summarizer
emoji: 📚
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
---

# AI Paper Summary Pilot

A Gradio-based AI paper summarization tool that supports PDF upload, intelligent analysis, and humanized output.

## Features

* 📄 **PDF Document Processing**: Automatically extracts key information such as paper title, abstract, keywords, etc.
* 🤖 **AI Intelligent Analysis**: Uses Nebius API for deep paper analysis
* 💬 **Humanized Output**: Converts AI responses into more natural, conversational expressions
* 📊 **Multi-type Support**: Supports various analysis types including reason analysis, framework models, correlation analysis, and result summaries
* 💾 **History Management**: Saves conversation history with search and export capabilities
* 🎛️ **Parameter Adjustment**: Adjustable AI temperature and top_p parameters

## Tech Stack

* **Frontend**: Gradio
* **AI Models**: Meta-Llama-3.1-70B-Instruct, DeepSeek-R1
* **PDF Processing**: PyMuPDF
* **API**: Nebius AI

## Local Setup

1. **Clone the repository**:
```bash
git clone <your-repo-url>
cd agentic_Ai_humanizer_mcp
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Run the application**:
```bash
python app.py
```

4. **Access the app**: Open your browser and visit `http://127.0.0.1:7870`

## Usage Instructions

1. **Upload PDF**: Click "Upload a PDF" button to upload your paper file
2. **Auto-fill**: Click "Fill from PDF" to automatically extract paper content to the query box
3. **Select Type**: Choose appropriate analysis type (reason, framework, connection, result)
4. **Adjust Parameters**: Modify AI temperature and top_p parameters as needed
5. **Humanize**: Check "Humanize AI response" to get more natural output
6. **Submit Query**: Click "Submit" to start analysis

## Deployment

### Hugging Face Spaces

This project is configured to be deployed directly on Hugging Face Spaces.

### Local Deployment

Ensure all dependencies are installed, then run `python app.py`.

## API Configuration

The application uses Nebius AI API for processing. Make sure to configure your API keys in the application.

## License

MIT License

---

**license**: mit  
**language**: 
- en
- zh  
**base_model**:
- deepseek-ai/DeepSeek-R1
- meta-llama/Meta-Llama-3.1-70B-Instruct