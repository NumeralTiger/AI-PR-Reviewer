import json
import requests
from reviewer.config import OPENAI_API_KEY, OPENAI_API_URL
import argparse
import os

def build_prompt(diff_text: str, sonar_issues: list = None) -> list:
    """
    Constructs a prompt for the LLM, including git diff and optional SonarQube issues.
    """
    system_messages = [
        "You are an expert AI code reviewer, acting like a senior developer.",
        "You will be given a git diff and a list of issues reported by SonarQube (if available).",
        "Your primary goal is to provide comprehensive feedback on the code changes in the diff.",
        "Consider the SonarQube issues as high-priority items. You should:",
        "  - Confirm, elaborate on, or suggest specific fixes for these SonarQube issues within the context of the diff.",
        "  - If you believe a SonarQube issue might be a false positive or not critical in this specific context, explain your reasoning.",
        "Beyond SonarQube's findings, provide your own insights on:",
        "  - Potential bugs, anti-patterns, and security vulnerabilities.",
        "  - Best practices regarding code clarity, maintainability, and performance.",
        "  - Suggestions for better variable names, function signatures, docstrings, and comments.",
        "  - Missing test cases or areas where testing could be improved.",
        "  - Misplaced API keys or other sensitive data.",
        "Be concise and actionable. Focus on the changes presented in the diff include what lines are problematic and are in which file.",
        "You must return a single JSON array. Do NOT return a dictionary, wrapped object, or plain object. The response must be a single array like: [{...}, {...}]."
        "Each comment object must have the following keys: 'file_path' (string, path from the diff), 'line' (integer, relevant line number from the diff), and 'comment' (string, your detailed feedback).",
        "If a comment is general to the diff and not a specific line, use 'line': 0 or omit it.",
        "If no specific issues are found, return an empty array []."
    ]
    system_msg = "\n".join(system_messages)

    user_content_parts = [f"Here is the git diff:\n```diff\n{diff_text}\n```"]

    if sonar_issues:
        user_content_parts.append("\nHere are the SonarQube issues reported for the project (consider these in your review of the diff):")
        if not sonar_issues: # Handles case where sonar_issues list is explicitly passed but empty
            user_content_parts.append("No SonarQube issues were provided or found.")
        else:
            for issue in sonar_issues[:20]: # Limit to avoid excessive prompt length, prioritize first N issues
                user_content_parts.append(
                    f"- File: {issue.get('file_path', 'N/A')}, Line: {issue.get('line', 'N/A')}, Type: {issue.get('type', 'N/A')}, Severity: {issue.get('severity', 'N/A')}, Message: {issue.get('message', 'N/A')}"
                )
            if len(sonar_issues) > 20:
                user_content_parts.append(f"...and {len(sonar_issues) - 20} more SonarQube issues not listed here.")
    else:
        user_content_parts.append("\nNo SonarQube issues were provided for this review.")

    user_msg = "\n".join(user_content_parts)
    
    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg}
    ]


def call_openai_llm(diff_text: str, sonar_issues: list = None, model: str = "gpt-4o") -> tuple[list, str]: # Changed default model to "gpt-4o"
    """
    Sends the constructed prompt to OpenAI’s Chat API.
    Returns a tuple: (list of comment dicts, raw_reply_text)
    """
    if not OPENAI_API_KEY or OPENAI_API_KEY == "nbhb5b23SFEWN": # Check for placeholder
        error_msg = "Error: OPENAI_API_KEY is not configured or is a placeholder. Please set it in your .env file or environment variables."
        print(error_msg)
        raise ValueError(error_msg)

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt_messages = build_prompt(diff_text, sonar_issues)

    estimated_prompt_size = len(json.dumps(prompt_messages))
    if estimated_prompt_size > 120000 and "gpt-4o" in model: # gpt-4o typically has 128k context
        print(f"Warning: Prompt size ({estimated_prompt_size} chars) is very large even for {model}. Consider truncating if issues arise.")
    elif estimated_prompt_size > 15000 and "gpt-3.5-turbo" in model: # gpt-3.5-turbo context window is often 4k or 16k tokens 
        print(f"Warning: Prompt size ({estimated_prompt_size} chars) might be too large for {model}. Consider truncating diff or Sonar issues.")

    data = {
        "model": model,
        "messages": prompt_messages,
        "temperature": 0.2,
        "max_tokens": 2000,  # Increased max_tokens for potentially more detailed JSON output
        "response_format": {"type": "json_object"} # This should now work with gpt-4o
    }

    print(f"Sending request to OpenAI API with model {model}. Prompt (first 200 chars of user message): {prompt_messages[1]['content'][:200]}...")

    comments = []
    raw_reply = ""
    try:
        response = requests.post(OPENAI_API_URL, headers=headers, json=data, timeout=180) # Increased timeout
        response.raise_for_status()
        content = response.json()
        raw_reply = content.get("choices", [{}])[0].get("message", {}).get("content", "")

        if raw_reply:
            print(f"Raw LLM reply (first 200 chars): {raw_reply[:200]}")
            try:
                parsed_json_data = json.loads(raw_reply)

                # Normalize to array
                if isinstance(parsed_json_data, list):
                    comments = parsed_json_data

                elif isinstance(parsed_json_data, dict):
                    # Try to unwrap known keys
                    for key in ["comments", "review_comments", "feedback", "issues"]:
                        if key in parsed_json_data and isinstance(parsed_json_data[key], list):
                            comments = parsed_json_data[key]
                            break
                    else:
                        # Single comment object – wrap into list
                        if all(k in parsed_json_data for k in ['file_path', 'line', 'comment']):
                            print("Info: LLM returned a single comment object. Wrapping it into a list.")
                            comments = [parsed_json_data]
                        else:
                            print(f"Warning: LLM returned a JSON object, but it was not in a known format. Raw: {raw_reply[:300]}")

                else:
                    print(f"Warning: LLM reply was valid JSON but not a list or expected dict structure. Raw: {raw_reply[:300]}")

            except json.JSONDecodeError:
                print(f"Error: Could not parse LLM reply as JSON. Raw reply (first 300 chars): {raw_reply[:300]}")

        else:
            print("LLM returned an empty reply.")
            
    except requests.exceptions.Timeout:
        error_msg = f"Timeout error calling OpenAI API after {data.get('timeout', 180)} seconds."
        print(error_msg)
        raw_reply = f'{{"error": "{error_msg}"}}' # Provide raw_reply with error
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP error calling OpenAI API: {e.response.status_code} {e.response.text}"
        print(error_msg)
        raw_reply = f'{{"error": "{error_msg}", "status_code": {e.response.status_code}}}' # Provide raw_reply with error
    except Exception as e:
        error_msg = f"An unexpected error occurred during LLM call: {e}"
        print(error_msg)
        raw_reply = f'{{"error": "{error_msg}"}}' # Provide raw_reply with error

    valid_comments = []
    if isinstance(comments, list):
        for c in comments:
            if isinstance(c, dict) and 'comment' in c:
                if 'file_path' not in c: c['file_path'] = "General"
                if 'line' not in c: c['line'] = 0 # Default line for general comments on a file or diff
                valid_comments.append(c)
            else:
                print(f"Warning: Discarding malformed comment object: {c}")
    else:
        print(f"Warning: Parsed comments from LLM was not a list. Received: {comments}")

    return valid_comments, raw_reply

