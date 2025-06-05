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
    "You are an AI code reviewer. You will be given a git diff. Identify any obvious bugs or anti-patterns. "
    "Suggest improvements to variable names, docstrings, missing tests, misplaced API keys, or anything you "
    "find could be better done, excluding suggestions related to Javadoc style comments and the 'final' keyword. "
    "For each issue, output entries with: {'file_path': &lt;path>, 'line': &lt;line_number>, 'comment': &lt;advice>}."
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
        raise ValueError("OPENAI_API_KEY not configured.")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt_messages = build_prompt(diff_text)

    data = {
        "model": model,
        "messages": prompt_messages,
        "temperature": 0.2,
        "max_tokens": 800
    }

    response = requests.post(OPENAI_API_URL, headers=headers, json=data)
    response.raise_for_status()
    content = response.json()

    raw_reply = content.get("choices", [{}])[0].get("message", {}).get("content", "")
    comments = []
    if raw_reply:
        try:
            parsed_json = json.loads(raw_reply)
            if isinstance(parsed_json, list):
                comments = parsed_json
            elif isinstance(parsed_json, dict) and "comments" in parsed_json and isinstance(parsed_json["comments"], list):
                comments = parsed_json["comments"]
        except json.JSONDecodeError:
            pass
    return comments

def format_comments_to_markdown(llm_comments: list, raw_reply: str = None) -> str:
    """Formats LLM comments into a Markdown string. If no comments, includes raw LLM reply if available."""
    if llm_comments:
        report_lines = ["## LLM Feedback"]
        for idx, c in enumerate(llm_comments, start=1):
            file_path = c.get('file_path', 'N/A')
            line = c.get('line', 'N/A')
            comment_text = c.get('comment', 'No comment text.')
            report_lines.append(f"{idx}. **{file_path}:{line}** – {comment_text}")
        return "\n".join(report_lines)
    elif raw_reply and raw_reply.strip():
        return f"## LLM Feedback\nRaw LLM output (could not parse as JSON):\n\n{raw_reply.strip()}"
    else:
        return "## LLM Feedback\nNo actionable comments from LLM."

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get LLM feedback for a diff file.")
    parser.add_argument("--diff-file", required=True, help="Path to the diff file.")
    parser.add_argument("--output-file", required=True, help="Path to save the LLM feedback Markdown file.")
    parser.add_argument("--model", default="gpt-4", help="OpenAI model to use (e.g., gpt-3.5-turbo, gpt-4). Consider gpt-3.5-turbo for speed/cost if gpt-4 is not essential.")
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
        markdown_output = "## LLM Feedback\nDiff file was empty or contained only whitespace.\n"
    else:
        try:
            # --- Capture raw_reply from call_openai_llm ---
            raw_reply = None
            llm_comments = []
            try:
                # Patch: call_openai_llm returns both comments and raw_reply
                def call_and_capture(diff_text, model):
                    if not OPENAI_API_KEY:
                        raise ValueError("OPENAI_API_KEY not configured.")
                    headers = {
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    }
                    prompt_messages = build_prompt(diff_text)
                    data = {
                        "model": model,
                        "messages": prompt_messages,
                        "temperature": 0.2,
                        "max_tokens": 800
                    }
                    response = requests.post(OPENAI_API_URL, headers=headers, json=data)
                    response.raise_for_status()
                    content = response.json()
                    raw_reply = content.get("choices", [{}])[0].get("message", {}).get("content", "")
                    comments = []
                    if raw_reply:
                        try:
                            parsed_json = json.loads(raw_reply)
                            if isinstance(parsed_json, list):
                                comments = parsed_json
                            elif isinstance(parsed_json, dict) and "comments" in parsed_json and isinstance(parsed_json["comments"], list):
                                comments = parsed_json["comments"]
                        except json.JSONDecodeError:
                            pass
                    return comments, raw_reply
                llm_comments, raw_reply = call_and_capture(diff_text, model=args.model)
            except Exception:
                pass
            markdown_output = format_comments_to_markdown(llm_comments, raw_reply)
        except ValueError as e:
            print(f"Configuration Error: {e}")
            exit(1)
        except requests.exceptions.HTTPError as e:
            print(f"Error calling OpenAI API: {e.response.status_code} {e.response.text}")
            exit(1)
        except Exception as e:
            print(f"An unexpected error occurred during LLM call: {e}")
            exit(1)

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(args.output_file)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except OSError as e:
            print(f"Error creating output directory {output_dir}: {e}")
            exit(1)
    try:
        with open(args.output_file, "w", encoding="utf-8") as f:
            f.write(markdown_output)
    except Exception as e:
        print(f"Error writing output file: {e}")
        exit(1)