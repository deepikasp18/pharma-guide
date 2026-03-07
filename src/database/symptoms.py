"""
In-memory symptom storage
"""
from typing import Dict, List
from datetime import datetime

# In-memory storage: {user_id: [symptoms]}
_symptoms: Dict[str, List[Dict]] = {}


def add_symptom(user_id: str, symptom_data: Dict) -> Dict:
    """Add a symptom for a user"""
    if user_id not in _symptoms:
        _symptoms[user_id] = []
    
    symptom_data["id"] = f"symptom_{user_id}_{len(_symptoms[user_id])}_{datetime.utcnow().timestamp()}"
    symptom_data["user_id"] = user_id
    symptom_data["created_at"] = datetime.utcnow().isoformat()
    
    _symptoms[user_id].append(symptom_data)
    return symptom_data


def get_symptoms_by_user_id(user_id: str) -> List[Dict]:
    """Get all symptoms for a user"""
    return _symptoms.get(user_id, [])


def delete_symptom(user_id: str, symptom_id: str) -> bool:
    """Delete a symptom"""
    if user_id not in _symptoms:
        return False
    
    original_length = len(_symptoms[user_id])
    _symptoms[user_id] = [s for s in _symptoms[user_id] if s["id"] != symptom_id]
    return len(_symptoms[user_id]) < original_length
