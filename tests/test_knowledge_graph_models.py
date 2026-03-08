"""
Tests for knowledge graph entity models
"""
import pytest
from datetime import datetime
from src.knowledge_graph.models import (
    DrugEntity, SideEffectEntity, InteractionEntity, PatientContext,
    CausesRelationship, SeverityLevel, FrequencyCategory
)
from src.knowledge_graph.validators import EntityValidator
from src.knowledge_graph.serializers import EntitySerializer

class TestDrugEntity:
    """Test DrugEntity model"""
    
    def test_create_drug_entity(self):
        """Test creating a drug entity"""
        drug = DrugEntity(
            id="drug-1",
            name="Lisinopril",
            generic_name="lisinopril",
            drugbank_id="DB00722",
            rxcui="29046"
        )
        
        assert drug.id == "drug-1"
        assert drug.name == "Lisinopril"
        assert drug.generic_name == "lisinopril"
        assert drug.drugbank_id == "DB00722"
        assert drug.rxcui == "29046"
        assert isinstance(drug.created_at, datetime)
    
    def test_drug_entity_with_optional_fields(self):
        """Test drug entity with optional fields"""
        drug = DrugEntity(
            id="drug-2",
            name="Aspirin",
            generic_name="acetylsalicylic acid",
            atc_codes=["N02BA01"],
            mechanism="COX inhibition",
            indications=["pain relief", "fever reduction"],
            contraindications=["bleeding disorders"]
        )
        
        assert len(drug.atc_codes) == 1
        assert drug.mechanism == "COX inhibition"
        assert len(drug.indications) == 2
        assert len(drug.contraindications) == 1

class TestSideEffectEntity:
    """Test SideEffectEntity model"""
    
    def test_create_side_effect_entity(self):
        """Test creating a side effect entity"""
        side_effect = SideEffectEntity(
            id="se-1",
            name="Headache",
            meddra_code="10019211",
            severity=SeverityLevel.MINOR,
            frequency_category=FrequencyCategory.COMMON
        )
        
        assert side_effect.id == "se-1"
        assert side_effect.name == "Headache"
        assert side_effect.meddra_code == "10019211"
        assert side_effect.severity == SeverityLevel.MINOR
        assert side_effect.frequency_category == FrequencyCategory.COMMON

class TestInteractionEntity:
    """Test InteractionEntity model"""
    
    def test_create_interaction_entity(self):
        """Test creating an interaction entity"""
        interaction = InteractionEntity(
            id="int-1",
            drug_a_id="drug-1",
            drug_b_id="drug-2",
            severity=SeverityLevel.MODERATE,
            mechanism="CYP450 inhibition",
            clinical_effect="Increased drug levels"
        )
        
        assert interaction.id == "int-1"
        assert interaction.drug_a_id == "drug-1"
        assert interaction.drug_b_id == "drug-2"
        assert interaction.severity == SeverityLevel.MODERATE

class TestPatientContext:
    """Test PatientContext model"""
    
    def test_create_patient_context(self):
        """Test creating a patient context"""
        patient = PatientContext(
            id="patient-1",
            demographics={"age": 65, "gender": "male", "weight": 80},
            conditions=["diabetes", "hypertension"],
            medications=[{"name": "lisinopril", "dosage": "10mg"}]
        )
        
        assert patient.id == "patient-1"
        assert patient.demographics["age"] == 65
        assert len(patient.conditions) == 2
        assert len(patient.medications) == 1

class TestCausesRelationship:
    """Test CausesRelationship model"""
    
    def test_create_causes_relationship(self):
        """Test creating a causes relationship"""
        relationship = CausesRelationship(
            drug_id="drug-1",
            side_effect_id="se-1",
            frequency=0.15,
            confidence=0.85,
            evidence_sources=["FAERS", "SIDER"]
        )
        
        assert relationship.drug_id == "drug-1"
        assert relationship.side_effect_id == "se-1"
        assert relationship.frequency == 0.15
        assert relationship.confidence == 0.85
        assert len(relationship.evidence_sources) == 2

class TestEntityValidator:
    """Test entity validation utilities"""
    
    def test_validate_drug_name(self):
        """Test drug name validation"""
        # Valid names
        assert EntityValidator.validate_drug_name("Lisinopril") == "Lisinopril"
        assert EntityValidator.validate_drug_name("  Aspirin  ") == "Aspirin"
        
        # Invalid names
        with pytest.raises(ValueError):
            EntityValidator.validate_drug_name("")
        with pytest.raises(ValueError):
            EntityValidator.validate_drug_name("   ")
    
    def test_validate_drugbank_id(self):
        """Test DrugBank ID validation"""
        # Valid IDs
        assert EntityValidator.validate_drugbank_id("DB00722") == "DB00722"
        assert EntityValidator.validate_drugbank_id(None) is None
        
        # Invalid IDs
        with pytest.raises(ValueError):
            EntityValidator.validate_drugbank_id("DB722")
        with pytest.raises(ValueError):
            EntityValidator.validate_drugbank_id("XB00722")
    
    def test_validate_confidence_score(self):
        """Test confidence score validation"""
        # Valid scores
        assert EntityValidator.validate_confidence_score(0.5) == 0.5
        assert EntityValidator.validate_confidence_score(0.0) == 0.0
        assert EntityValidator.validate_confidence_score(1.0) == 1.0
        
        # Invalid scores
        with pytest.raises(ValueError):
            EntityValidator.validate_confidence_score(-0.1)
        with pytest.raises(ValueError):
            EntityValidator.validate_confidence_score(1.1)

class TestEntitySerializer:
    """Test entity serialization utilities"""
    
    def test_serialize_drug_entity(self):
        """Test drug entity serialization"""
        drug = DrugEntity(
            id="drug-1",
            name="Lisinopril",
            generic_name="lisinopril"
        )
        
        # Test to_dict
        drug_dict = EntitySerializer.to_dict(drug)
        assert drug_dict["id"] == "drug-1"
        assert drug_dict["name"] == "Lisinopril"
        
        # Test to_json
        drug_json = EntitySerializer.to_json(drug)
        assert isinstance(drug_json, str)
        assert "drug-1" in drug_json
        
        # Test from_dict
        recreated_drug = EntitySerializer.from_dict(drug_dict, "drug")
        assert recreated_drug.id == drug.id
        assert recreated_drug.name == drug.name
    
    def test_serialize_patient_context(self):
        """Test patient context serialization"""
        patient = PatientContext(
            id="patient-1",
            demographics={"age": 65, "gender": "male"},
            conditions=["diabetes"]
        )
        
        patient_dict = EntitySerializer.to_dict(patient)
        assert patient_dict["demographics"]["age"] == 65
        
        recreated_patient = EntitySerializer.from_dict(patient_dict, "patient")
        assert recreated_patient.demographics["age"] == 65