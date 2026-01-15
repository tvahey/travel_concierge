"""Simple authentication module for Travel Concierge Agent."""

import hashlib
import json
from pathlib import Path
from typing import Optional

from logger import get_logger

logger = get_logger(__name__)

# Users file path
USERS_FILE = Path(__file__).parent / "data" / "users.json"


def _hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def _load_users() -> dict:
    """Load users from JSON file."""
    if not USERS_FILE.exists():
        return {}
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading users: {e}")
        return {}


def _save_users(users: dict) -> bool:
    """Save users to JSON file."""
    try:
        USERS_FILE.parent.mkdir(exist_ok=True)
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving users: {e}")
        return False


def authenticate(username: str, password: str) -> bool:
    """
    Authenticate a user with username and password.

    Returns True if authentication successful, False otherwise.
    """
    if not username or not password:
        return False

    users = _load_users()
    user = users.get(username.lower())

    if not user:
        logger.warning(f"Login attempt for non-existent user: {username}")
        return False

    password_hash = _hash_password(password)
    if user.get("password_hash") == password_hash:
        logger.info(f"User logged in: {username}")
        return True

    logger.warning(f"Failed login attempt for user: {username}")
    return False


def create_user(username: str, password: str, display_name: str = "") -> tuple[bool, str]:
    """
    Create a new user.

    Returns (success, message) tuple.
    """
    if not username or not password:
        return False, "Username and password are required"

    if len(username) < 3:
        return False, "Username must be at least 3 characters"

    if len(password) < 4:
        return False, "Password must be at least 4 characters"

    users = _load_users()
    username_lower = username.lower()

    if username_lower in users:
        return False, "Username already exists"

    users[username_lower] = {
        "username": username_lower,
        "display_name": display_name or username,
        "password_hash": _hash_password(password),
    }

    if _save_users(users):
        logger.info(f"New user created: {username}")
        return True, "Account created successfully"

    return False, "Error creating account"


def get_user_display_name(username: str) -> str:
    """Get the display name for a user."""
    users = _load_users()
    user = users.get(username.lower(), {})
    return user.get("display_name", username)


def user_exists(username: str) -> bool:
    """Check if a user exists."""
    users = _load_users()
    return username.lower() in users


def change_password(username: str, old_password: str, new_password: str) -> tuple[bool, str]:
    """
    Change a user's password.

    Returns (success, message) tuple.
    """
    if not authenticate(username, old_password):
        return False, "Current password is incorrect"

    if len(new_password) < 4:
        return False, "New password must be at least 4 characters"

    users = _load_users()
    username_lower = username.lower()

    if username_lower not in users:
        return False, "User not found"

    users[username_lower]["password_hash"] = _hash_password(new_password)

    if _save_users(users):
        logger.info(f"Password changed for user: {username}")
        return True, "Password changed successfully"

    return False, "Error changing password"


def delete_user(username: str) -> bool:
    """Delete a user account."""
    users = _load_users()
    username_lower = username.lower()

    if username_lower not in users:
        return False

    del users[username_lower]

    if _save_users(users):
        logger.info(f"User deleted: {username}")
        return True

    return False


def list_users() -> list[str]:
    """List all usernames."""
    users = _load_users()
    return list(users.keys())


# Create a default admin user if no users exist
def ensure_default_user():
    """Create a default user if none exist."""
    users = _load_users()
    if not users:
        create_user("admin", "admin", "Administrator")
        logger.info("Default admin user created (username: admin, password: admin)")
