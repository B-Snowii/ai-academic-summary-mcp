import gradio as gr
import requests
import json
import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# Nebius API configuration
NEBIUS_API_URL = os.getenv("NEBIUS_API_URL")
NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY")


# --- MCP Protocol Support ---
# This is a placeholder for MCP integration. In a real scenario, you would use the MCP protocol to wrap/unwrap requests and responses.
def mcp_supported_call(payload, endpoint, headers):
    # Here, you could add MCP-specific headers or payload structure if needed
    # For now, this just passes through to the Nebius API
    response = requests.post(endpoint, json=payload, headers=headers)
    return response


# Function to call Nebius API directly (now MCP supported)
def call_nebius_api(query, context_data=""):
    try:
        # Prepare payload for Nebius API
        nebius_payload = {
            "model": "meta-llama/Meta-Llama-3.1-70B-Instruct",
            "messages": [{"role": "user", "content": query}],
            "max_tokens": 1000,
            "temperature": 0.7,
        }

        # Call Nebius API
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


# Function to humanize AI text using another API call with a different model (now MCP supported)
def humanize_text(ai_response):
    try:
        humanize_prompt = f"""Please rewrite the following AI response to make it sound more natural, conversational, and human-like. 
        Add personality, use casual language where appropriate, include filler words occasionally, and make it feel like it's coming from a real person having a conversation:

        AI Response to humanize:
        {ai_response}

        Humanized version:"""

        # Use DeepSeek model for humanization - excellent at conversational and creative responses
        nebius_payload = {
            "model": "deepseek-ai/DeepSeek-R1",  # DeepSeek model for humanization
            "messages": [{"role": "user", "content": humanize_prompt}],
            "max_tokens": 1200,
            "temperature": 0.9,  # Higher temperature for more creative/human-like responses
        }

        headers = {
            "Authorization": f"Bearer {NEBIUS_API_KEY}",
            "Content-Type": "application/json",
        }
        response = mcp_supported_call(nebius_payload, NEBIUS_API_URL, headers)

        if response.status_code != 200:
            return ai_response  # Return original response if humanization fails

        nebius_response = response.json()
        humanized_result = (
            nebius_response.get("choices", [{}])[0]
            .get("message", {})
            .get("content", ai_response)
        )
        # Only return the humanized response, not the prompt or any instructions
        # Remove everything before the first line break if the model echoes the prompt or instructions
        if "Humanized version:" in humanized_result:
            humanized_result = humanized_result.split("Humanized version:", 1)[
                -1
            ].strip()
        # Remove any leading prompt/instruction lines (e.g., if model repeats the prompt or says what it's doing)
        lines = humanized_result.splitlines()
        # Remove lines that look like instructions or meta-comments
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
        # Join the remaining lines, strip leading/trailing whitespace
        cleaned = "\n".join(filtered_lines).strip()
        # If nothing left after cleaning, fall back to the original humanized_result
        return cleaned if cleaned else humanized_result

    except Exception as e:
        return ai_response  # Return original response if humanization fails


# --- Additional Functionality ---
def save_conversation(query, ai_response, humanized_response, context_data):
    """Save the conversation to a local file with timestamp."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("conversation_history.txt", "a", encoding="utf-8") as f:
        f.write(
            f"[{timestamp}]\nQuery: {query}\nContext: {context_data}\nAI Response: {ai_response}\nHumanized: {humanized_response}\n{'-' * 40}\n"
        )


def clear_history():
    """Clear the conversation history file."""
    open("conversation_history.txt", "w").close()
    return "History cleared."


def load_history():
    """Load the conversation history file."""
    try:
        with open("conversation_history.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "No history found."


# --- More Advanced Features ---
def export_history_to_file(filename="conversation_export.txt"):
    """Export the conversation history to a user-specified file."""
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
    """Search for a keyword in the conversation history."""
    try:
        with open("conversation_history.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
        matches = [line for line in lines if keyword.lower() in line.lower()]
        return "".join(matches) if matches else "No matches found."
    except FileNotFoundError:
        return "No history found."


def delete_last_conversation():
    """Delete the last conversation from the history file."""
    try:
        with open("conversation_history.txt", "r", encoding="utf-8") as f:
            content = f.read().strip().split("-" * 40)
        if len(content) > 1:
            content = content[:-1]  # Remove last conversation
            with open("conversation_history.txt", "w", encoding="utf-8") as f:
                f.write(("-" * 40).join(content).strip())
            return "Last conversation deleted."
        else:
            clear_history()
            return "History cleared."
    except FileNotFoundError:
        return "No history found."


# Gradio interface function
def gradio_interface(query, context_data, humanize=False, save=False):
    if not query.strip():
        return "Please enter a query.", "", load_history()

    # Get initial AI response
    ai_response = call_nebius_api(query, context_data)

    # If humanization is enabled and we got a valid response, humanize it
    if humanize and not ai_response.startswith("Error:"):
        humanized_response = humanize_text(ai_response)
    else:
        humanized_response = ""

    if save:
        save_conversation(query, ai_response, humanized_response, context_data)

    return ai_response, humanized_response, load_history()


# Create Gradio UI
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
        # Add event handlers for new features
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
            server_name="127.0.0.1",  # Changed to localhost only
            server_port=7870,  # Changed back to 7860 to avoid conflicts
            share=False,
            debug=True,
            show_error=True,
        )
    except Exception as e:
        print(f"Error launching Gradio app: {e}")
        import traceback

        traceback.print_exc()
