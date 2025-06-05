import subprocess
import os
import requests
import time
import base64
from reviewer.config import SONAR_HOST_URL, SONAR_TOKEN, SONAR_PROJECT_KEY, SONAR_PROJECT_NAME #

def run_sonar_scanner():
    # This requires 'sonar-scanner' to be on the system PATH
    # The 'shell=True' allows the command to be executed via the system shell
    # It uses SONAR_PROJECT_KEY from config which should align with sonar-project.properties or override it.
    cmd_string = f'sonar-scanner -Dsonar.projectKey={SONAR_PROJECT_KEY} -Dsonar.sources=. -Dsonar.host.url={SONAR_HOST_URL} -Dsonar.login={SONAR_TOKEN}' #
    print(f"Executing command via shell: {cmd_string}")

    try:
        result = subprocess.run(cmd_string, shell=True, capture_output=True, text=True, check=True, encoding='utf-8')
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
        raise RuntimeError(f"SonarScanner execution failed. Stderr: {e.stderr}") from e
    except FileNotFoundError:
        print(f"Error: 'sonar-scanner' not found on system PATH when using shell=True.")
        raise FileNotFoundError("'sonar-scanner' not found. Please ensure it is installed and in PATH.")
    except Exception as e:
        print(f"An unexpected error occurred during SonarScanner execution: {e}")
        raise RuntimeError(f"An unexpected error occurred during SonarScanner: {e}") from e

def wait_for_sonar_analysis():
    """
    After triggering a scan, poll SonarQube API until the analysis report is available.
    This function retrieves the analysis key of the *latest* completed analysis for the project.
    """
    # Constructing the URL to search for project analyses
    # Typically, SonarCloud tasks are associated with branches or pull requests.
    # For a generic desktop tool, getting the latest analysis for the main branch might be the default.
    # The API endpoint /api/project_analyses/search is correct for finding analysis keys.
    # It's important that SONAR_PROJECT_KEY correctly identifies the project in SonarQube.
    analysis_url = f"{SONAR_HOST_URL}/api/project_analyses/search?project={SONAR_PROJECT_KEY}" #
    # Authentication: SonarQube uses a token. The token should be passed in the username field for Basic Auth.
    # The colon at the end of the token is important: "YOUR_TOKEN:"
    auth_string = f"{SONAR_TOKEN}:".encode('utf-8') #
    headers = {
        "Authorization": f"Basic {base64.b64encode(auth_string).decode('utf-8')}" #
    }

    print(f"Polling for SonarQube analysis completion for project: {SONAR_PROJECT_KEY}...") #
    # Increased polling attempts and timeout for potentially larger projects
    for attempt in range(60):  # Poll for up to 5 minutes (60 attempts * 5 seconds)
        try:
            resp = requests.get(analysis_url, headers=headers, timeout=10) # Added timeout
            resp.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            data = resp.json()

            if data.get("analyses") and len(data["analyses"]) > 0:
                # Assuming the first analysis in the list is the most recent one.
                # SonarQube API usually returns analyses sorted by date in descending order.
                latest_analysis = data["analyses"][0]
                analysis_key = latest_analysis["key"] #
                # Optional: Check if the analysis status is 'SUCCESS'.
                # Some analyses might be 'PENDING', 'FAILED', or 'IN_PROGRESS'.
                # The 'status' field might not be directly in this response,
                # but in /api/ce/task?id= (requires task id from scanner output or another call)
                # For simplicity, we assume if an analysis key is present, it's usable.
                print(f"SonarQube analysis found. Analysis Key: {analysis_key}")
                return analysis_key
        except requests.exceptions.Timeout:
            print(f"Attempt {attempt + 1}: Timeout while polling SonarQube.")
        except requests.exceptions.HTTPError as e:
            print(f"Attempt {attempt + 1}: SonarQube API HTTP error: {e.response.status_code} - {e.response.text}")
            # Depending on the error (e.g., 401 Unauthorized), retrying might not help.
            if e.response.status_code == 401:
                raise RuntimeError("SonarQube authentication failed. Check SONAR_TOKEN.") from e #
            # For other errors, we continue polling.
        except requests.exceptions.RequestException as e: # Catch other network/request errors
            print(f"Attempt {attempt + 1}: Error communicating with SonarQube API: {e}")
        except ValueError as e: # Catch JSON decoding errors
             print(f"Attempt {attempt + 1}: Failed to parse JSON response from SonarQube: {e}. Response text: {resp.text if 'resp' in locals() else 'N/A'}")
        
        time.sleep(5) # Wait before the next poll

    raise TimeoutError(f"Timed out waiting for SonarQube analysis for project {SONAR_PROJECT_KEY}.") #


