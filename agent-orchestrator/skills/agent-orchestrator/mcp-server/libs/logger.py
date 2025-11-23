"""
Simple file-based logger for debugging MCP server
"""

import json
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class LogLevel(str, Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


# Get the project root directory (parent of src/)
PROJECT_ROOT = Path(__file__).parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "mcp-server.log"


def is_logging_enabled() -> bool:
    """Check if logging is enabled via environment variable"""
    return os.environ.get("MCP_SERVER_DEBUG", "false").lower() == "true"


def ensure_log_dir() -> None:
    """Ensure logs directory exists"""
    if not LOG_DIR.exists():
        LOG_DIR.mkdir(parents=True, exist_ok=True)


def log(level: LogLevel, message: str, data: Optional[Any] = None) -> None:
    """Write a log entry to the log file"""
    # Only log if debugging is enabled
    if not is_logging_enabled():
        return

    try:
        ensure_log_dir()

        timestamp = datetime.utcnow().isoformat() + "Z"
        log_entry = {
            "timestamp": timestamp,
            "level": level.value,
            "message": message,
        }

        if data is not None:
            log_entry["data"] = data

        log_line = json.dumps(log_entry) + "\n"

        with open(LOG_FILE, "a") as f:
            f.write(log_line)

    except Exception as error:
        # If logging fails, write to stderr but don't crash
        print(f"Failed to write to log file: {error}", file=__import__("sys").stderr)


class Logger:
    """Logger convenience class"""

    @staticmethod
    def debug(message: str, data: Optional[Any] = None) -> None:
        log(LogLevel.DEBUG, message, data)

    @staticmethod
    def info(message: str, data: Optional[Any] = None) -> None:
        log(LogLevel.INFO, message, data)

    @staticmethod
    def warn(message: str, data: Optional[Any] = None) -> None:
        log(LogLevel.WARN, message, data)

    @staticmethod
    def error(message: str, data: Optional[Any] = None) -> None:
        log(LogLevel.ERROR, message, data)


# Export singleton logger instance
logger = Logger()


def clear_log() -> None:
    """Clear the log file (useful for testing)"""
    if not is_logging_enabled():
        return

    try:
        ensure_log_dir()
        with open(LOG_FILE, "w") as f:
            f.write("")
    except Exception as error:
        print(f"Failed to clear log file: {error}", file=__import__("sys").stderr)
