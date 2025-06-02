import json
import requests
from reviewer.config import OPENAI_API_KEY, OPENAI_API_URL

def build_prompt(diff_text: str) -> str:
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
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = build_prompt(diff_text)

    data = {
        "model": model,
        "messages": prompt,
        "temperature": 0.2,
        "max_tokens": 800
    }

    response = requests.post(OPENAI_API_URL, headers=headers, json=data)
    response.raise_for_status()
    content = response.json()

    # The LLM should return JSON in its reply. Extract `content["choices"][0]["message"]["content"]`.
    raw_reply = content["choices"][0]["message"]["content"]
    try:
        comments = json.loads(raw_reply)
    except json.JSONDecodeError:
        # If the model did not return valid JSON, you might attempt to recover with a simple parse or fallback.
        print("Warning: LLM did not return valid JSON. Raw reply:", raw_reply)
        comments = []
    return comments
