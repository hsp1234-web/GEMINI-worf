import logging
import os
from src import config # Assuming src is in PYTHONPATH or structure allows this

# Custom Exceptions
class AppBaseError(Exception):
    """Base class for custom exceptions in this application."""
    pass

class APIError(AppBaseError):
    """Custom exception for API related errors."""
    def __init__(self, message, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code

    def __str__(self):
        if self.status_code:
            return f"{super().__str__()} (Status Code: {self.status_code})"
        return super().__str__()

class DataProcessingError(AppBaseError):
    """Custom exception for data processing errors."""
    pass

class FileIOError(AppBaseError):
    """Custom exception for file input/output errors."""
    pass

class ConfigError(AppBaseError):
    """Custom exception for configuration errors."""
    pass

class GeminiAPIError(APIError):
    """Specific error for Gemini API."""
    pass

class FredAPIError(APIError):
    """Specific error for FRED API."""
    pass

class FinMindAPIError(APIError):
    """Specific error for FinMind API."""
    pass

# File System Utils
def ensure_directory_exists(dir_path: str):
    """
    Ensures that a directory exists. If it doesn't, it creates it.
    Raises FileIOError if creation fails for reasons other than already existing.
    """
    if not dir_path:
        raise FileIOError("Directory path cannot be empty.")
    try:
        os.makedirs(dir_path, exist_ok=True)
    except OSError as e:
        raise FileIOError(f"Could not create directory {dir_path}: {e}")

# Logger Setup
def setup_logger(name: str, log_file: str | None = None, level: int | None = None) -> logging.Logger:
    """
    Sets up a logger with console and optional file handlers.

    Args:
        name: The name of the logger (e.g., __name__ from the calling module).
        log_file: Optional. Path to the log file. If None, uses a default from config.
        level: Optional. Logging level. If None, uses LOG_LEVEL from config.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)

    # Set level
    effective_level = level if level is not None else config.LOG_LEVEL
    logger.setLevel(effective_level)

    # Prevent adding multiple handlers if logger already configured
    if logger.hasHandlers():
        # Clear existing handlers if you want to reconfigure, or return logger if setup is idempotent
        # For simplicity here, we'll assume re-configuration is intended if called again,
        # though typically setup_logger might be called once per logger name.
        # A more robust approach might involve checking handler types before adding.
        for handler in logger.handlers[:]: # Iterate over a copy
            logger.removeHandler(handler)
            handler.close()


    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s"
    )

    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(effective_level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File Handler
    effective_log_file = log_file
    if effective_log_file is None: # Default log file path
        ensure_directory_exists(config.LOGS_DIR) # Ensure log directory exists
        effective_log_file = os.path.join(config.LOGS_DIR, "project_log.log")

    if effective_log_file: # Check if a file path is set (either user-provided or default)
        try:
            # Ensure directory for the log file exists
            log_file_dir = os.path.dirname(effective_log_file)
            if log_file_dir: # If log_file_dir is empty, it means log file is in current dir
                 ensure_directory_exists(log_file_dir)

            fh = logging.FileHandler(effective_log_file)
            fh.setLevel(effective_level)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        except Exception as e:
            logger.error(f"Failed to set up FileHandler for {effective_log_file}: {e}", exc_info=True)


    return logger

if __name__ == '__main__':
    # Test ensure_directory_exists
    print("Testing ensure_directory_exists...")
    ensure_directory_exists(os.path.join(config.DATA_DIR, "test_ensure_dir"))
    print(f"Directory {os.path.join(config.DATA_DIR, 'test_ensure_dir')} should now exist.")

    # Test logger
    print("\nTesting logger setup...")
    # Ensure LOGS_DIR exists for default log file creation
    ensure_directory_exists(config.LOGS_DIR)

    logger1 = setup_logger("my_module")
    logger1.info("This is an info message from my_module (default log file).")
    logger1.error("This is an error message from my_module (default log file).")

    custom_log_path = os.path.join(config.LOGS_DIR, "custom_test.log")
    logger2 = setup_logger("another_module", log_file=custom_log_path, level=logging.DEBUG)
    logger2.debug("This is a debug message from another_module (custom log file).")
    logger2.info("This is an info message from another_module (custom log file).")

    print(f"Default log should be at: {os.path.join(config.LOGS_DIR, 'project_log.log')}")
    print(f"Custom log should be at: {custom_log_path}")

    # Test Exceptions
    print("\nTesting custom exceptions...")
    try:
        raise GeminiAPIError("Failed to connect to Gemini.", status_code=500)
    except APIError as e:
        print(f"Caught APIError: {e}")
        if isinstance(e, GeminiAPIError):
            print("It's a GeminiAPIError!")

    try:
        raise DataProcessingError("Something went wrong during data processing.")
    except AppBaseError as e:
        print(f"Caught AppBaseError: {e}")

    # Test FileIOError during ensure_directory_exists by trying to create a dir where a file exists
    # This requires creating a file where we want a directory
    # For simplicity, we'll just demonstrate a FileIOError for an empty path
    print("\nTesting FileIOError...")
    try:
        ensure_directory_exists("")
    except FileIOError as e:
        print(f"Caught expected FileIOError for empty path: {e}")
