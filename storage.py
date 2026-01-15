"""JSON file-based storage for user state persistence."""

import json
from pathlib import Path
from typing import Optional

from state import TravelState, get_default_user_state

DATA_DIR = Path(__file__).parent / "data"


def ensure_data_dir() -> None:
    """Ensure the data directory exists."""
    DATA_DIR.mkdir(exist_ok=True)


def get_user_file_path(user_id: str) -> Path:
    """Get the file path for a user's state."""
    return DATA_DIR / f"{user_id}.json"


def load_user_state(user_id: str) -> TravelState:
    """Load user state from JSON file, or create default if not exists."""
    ensure_data_dir()
    file_path = get_user_file_path(user_id)

    if file_path.exists():
        with open(file_path, "r") as f:
            data = json.load(f)
        return TravelState.from_dict(data)

    # Create default state for new users
    state = get_default_user_state()
    save_user_state(user_id, state)
    return state


def save_user_state(user_id: str, state: TravelState) -> None:
    """Save user state to JSON file."""
    ensure_data_dir()
    file_path = get_user_file_path(user_id)

    with open(file_path, "w") as f:
        json.dump(state.to_dict(), f, indent=2)


def list_users() -> list[str]:
    """List all user IDs with saved state."""
    ensure_data_dir()
    return [f.stem for f in DATA_DIR.glob("*.json")]


def delete_user_state(user_id: str) -> bool:
    """Delete a user's state file. Returns True if deleted, False if not found."""
    file_path = get_user_file_path(user_id)
    if file_path.exists():
        file_path.unlink()
        return True
    return False
