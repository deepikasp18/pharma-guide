"""
Pytest configuration and fixtures
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app

@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)

@pytest.fixture
def sample_drug_entity():
    """Sample drug entity for testing"""
    return {
        "id": "test-drug-1",
        "name": "Lisinopril",
        "generic_name": "lisinopril",
        "drugbank_id": "DB00722",
        "rxcui": "29046"
    }

@pytest.fixture
def sample_patient_context():
    """Sample patient context for testing"""
    return {
        "id": "test-patient-1",
        "demographics": {"age": 65, "gender": "male", "weight": 80},
        "conditions": ["diabetes", "hypertension"],
        "medications": [{"name": "lisinopril", "dosage": "10mg", "frequency": "daily"}]
    }