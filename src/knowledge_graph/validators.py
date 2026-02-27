"""
Validation utilities for knowledge graph entities
"""
import re
from typing import Any, Dict, List, Optional
from pydantic import field_validator
from .models import DrugEntity, SideEffectEntity, PatientContext

class EntityValidator:
    """Validation utilities for knowledge graph entities"""
    
    @staticmethod
    def validate_drug_name(name: str) -> str:
        """Validate drug name format"""
        if not name or len(name.strip()) == 0:
            raise ValueError("Drug name cannot be empty")
        
        # Remove extra whitespace
        name = name.strip()
        
        # Check for reasonable length
        if len(name) > 200:
            raise ValueError("Drug name too long")
            
        return name
    
    @staticmethod
    def validate_drugbank_id(drugbank_id: Optional[str]) -> Optional[str]:
        """Validate DrugBank ID format (DB followed by 5 digits)"""
        if drugbank_id is None:
            return None
            
        pattern = r'^DB\d{5}$'
        if not re.match(pattern, drugbank_id):
            raise ValueError(f"Invalid DrugBank ID format: {drugbank_id}")
            
        return drugbank_id
    
    @staticmethod
    def validate_rxcui(rxcui: Optional[str]) -> Optional[str]:
        """Validate RxCUI format (numeric string)"""
        if rxcui is None:
            return None
            
        if not rxcui.isdigit():
            raise ValueError(f"Invalid RxCUI format: {rxcui}")
            
        return rxcui
    
    @staticmethod
    def validate_meddra_code(meddra_code: Optional[str]) -> Optional[str]:
        """Validate MedDRA code format"""
        if meddra_code is None:
            return None
            
        # MedDRA codes are typically 8-digit numbers
        if not meddra_code.isdigit() or len(meddra_code) != 8:
            raise ValueError(f"Invalid MedDRA code format: {meddra_code}")
            
        return meddra_code
    
    @staticmethod
    def validate_patient_demographics(demographics: Dict[str, Any]) -> Dict[str, Any]:
        """Validate patient demographics"""
        if not demographics:
            return demographics
            
        # Validate age
        if 'age' in demographics:
            age = demographics['age']
            if not isinstance(age, (int, float)) or age < 0 or age > 150:
                raise ValueError(f"Invalid age: {age}")
        
        # Validate weight
        if 'weight' in demographics:
            weight = demographics['weight']
            if not isinstance(weight, (int, float)) or weight <= 0 or weight > 1000:
                raise ValueError(f"Invalid weight: {weight}")
        
        # Validate gender
        if 'gender' in demographics:
            gender = demographics['gender'].lower()
            valid_genders = ['male', 'female', 'other', 'unknown']
            if gender not in valid_genders:
                raise ValueError(f"Invalid gender: {gender}")
            demographics['gender'] = gender
            
        return demographics
    
    @staticmethod
    def validate_confidence_score(score: float) -> float:
        """Validate confidence score is between 0 and 1"""
        if not isinstance(score, (int, float)):
            raise ValueError("Confidence score must be numeric")
            
        if score < 0.0 or score > 1.0:
            raise ValueError(f"Confidence score must be between 0 and 1: {score}")
            
        return float(score)
    
    @staticmethod
    def validate_frequency(frequency: float) -> float:
        """Validate frequency is between 0 and 1"""
        if not isinstance(frequency, (int, float)):
            raise ValueError("Frequency must be numeric")
            
        if frequency < 0.0 or frequency > 1.0:
            raise ValueError(f"Frequency must be between 0 and 1: {frequency}")
            
        return float(frequency)

# Add validators to models using Pydantic's field_validator decorator
def add_drug_validators():
    """Add validators to DrugEntity"""
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        return EntityValidator.validate_drug_name(v)
    
    @field_validator('drugbank_id')
    @classmethod
    def validate_drugbank_id(cls, v):
        return EntityValidator.validate_drugbank_id(v)
    
    @field_validator('rxcui')
    @classmethod
    def validate_rxcui(cls, v):
        return EntityValidator.validate_rxcui(v)
    
    # Apply validators to DrugEntity
    DrugEntity.validate_name = validate_name
    DrugEntity.validate_drugbank_id = validate_drugbank_id
    DrugEntity.validate_rxcui = validate_rxcui

def add_side_effect_validators():
    """Add validators to SideEffectEntity"""
    
    @field_validator('meddra_code')
    @classmethod
    def validate_meddra_code(cls, v):
        return EntityValidator.validate_meddra_code(v)
    
    # Apply validator to SideEffectEntity
    SideEffectEntity.validate_meddra_code = validate_meddra_code

def add_patient_validators():
    """Add validators to PatientContext"""
    
    @field_validator('demographics')
    @classmethod
    def validate_demographics(cls, v):
        return EntityValidator.validate_patient_demographics(v)
    
    # Apply validator to PatientContext
    PatientContext.validate_demographics = validate_demographics

# Initialize validators
add_drug_validators()
add_side_effect_validators()
add_patient_validators()