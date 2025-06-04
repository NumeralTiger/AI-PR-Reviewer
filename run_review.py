# run_review.py
import argparse
import os

import requests
from reviewer import diff_extractor, llm_reviewer, sonar_wrapper, config

def main():
    parser = argparse.ArgumentParser(description="Run AI Code Review with LLM and SonarQube.")
    parser.add_argument("--pr-number", type=int, help="Pull Request number (required for reporting if not in GitHub Actions env).")
    parser.add_argument("--diff-file", type=str, help="Path to a diff file (optional; if not provided, attempts to extract from GitHub Actions env).")
    # Add other arguments as needed, e.g., to override specific SonarQube settings
    
    args = parser.parse_args()

    pr_info = None
    diff_text_content = None # Renamed to avoid conflict with diff_extractor module
    pr_number_for_report = args.pr_number

    # 1. Get PR Info & Diff
    if args.diff_file:
        print(f"Using provided diff file: {args.diff_file}")
        try:
            with open(args.diff_file, 'r', encoding='utf-8') as f:
                diff_text_content = f.read()
            if not pr_number_for_report:
                print("Warning: --pr-number not provided with --diff-file. Report may need a PR number.")
                # Consider making --pr-number mandatory if --diff-file is used, or use a default.
                pr_number_for_report = 0 # Default or placeholder
        except FileNotFoundError:
            print(f"Error: Diff file not found at {args.diff_file}")
            return
        except Exception as e:
            print(f"Error reading diff file {args.diff_file}: {e}")
            return
    else:
        try:
            print("Attempting to extract PR info and diff using GitHub environment variables...")
            pr_info = diff_extractor.get_pr_info() #
            diff_text_content = diff_extractor.extract_diff() #
            pr_number_for_report = pr_info["pr_number"]
            print(f"Extracted diff for PR #{pr_number_for_report} from repository {pr_info['repo_full_name']}.")
        except RuntimeError as e:
            print(f"Could not automatically extract diff (ensure GITHUB_EVENT_PATH is set for GitHub Actions): {e}")
            print("Alternatively, provide a diff file using --diff-file.")
            return
        except Exception as e:
            print(f"An unexpected error occurred during diff extraction: {e}")
            return

    if not diff_text_content:
        print("No diff content available to review.")
        return

    # 2. Get LLM Review
    print("Requesting LLM review...")
    if not config.OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY is not configured. Please set it in your .env file or environment variables.")
        return
        
    llm_comments_list = llm_reviewer.call_openai_llm(diff_text_content) #
    print(f"Received {len(llm_comments_list)} comments from LLM.")

    # 3. Run SonarQube Analysis & Get Metrics
    sonar_metrics_dict = {} # Renamed for clarity
    # Check if SonarQube is configured by looking for essential config variables
    if config.SONAR_TOKEN and config.SONAR_PROJECT_KEY and config.SONAR_HOST_URL:
        try:
            print("Running SonarQube scanner...")
            sonar_wrapper.run_sonar_scanner() #
            print("Waiting for SonarQube analysis to complete...")
            analysis_key = sonar_wrapper.wait_for_sonar_analysis() #
            print(f"SonarQube analysis completed. Analysis Key: {analysis_key}")
            sonar_metrics_dict = sonar_wrapper.fetch_sonar_metrics(analysis_key) #
            print("Fetched SonarQube metrics:", sonar_metrics_dict)
        except RuntimeError as e:
            print(f"SonarQube scanner execution failed: {e}")
        except TimeoutError as e:
            print(f"Timed out waiting for SonarQube analysis: {e}")
        except requests.exceptions.RequestException as e: # Catch potential network/API errors
            print(f"Error communicating with SonarQube API: {e}")
        except Exception as e: # Catch any other unexpected errors during SonarQube processing
            print(f"An unexpected error occurred with SonarQube integration: {e}")
    else:
        print("SonarQube TOKEN, PROJECT_KEY, or HOST_URL not fully configured. Skipping SonarQube analysis.")
        print(f"SONAR_TOKEN set: {'Yes' if config.SONAR_TOKEN else 'No'}")
        print(f"SONAR_PROJECT_KEY set: {'Yes' if config.SONAR_PROJECT_KEY else 'No'}")
        print(f"SONAR_HOST_URL set: {'Yes' if config.SONAR_HOST_URL else 'No'}")

    # 4. Aggregate Results
    # The aggregate_results function saves the report to a file and returns the path
    print("Aggregating LLM comments and SonarQube metrics into a report...")
    if pr_number_for_report is None: # Ensure pr_number is set before calling aggregate_results
        print("Error: PR Number is required for the report but was not determined. Please provide --pr-number.")
        # Use a default if pr_number_for_report is still None, though it should be set by now if diff was processed.
        pr_number_for_report = 0 # Or handle as a critical error
    
    output_report_file_path = sonar_wrapper.aggregate_results(llm_comments_list, sonar_metrics_dict, pr_number_for_report)
    print(f"Combined review report generated at: {output_report_file_path}")

if __name__ == "__main__":
    main()