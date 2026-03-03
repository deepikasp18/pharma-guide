"""
Unit tests for personalization engine

Tests risk-based ranking, physiological factor analysis, and dosing adjustments
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
import anyio

from src.knowledge_graph.personalization_engine import (
    PersonalizationEngine,
    RankedResult,
    PhysiologicalFactor,
    DosingAdjustment,
    RiskCategory,
    DosingAdjustmentReason
)
from src.knowledge_graph.models import PatientContext
from src.knowledge_graph.database import KnowledgeGraphDatabase
from src.knowledge_graph.reasoning_engine import GraphReasoningEngine


pytestmark = pytest.mark.anyio


@pytest.fixture
def mock_database():
    """Create mock database"""
    db = MagicMock(spec=KnowledgeGraphDatabase)
    db.connection = MagicMock()
    db.connection.g = MagicMock()
    return db


@pytest.fixture
def mock_reasoning_engine():
    """Create mock reasoning engine"""
    engine = MagicMock(spec=GraphReasoningEngine)
    return engine


@pytest.fixture
def personalization_engine(mock_database, mock_reasoning_engine):
    """Create personalization engine"""
    return PersonalizationEngine(mock_database, mock_reasoning_engine)


@pytest.fixture
def sample_patient_context():
    """Create sample patient context"""
    return PatientContext(
        id="patient-001",
        demographics={
            'age': 70,
            'gender': 'male',
            'weight': 75.0,
            'height': 175.0
        },
        conditions=['diabetes', 'hypertension'],
        medications=[
            {'name': 'Metformin', 'dosage': '500mg', 'frequency': 'twice daily'},
            {'name': 'Lisinopril', 'dosage': '10mg', 'frequency': 'daily'}
        ],
        allergies=['penicillin'],
        risk_factors=['smoking', 'family_history'],
        genetic_factors={},
        preferences={}
    )


async def test_rank_by_personalized_risk_basic(personalization_engine, sample_patient_context):
    """Test basic risk-based ranking"""
    # Mock database responses
    personalization_engine.db.connection.g.V().has().inE().valueMap().toList = MagicMock(
        return_value=[]
    )
    
    # Sample results to rank
    results = [
        {
            'id': 'side-effect-001',
            'type': 'SideEffect',
            'name': 'Nausea',
            'risk_score': 0.3,
            'evidence_sources': ['SIDER']
        },
        {
            'id': 'side-effect-002',
            'type': 'SideEffect',
            'name': 'Dizziness',
            'risk_score': 0.5,
            'evidence_sources': ['FAERS']
        }
    ]
    
    # Rank results
    ranked = await personalization_engine.rank_by_personalized_risk(
        results,
        sample_patient_context,
        include_rwe=False
    )
    
    # Verify results
    assert len(ranked) == 2
    assert all(isinstance(r, RankedResult) for r in ranked)
    
    # Verify ranking (higher risk first)
    assert ranked[0].personalized_risk_score >= ranked[1].personalized_risk_score
    
    # Verify personalization factors are applied
    for result in ranked:
        assert result.personalized_risk_score >= result.base_risk_score
        assert len(result.contributing_factors) > 0


async def test_personalized_risk_increases_for_elderly(personalization_engine):
    """Test that risk increases for elderly patients"""
    # Elderly patient
    elderly_patient = PatientContext(
        id="patient-elderly",
        demographics={'age': 75, 'gender': 'female', 'weight': 60.0},
        conditions=[],
        medications=[],
        allergies=[],
        risk_factors=[],
        genetic_factors={},
        preferences={}
    )
    
    # Mock database
    personalization_engine.db.connection.g.V().has().inE().valueMap().toList = MagicMock(
        return_value=[]
    )
    
    results = [
        {
            'id': 'side-effect-001',
            'type': 'SideEffect',
            'name': 'Dizziness',
            'risk_score': 0.3,
            'evidence_sources': []
        }
    ]
    
    ranked = await personalization_engine.rank_by_personalized_risk(
        results,
        elderly_patient,
        include_rwe=False
    )
    
    # Verify risk increased for elderly
    assert ranked[0].personalized_risk_score > ranked[0].base_risk_score
    assert any('age' in factor.lower() for factor in ranked[0].contributing_factors)


async def test_personalized_risk_increases_for_polypharmacy(personalization_engine):
    """Test that risk increases for patients with many medications"""
    # Patient with polypharmacy
    polypharmacy_patient = PatientContext(
        id="patient-poly",
        demographics={'age': 60, 'gender': 'male', 'weight': 80.0},
        conditions=[],
        medications=[
            {'name': f'Drug{i}', 'dosage': '10mg', 'frequency': 'daily'}
            for i in range(8)  # 8 medications
        ],
        allergies=[],
        risk_factors=[],
        genetic_factors={},
        preferences={}
    )
    
    # Mock database
    personalization_engine.db.connection.g.V().has().inE().valueMap().toList = MagicMock(
        return_value=[]
    )
    
    results = [
        {
            'id': 'side-effect-001',
            'type': 'SideEffect',
            'name': 'Interaction',
            'risk_score': 0.4,
            'evidence_sources': []
        }
    ]
    
    ranked = await personalization_engine.rank_by_personalized_risk(
        results,
        polypharmacy_patient,
        include_rwe=False
    )
    
    # Verify risk increased for polypharmacy
    assert ranked[0].personalized_risk_score > ranked[0].base_risk_score
    assert any('polypharmacy' in factor.lower() for factor in ranked[0].contributing_factors)


async def test_analyze_physiological_factors_age(personalization_engine, sample_patient_context):
    """Test physiological factor analysis for age"""
    # Mock database responses
    personalization_engine.db.connection.g.V().has().outE().valueMap().toList = MagicMock(
        return_value=[]
    )
    
    factors = await personalization_engine.analyze_physiological_factors(
        'drug-001',
        sample_patient_context
    )
    
    # Verify factors were identified
    assert len(factors) > 0
    assert all(isinstance(f, PhysiologicalFactor) for f in factors)
    
    # Verify age factor is present for elderly patient
    age_factors = [f for f in factors if 'age' in f.factor_name.lower()]
    assert len(age_factors) > 0


async def test_generate_dosing_adjustments_elderly(personalization_engine):
    """Test dosing adjustment for elderly patient"""
    # Elderly patient
    elderly_patient = PatientContext(
        id="patient-elderly",
        demographics={'age': 82, 'gender': 'female', 'weight': 55.0},
        conditions=[],
        medications=[],
        allergies=[],
        risk_factors=[],
        genetic_factors={},
        preferences={}
    )
    
    # Mock drug info
    async def mock_get_drug_info(drug_id):
        return {
            'name': 'TestDrug',
            'standard_dose': '100mg daily',
            'weight_based_dosing': False
        }
    
    personalization_engine._get_drug_info = mock_get_drug_info
    
    # Mock database responses
    personalization_engine.db.connection.g.V().has().outE().valueMap().toList = MagicMock(
        return_value=[]
    )
    
    adjustment = await personalization_engine.generate_dosing_adjustments(
        'drug-001',
        elderly_patient
    )
    
    # Verify adjustment was generated
    assert adjustment is not None
    assert isinstance(adjustment, DosingAdjustment)
    
    # Verify dose reduction for elderly
    assert adjustment.adjustment_factor < 1.0
    assert DosingAdjustmentReason.AGE in adjustment.reasons
    assert 'reduced' in adjustment.adjusted_dose.lower()


async def test_generate_dosing_adjustments_renal_impairment(personalization_engine):
    """Test dosing adjustment for renal impairment"""
    # Patient with kidney disease
    renal_patient = PatientContext(
        id="patient-renal",
        demographics={'age': 65, 'gender': 'male', 'weight': 70.0},
        conditions=['chronic kidney disease'],
        medications=[],
        allergies=[],
        risk_factors=[],
        genetic_factors={},
        preferences={}
    )
    
    # Mock drug info
    async def mock_get_drug_info(drug_id):
        return {
            'name': 'TestDrug',
            'standard_dose': '200mg daily',
            'weight_based_dosing': False
        }
    
    personalization_engine._get_drug_info = mock_get_drug_info
    
    # Mock database responses - drug is renally cleared
    def mock_toList():
        return [
            {
                'renal_clearance_percentage': 80,
                'sources': ['DrugBank']
            }
        ]
    
    mock_traversal = MagicMock()
    mock_traversal.toList = mock_toList
    personalization_engine.db.connection.g.V().has().outE().valueMap = MagicMock(
        return_value=mock_traversal
    )
    
    adjustment = await personalization_engine.generate_dosing_adjustments(
        'drug-001',
        renal_patient
    )
    
    # Verify adjustment was generated
    assert adjustment is not None
    
    # Verify dose reduction for renal impairment
    assert adjustment.adjustment_factor < 1.0
    assert DosingAdjustmentReason.RENAL_IMPAIRMENT in adjustment.reasons
    assert 'renal' in adjustment.explanation.lower()


async def test_no_dosing_adjustment_for_healthy_adult(personalization_engine):
    """Test that no adjustment is generated for healthy adult"""
    # Healthy adult patient
    healthy_patient = PatientContext(
        id="patient-healthy",
        demographics={'age': 35, 'gender': 'male', 'weight': 75.0},
        conditions=[],
        medications=[],
        allergies=[],
        risk_factors=[],
        genetic_factors={},
        preferences={}
    )
    
    # Mock drug info
    async def mock_get_drug_info(drug_id):
        return {
            'name': 'TestDrug',
            'standard_dose': '100mg daily',
            'weight_based_dosing': False
        }
    
    personalization_engine._get_drug_info = mock_get_drug_info
    
    # Mock database responses
    personalization_engine.db.connection.g.V().has().outE().valueMap().toList = MagicMock(
        return_value=[]
    )
    
    adjustment = await personalization_engine.generate_dosing_adjustments(
        'drug-001',
        healthy_patient
    )
    
    # Verify no significant adjustment for healthy adult
    assert adjustment is None or abs(adjustment.adjustment_factor - 1.0) < 0.1


def test_determine_risk_category(personalization_engine):
    """Test risk category determination"""
    assert personalization_engine._determine_risk_category(0.1) == RiskCategory.LOW
    assert personalization_engine._determine_risk_category(0.3) == RiskCategory.MODERATE
    assert personalization_engine._determine_risk_category(0.6) == RiskCategory.HIGH
    assert personalization_engine._determine_risk_category(0.9) == RiskCategory.CRITICAL


def test_calculate_age_adjustment(personalization_engine):
    """Test age-based adjustment calculation"""
    # Elderly patient
    elderly_context = PatientContext(
        id="test",
        demographics={'age': 75},
        conditions=[],
        medications=[],
        allergies=[],
        risk_factors=[],
        genetic_factors={},
        preferences={}
    )
    
    adjustment, reason = personalization_engine._calculate_age_adjustment(
        elderly_context,
        {}
    )
    
    assert adjustment < 1.0
    assert reason == DosingAdjustmentReason.AGE
    
    # Pediatric patient
    pediatric_context = PatientContext(
        id="test",
        demographics={'age': 10},
        conditions=[],
        medications=[],
        allergies=[],
        risk_factors=[],
        genetic_factors={},
        preferences={}
    )
    
    adjustment, reason = personalization_engine._calculate_age_adjustment(
        pediatric_context,
        {}
    )
    
    assert adjustment < 1.0
    assert reason == DosingAdjustmentReason.AGE
    
    # Adult patient
    adult_context = PatientContext(
        id="test",
        demographics={'age': 40},
        conditions=[],
        medications=[],
        allergies=[],
        risk_factors=[],
        genetic_factors={},
        preferences={}
    )
    
    adjustment, reason = personalization_engine._calculate_age_adjustment(
        adult_context,
        {}
    )
    
    assert adjustment == 1.0
    assert reason is None


def test_calculate_weight_adjustment(personalization_engine):
    """Test weight-based adjustment calculation"""
    # Low weight patient
    low_weight_context = PatientContext(
        id="test",
        demographics={'weight': 45.0},
        conditions=[],
        medications=[],
        allergies=[],
        risk_factors=[],
        genetic_factors={},
        preferences={}
    )
    
    adjustment, reason = personalization_engine._calculate_weight_adjustment(
        low_weight_context,
        {}
    )
    
    assert adjustment < 1.0
    assert reason == DosingAdjustmentReason.WEIGHT
    
    # Normal weight patient
    normal_weight_context = PatientContext(
        id="test",
        demographics={'weight': 70.0},
        conditions=[],
        medications=[],
        allergies=[],
        risk_factors=[],
        genetic_factors={},
        preferences={}
    )
    
    adjustment, reason = personalization_engine._calculate_weight_adjustment(
        normal_weight_context,
        {}
    )
    
    assert adjustment == 1.0
    assert reason is None


def test_age_in_range(personalization_engine):
    """Test age range checking"""
    assert personalization_engine._age_in_range(70, '65-75') is True
    assert personalization_engine._age_in_range(60, '65-75') is False
    assert personalization_engine._age_in_range(80, '65-75') is False
    assert personalization_engine._age_in_range(65, '65') is True


def test_weight_in_range(personalization_engine):
    """Test weight range checking"""
    assert personalization_engine._weight_in_range(70.0, '60-80') is True
    assert personalization_engine._weight_in_range(50.0, '60-80') is False
    assert personalization_engine._weight_in_range(90.0, '60-80') is False
    assert personalization_engine._weight_in_range(70.0, '70') is True
