import os
from dotenv import load_dotenv

# Load .env variables (if present)
load_dotenv()

# GitHub settings
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # A Personal Access Token with repo:write scope
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")  
# e.g., "your-username/ai-code-reviewer-demo"
GITHUB_API_URL = "https://api.github.com"

# OpenAI (or chosen LLM) settings
# api_key = "nbhb5b23SFEWN" # This seems like a placeholder, ensure OPENAI_API_KEY is correctly set in env
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
# Adjust the endpoint if using Azure or other LLM providers

# SonarQube settings
SONAR_HOST_URL = os.getenv("SONAR_HOST_URL", "https://sonarcloud.io")
SONAR_TOKEN = os.getenv("SONAR_TOKEN")  # Generated in SonarQube for API access
SONAR_PROJECT_KEY = os.getenv("SONAR_PROJECT_KEY", "NumeralTiger_AI-PR-Reviewer") # Ensure this is the correct key for the target project or overridden by env
SONAR_PROJECT_NAME = os.getenv("SONAR_PROJECT_NAME", "AI-PR-Reviewer")
# SONAR_ORG = os.getenv("SONAR_ORG") # Add if your SonarQube instance/API usage requires organization key