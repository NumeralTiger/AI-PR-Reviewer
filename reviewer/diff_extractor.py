import os
import subprocess
import json

def get_pr_info():
    """
    GitHub Actions exposes certain environment variables for the current PR:
      - GITHUB_EVENT_PATH: path to a JSON file describing the webhook event.
    We can parse that to get PR number, base SHA, head SHA, etc.
    """
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path:
        raise RuntimeError("GITHUB_EVENT_PATH not set in environment.")

    with open(event_path, "r") as f:
        event_data = json.load(f)

    # Extract relevant info
    pr_number = event_data["pull_request"]["number"]
    base_sha = event_data["pull_request"]["base"]["sha"]
    head_sha = event_data["pull_request"]["head"]["sha"]
    repo_full_name = event_data["repository"]["full_name"]
    return {
        "pr_number": pr_number,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "repo_full_name": repo_full_name
    }

def checkout_pr_branch():
    pass

def extract_diff():
    """
    Use `git diff` to get only the changed lines between base and head.
    Returns a dict mapping file paths to lists of changed line ranges or snippets.
    """
    info = get_pr_info()
    base_sha = info["base_sha"]
    head_sha = info["head_sha"]

    # Fetch the base
    subprocess.run(["git", "fetch", "origin", base_sha], check=True)
    # Now generate diff. `-U0` means “0 lines of context” – only show changed lines.
    result = subprocess.run(
        ["git", "diff", f"{base_sha}..{head_sha}", "-U0"], 
        stdout=subprocess.PIPE,
        check=True,
        universal_newlines=True
    )
    diff_text = result.stdout  # This is a unified diff string

    # For simplicity, we’ll just return raw diff_text. The LLM can parse it.
    return diff_text
