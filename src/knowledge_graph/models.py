"""
Core knowledge graph entity models for PharmaGuide
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum

class SeverityLevel(str, Enum):
    """Severity levels for interactions and side effects"""
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CONTRAINDICATED = "contraindicated"

class FrequencyCategory(str, Enum):
    """Frequency categories for side effects"""
    VERY_COMMON = "very_common"  # ≥1/10
    COMMON = "common"  # ≥1/100 to <1/10
    UNCOMMON = "uncommon"  # ≥1/1,000 to <1/100
    RARE = "rare"  # ≥1/10,000 to <1/1,000
    VERY_RARE = "very_rare"  # <1/10,000
    UNKNOWN = "unknown"

class DrugEntity(BaseModel):
    """Drug entity model"""
    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Brand name")
    generic_name: str = Field(..., description="Generic/chemical name")
    drugbank_id: Optional[str] = Field(None, description="DrugBank identifier")
    rxcui: Optional[str] = Field(None, description="RxNorm concept identifier")
    atc_codes: List[str] = Field(default_factory=list, description="Anatomical Therapeutic Chemical codes")
    mechanism: Optional[str] = Field(None, description="Mechanism of action")
    pharmacokinetics: Dict[str, Any] = Field(default_factory=dict, description="ADME properties")
    indications: List[str] = Field(default_factory=list, description="Approved uses")
    contraindications: List[str] = Field(default_factory=list, description="Contraindications")
    dosage_forms: List[str] = Field(default_factory=list, description="Available formulations")
    created_from: List[str] = Field(default_factory=list, description="Source datasets")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SideEffectEntity(BaseModel):
    """Side effect entity model"""
    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Side effect name")
    meddra_code: Optional[str] = Field(None, description="MedDRA terminology code")
    severity: Optional[SeverityLevel] = Field(None, description="Severity classification")
    frequency_category: Optional[FrequencyCategory] = Field(None, description="Frequency category")
    system_organ_class: Optional[str] = Field(None, description="Affected body system")
    description: Optional[str] = Field(None, description="Detailed description")
    created_from: List[str] = Field(default_factory=list, description="Source datasets")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CausesRelationship(BaseModel):
    """Drug-SideEffect relationship model"""
    drug_id: str = Field(..., description="Source drug entity")
    side_effect_id: str = Field(..., description="Target side effect entity")
    frequency: float = Field(..., ge=0.0, le=1.0, description="Occurrence frequency (0-1)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Evidence confidence (0-1)")
    evidence_sources: List[str] = Field(default_factory=list, description="Supporting datasets")
    patient_count: Optional[int] = Field(None, description="Number of patients reporting")
    statistical_significance: Optional[float] = Field(None, description="P-value or similar")
    temporal_relationship: Optional[str] = Field(None, description="Timing of occurrence")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class InteractionEntity(BaseModel):
    """Drug interaction entity model"""
    id: str = Field(..., description="Unique identifier")
    drug_a_id: str = Field(..., description="First drug")
    drug_b_id: str = Field(..., description="Second drug")
    severity: SeverityLevel = Field(..., description="Interaction severity")
    mechanism: Optional[str] = Field(None, description="Interaction mechanism")
    clinical_effect: Optional[str] = Field(None, description="Expected clinical outcome")
    management: Optional[str] = Field(None, description="Management recommendations")
    evidence_level: Optional[str] = Field(None, description="Quality of evidence")
    onset: Optional[str] = Field(None, description="Rapid, delayed, not specified")
    documentation: Optional[str] = Field(None, description="Well-documented, probable, possible")
    created_from: List[str] = Field(default_factory=list, description="Source datasets")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class PatientContext(BaseModel):
    """Patient context model for personalization"""
    id: str = Field(..., description="Patient identifier")
    demographics: Dict[str, Any] = Field(default_factory=dict, description="Age, gender, weight, height")
    conditions: List[str] = Field(default_factory=list, description="Current medical conditions")
    medications: List[Dict[str, Any]] = Field(default_factory=list, description="Current medications with dosing")
    allergies: List[str] = Field(default_factory=list, description="Known drug allergies")
    genetic_factors: Dict[str, Any] = Field(default_factory=dict, description="Pharmacogenomic information")
    risk_factors: List[str] = Field(default_factory=list, description="Clinical and lifestyle risks")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences and settings")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SemanticQuery(BaseModel):
    """Semantic query model"""
    id: str = Field(..., description="Query identifier")
    patient_id: Optional[str] = Field(None, description="Associated patient")
    raw_query: str = Field(..., description="Original natural language query")
    intent: Optional[str] = Field(None, description="Classified intent type")
    entities: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted medical entities")
    cypher_query: Optional[str] = Field(None, description="Generated graph query")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Query understanding confidence")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class GraphResponse(BaseModel):
    """Knowledge graph response model"""
    query_id: str = Field(..., description="Associated query")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Query results")
    evidence_paths: List[List[str]] = Field(default_factory=list, description="Graph traversal paths")
    confidence_scores: Dict[str, float] = Field(default_factory=dict, description="Confidence for each result")
    data_sources: List[str] = Field(default_factory=list, description="Contributing datasets")
    reasoning_steps: List[str] = Field(default_factory=list, description="Explanation of reasoning")
    personalization_factors: List[str] = Field(default_factory=list, description="Applied patient factors")
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class EvidenceProvenance(BaseModel):
    """Evidence provenance model"""
    id: str = Field(..., description="Evidence identifier")
    source_dataset: str = Field(..., description="Originating dataset")
    entity_ids: List[str] = Field(default_factory=list, description="Related entities")
    relationship_type: Optional[str] = Field(None, description="Type of relationship")
    evidence_strength: float = Field(..., ge=0.0, le=1.0, description="Strength of evidence (0-1)")
    publication_date: Optional[datetime] = Field(None, description="When evidence was published")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="When evidence was last verified")
    authority_score: float = Field(..., ge=0.0, le=1.0, description="Source authority weighting")
    patient_count: Optional[int] = Field(None, description="Number of patients in evidence")

class DatasetMetadata(BaseModel):
    """Dataset metadata model"""
    name: str = Field(..., description="Dataset name (OnSIDES, SIDER, etc.)")
    version: str = Field(..., description="Dataset version")
    last_updated: datetime = Field(..., description="Last update timestamp")
    record_count: int = Field(..., description="Number of records")
    entity_types: List[str] = Field(default_factory=list, description="Types of entities included")
    relationship_types: List[str] = Field(default_factory=list, description="Types of relationships")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality assessment")
    authority_level: str = Field(..., description="High, medium, low authority")
    license: Optional[str] = Field(None, description="Usage license")
    description: Optional[str] = Field(None, description="Dataset description")

class EntityMapping(BaseModel):
    """Entity mapping model for cross-dataset resolution"""
    source_id: str = Field(..., description="Original entity ID from dataset")
    canonical_id: str = Field(..., description="Unified entity ID in knowledge graph")
    source_dataset: str = Field(..., description="Originating dataset")
    entity_type: str = Field(..., description="Drug, condition, side effect, etc.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Mapping confidence")
    mapping_method: str = Field(..., description="How mapping was determined")
    verified: bool = Field(default=False, description="Whether mapping was manually verified")
    created_at: datetime = Field(default_factory=datetime.utcnow)