import sys
import os
from loguru import logger

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app_{time}.log")
LOG_LEVEL_FILE = os.environ.get("LOG_LEVEL_FILE", "DEBUG").upper()
LOG_LEVEL_CONSOLE = os.environ.get("LOG_LEVEL_CONSOLE", "INFO").upper()
LOG_ROTATION = "10 MB"  # Rotate log file when it reaches 10 MB
LOG_RETENTION = "7 days" # Keep logs for 7 days
LOG_FORMAT_FILE = ( # Slightly simpler format for file, no color
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{name}:{function}:{line} - {message}"
)
LOG_FORMAT_CONSOLE = ( # Keep the original colored format for console
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

def setup_logger():
    """
    Configures the Loguru logger for the application.

    Sets up file logging with rotation and retention, and console logging.
    Log levels for file and console can be controlled via environment variables:
    - LOG_LEVEL_FILE (default: DEBUG)
    - LOG_LEVEL_CONSOLE (default: INFO)
    """
    # Ensure log directory exists
    os.makedirs(LOG_DIR, exist_ok=True)

    # Remove default handler
    logger.remove()

    # Add file handler
    logger.add(
        LOG_FILE,
        level=LOG_LEVEL_FILE,
        format=LOG_FORMAT_FILE,
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
        enqueue=True,  # Asynchronous logging
        backtrace=True, # Better tracebacks
        diagnose=True,  # More detailed exceptions
        serialize=False # Human-readable logs
    )
    logger.info(f"File logging configured: level={LOG_LEVEL_FILE}, rotation='{LOG_ROTATION}', retention='{LOG_RETENTION}'")

    # Add console handler
    logger.add(
        sys.stderr,
        level=LOG_LEVEL_CONSOLE,
        format=LOG_FORMAT_CONSOLE,
        colorize=True,
        backtrace=True, # Also enable for console during development
        diagnose=True
    )
    logger.info(f"Console logging configured: level={LOG_LEVEL_CONSOLE}")

    logger.info("Logger setup complete.")