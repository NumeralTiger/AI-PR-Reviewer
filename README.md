# AI-Powered Code Review with SonarQube Feedback


This project merges static code analysis from **SonarQube** with AI-driven feedback from OpenAI to review your changes after you modify code or add a new feature. It acts like a senior developer approving changes, providing information on potential errors and security vulnerabilities through a clear report, helping catch issues early and reducing human involvement.

![System Architecture](images/LLM_powered_code_reviewer%20(2).jpg)
---

## Features

* Analyzes code changes using a `.diff` file, making it suitable for reviewing Pull Requests.
* Integrates **SonarScanner** for  static code analysis.
* Provides comprehensive feedback using OpenAI's AI models, considering:
    * Code best practices
    * Security vulnerabilities
    * Performance and optimization
    * Maintainability
* Generates a consolidated and clear review report in Markdown format (e.g., `output/review_report.md`), allowing for easy access to feedback without having to leaving your editor.

---

## Prerequisites

Ensure you have the following in place:

1.  **Python 3.8+**: This project requires Python. You can download and install the latest version from the [official Python website](https://www.python.org/downloads/).
2.  **Git**: Necessary for making `.diff` files from code changes. Download Git from [git-scm.com](https://git-scm.com/downloads).
3.  **SonarQube Instance & Account**:
    * You'll need a running SonarQube instance (self-hosted or SonarCloud). I used SonarCloud.
    * If you don't have a SonarQube account, you can create one. For SonarCloud, visit [SonarCloud documentation](https://sonarcloud.io/about/accounts). For a self-hosted SonarQube server, refer to the [SonarQube documentation](https://docs.sonarsource.com/sonarqube-server/latest/instance-administration/user-management/creating-users/) for instructions.
    * **Sonar Project Properties**: Create a `sonar-project.properties` file in your project's root directory. This file configures how SonarQube analyzes your project. Refer to the [SonarScanner documentation](https://docs.sonarsource.com/sonarqube/latest/analyzing-source-code/scanners/sonarscanner-cli/) for details (e.g., `sonar.projectKey`, `sonar.sources`).
4.  **OpenAI API Key**:
    * You need an OpenAI account and an API key to utilize ChatGPT for analysis.
    * If you don't have an account, sign up at the [OpenAI Platform](https://platform.openai.com/).
    * Once logged in, navigate to the [API keys section](https://platform.openai.com/api-keys) to generate a key.
5.  **Environment Variables**: Set up environment variables by creating a `.env` file in the root of your project. This file will store your sensitive variables.

    ```env
    OPENAI_API_KEY=your_openai_api_key_here
    SONAR_TOKEN=your_sonarqube_user_token_here
    SONAR_HOST_URL=https://sonarcloud.io # Or your SonarQube instance URL

    # Add other SonarQube related variables as needed, e.g., SONAR_PROJECT_KEY
    ```
    *Make sure to replace the placeholder values with your actual keys and URLs.*

---

## Installation

To set up the project for development or general use, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/NumeralTiger/AI-PR-Reviewer.git
    cd AI-PR-Reviewer
    ```
2.  **Install dependencies:**
    It's highly recommended to use a virtual environment.
    ```bash
    python -m venv venv
    source venv/bin/activate # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```
3.  **Install in editable mode (for development):**
    If you plan to contribute or modify the code, install the package in editable mode:
    ```bash
    pip install -e .
    ```

---

## Usage

This tool can be triggered via a CLI command, typically after a code change or as part of a Pull Request workflow.

**1. Generate a `.diff` file:**

First, you need a `.diff` file representing the code changes you want to review. Place this file in your project's root directory.

* **For a local Git repository (e.g., comparing current changes to `main` branch):**
    ```bash
    git diff main > tmp.diff
    ```
    Or, to get the diff for staged changes:
    ```bash
    git diff --staged > tmp.diff
    ```
* **For a Pull Request (PR) in a CI/CD pipeline (example for GitHub Actions):**
    In a CI/CD environment, the `.diff` file for a PR can usually be generated using Git commands comparing the base and head branches. For example:
    ```bash
    git diff origin/main...HEAD > tmp.diff
    ```
    *(Adjust `origin/main` to your base branch name and `HEAD` to your feature branch as per your CI/CD setup.)*

**2. Run the AI-powered review:**

Once you have your `tmp.diff` file (or your chosen diff file name) in your project's root, execute the `run-ai-review` command:

```bash
python run-ai-review --diff-file tmp.diff --output-file output/review_report.md
