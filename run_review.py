import argparse
import os
import sys # For sys.exit

import requests # for direct API calls
from reviewer import diff_extractor, llm_reviewer, sonar_wrapper, config 

def main():
    parser = argparse.ArgumentParser(description="Run AI Code Review with LLM and SonarQube.") #
    parser.add_argument("--pr-number", type=int, help="Pull Request number (optional, for context in report).") #
    parser.add_argument("--diff-file", type=str, help="Path to a diff file (e.g., tmp.diff). Required if not in GitHub Actions env.") #
    parser.add_argument("--output-file", type=str, default="output/ai_code_review.md", help="Path to save the combined review report Markdown file (default: output/ai_code_review.md).")
    # Could add other arguments if needed, e.g., to override specific SonarQube settings
    
    args = parser.parse_args()

    # Configuration Check
    if not config.OPENAI_API_KEY: 
        print("Error: OPENAI_API_KEY is not configured or is a placeholder. Please set it in your .env file or environment variables.") #
        sys.exit(1)
        
    sonarqube_configured = bool(config.SONAR_TOKEN and config.SONAR_PROJECT_KEY and config.SONAR_HOST_URL)
    if not sonarqube_configured:
        print("Warning: SonarQube TOKEN, PROJECT_KEY, or HOST_URL not fully configured. SonarQube analysis will be skipped.") #
        print(f"  SONAR_TOKEN set: {'Yes' if config.SONAR_TOKEN else 'No'}") #
        print(f"  SONAR_PROJECT_KEY set: {'Yes' if config.SONAR_PROJECT_KEY else 'No'}") #
        print(f"  SONAR_HOST_URL set: {'Yes' if config.SONAR_HOST_URL else 'No'}") #


    # Get Diff Content
    diff_text_content = None
    pr_number_for_report = args.pr_number 

    if args.diff_file: 
        print(f"Using provided diff file: {args.diff_file}")
        try:
            try:
                with open(args.diff_file, 'r', encoding='utf-8') as f:
                    diff_text_content = f.read()
            except UnicodeDecodeError:
                print(f"Warning: Could not decode '{args.diff_file}' as UTF-8. Trying latin-1 encoding...")
                with open(args.diff_file, 'r', encoding='latin-1') as f:
                    diff_text_content = f.read()
            if not diff_text_content.strip():
                print(f"Error: Diff file '{args.diff_file}' is empty or contains only whitespace.")
                sys.exit(1)
            # If diff file is provided, pr_number might not be automatically available unless given
            if not pr_number_for_report: 
                print("Info: --pr-number not provided with --diff-file. Report will not reference a PR number unless set.") #
        except FileNotFoundError: 
            print(f"Error: Diff file not found at {args.diff_file}") #=
            sys.exit(1)
        except Exception as e: 
            print(f"Error reading diff file {args.diff_file}: {e}") #=
            sys.exit(1)
    else: # Try to extract from GitHub Actions env if no diff file provided
        try:
            print("Attempting to extract PR info and diff using GitHub environment variables...") 
            # This part is for CI/CD
            if os.getenv("GITHUB_EVENT_PATH"): # Check if likely in GitHub Actions
                pr_info = diff_extractor.get_pr_info() 
                diff_text_content = diff_extractor.extract_diff() 
                pr_number_for_report = pr_info["pr_number"] 
                print(f"Extracted diff for PR #{pr_number_for_report} from repository {pr_info['repo_full_name']}.") 
            else:
                print("Error: Not in GitHub Actions environment and --diff-file not provided.")
                print("Please provide a diff file using --diff-file for desktop execution.")
                sys.exit(1)
        except RuntimeError as e: 
            print(f"Could not automatically extract diff (ensure GITHUB_EVENT_PATH is set for GitHub Actions or use --diff-file): {e}") 
            sys.exit(1)
        except Exception as e: 
            print(f"An unexpected error occurred during diff extraction: {e}") 
            sys.exit(1)

    if not diff_text_content: 
        print("No diff content available to review. Exiting.") 
        sys.exit(1)

    # Run SonarQube Analysis & Get Issues/Metrics
    sonar_issues_list = []
    sonar_metrics_dict = {} 
    sonar_report_md = ""

    if sonarqube_configured:
        try:
            print("\n--- Starting SonarQube Analysis ---")

            sonar_wrapper.run_sonar_scanner() 
            print("SonarQube scanner finished.")

            print("Waiting for SonarQube analysis to complete on the server...") 

            print(f"Fetching SonarQube issues for project: {config.SONAR_PROJECT_KEY}...") 
            sonar_issues_list = sonar_wrapper.fetch_sonar_issues(config.SONAR_PROJECT_KEY) 
            
            print(f"Fetching SonarQube metrics for project: {config.SONAR_PROJECT_KEY}...") 
            sonar_metrics_dict = sonar_wrapper.fetch_sonar_metrics(config.SONAR_PROJECT_KEY) 
            
            sonar_report_md = sonar_wrapper.format_sonarqube_report(sonar_issues_list, sonar_metrics_dict)
            print("--- SonarQube Analysis Finished ---")

        except FileNotFoundError as e: # From run_sonar_scanner
            print(f"SonarQube Error: {e}. Skipping SonarQube part.")
            sonar_report_md = "\n## SonarQube Analysis\nSonarScanner not found. Please ensure it's installed and in PATH."
        except RuntimeError as e: # From SonarQube steps
            print(f"SonarQube processing failed: {e}. Skipping SonarQube part.") #
            sonar_report_md = f"\n## SonarQube Analysis\nError during SonarQube processing: {e}"
        except TimeoutError as e: # From wait_for_sonar_analysis
            print(f"Timed out waiting for SonarQube analysis: {e}. Skipping SonarQube part.") #
            sonar_report_md = f"\n## SonarQube Analysis\nTimed out waiting for SonarQube: {e}"
        except requests.exceptions.RequestException as e: # Catch potential network/API errors
            print(f"Error communicating with SonarQube API: {e}. Skipping SonarQube part.") #
            sonar_report_md = f"\n## SonarQube Analysis\nAPI communication error: {e}"
        except Exception as e: # Catch any other unexpected errors during SonarQube processing
            print(f"An unexpected error occurred with SonarQube integration: {e}. Skipping SonarQube part.") #
            sonar_report_md = f"\n## SonarQube Analysis\nUnexpected error: {e}"
    else:
        print("Skipping SonarQube analysis due to missing configuration.") #
        sonar_report_md = "\n## SonarQube Analysis\nSkipped: SonarQube not fully configured (SONAR_TOKEN, SONAR_PROJECT_KEY, SONAR_HOST_URL)." #


    # Get LLM Review combined with SonarQube issues
    print("\n--- Starting LLM Code Review ---")
    print("Requesting LLM review...") 
    # Pass SonarQube issues to the LLM for integrated feedback
    llm_comments_list, raw_llm_reply = [], ""
    try:
        llm_comments_list, raw_llm_reply = llm_reviewer.call_openai_llm(diff_text_content, sonar_issues_list) #
        print(f"Received {len(llm_comments_list)} comments from LLM.") #
    except ValueError as e: # Configuration error from LLM 
        print(f"LLM Configuration Error: {e}. Cannot proceed with LLM review.")
        # llm_reviewer.format_llm_feedback_to_markdown will handle the error message.
        raw_llm_reply = f'{{"error": "LLM Configuration Error: {e}"}}' # Create a raw reply indicating error
    except Exception as e: # Catch any other unexpected error during LLM call
        print(f"An unexpected error occurred during LLM review: {e}")
        raw_llm_reply = f'{{"error": "Unexpected error during LLM review: {e}"}}'

    llm_feedback_md = llm_reviewer.format_llm_feedback_to_markdown(llm_comments_list, raw_llm_reply)
    print("--- LLM Code Review Finished ---")

    # Aggregate Results & Write Report ---
    print("\n--- Generating Combined Report ---")
    
    # Use the --output-file argument for the path
    output_report_file_path = args.output_file

    try:
        sonar_wrapper.aggregate_and_write_report(
            llm_comments_markdown=llm_feedback_md,
            sonar_report_markdown=sonar_report_md,
            pr_number=pr_number_for_report, #
            output_file_path=output_report_file_path
        )
    except Exception as e:
        print(f"Error writing the final report to {output_report_file_path}: {e}")
        sys.exit(1)
    
    print(f"\nReview process complete. Report saved to: {output_report_file_path}")


if __name__ == "__main__":
    main() 