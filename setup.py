# setup.py
import os
from setuptools import setup, find_packages

# Read README.md for long description
try:
    with open(os.path.join(os.path.dirname(__file__), 'README.md'), encoding='utf-8') as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = 'AI Code Reviewer tool combining LLM and SonarQube.'

setup(
    name="ai_code_reviewer",
    version="0.1.0",
    packages=find_packages(),  # Automatically find the 'reviewer' package
    # Add your orchestrator script's module if it's not in a package
    # For run_review.py at the root, ensure it can be found or package it too.
    # If run_review.py is at the root, entry_points will refer to it.
    py_modules=['run_review'], # Make run_review.py installable
    install_requires=[
        "python-dotenv>=0.15.0", # Specify versions as appropriate
        "requests>=2.25.0",
        # Add any other dependencies your project has (e.g., from a requirements.txt)
    ],
    entry_points={
        "console_scripts": [
            "run-ai-review=run_review:main",  # This creates a command-line callable script
        ],
    },
    author="Your Name / Organization",
    author_email="your.email@example.com",
    description="An AI Code Reviewer tool combining LLM feedback and SonarQube metrics.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="<your_project_repository_url_if_any>", # Optional: URL to your project
    classifiers=[ # Optional: Trove classifiers
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License", # Choose your license
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7', # Specify your Python version compatibility
)