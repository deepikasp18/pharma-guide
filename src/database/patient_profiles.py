"""
In-memory patient profile storage
"""
from typing import Dict, Optional, List
from datetime import datetime

# In-memory storage: {user_id: profile_data}
_profiles: Dict[str, Dict] = {}


def create_or_update_profile(user_id: str, profile_data: Dict) -> Dict:
    """Create or update a patient profile"""
    profile_data["user_id"] = user_id
    profile_data["updated_at"] = datetime.utcnow().isoformat()
    
    if user_id not in _profiles:
        profile_data["created_at"] = datetime.utcnow().isoformat()
        profile_data["patient_id"] = f"patient_{user_id}"
    else:
        profile_data["created_at"] = _profiles[user_id].get("created_at")
        profile_data["patient_id"] = _profiles[user_id].get("patient_id")
    
    _profiles[user_id] = profile_data
    return profile_data


def get_profile_by_user_id(user_id: str) -> Optional[Dict]:
    """Get patient profile by user_id"""
    return _profiles.get(user_id)


def profile_exists(user_id: str) -> bool:
    """Check if profile exists for user"""
    return user_id in _profiles