def fetch_sonar_issues(project_key: str) -> list:
    """
    Fetches all open issues (bugs, vulnerabilities, code smells) for the given SonarQube project.
    """
    issues_url = f"{SONAR_HOST_URL}/api/issues/search" #
    auth_string = f"{SONAR_TOKEN}:".encode('utf-8') #
    headers = {"Authorization": f"Basic {base64.b64encode(auth_string).decode('utf-8')}"}
    
    all_issues = []
    page_index = 1
    page_size = 100 # Max 500 allowed by SonarQube API, using 100 for safety

    params = {
        "componentKeys": project_key,
        "resolved": "false", # Fetch only unresolved issues
        "ps": page_size,
        "p": page_index
        # Optional: Add filters like 'types' (BUG,VULNERABILITY,CODE_SMELL), 'severities'
        # "types": "BUG,VULNERABILITY,CODE_SMELL",
    }
    
    print(f"Fetching SonarQube issues for project: {project_key}...")

    while True:
        try:
            params["p"] = page_index
            resp = requests.get(issues_url, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            current_issues = data.get("issues", [])
            if not current_issues:
                break # No more issues

            for issue in current_issues:
                all_issues.append({
                    "file_path": issue.get("component", "").split(':')[-1], # Gets path relative to project
                    "line": issue.get("line"),
                    "message": issue.get("message"),
                    "severity": issue.get("severity"),
                    "type": issue.get("type")
                })
            
            total_fetched = page_index * page_size
            total_available = data.get("total", 0)
            if total_fetched >= total_available:
                break # Fetched all available issues
            
            page_index += 1
            if page_index > 100: # Safety break for very large number of issues (100 pages * 100 issues/page = 10,000 issues)
                print("Warning: Reached maximum page limit (100) for fetching SonarQube issues.")
                break
            time.sleep(0.5) # Brief pause to be nice to the API

        except requests.exceptions.Timeout:
            print(f"Timeout while fetching page {page_index} of SonarQube issues.")
            break # Or implement retry logic
        except requests.exceptions.HTTPError as e:
            print(f"SonarQube API HTTP error while fetching issues: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 401:
                 raise RuntimeError("SonarQube authentication failed. Check SONAR_TOKEN.") from e #
            break # Stop fetching on error
        except requests.exceptions.RequestException as e:
            print(f"Error communicating with SonarQube API for issues: {e}")
            break
        except ValueError as e: # JSON decoding error
            print(f"Failed to parse JSON response for issues: {e}. Response text: {resp.text if 'resp' in locals() else 'N/A'}")
            break

    print(f"Fetched {len(all_issues)} issues from SonarQube.")
    return all_issues


def fetch_sonar_metrics(project_key: str) -> dict: # Changed to take project_key for clarity
    """
    Use SonarQube API to fetch measures for the given project key.
    For example: code smells, bugs, coverage, complexity.
    This fetches current metrics for the project.
    """
    metrics = ["bugs", "code_smells", "coverage", "duplicated_lines_density", "sqale_debt_ratio", "vulnerabilities", "security_hotspots", "security_rating"] # Added more relevant metrics
    metric_str = ",".join(metrics)
    # Using component key (project key) to get metrics for the whole project
    url = f"{SONAR_HOST_URL}/api/measures/component?component={project_key}&metricKeys={metric_str}" #
    auth_string = f"{SONAR_TOKEN}:".encode('utf-8') #
    headers = {"Authorization": f"Basic {base64.b64encode(auth_string).decode('utf-8')}"} #

    print(f"Fetching SonarQube metrics for project: {project_key}...")
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        measures = {}
        if "component" in data and "measures" in data["component"]:
            for m in data["component"]["measures"]: #
                measures[m["metric"]] = m.get("value", m.get("period", {}).get("value", "N/A")) # Handle different structures for metric values
        if not measures:
            print(f"Warning: No metrics found for project {project_key}. Response: {data}")
        return measures
    except requests.exceptions.Timeout:
        print(f"Timeout while fetching SonarQube metrics for {project_key}.")
        return {"error": "Timeout fetching metrics"}
    except requests.exceptions.HTTPError as e:
        print(f"SonarQube API HTTP error while fetching metrics: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 401:
            raise RuntimeError("SonarQube authentication failed. Check SONAR_TOKEN.") from e #
        return {"error": f"API error {e.response.status_code} fetching metrics"}
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with SonarQube API for metrics: {e}")
        return {"error": f"RequestException fetching metrics: {e}"}
    except ValueError as e: # JSON decoding error
        print(f"Failed to parse JSON response for metrics: {e}. Response text: {resp.text if 'resp' in locals() else 'N/A'}")
        return {"error": f"JSONDecodeError fetching metrics: {e}"}


def format_sonarqube_report(sonar_issues: list, sonar_metrics: dict) -> str:
    """Formats SonarQube issues and metrics into a Markdown string."""
    report_lines = ["\n## SonarQube Analysis"]

    if sonar_issues:
        report_lines.append("\n### SonarQube Issues Found:")
        for idx, issue in enumerate(sonar_issues, start=1):
            report_lines.append(
                f"{idx}. **{issue['file_path']}"
                f"{(':' + str(issue['line'])) if issue['line'] else ''}** - "
                f"[{issue['type']}/{issue['severity']}] {issue['message']}"
            )
    else:
        report_lines.append("\nNo specific issues reported by SonarQube (or relevant to the diff).")

    if sonar_metrics and not sonar_metrics.get("error"):
        report_lines.append("\n### SonarQube Metrics:")
        report_lines.append("| Metric                 | Value |")
        report_lines.append("|------------------------|-------|")
        for metric, value in sonar_metrics.items(): #
            report_lines.append(f"| {metric.replace('_', ' ').title()} | {value} |") #
    elif sonar_metrics.get("error"):
        report_lines.append(f"\nCould not retrieve SonarQube metrics: {sonar_metrics.get('error')}")
    else:
        report_lines.append("\nNo metrics available from SonarQube.")
        
    return "\n".join(report_lines)


def aggregate_and_write_report(llm_comments_markdown: str, sonar_report_markdown: str, pr_number: int, output_file_path: str):
    """
    Combines LLM feedback summary with Sonar report into a Markdown report and saves it.
    """
    report_title_pr_context = f"for PR #{pr_number}" if pr_number is not None and pr_number != 0 else "for Diff File"
    final_report_lines = [
        f"# Automated Code Review Summary {report_title_pr_context}",
        llm_comments_markdown, # This is already formatted with "## LLM Feedback"
        sonar_report_markdown  # This is already formatted with "## SonarQube Analysis"
    ]
    
    final_report = "\n".join(final_report_lines)

    # Ensure output directory exists
    output_dir = os.path.dirname(output_file_path)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")
        except OSError as e:
            print(f"Error creating output directory {output_dir}: {e}")
            # Fallback to current directory if creating output_dir fails
            output_file_path = os.path.basename(output_file_path)
            print(f"Saving report to current directory as: {output_file_path}")


    with open(output_file_path, "w", encoding='utf-8') as f:
        f.write(final_report)
    print(f"Combined review report generated at: {output_file_path}")

# Removed the old aggregate_results function as its logic is now split and enhanced.
# The if __name__ == "__main__": block is for testing sonar_wrapper.py independently.
# It's good practice to keep it or adapt it for new functions.
if __name__ == "__main__":
    # Example of how to test the new functions (ensure config is set up)
    if not (SONAR_TOKEN and SONAR_PROJECT_KEY and SONAR_HOST_URL): #
        print("Error: SonarQube environment variables (SONAR_TOKEN, SONAR_PROJECT_KEY, SONAR_HOST_URL) must be set.") #
    else:
        try:
            print("Testing SonarQube integration...")
            # 1. Run scanner (optional, can be run manually first)
            # run_sonar_scanner() # Be cautious running this automatically during tests if not intended
            
            # 2. Wait for analysis (if scanner was run programmatically)
            # analysis_key = wait_for_sonar_analysis()
            # print(f"Analysis Key: {analysis_key}") #

            # 3. Fetch issues for the project
            issues = fetch_sonar_issues(SONAR_PROJECT_KEY) #
            if issues:
                print(f"\nFetched {len(issues)} issues. First 3:")
                for issue in issues[:3]:
                    print(issue)
            else:
                print("\nNo issues fetched.")

            # 4. Fetch metrics for the project
            metrics = fetch_sonar_metrics(SONAR_PROJECT_KEY) #
            print("\nSonarQube Metrics:", metrics)

            # 5. Format SonarQube part of the report
            sonar_markdown = format_sonarqube_report(issues, metrics)
            print("\nFormatted SonarQube Report (Markdown Preview):")
            print(sonar_markdown)

        except RuntimeError as e:
            print(f"Runtime Error: {e}")
        except FileNotFoundError as e:
            print(f"File Not Found Error: {e}")
        except TimeoutError as e:
            print(f"Timeout Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")