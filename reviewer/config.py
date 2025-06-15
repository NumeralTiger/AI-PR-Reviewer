import os
from dotenv import load_dotenv

# Load .env variables (if present)
load_dotenv()

# GitHub settings
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
GITHUB_API_URL = "https://api.github.com"

# OpenAI (or chosen LLM) settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# SonarQube settings
SONAR_HOST_URL = os.getenv("SONAR_HOST_URL", "https://sonarcloud.io")
SONAR_TOKEN = os.getenv("SONAR_TOKEN") # Generated in SonarQube for API access
SONAR_PROJECT_KEY = os.getenv("SONAR_PROJECT_KEY", "NumeralTiger_AI-PR-Reviewer") # Ensure this is the correct key for the target project or overridden by env
SONAR_PROJECT_NAME = os.getenv("SONAR_PROJECT_NAME", "AI-PR-Reviewer")

# New settings for Java projects:
# Set SONAR_JAVA_BINARIES if you want to analyze Java .class files.
# Common paths: "target/classes" (Maven/Gradle), "bin" (Eclipse), "out" (IntelliJ)
# Leave empty or None to not set it.
SONAR_JAVA_BINARIES = os.getenv("SONAR_JAVA_BINARIES") # e.g., "target/classes"

# Set SONAR_JAVA_EXCLUSIONS to exclude specific Java files/patterns from analysis.
# e.g., "**/*.spec.java" or "**/generated-sources/**"
# Leave empty or None to not set it.
SONAR_JAVA_EXCLUSIONS = os.getenv("SONAR_JAVA_EXCLUSIONS") # e.g., "**/*.java" if you want to exclude all Java source files