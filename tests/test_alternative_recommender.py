"""
Tests for alternative medication recommender
"""
import pytest
import pytest_asyncio
from datetime import datetime

from src.knowledge_graph.models import (
    DrugEntity, SeverityLevel, PatientContext
)
from src.knowledge_graph.database import KnowledgeGraphDatabase
from src.knowledge_graph.reasoning_engine import GraphReasoningEngine
from src.knowledge_graph.interaction_detector import InteractionResult, ContraindicationResult
from src.knowledge_graph.alternative_recommender import (
    AlternativeRecommender, AlternativeMedication, ManagementStrategy
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
async def alternative_recommender(reasoning_engine):
    """Create alternative recommender"""
    recommender = AlternativeRecommender(reasoning_engine)
    return recommender


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
        risk_factors=["smoking"]
    )


@pytest.fixture
def sample_interaction():
    """Create sample interaction"""
    return InteractionResult(
        drug_a_id="drug_001",
        drug_b_id="drug_002",
        drug_a_name="Warfarin",
        drug_b_name="Aspirin",
        severity=SeverityLevel.MAJOR,
        mechanism="Increased bleeding risk",
        clinical_effect="Enhanced anticoagulation",
        management="Monitor INR closely",
        confidence=0.85
    )


@pytest.fixture
def sample_contraindication():
    """Create sample contraindication"""
    return ContraindicationResult(
        drug_id="drug_003",
        drug_name="Metformin",
        condition_id="kidney_failure",
        condition_name="kidney failure",
        severity=SeverityLevel.CONTRAINDICATED,
        reason="Risk of lactic acidosis",
        confidence=0.9
    )


class TestAlternativeRecommender:
    """Test alternative recommendation functionality"""
    
    @pytest.mark.asyncio
    async def test_calculate_drug_similarity_identical_indications(self, alternative_recommender):
        """Test similarity calculation with identical indications"""
        drug1 = {
            'id': 'drug_001',
            'indications': 'diabetes,hypertension',
            'atc_codes': ['A10BA02'],
            'mechanism': 'reduces glucose production'
        }
        drug2 = {
            'id': 'drug_002',
            'indications': 'diabetes,hypertension',
            'atc_codes': ['A10BA02'],
            'mechanism': 'reduces glucose production'
        }
        
        similarity = alternative_recommender._calculate_drug_similarity(drug1, drug2)
        assert similarity > 0.8
    
    @pytest.mark.asyncio
    async def test_calculate_drug_similarity_different_drugs(self, alternative_recommender):
        """Test similarity calculation with different drugs"""
        drug1 = {
            'id': 'drug_001',
            'indications': 'diabetes',
            'atc_codes': ['A10BA02'],
            'mechanism': 'reduces glucose'
        }
        drug2 = {
            'id': 'drug_002',
            'indications': 'pain',
            'atc_codes': ['N02BE01'],
            'mechanism': 'inhibits prostaglandins'
        }
        
        similarity = alternative_recommender._calculate_drug_similarity(drug1, drug2)
        assert similarity < 0.5
    
    @pytest.mark.asyncio
    async def test_calculate_safety_score_no_contraindications(self, alternative_recommender):
        """Test safety score with no contraindications"""
        # Use a patient without conditions to test baseline safety
        patient = PatientContext(
            id="patient_test",
            demographics={"age": 30, "gender": "male"},
            conditions=[],
            medications=[]
        )
        
        drug = {
            'id': 'drug_001',
            'contraindications': ''
        }
        
        safety_score = await alternative_recommender._calculate_safety_score(drug, patient)
        assert safety_score >= 0.9
    
    @pytest.mark.asyncio
    async def test_calculate_safety_score_with_contraindications(self, alternative_recommender, sample_patient):
        """Test safety score with contraindications"""
        drug = {
            'id': 'drug_001',
            'contraindications': 'diabetes,hypertension'
        }
        
        safety_score = await alternative_recommender._calculate_safety_score(drug, sample_patient)
        assert safety_score < 0.8
    
    @pytest.mark.asyncio
    async def test_generate_alternative_reasons(self, alternative_recommender):
        """Test generation of alternative reasons"""
        original_drug = {
            'id': 'drug_001',
            'indications': 'diabetes',
            'atc_codes': ['A10BA02']
        }
        alternative_drug = {
            'id': 'drug_002',
            'indications': 'diabetes',
            'atc_codes': ['A10BA02']
        }
        
        reasons = alternative_recommender._generate_alternative_reasons(
            original_drug, alternative_drug, 0.85
        )
        
        assert len(reasons) > 0
        assert any('similar' in r.lower() for r in reasons)
    
    @pytest.mark.asyncio
    async def test_generate_alternative_advantages(self, alternative_recommender):
        """Test generation of alternative advantages"""
        drug = {
            'id': 'drug_001',
            'dosage_forms': ['tablet', 'liquid', 'injection']
        }
        
        advantages = alternative_recommender._generate_alternative_advantages(drug, 0.9)
        
        assert len(advantages) > 0
        assert any('safety' in adv.lower() for adv in advantages)
    
    @pytest.mark.asyncio
    async def test_generate_alternative_considerations(self, alternative_recommender, sample_patient):
        """Test generation of alternative considerations"""
        drug = {
            'id': 'drug_001',
            'generic_name': 'metformin',
            'dosage_forms': ['tablet', 'extended-release']
        }
        
        considerations = alternative_recommender._generate_alternative_considerations(
            drug, sample_patient
        )
        
        assert len(considerations) > 0
        # Check that considerations include relevant information
        assert any('metformin' in c.lower() or 'dosage' in c.lower() or 'elderly' in c.lower() for c in considerations)
    
    @pytest.mark.asyncio
    async def test_generate_management_strategies_contraindicated(
        self, alternative_recommender, sample_patient
    ):
        """Test management strategy generation for contraindicated interaction"""
        interaction = InteractionResult(
            drug_a_id="drug_001",
            drug_b_id="drug_002",
            drug_a_name="Drug A",
            drug_b_name="Drug B",
            severity=SeverityLevel.CONTRAINDICATED,
            confidence=0.9
        )
        
        strategies = await alternative_recommender._generate_management_strategies(
            interaction, sample_patient
        )
        
        assert len(strategies) > 0
        assert any(s.strategy_type == "alternative" for s in strategies)
    
    @pytest.mark.asyncio
    async def test_generate_management_strategies_major(
        self, alternative_recommender, sample_patient
    ):
        """Test management strategy generation for major interaction"""
        interaction = InteractionResult(
            drug_a_id="drug_001",
            drug_b_id="drug_002",
            drug_a_name="Drug A",
            drug_b_name="Drug B",
            severity=SeverityLevel.MAJOR,
            confidence=0.8
        )
        
        strategies = await alternative_recommender._generate_management_strategies(
            interaction, sample_patient
        )
        
        assert len(strategies) > 0
        assert any(s.strategy_type == "monitoring" for s in strategies)
    
    @pytest.mark.asyncio
    async def test_generate_contraindication_management(
        self, alternative_recommender, sample_contraindication, sample_patient
    ):
        """Test contraindication management strategy generation"""
        strategies = await alternative_recommender._generate_contraindication_management(
            sample_contraindication, sample_patient
        )
        
        assert len(strategies) > 0
        assert any(s.strategy_type == "alternative" for s in strategies)
        assert any("avoid" in s.description.lower() for s in strategies)
    
    @pytest.mark.asyncio
    async def test_generate_patient_notes(
        self, alternative_recommender, sample_interaction, sample_patient
    ):
        """Test patient note generation"""
        alternatives = [
            AlternativeMedication(
                drug_id="alt_001",
                drug_name="Alternative Drug",
                overall_score=0.8,
                confidence=0.8
            )
        ]
        
        notes = alternative_recommender._generate_patient_notes(
            sample_interaction, alternatives, sample_patient
        )
        
        assert len(notes) > 0
        assert any("healthcare provider" in note.lower() for note in notes)
    
    @pytest.mark.asyncio
    async def test_filter_contraindicated_drugs(self, alternative_recommender):
        """Test filtering of contraindicated drugs"""
        drugs = [
            {
                'id': 'drug_001',
                'contraindications': 'diabetes,hypertension'
            },
            {
                'id': 'drug_002',
                'contraindications': 'pregnancy'
            },
            {
                'id': 'drug_003',
                'contraindications': ''
            }
        ]
        
        filtered = await alternative_recommender._filter_contraindicated_drugs(
            drugs, 'diabetes'
        )
        
        # Should filter out drug_001 which has diabetes contraindication
        # Should keep drug_002 and drug_003
        assert len(filtered) >= 1
        assert 'drug_001' not in [d['id'] for d in filtered]
        assert 'drug_003' in [d['id'] for d in filtered]


