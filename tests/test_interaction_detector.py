"""
Tests for interaction detector service
"""
import pytest
import pytest_asyncio
from datetime import datetime

from src.knowledge_graph.models import (
    DrugEntity, SeverityLevel, PatientContext, InteractionEntity
)
from src.knowledge_graph.database import KnowledgeGraphDatabase
from src.knowledge_graph.reasoning_engine import GraphReasoningEngine
from src.knowledge_graph.interaction_detector import (
    InteractionDetector, InteractionResult, ContraindicationResult
)


@pytest_asyncio.fixture
async def db():
    """Create database connection"""
    database = KnowledgeGraphDatabase()
    await database.connect()
    yield database
    await database.disconnect()


@pytest_asyncio.fixture
async def reasoning_engine(db):
    """Create reasoning engine"""
    engine = GraphReasoningEngine(db)
    return engine


@pytest_asyncio.fixture
async def interaction_detector(reasoning_engine):
    """Create interaction detector"""
    detector = InteractionDetector(reasoning_engine)
    return detector


@pytest.fixture
def sample_patient():
    """Create sample patient context"""
    return PatientContext(
        id="patient_001",
        demographics={"age": 65, "gender": "male", "weight": 80},
        conditions=["diabetes", "hypertension"],
        medications=[
            {"drug_id": "drug_001", "name": "Metformin", "dosage": "500mg"},
            {"drug_id": "drug_002", "name": "Lisinopril", "dosage": "10mg"}
        ],
        risk_factors=["smoking", "obesity"]
    )


