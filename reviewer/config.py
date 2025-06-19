import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# GitHub settings
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
GITHUB_API_URL = "https://api.github.com"

# OpenAIsettings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# SonarQube settings
SONAR_HOST_URL = os.getenv("SONAR_HOST_URL", "https://sonarcloud.io")
SONAR_TOKEN = os.getenv("SONAR_TOKEN") # Generated in SonarQube for API access
SONAR_PROJECT_KEY = os.getenv("SONAR_PROJECT_KEY", "NumeralTiger_AI-PR-Reviewer")
SONAR_ORGANIZATION = os.getenv("SONAR_ORGANIZATION", "numeraltiger")
SONAR_PROJECT_NAME = os.getenv("SONAR_PROJECT_NAME", "AI-PR-Reviewer")