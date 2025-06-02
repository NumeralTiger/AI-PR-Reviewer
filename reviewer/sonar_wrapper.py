import subprocess
import os
import requests
import time
from reviewer.config import SONAR_HOST_URL, SONAR_TOKEN, SONAR_PROJECT_KEY, SONAR_PROJECT_NAME

def run_sonar_scanner():
    """
    Use the official Sonar Scanner CLI to analyze the project.
    Requires:
      - sonar-scanner installed OR sonar-scanner CLI containerized in Docker.
      - sonar-project.properties configured in project root.
    """
    # If you installed sonar-scanner on the PATH:
    cmd = ["sonar-scanner", f"-Dsonar.login={SONAR_TOKEN}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Sonar Scanner failed:", result.stderr)
        raise RuntimeError("Sonar Scanner execution failed.")
    print("Sonar Scanner output:", result.stdout)

def wait_for_sonar_analysis():
    """
    After triggering a scan, poll SonarQube API until the analysis report is available.
    """
    analysis_url = f"{SONAR_HOST_URL}/api/project_analyses/search?project={SONAR_PROJECT_KEY}"
    headers = {"Authorization": f"Basic {SONAR_TOKEN}:"}  # SonarQube uses basic auth where token is user, blank password

    for _ in range(30):  # Poll up to ~30 times (adjust sleep as needed)
        resp = requests.get(analysis_url, headers=headers)
        data = resp.json()
        if data["analyses"]:
            # Latest analysis should be at index 0
            analysis_key = data["analyses"][0]["key"]
            return analysis_key
        time.sleep(5)

    raise TimeoutError("Timed out waiting for Sonar analysis.")

def fetch_sonar_metrics(analysis_key: str) -> dict:
    """
    Use SonarQube API to fetch measures for the given analysis key.
    For example: code smells, bugs, coverage, complexity.
    """
    metrics = ["bugs", "code_smells", "coverage", "duplicated_lines_density", "sqale_debt_ratio"]
    metric_str = ",".join(metrics)
    url = f"{SONAR_HOST_URL}/api/measures/component?component={SONAR_PROJECT_KEY}&metricKeys={metric_str}"
    headers = {"Authorization": f"Basic {SONAR_TOKEN}:"}

    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    measures = {m["metric"]: m["value"] for m in data["component"]["measures"]}
    return measures

def aggregate_results(llm_comments: list, sonar_metrics: dict, pr_number: int):
    """
    Combine LLM feedback summary with Sonar metrics into a Markdown report.
    Save to disk or return as a string.
    """
    report_lines = [
        f"# Automated Code Review Summary for PR #{pr_number}",
        "",
        "## LLM Feedback",
    ]
    if not llm_comments:
        report_lines.append("No actionable comments from LLM.")
    else:
        for idx, c in enumerate(llm_comments, start=1):
            report_lines.append(f"{idx}. **{c['file_path']}:{c['line']}** – {c['comment']}")
    report_lines += [
        "",
        "## SonarQube Metrics",
        "| Metric                 | Value |",
        "|------------------------|-------|"
    ]
    for metric, value in sonar_metrics.items():
        report_lines.append(f"| {metric} | {value} |")
    report = "\n".join(report_lines)

    # Write to file
    output_path = f"review_summary_pr_{pr_number}.md"
    with open(output_path, "w") as f:
        f.write(report)
    print(f"Generated summary report: {output_path}")
    return output_path
