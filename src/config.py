import os
import logging

# Project Directory Structure
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This will be <project_root>/src
SRC_DIR = ROOT_DIR
DATA_DIR = os.path.join(os.path.dirname(ROOT_DIR), "data")
OUTPUT_DIR = os.path.join(os.path.dirname(ROOT_DIR), "output")
LOGS_DIR = os.path.join(os.path.dirname(ROOT_DIR), "logs")
MOCK_DATA_DIR = os.path.join(DATA_DIR, "mock")

# API Key Loading
def load_api_key(key_name: str, colab_secret_name: str) -> str | None:
    """
    Loads an API key, trying Colab Secrets first, then environment variables.
    Prints a message if the key is not found.
    """
    try:
        from google.colab import userdata
        api_key = userdata.get(colab_secret_name)
        if api_key:
            return api_key
    except ImportError:
        # Not in Colab environment
        pass

    api_key = os.getenv(key_name)
    if api_key:
        return api_key

    print(f"Warning: API key '{key_name}' not found. "
          f"Please set it in Colab Secrets as '{colab_secret_name}' or as an environment variable.")
    return None

GEMINI_API_KEY = load_api_key("GEMINI_API_KEY", "GEMINI_API_KEY")
FRED_API_KEY = load_api_key("FRED_API_KEY", "FRED_API_KEY")
FINMIND_API_KEY = load_api_key("FINMIND_API_KEY", "FINMIND_API_KEY")

# Retry/Circuit Breaker Parameters
RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 5
CIRCUIT_BREAKER_FAIL_MAX = 3
CIRCUIT_BREAKER_RESET_TIMEOUT = 60  # seconds

# Simulation Mode
SIMULATION_MODE = True  # Default to True for safety

# Log Level
LOG_LEVEL = logging.INFO # Default log level
# Example of how to set it from an environment variable if needed:
# LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "INFO").upper()
# LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)

if __name__ == '__main__':
    # Test directory structure (paths will be relative to executed script if not installed)
    print(f"ROOT_DIR: {ROOT_DIR}")
    print(f"SRC_DIR: {SRC_DIR}")
    print(f"DATA_DIR: {DATA_DIR}")
    print(f"OUTPUT_DIR: {OUTPUT_DIR}")
    print(f"LOGS_DIR: {LOGS_DIR}")
    print(f"MOCK_DATA_DIR: {MOCK_DATA_DIR}")

    # Test API Key loading (will print warnings if not set)
    print(f"GEMINI_API_KEY: {GEMINI_API_KEY}")
    print(f"FRED_API_KEY: {FRED_API_KEY}")
    print(f"FINMIND_API_KEY: {FINMIND_API_KEY}")

    print(f"RETRY_ATTEMPTS: {RETRY_ATTEMPTS}")
    print(f"SIMULATION_MODE: {SIMULATION_MODE}")
    print(f"LOG_LEVEL: {LOG_LEVEL}")