def format_llm_feedback_to_markdown(llm_comments: list, raw_llm_reply: str = None) -> str:
    """Formats LLM comments into a Markdown string. If no comments, includes raw LLM reply if available."""
    report_lines = ["## LLM Feedback"]
    if llm_comments:
        for idx, c in enumerate(llm_comments, start=1):
            file_path = c.get('file_path', 'N/A')
            line = c.get('line', 'N/A')
            line_display = str(line) if line is not None else 'N/A'
            comment_text = c.get('comment', 'No comment text.')
            report_lines.append(f"{idx}. **{file_path}:{line_display}** – {comment_text}")
    elif raw_llm_reply and raw_llm_reply.strip() and "error" in raw_llm_reply.lower() : # Check if raw_reply indicates an error
        report_lines.append(f"Could not get feedback from LLM. Error details:")
        try:
            error_details = json.loads(raw_llm_reply)
            report_lines.append(f"```json\n{json.dumps(error_details, indent=2)}\n```")
        except json.JSONDecodeError:
            report_lines.append(f"Raw error output:\n```\n{raw_llm_reply.strip()}\n```")
    elif raw_llm_reply and raw_llm_reply.strip() and raw_llm_reply != "[]": # Non-error, but unparseable or unexpected content
        report_lines.append(f"LLM produced a response, but it could not be parsed into actionable comments or was empty.")
        report_lines.append(f"Raw LLM output (first 500 chars):\n```\n{raw_llm_reply.strip()[:500]}\n```")
    else:
        report_lines.append("No actionable comments or feedback received from LLM.")
    return "\n".join(report_lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get LLM feedback for a diff file, optionally with SonarQube issues.")
    parser.add_argument("--diff-file", required=True, help="Path to the diff file.")
    parser.add_argument("--output-file", required=True, help="Path to save the LLM feedback Markdown file.")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model to use (e.g., gpt-4o, gpt-3.5-turbo).") # Changed default model here too
    parser.add_argument("--sonar-issues-file", help="Path to a JSON file containing SonarQube issues (optional).")
    args = parser.parse_args()

    if not OPENAI_API_KEY or OPENAI_API_KEY == "nbhb5b23SFEWN":
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

    sonar_issues_list = None
    if args.sonar_issues_file:
        try:
            with open(args.sonar_issues_file, "r", encoding="utf-8") as f:
                sonar_issues_list = json.load(f)
            print(f"Loaded {len(sonar_issues_list)} SonarQube issues from {args.sonar_issues_file}")
        except FileNotFoundError:
            print(f"Warning: Sonar issues file not found at {args.sonar_issues_file}")
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from Sonar issues file {args.sonar_issues_file}")
        except Exception as e:
            print(f"Warning: Error reading Sonar issues file {args.sonar_issues_file}: {e}")

    markdown_output = "## LLM Feedback\nAn unexpected error occurred before calling the LLM."
    if not diff_text.strip():
        markdown_output = "## LLM Feedback\nDiff file was empty or contained only whitespace.\n"
    else:
        try:
            llm_comments, raw_llm_reply_text = call_openai_llm(diff_text, sonar_issues_list, model=args.model)
            markdown_output = format_llm_feedback_to_markdown(llm_comments, raw_llm_reply_text)
        except ValueError as e: # Configuration error from call_openai_llm
            print(f"Configuration Error: {e}")
            markdown_output = f"## LLM Feedback\nConfiguration Error: {e}"

    output_dir = os.path.dirname(args.output_file)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except OSError as e:
            print(f"Error creating output directory {output_dir}: {e}")
    try:
        with open(args.output_file, "w", encoding="utf-8") as f:
            f.write(markdown_output)
        print(f"LLM feedback written to: {args.output_file}")
    except Exception as e:
        print(f"Error writing output file: {e}")
        exit(1)