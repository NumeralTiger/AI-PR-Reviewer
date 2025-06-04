import json
import requests
from reviewer.config import OPENAI_API_KEY, OPENAI_API_URL
import argparse # Added
import os # Added

def build_prompt(diff_text: str) -> list: # Return type annotation changed to list
    """
    Construct a few-shot + instruction prompt to send to the LLM.
    We give it context: “Below is a git diff. Provide high-level feedback, point out obvious bugs,
    suggest better variable names, docstrings, or missing tests. Be concise, and return JSON
    with a list of comments, each containing: file_path, line_number, comment_text.”
    """
    system_msg = (
        "You are an AI code reviewer. You will be given a git diff. "
        "Identify any obvious bugs or anti-patterns. Suggest improvements to variable names, "
        "docstrings, or missing tests. For each issue, output JSON entries with: "
        "{'file_path': <path>, 'line': <line_number>, 'comment': <advice>}."
        " The entire response should be a single JSON array of these objects."
    )
    user_msg = f"Here is the diff:\n```\n{diff_text}\n```"
    # Depending on token limits, you might truncate or chunk the diff.
    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg}
    ]

def call_openai_llm(diff_text: str, model: str = "gpt-4") -> list:
    """
    Sends the constructed prompt to OpenAI’s Chat API.
    Returns a list of comment dicts: [{'file_path': ..., 'line': ..., 'comment': ...}, ...]
    """
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY is not set. Please check your .env file or environment variables.")
        # Consider raising an error or returning empty list based on desired handling
        raise ValueError("OPENAI_API_KEY not configured.")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt_messages = build_prompt(diff_text) # Renamed for clarity

    data = {
        "model": model,
        "messages": prompt_messages,
        "temperature": 0.2,
        "max_tokens": 800,
        "response_format": {"type": "json_object"} # Recommended for reliable JSON output if model supports
    }

    print(f"Calling OpenAI API with model: {model}...")
    response = requests.post(OPENAI_API_URL, headers=headers, json=data)
    response.raise_for_status() # Will raise an HTTPError for bad responses (4xx or 5xx)
    content = response.json()

    raw_reply = content.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    comments = []
    if raw_reply:
        try:
            # The prompt guides the LLM to return a list of JSON objects.
            # If response_format: {"type": "json_object"} is used and the prompt is clear,
            # the LLM might return a JSON object like {"comments": [...]}. Adjust parsing if so.
            # For now, assuming raw_reply is a string that IS the JSON array.
            parsed_json = json.loads(raw_reply)
            if isinstance(parsed_json, list):
                 comments = parsed_json
            # If the LLM wraps the list in a dictionary (e.g. {"comments": [...]})
            elif isinstance(parsed_json, dict) and "comments" in parsed_json and isinstance(parsed_json["comments"], list):
                comments = parsed_json["comments"]
            else:
                print(f"Warning: LLM returned JSON but not in the expected list format. Raw reply: {raw_reply}")
        except json.JSONDecodeError:
            print(f"Warning: LLM did not return valid JSON. Raw reply: {raw_reply}")
    else:
        print("Warning: Received an empty reply from LLM.")
        
    return comments

def format_comments_to_markdown(llm_comments: list) -> str:
    """Formats LLM comments into a Markdown string."""
    if not llm_comments:
        return "## LLM Feedback\nNo actionable comments from LLM."

    report_lines = ["## LLM Feedback"]
    for idx, c in enumerate(llm_comments, start=1):
        file_path = c.get('file_path', 'N/A')
        line = c.get('line', 'N/A')
        comment_text = c.get('comment', 'No comment text.')
        report_lines.append(f"{idx}. **{file_path}:{line}** – {comment_text}")
    return "\n".join(report_lines)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get LLM feedback for a diff file.")
    parser.add_argument("--diff-file", required=True, help="Path to the diff file.")
    parser.add_argument("--output-file", required=True, help="Path to save the LLM feedback Markdown file.")
    parser.add_argument("--model", default="gpt-3.5-turbo", help="OpenAI model to use (e.g., gpt-3.5-turbo, gpt-4). Consider gpt-3.5-turbo for speed/cost if gpt-4 is not essential.")
    args = parser.parse_args()

    if not OPENAI_API_KEY or OPENAI_API_KEY == "nbhb5b23SFEWN": # Double check config
        print("Error: OPENAI_API_KEY is not set or is still a placeholder.")
        print("Please set it in your .env file or as an environment variable.")
        exit(1)

    try:
        with open(args.diff_file, "r", encoding="utf-8") as f:
            diff_text = f.read()
    except FileNotFoundError:
        print(f"Error: Diff file not found at {args.diff_file}")
        exit(1)
    except Exception as e:
        print(f"Error reading diff file: {e}")
        exit(1)

    if not diff_text.strip():
        print(f"Warning: The diff file {args.diff_file} is empty or contains only whitespace.")
        markdown_output = "## LLM Feedback\nDiff file was empty or contained only whitespace.\n"
    else:
        print(f"Sending diff from {args.diff_file} to LLM (model: {args.model})...")
        try:
            llm_comments = call_openai_llm(diff_text, model=args.model)
            markdown_output = format_comments_to_markdown(llm_comments)
        except ValueError as e: # Catch specific error for API key
            print(f"Configuration Error: {e}")
            exit(1)
        except requests.exceptions.HTTPError as e:
            print(f"Error calling OpenAI API: {e.response.status_code} {e.response.text}")
            # Optionally write error to output file or just exit
            exit(1)
        except Exception as e:
            print(f"An unexpected error occurred during LLM call: {e}")
            exit(1)

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(args.output_file)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")
        except OSError as e:
            print(f"Error creating output directory {output_dir}: {e}")
            exit(1)
    
    try:
        with open(args.output_file, "w", encoding="utf-8") as f:
            f.write(markdown_output)
        print(f"LLM feedback saved to {args.output_file}")
    except Exception as e:
        print(f"Error writing output file: {e}")
        exit(1)