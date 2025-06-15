import os
import requests
import json

# --- GOOD CODE EXAMPLES ---

def calculate_area_rectangle(length, width):
    """Calculates the area of a rectangle."""
    if not isinstance(length, (int, float)) or not isinstance(width, (int, float)):
        raise TypeError("Length and width must be numeric.")
    if length < 0 or width < 0:
        raise ValueError("Length and width cannot be negative.")
    return length * width

def fetch_data_from_api(endpoint, params=None, timeout=10):
    """
    Fetches data from a given API endpoint with a timeout.
    Handles basic error checking for successful requests.
    """
    try:
        response = requests.get(endpoint, params=params, timeout=timeout)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from {endpoint}: {e}")
        return None

# --- BAD CODE EXAMPLES ---

# Pubicly exposed API keys

BAD_API_KEY_EXAMPLE_1 = "your_insecurely_stored_api_key_12345"
ANOTHER_BAD_API_KEY = "another_hardcoded_key_abcde"

def process_data(data_string):
    # Missing error handling and potential for injection
    eval(f"print({data_string})") # HIGHLY DANGEROUS! bad practice.

def connect_to_database(db_user, db_pass):
    # This is a placeholder for a real database connection string
    # In a real scenario, this would likely involve hardcoded credentials
    # or an insecure connection string.
    pass # No actual connection made for safety reasons

def log_user_action(user_id, action):
    # Prints directly to console, no proper logging framework, sensitive info might be logged
    print(f"User {user_id} performed action: {action}")

class MyUtility:
    def __init__(self):
        self.config = {} # Should load from a config file, not be empty

    def load_config(self, filename):
        # Basic file read, no error handling for file not found or malformed JSON
        with open(filename, 'r') as f:
            self.config = json.load(f)

# --- MIXED/POTENTIALLY PROBLEMATIC ---

def get_user_settings(user_id):
    # Imagine this fetches settings from a database or API
    # It might return a dictionary that *could* contain sensitive info
    # if not properly filtered or handled.
    settings = {"theme": "dark", "notifications": True, "api_access_token": "some_token_here_if_misconfigured"}
    return settings

# --- Main execution block (can have good/bad calls) ---
if __name__ == "__main__":
    print("--- Running Tests ---")

    # Good code usage
    try:
        area = calculate_area_rectangle(10, 5)
        print(f"Area of rectangle: {area}")
        # area_bad = calculate_area_rectangle("10", 5) # This would raise TypeError
    except (TypeError, ValueError) as e:
        print(f"Error calculating area: {e}")