class TestAlternativeRecommenderIntegration:
    """Integration tests for alternative recommender"""
    
    @pytest.mark.asyncio
    async def test_recommend_alternatives_for_interaction(
        self, alternative_recommender, sample_interaction, sample_patient
    ):
        """Test complete alternative recommendation for interaction"""
        recommendation = await alternative_recommender.recommend_alternatives_for_interaction(
            sample_interaction, sample_patient
        )
        
        # Verify recommendation structure
        assert recommendation.original_drug_id == sample_interaction.drug_a_id
        assert recommendation.original_drug_name == sample_interaction.drug_a_name
        assert isinstance(recommendation.alternatives, list)
        assert isinstance(recommendation.management_strategies, list)
        assert isinstance(recommendation.patient_specific_notes, list)
        assert isinstance(recommendation.generated_at, datetime)
        
        # Verify management strategies exist
        assert len(recommendation.management_strategies) > 0
    
    @pytest.mark.asyncio
    async def test_recommend_alternatives_for_contraindication(
        self, alternative_recommender, sample_contraindication, sample_patient
    ):
        """Test complete alternative recommendation for contraindication"""
        recommendation = await alternative_recommender.recommend_alternatives_for_contraindication(
            sample_contraindication, sample_patient
        )
        
        # Verify recommendation structure
        assert recommendation.original_drug_id == sample_contraindication.drug_id
        assert recommendation.original_drug_name == sample_contraindication.drug_name
        assert isinstance(recommendation.alternatives, list)
        assert isinstance(recommendation.management_strategies, list)
        assert isinstance(recommendation.patient_specific_notes, list)
        
        # Verify patient notes mention the contraindication
        assert any(
            sample_contraindication.drug_name in note
            for note in recommendation.patient_specific_notes
        )
