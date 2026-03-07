"""
User database operations
"""
from datetime import datetime
from typing import Dict, Optional
import uuid

# In-memory user storage (replace with actual database in production)
users_db: Dict[str, dict] = {}


def create_user(username: str, hashed_password: str) -> dict:
    """Create a new user"""
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "username": username,
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow().isoformat()
    }
    users_db[username] = user
    return user


def get_user_by_username(username: str) -> Optional[dict]:
    """Get user by username"""
    return users_db.get(username)


def username_exists(username: str) -> bool:
    """Check if username already exists"""
    return username in users_db
