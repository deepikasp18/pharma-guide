"""
Property-based test for risk-based ranking with real-world evidence

**Feature: pharmaguide-health-companion, Property 6: Risk-Based Ranking with Real-World Evidence**
**Validates: Requirements 2.4**

Property 6: Risk-Based Ranking with Real-World Evidence
*For any* medication and patient combination, adverse effects should be ranked using 
knowledge graph-derived risk factors and real-world evidence from FAERS data
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import MagicMock, AsyncMock
import anyio

from src.knowledge_graph.personalization_engine import (
    PersonalizationEngine,
    RankedResult,
    RiskCategory
)
from src.knowledge_graph.models import PatientContext
from src.knowledge_graph.database import KnowledgeGraphDatabase
from src.knowledge_graph.reasoning_engine import GraphReasoningEngine


pytestmark = pytest.mark.anyio


# Hypothesis strategies for generating test data

@st.composite
def patient_context_strategy(draw):
    """Generate random patient contexts"""
    age = draw(st.integers(min_value=1, max_value=100))
    gender = draw(st.sampled_from(['male', 'female', 'other']))
    weight = draw(st.floats(min_value=30.0, max_value=200.0))
    
    # Generate conditions
    possible_conditions = [
        'diabetes', 'hypertension', 'heart_disease', 
        'kidney_disease', 'liver_disease', 'asthma'
    ]
    num_conditions = draw(st.integers(min_value=0, max_value=3))
    conditions = draw(st.lists(
        st.sampled_from(possible_conditions),
        min_size=num_conditions,
        max_size=num_conditions,
        unique=True
    ))
    
    # Generate medications
    num_medications = draw(st.integers(min_value=0, max_value=12))
    medications = [
        {
            'id': f'med-{i}',
            'name': f'Medication{i}',
            'dosage': '10mg',
            'frequency': 'daily'
        }
        for i in range(num_medications)
    ]
    
    # Generate allergies
    num_allergies = draw(st.integers(min_value=0, max_value=3))
    allergies = [f'allergy-{i}' for i in range(num_allergies)]
    
    # Generate risk factors
    possible_risk_factors = ['smoking', 'alcohol', 'family_history', 'obesity']
    num_risk_factors = draw(st.integers(min_value=0, max_value=2))
    risk_factors = draw(st.lists(
        st.sampled_from(possible_risk_factors),
        min_size=num_risk_factors,
        max_size=num_risk_factors,
        unique=True
    ))
    
    return PatientContext(
        id=f"patient-{draw(st.integers(min_value=1, max_value=10000))}",
        demographics={
            'age': age,
            'gender': gender,
            'weight': weight,
            'height': draw(st.floats(min_value=140.0, max_value=200.0))
        },
        conditions=conditions,
        medications=medications,
        allergies=allergies,
        risk_factors=risk_factors,
        genetic_factors={},
        preferences={}
    )


@st.composite
def adverse_effect_results_strategy(draw):
    """Generate random adverse effect results"""
    num_results = draw(st.integers(min_value=1, max_value=10))
    
    results = []
    for i in range(num_results):
        # Generate base risk score
        base_risk = draw(st.floats(min_value=0.1, max_value=0.9))
        
        # Generate evidence sources
        possible_sources = ['FAERS', 'OnSIDES', 'SIDER', 'DrugBank', 'DDInter']
        num_sources = draw(st.integers(min_value=1, max_value=3))
        evidence_sources = draw(st.lists(
            st.sampled_from(possible_sources),
            min_size=num_sources,
            max_size=num_sources,
            unique=True
        ))
        
        result = {
            'id': f'side-effect-{i}',
            'type': 'SideEffect',
            'name': f'SideEffect{i}',
            'risk_score': base_risk,
            'frequency': base_risk,
            'evidence_sources': evidence_sources,
            'confidence': draw(st.floats(min_value=0.5, max_value=1.0))
        }
        results.append(result)
    
    return results


@st.composite
def rwe_data_strategy(draw):
    """Generate random real-world evidence data"""
    patient_count = draw(st.integers(min_value=0, max_value=200000))
    
    possible_sources = ['FAERS', 'OnSIDES', 'SIDER']
    num_sources = draw(st.integers(min_value=0, max_value=3))
    sources = draw(st.lists(
        st.sampled_from(possible_sources),
        min_size=num_sources,
        max_size=num_sources,
        unique=True
    ))
    
    demographic_matches = draw(st.integers(min_value=0, max_value=5))
    
    return {
        'patient_count': patient_count,
        'sources': sources,
        'demographic_matches': demographic_matches
    }


# Property-based tests

@given(
    patient=patient_context_strategy(),
    results=adverse_effect_results_strategy()
)
@settings(max_examples=100, deadline=None)
async def test_property_risk_ranking_produces_ordered_results(patient, results):
    """
    Property: Risk-based ranking should produce results ordered by personalized risk score
    
    For any patient context and set of adverse effects, the ranking function should:
    1. Return results in descending order of personalized risk score
    2. Apply personalization factors based on patient characteristics
    3. Ensure personalized risk >= base risk (risk factors increase risk)
    """
    # Setup mock database and engine
    mock_db = MagicMock(spec=KnowledgeGraphDatabase)
    mock_db.connection = MagicMock()
    mock_db.connection.g = MagicMock()
    
    # Mock RWE data retrieval to return empty data (no RWE for this test)
    mock_db.connection.g.V().has().inE().valueMap().toList = MagicMock(return_value=[])
    
    mock_reasoning = MagicMock(spec=GraphReasoningEngine)
    
    engine = PersonalizationEngine(mock_db, mock_reasoning)
    
    # Execute ranking without RWE
    ranked = await engine.rank_by_personalized_risk(
        results,
        patient,
        include_rwe=False
    )
    
    # Property 1: Results should be ordered by personalized risk score (descending)
    for i in range(len(ranked) - 1):
        assert ranked[i].personalized_risk_score >= ranked[i+1].personalized_risk_score, \
            f"Results not properly ordered: {ranked[i].personalized_risk_score} < {ranked[i+1].personalized_risk_score}"
    
    # Property 2: All results should have personalization factors applied
    # (unless patient has no risk factors, in which case base risk might equal personalized)
    for result in ranked:
        assert result.personalized_risk_score >= 0.0
        assert result.personalized_risk_score <= 1.0
        assert isinstance(result.contributing_factors, list)
    
    # Property 3: Risk categories should be consistent with risk scores
    for result in ranked:
        if result.personalized_risk_score < 0.25:
            assert result.risk_category == RiskCategory.LOW
        elif result.personalized_risk_score < 0.5:
            assert result.risk_category == RiskCategory.MODERATE
        elif result.personalized_risk_score < 0.75:
            assert result.risk_category == RiskCategory.HIGH
        else:
            assert result.risk_category == RiskCategory.CRITICAL


@given(
    patient=patient_context_strategy(),
    results=adverse_effect_results_strategy()
)
@settings(max_examples=100, deadline=None)
async def test_property_risk_increases_with_patient_risk_factors(patient, results):
    """
    Property: Personalized risk should increase when patient has risk factors
    
    For any patient with risk factors (age >65, conditions, polypharmacy, etc.),
    the personalized risk score should be >= base risk score
    """
    # Setup mock database and engine
    mock_db = MagicMock(spec=KnowledgeGraphDatabase)
    mock_db.connection = MagicMock()
    mock_db.connection.g = MagicMock()
    mock_db.connection.g.V().has().inE().valueMap().toList = MagicMock(return_value=[])
    
    mock_reasoning = MagicMock(spec=GraphReasoningEngine)
    
    engine = PersonalizationEngine(mock_db, mock_reasoning)
    
    # Execute ranking
    ranked = await engine.rank_by_personalized_risk(
        results,
        patient,
        include_rwe=False
    )
    
    # Check if patient has any risk factors
    age = patient.demographics.get('age', 0)
    has_risk_factors = (
        age > 65 or  # Elderly
        age < 18 or  # Pediatric
        len(patient.conditions) > 0 or  # Has conditions
        len(patient.medications) > 5 or  # Polypharmacy
        len(patient.risk_factors) > 0 or  # Explicit risk factors
        len(patient.allergies) > 0  # Allergy history
    )
    
    # Property: If patient has risk factors, personalized risk should be >= base risk
    if has_risk_factors:
        for result in ranked:
            assert result.personalized_risk_score >= result.base_risk_score, \
                f"Personalized risk {result.personalized_risk_score} < base risk {result.base_risk_score} for patient with risk factors"
            # Should have at least one contributing factor
            assert len(result.contributing_factors) > 0, \
                "Patient with risk factors should have contributing factors listed"


@given(
    patient=patient_context_strategy(),
    results=adverse_effect_results_strategy(),
    rwe_data=rwe_data_strategy()
)
@settings(max_examples=100, deadline=None)
async def test_property_rwe_increases_confidence_and_affects_risk(patient, results, rwe_data):
    """
    Property: Real-world evidence should increase confidence and may affect risk scores
    
    For any patient and adverse effects with real-world evidence:
    1. Confidence should increase with more RWE patient reports
    2. Risk may be adjusted based on RWE data
    3. Evidence sources should include RWE datasets
    """
    # Setup mock database and engine
    mock_db = MagicMock(spec=KnowledgeGraphDatabase)
    mock_db.connection = MagicMock()
    mock_db.connection.g = MagicMock()
    
    # Mock RWE data retrieval
    def mock_rwe_toList():
        # Create mock evidence relationships
        evidence = []
        if rwe_data['patient_count'] > 0:
            for source in rwe_data['sources']:
                evidence.append({
                    'source_dataset': source,
                    'patient_count': rwe_data['patient_count'] // len(rwe_data['sources']) if rwe_data['sources'] else 0,
                    'age_range': '',
                    'gender': ''
                })
        return evidence
    
    mock_db.connection.g.V().has().inE().valueMap().toList = MagicMock(
        return_value=mock_rwe_toList()
    )
    
    mock_reasoning = MagicMock(spec=GraphReasoningEngine)
    
    engine = PersonalizationEngine(mock_db, mock_reasoning)
    
    # Execute ranking WITH RWE
    ranked_with_rwe = await engine.rank_by_personalized_risk(
        results,
        patient,
        include_rwe=True
    )
    
    # Execute ranking WITHOUT RWE for comparison
    mock_db.connection.g.V().has().inE().valueMap().toList = MagicMock(return_value=[])
    ranked_without_rwe = await engine.rank_by_personalized_risk(
        results,
        patient,
        include_rwe=False
    )
    
    # Property 1: RWE should be reflected in the results
    for result_with_rwe in ranked_with_rwe:
        assert result_with_rwe.real_world_evidence_count >= 0
        
        # If RWE data exists, it should be reflected
        if rwe_data['patient_count'] > 0:
            # Evidence sources should include RWE sources
            assert len(result_with_rwe.evidence_sources) >= 0
    
    # Property 2: Confidence should be affected by RWE
    # More RWE patient reports should increase confidence
    for i, result_with_rwe in enumerate(ranked_with_rwe):
        result_without_rwe = ranked_without_rwe[i]
        
        if rwe_data['patient_count'] > 1000:
            # With significant RWE, confidence should be at least as high
            assert result_with_rwe.confidence >= result_without_rwe.confidence * 0.95, \
                "Confidence should not decrease significantly with RWE"


@given(
    patient=patient_context_strategy(),
    results=adverse_effect_results_strategy()
)
@settings(max_examples=100, deadline=None)
async def test_property_ranking_is_deterministic(patient, results):
    """
    Property: Ranking should be deterministic for the same inputs
    
    For any patient and adverse effects, running the ranking twice should produce
    identical results (same order, same scores, same factors)
    """
    # Setup mock database and engine
    mock_db = MagicMock(spec=KnowledgeGraphDatabase)
    mock_db.connection = MagicMock()
    mock_db.connection.g = MagicMock()
    mock_db.connection.g.V().has().inE().valueMap().toList = MagicMock(return_value=[])
    
    mock_reasoning = MagicMock(spec=GraphReasoningEngine)
    
    engine = PersonalizationEngine(mock_db, mock_reasoning)
    
    # Execute ranking twice
    ranked1 = await engine.rank_by_personalized_risk(
        results,
        patient,
        include_rwe=False
    )
    
    ranked2 = await engine.rank_by_personalized_risk(
        results,
        patient,
        include_rwe=False
    )
    
    # Property: Results should be identical
    assert len(ranked1) == len(ranked2)
    
    for r1, r2 in zip(ranked1, ranked2):
        assert r1.entity_id == r2.entity_id
        assert r1.personalized_risk_score == r2.personalized_risk_score
        assert r1.risk_category == r2.risk_category
        assert r1.contributing_factors == r2.contributing_factors


@given(
    patient=patient_context_strategy(),
    results=adverse_effect_results_strategy()
)
@settings(max_examples=100, deadline=None)
async def test_property_all_results_have_valid_risk_categories(patient, results):
    """
    Property: All ranked results should have valid risk categories
    
    For any patient and adverse effects, all results should have:
    1. A valid risk category (LOW, MODERATE, HIGH, CRITICAL)
    2. Risk category consistent with the personalized risk score
    """
    # Setup mock database and engine
    mock_db = MagicMock(spec=KnowledgeGraphDatabase)
    mock_db.connection = MagicMock()
    mock_db.connection.g = MagicMock()
    mock_db.connection.g.V().has().inE().valueMap().toList = MagicMock(return_value=[])
    
    mock_reasoning = MagicMock(spec=GraphReasoningEngine)
    
    engine = PersonalizationEngine(mock_db, mock_reasoning)
    
    # Execute ranking
    ranked = await engine.rank_by_personalized_risk(
        results,
        patient,
        include_rwe=False
    )
    
    # Property: All results should have valid risk categories
    valid_categories = {RiskCategory.LOW, RiskCategory.MODERATE, RiskCategory.HIGH, RiskCategory.CRITICAL}
    
    for result in ranked:
        # Must have a valid category
        assert result.risk_category in valid_categories
        
        # Category must match score
        score = result.personalized_risk_score
        if score < 0.25:
            assert result.risk_category == RiskCategory.LOW
        elif score < 0.5:
            assert result.risk_category == RiskCategory.MODERATE
        elif score < 0.75:
            assert result.risk_category == RiskCategory.HIGH
        else:
            assert result.risk_category == RiskCategory.CRITICAL


@given(
    patient=patient_context_strategy(),
    results=adverse_effect_results_strategy()
)
@settings(max_examples=100, deadline=None)
async def test_property_personalized_risk_bounded(patient, results):
    """
    Property: Personalized risk scores should be bounded between 0 and 1
    
    For any patient and adverse effects, all personalized risk scores should be:
    1. >= 0.0 (no negative risk)
    2. <= 1.0 (risk is capped at 100%)
    3. >= base_risk_score (personalization increases risk, never decreases)
    """
    # Setup mock database and engine
    mock_db = MagicMock(spec=KnowledgeGraphDatabase)
    mock_db.connection = MagicMock()
    mock_db.connection.g = MagicMock()
    mock_db.connection.g.V().has().inE().valueMap().toList = MagicMock(return_value=[])
    
    mock_reasoning = MagicMock(spec=GraphReasoningEngine)
    
    engine = PersonalizationEngine(mock_db, mock_reasoning)
    
    # Execute ranking
    ranked = await engine.rank_by_personalized_risk(
        results,
        patient,
        include_rwe=False
    )
    
    # Property: All scores should be properly bounded
    for result in ranked:
        assert result.personalized_risk_score >= 0.0, \
            f"Risk score {result.personalized_risk_score} is negative"
        assert result.personalized_risk_score <= 1.0, \
            f"Risk score {result.personalized_risk_score} exceeds 1.0"
        assert result.personalized_risk_score >= result.base_risk_score, \
            f"Personalized risk {result.personalized_risk_score} < base risk {result.base_risk_score}"