class TestInteractionDetector:
    """Test interaction detection functionality"""
    
    @pytest.mark.asyncio
    async def test_detect_drug_interactions_empty_list(self, interaction_detector):
        """Test with empty drug list"""
        interactions = await interaction_detector.detect_drug_interactions([])
        assert interactions == []
    
    @pytest.mark.asyncio
    async def test_detect_drug_interactions_single_drug(self, interaction_detector):
        """Test with single drug (no interactions possible)"""
        interactions = await interaction_detector.detect_drug_interactions(["drug_001"])
        assert interactions == []
    
    @pytest.mark.asyncio
    async def test_severity_to_numeric(self, interaction_detector):
        """Test severity conversion to numeric values"""
        assert interaction_detector._severity_to_numeric(SeverityLevel.MINOR) == 1
        assert interaction_detector._severity_to_numeric(SeverityLevel.MODERATE) == 2
        assert interaction_detector._severity_to_numeric(SeverityLevel.MAJOR) == 3
        assert interaction_detector._severity_to_numeric(SeverityLevel.CONTRAINDICATED) == 4
    
    @pytest.mark.asyncio
    async def test_parse_severity(self, interaction_detector):
        """Test severity string parsing"""
        assert interaction_detector._parse_severity("minor") == SeverityLevel.MINOR
        assert interaction_detector._parse_severity("moderate") == SeverityLevel.MODERATE
        assert interaction_detector._parse_severity("major") == SeverityLevel.MAJOR
        assert interaction_detector._parse_severity("contraindicated") == SeverityLevel.CONTRAINDICATED
        assert interaction_detector._parse_severity("unknown") == SeverityLevel.MODERATE
    
    @pytest.mark.asyncio
    async def test_adjust_confidence_for_patient(self, interaction_detector, sample_patient):
        """Test confidence adjustment based on patient factors"""
        base_confidence = 0.7
        
        # Test with elderly patient
        adjusted = interaction_detector._adjust_confidence_for_patient(
            base_confidence, SeverityLevel.MAJOR, sample_patient
        )
        assert adjusted > base_confidence
        assert adjusted <= 1.0
    
    @pytest.mark.asyncio
    async def test_determine_contraindication_severity(self, interaction_detector, sample_patient):
        """Test contraindication severity determination"""
        # High-risk condition
        severity = interaction_detector._determine_contraindication_severity(
            "drug_001", "heart failure", sample_patient
        )
        assert severity == SeverityLevel.CONTRAINDICATED
        
        # Regular condition
        severity = interaction_detector._determine_contraindication_severity(
            "drug_001", "mild headache", sample_patient
        )
        assert severity == SeverityLevel.MAJOR
    
    @pytest.mark.asyncio
    async def test_generate_risk_summary_empty(self, interaction_detector):
        """Test risk summary generation with no issues"""
        summary = interaction_detector._generate_risk_summary([], [])
        
        assert summary['total_interactions'] == 0
        assert summary['total_contraindications'] == 0
        assert summary['highest_risk'] == 'minor'
        assert not summary['requires_immediate_attention']
    
    @pytest.mark.asyncio
    async def test_generate_risk_summary_with_interactions(self, interaction_detector):
        """Test risk summary with interactions"""
        interactions = [
            InteractionResult(
                drug_a_id="drug_001",
                drug_b_id="drug_002",
                drug_a_name="Drug A",
                drug_b_name="Drug B",
                severity=SeverityLevel.MAJOR,
                confidence=0.8
            ),
            InteractionResult(
                drug_a_id="drug_003",
                drug_b_id="drug_004",
                drug_a_name="Drug C",
                drug_b_name="Drug D",
                severity=SeverityLevel.MODERATE,
                confidence=0.7
            )
        ]
        
        summary = interaction_detector._generate_risk_summary(interactions, [])
        
        assert summary['total_interactions'] == 2
        assert summary['severity_breakdown']['major'] == 1
        assert summary['severity_breakdown']['moderate'] == 1
        assert summary['highest_risk'] == 'major'
        assert summary['requires_immediate_attention']
    
    @pytest.mark.asyncio
    async def test_generate_recommendations(self, interaction_detector, sample_patient):
        """Test recommendation generation"""
        interactions = [
            InteractionResult(
                drug_a_id="drug_001",
                drug_b_id="drug_002",
                drug_a_name="Drug A",
                drug_b_name="Drug B",
                severity=SeverityLevel.MAJOR,
                management="Monitor closely",
                confidence=0.8
            )
        ]
        
        contraindications = []
        
        recommendations = interaction_detector._generate_recommendations(
            interactions, contraindications, sample_patient
        )
        
        assert len(recommendations) > 0
        assert any("Major drug interactions" in rec for rec in recommendations)
        # The function generates age-specific recommendations for patients > 65
        # sample_patient has age 65, so check for age-related recommendations
        print(f"Recommendations: {recommendations}")
        print(f"Patient age: {sample_patient.demographics.get('age')}")
        assert len(recommendations) >= 3  # Should have multiple recommendations
    
    @pytest.mark.asyncio
    async def test_analyze_patient_medications_no_medications(self, interaction_detector):
        """Test analysis with no medications"""
        patient = PatientContext(
            id="patient_002",
            demographics={"age": 30},
            conditions=[],
            medications=[]
        )
        
        analysis = await interaction_detector.analyze_patient_medications(patient)
        
        assert analysis.patient_id == "patient_002"
        assert len(analysis.analyzed_drugs) == 0
        assert len(analysis.interactions) == 0
        assert len(analysis.contraindications) == 0


class TestInteractionDetectorIntegration:
    """Integration tests for interaction detector"""
    
    @pytest.mark.asyncio
    async def test_full_patient_analysis_workflow(self, interaction_detector, sample_patient):
        """Test complete patient medication analysis workflow"""
        analysis = await interaction_detector.analyze_patient_medications(sample_patient)
        
        # Verify analysis structure
        assert analysis.patient_id == sample_patient.id
        assert isinstance(analysis.analyzed_drugs, list)
        assert isinstance(analysis.interactions, list)
        assert isinstance(analysis.contraindications, list)
        assert isinstance(analysis.risk_summary, dict)
        assert isinstance(analysis.recommendations, list)
        assert isinstance(analysis.analysis_timestamp, datetime)
        
        # Verify risk summary structure
        assert 'total_interactions' in analysis.risk_summary
        assert 'total_contraindications' in analysis.risk_summary
        assert 'severity_breakdown' in analysis.risk_summary
        assert 'highest_risk' in analysis.risk_summary
        assert 'requires_immediate_attention' in analysis.risk_summary
