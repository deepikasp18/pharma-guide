"""
Patient context management API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from src.auth.dependencies import get_current_user
from src.models.user import User
from src.database import patient_profiles, medications, symptoms

router = APIRouter(prefix="/patient", tags=["patient"])


class PatientProfileRequest(BaseModel):
    """Patient profile request model"""
    name: str
    age: int
    gender: str
    weight: float
    height: float
    conditions: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)


class PatientProfileResponse(BaseModel):
    """Patient profile response model"""
    patient_id: str
    user_id: str
    name: str
    age: int
    gender: str
    weight: float
    height: float
    conditions: List[str]
    allergies: List[str]
    created_at: str
    updated_at: str


class MedicationRequest(BaseModel):
    """Medication request model"""
    name: str
    dosage: str
    frequency: str
    startDate: str


class MedicationResponse(BaseModel):
    """Medication response model"""
    id: str
    name: str
    dosage: str
    frequency: str
    startDate: str
    user_id: str
    created_at: str


class SymptomRequest(BaseModel):
    """Symptom request model"""
    name: str
    severity: int
    date: str
    notes: Optional[str] = None


class SymptomResponse(BaseModel):
    """Symptom response model"""
    id: str
    name: str
    severity: int
    date: str
    notes: Optional[str]
    user_id: str
    created_at: str


@router.get("/profile", response_model=Optional[PatientProfileResponse])
async def get_profile(current_user: User = Depends(get_current_user)):
    """
    Get patient profile for current user
    
    Returns None if no profile exists (not an error)
    """
    profile = patient_profiles.get_profile_by_user_id(current_user.id)
    if not profile:
        return None
    return PatientProfileResponse(**profile)


@router.post("/profile", response_model=PatientProfileResponse)
async def create_or_update_profile(
    request: PatientProfileRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create or update patient profile
    
    Stores patient information and establishes personalization context
    for knowledge graph queries.
    """
    try:
        profile_data = request.model_dump()
        profile = patient_profiles.create_or_update_profile(current_user.id, profile_data)
        return PatientProfileResponse(**profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating profile: {str(e)}")


@router.get("/medications", response_model=List[MedicationResponse])
async def get_medications(current_user: User = Depends(get_current_user)):
    """
    Get all medications for current user
    
    Returns empty list if no medications exist
    """
    meds = medications.get_medications_by_user_id(current_user.id)
    return [MedicationResponse(**med) for med in meds]


@router.post("/medications", response_model=MedicationResponse)
async def add_medication(
    request: MedicationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Add a medication for current user
    """
    try:
        medication_data = request.model_dump()
        medication = medications.add_medication(current_user.id, medication_data)
        return MedicationResponse(**medication)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding medication: {str(e)}")


@router.delete("/medications/{medication_id}")
async def delete_medication(
    medication_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a medication
    """
    success = medications.delete_medication(current_user.id, medication_id)
    if not success:
        raise HTTPException(status_code=404, detail="Medication not found")
    return {"status": "success", "message": "Medication deleted"}


@router.get("/symptoms", response_model=List[SymptomResponse])
async def get_symptoms(current_user: User = Depends(get_current_user)):
    """
    Get all symptoms for current user
    
    Returns empty list if no symptoms exist
    """
    symp = symptoms.get_symptoms_by_user_id(current_user.id)
    return [SymptomResponse(**s) for s in symp]


@router.post("/symptoms", response_model=SymptomResponse)
async def add_symptom(
    request: SymptomRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Add a symptom for current user
    """
    try:
        symptom_data = request.model_dump()
        symptom = symptoms.add_symptom(current_user.id, symptom_data)
        return SymptomResponse(**symptom)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding symptom: {str(e)}")


@router.delete("/symptoms/{symptom_id}")
async def delete_symptom(
    symptom_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a symptom
    """
    success = symptoms.delete_symptom(current_user.id, symptom_id)
    if not success:
        raise HTTPException(status_code=404, detail="Symptom not found")
    return {"status": "success", "message": "Symptom deleted"}
