# AI-Powered Code Review with SonarQube Feedback

This project merges static code analysis from **SonarQube** with AI-driven feedback from OpenAI to review your changes after you modify code or add a new feature. It acts like a senior developer approving changes, providing information on potential errors through a clear report, helping catch issues early and reducing human involvement.

---

## Features

-   Analyzes code changes using a `tmp.diff` file.
-   Integrates **SonarScanner** for static analysis.
-   Provides feedback using AI, considering:
    -   Code best practices
    -   Security vulnerabilities
    -   Performance and optimization 
-   Generates a consolidated review report in `output/review_report.md`, so you don't have to leave your editor.

---

##  Prerequisites

ensure you have the following set up:

1.  **SonarQube**: Install and configure SonarQube for your project.
2.  **Sonar Project Properties**: Create a `sonar-project.properties` file in your project's root directory. Refer to the [SonarQube documentation](https://docs.sonarsource.com/).
3.  **OpenAI API Key**: etup environment variables by setting up a `.env` file in the root of the project and add your API key, sonarQube credentials etc:

    ```env
    OPENAI_API_KEY=your_api_key_here
    SONAR_TOKEN=your_token_here
    #rest of your variables
    ```

---

## Personal Development Setup

To install the package in editable mode for development, run the following command:

```bash
pip install -e .
```

then 
finally,

given that tmp.diff is located in ur root, run the following command to start the review:

```bash
python run-ai-review --diff-file tmp.diff --output-file output/review_report.md
