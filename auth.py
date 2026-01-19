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


# Try to load users from Streamlit secrets, fall back to local defaults
def _get_default_users() -> list:
    """Get default users from Streamlit secrets or fallback to local config."""
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'users' in st.secrets:
            # Convert from Streamlit secrets format to list of dicts
            return [dict(user) for user in st.secrets['users']]
    except Exception:
        pass

    # Fallback for local development (or if secrets not configured)
    # You can keep a minimal admin user here for local testing
    return [
        {
            "username": "admin",
            "password": "admin",
            "display_name": "Administrator",
            "home_airport": "SFO",
            "home_city": "San Francisco",
        },
    ]


# Load users (cached at module level)
DEFAULT_USERS = _get_default_users()


def get_default_user_profile(username: str) -> dict:
    """Get the default profile for a user if they're in the default users list."""
    for user in DEFAULT_USERS:
        if user["username"].lower() == username.lower():
            return {
                "home_airport": user.get("home_airport", ""),
                "home_city": user.get("home_city", ""),
                "display_name": user.get("display_name", ""),
            }
    return {}


def ensure_default_user():
    """Create default users if they don't exist."""
    users = _load_users()

    for default_user in DEFAULT_USERS:
        username = default_user["username"].lower()
        if username not in users:
            create_user(
                default_user["username"],
                default_user["password"],
                default_user["display_name"]
            )
            logger.info(f"Default user created: {default_user['username']}")
