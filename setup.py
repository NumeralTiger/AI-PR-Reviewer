import os
from setuptools import setup, find_packages

# Read README.md for long description
try:
    with open(os.path.join(os.path.dirname(__file__), 'README.md'), encoding='utf-8') as f: #
        long_description = f.read() 
except FileNotFoundError: 
    long_description = 'AI Code Reviewer tool combining LLM and SonarQube.' 

# Read requirements.txt for install_requires
try:
    with open(os.path.join(os.path.dirname(__file__), 'requirements.txt'), encoding='utf-8') as f:
        install_requires = [line.strip() for line in f if line.strip() and not line.startswith('#')]
except FileNotFoundError:
    # Fallback if requirements.txt is not found, though it's provided.
    install_requires=[
        "requests>=2.28.0",
        "PyGithub>=1.79.0", 
        "python-dotenv>=1.0.0", 
        "setuptools" 
    ]


setup(
    name="ai_code_reviewer", 
    version="0.2.0", 
    author="ZM", 
    author_email="zaidmohiuddin6@gmail.com", 
    description="An AI Code Reviewer tool combining LLM feedback and SonarQube metrics.", 
    long_description=long_description, 
    long_description_content_type="text/markdown", 
    url="https://github.com/NumeralTiger/AI-PR-Reviewer", # URL to project
    
    # Assuming run_review.py is at the root, alongside setup.py
    # and the 'reviewer' directory contains the package modules.
    py_modules=["run_review"], # Make run_review.py importable for the entry point
    packages=find_packages(where=".", include=['reviewer', 'reviewer.*']), # Automatically find the 'reviewer' package
                                                                        # and any sub-packages if they exist.
    
    install_requires=install_requires, 
    
    entry_points={ 
        "console_scripts": [ 
            "run-ai-review=run_review:main",  # This creates a command-line callable script
        ],
    },
    
    classifiers=[ #Trove classifiers
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent", 
    ],
    python_requires='>=3.8', # recent Python version
)