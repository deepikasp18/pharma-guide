"""
In-memory medication storage
"""
from typing import Dict, List
from datetime import datetime

# In-memory storage: {user_id: [medications]}
_medications: Dict[str, List[Dict]] = {}


def add_medication(user_id: str, medication_data: Dict) -> Dict:
    """Add a medication for a user"""
    if user_id not in _medications:
        _medications[user_id] = []
    
    medication_data["id"] = f"med_{user_id}_{len(_medications[user_id])}_{datetime.utcnow().timestamp()}"
    medication_data["user_id"] = user_id
    medication_data["created_at"] = datetime.utcnow().isoformat()
    
    _medications[user_id].append(medication_data)
    return medication_data


def get_medications_by_user_id(user_id: str) -> List[Dict]:
    """Get all medications for a user"""
    return _medications.get(user_id, [])


def delete_medication(user_id: str, medication_id: str) -> bool:
    """Delete a medication"""
    if user_id not in _medications:
        return False
    
    original_length = len(_medications[user_id])
    _medications[user_id] = [m for m in _medications[user_id] if m["id"] != medication_id]
    return len(_medications[user_id]) < original_length
