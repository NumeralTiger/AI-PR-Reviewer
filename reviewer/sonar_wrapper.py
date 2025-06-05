import subprocess
import os
import requests
import time
import base64
from reviewer.config import SONAR_HOST_URL, SONAR_TOKEN, SONAR_PROJECT_KEY, SONAR_PROJECT_NAME

def run_sonar_scanner():
    # This requires 'sonar-scanner' to be on the system PATH
    # The 'shell=True' allows the command to be executed via the system shell (powershell )
    cmd_string = 'sonar-scanner -Dsonar.projectKey=NumeralTiger_AI-PR-Reviewer -Dsonar.sources=.' # Single string command
    print(f"Executing command via shell: {cmd_string}")

    try:
        # Popen is often more direct when shell=True for complex commands,
        # but subprocess.run can also work.
        result = subprocess.run(cmd_string, shell=True, capture_output=True, text=True, check=True)
        print("SonarScanner stdout:")
        print(result.stdout)
        if result.stderr:
            print("SonarScanner stderr:")
            print(result.stderr)
        print(f"SonarScanner finished with exit code: {result.returncode}")
    except subprocess.CalledProcessError as e:
        print(f"Error running SonarScanner: {e}")
        print(f"Command: {e.cmd}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
    except FileNotFoundError:
        print(f"Error: 'sonar-scanner' not found on system PATH when using shell=True.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def wait_for_sonar_analysis():
    """
    After triggering a scan, poll SonarQube API until the analysis report is available.
    """
    analysis_url = f"{SONAR_HOST_URL}/api/project_analyses/search?project={SONAR_PROJECT_KEY}"
    token = f"{SONAR_TOKEN}:".encode("utf-8")
    b64_token = base64.b64encode(token).decode("utf-8")
    headers = {"Authorization": f"Basic {b64_token}"}

    for _ in range(30):  # Poll up to ~30 times (adjust sleep as needed)
        resp = requests.get(analysis_url, headers=headers)
        if resp.status_code != 200:
            print(f"SonarQube API error: {resp.status_code} - {resp.text}")
            continue
        try:
            data = resp.json()
        except Exception as e:
            print(f"Failed to parse JSON: {e}, response text: {resp.text}")
            continue
        if data.get("analyses"):
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
    token = f"{SONAR_TOKEN}:".encode("utf-8")
    b64_token = base64.b64encode(token).decode("utf-8")
    headers = {"Authorization": f"Basic {b64_token}"}

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

if __name__ == "__main__":
    run_sonar_scanner()
    analysis_key = wait_for_sonar_analysis()
    metrics = fetch_sonar_metrics(analysis_key)
    print("Sonar metrics:", metrics)
