import os
from reviewer.config import GITHUB_TOKEN, GITHUB_API_URL, GITHUB_REPOSITORY
import requests

def post_review_comments(pr_number: int, comments: list):
    """
    For each comment dict in comments (with keys 'file_path', 'line', 'comment'),
    post a review comment to the given PR number.
    """
    url = f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/pulls/{pr_number}/comments"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    for c in comments:
        payload = {
            "body": c["comment"],
            "path": c["file_path"],
            "line": c["line"],
            "side": "RIGHT"   # Indicates we comment on the changed (new) code side
        }
        resp = requests.post(url, headers=headers, json=payload)
        if not resp.ok:
            print(f"Failed to post comment for {c['file_path']}:{c['line']}: {resp.status_code} {resp.text}")
        else:
            print(f"Posted comment on {c['file_path']}:{c['line']}")
