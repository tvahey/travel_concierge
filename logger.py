"""Logging configuration for Travel Concierge Agent."""

import logging
import os
from datetime import datetime
from pathlib import Path

# Create logs directory
LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Log file path
LOG_FILE = LOGS_DIR / "app.log"


def setup_logging():
    """Configure application logging."""
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler (errors only)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers = []
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module."""
    return logging.getLogger(name)


def read_logs(lines: int = 100) -> str:
    """Read the last N lines from the log file."""
    if not LOG_FILE.exists():
        return "No logs yet."

    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return "".join(recent_lines)
    except Exception as e:
        return f"Error reading logs: {e}"


def read_errors(lines: int = 50) -> str:
    """Read only ERROR and WARNING lines from the log file."""
    if not LOG_FILE.exists():
        return "No logs yet."

    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            error_lines = [
                line for line in all_lines
                if "| ERROR" in line or "| WARNING" in line
            ]
            recent_errors = error_lines[-lines:] if len(error_lines) > lines else error_lines
            if not recent_errors:
                return "No errors or warnings logged."
            return "".join(recent_errors)
    except Exception as e:
        return f"Error reading logs: {e}"


def clear_logs() -> bool:
    """Clear the log file."""
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("")
        return True
    except Exception:
        return False


def get_log_stats() -> dict:
    """Get statistics about the log file."""
    if not LOG_FILE.exists():
        return {"exists": False, "size": 0, "errors": 0, "warnings": 0}

    try:
        size = LOG_FILE.stat().st_size
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            errors = content.count("| ERROR")
            warnings = content.count("| WARNING")

        return {
            "exists": True,
            "size": size,
            "size_kb": round(size / 1024, 2),
            "errors": errors,
            "warnings": warnings,
            "path": str(LOG_FILE),
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}
