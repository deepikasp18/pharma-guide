"""
Property-based tests for patient context integration

Feature: pharmaguide-health-companion, Property 5: Patient Context Integration
Validates: Requirements 2.1, 2.2, 2.3
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import AsyncMock, MagicMock
import asyncio

from src.knowledge_graph.patient_context_manager import (
    PatientContextManager,
    ContextLayer
)
from src.knowledge_graph.models import PatientContext
from src.knowledge_graph.database import KnowledgeGraphDatabase


# Strategies for generating test data

@st.composite
def demographics_strategy(draw):
    """Generate patient demographics"""
    age = draw(st.integers(min_value=0, max_value=120))
    gender = draw(st.sampled_from(['male', 'female', 'other']))
    weight = draw(st.floats(min_value=2.0, max_value=300.0))
    height = draw(st.floats(min_value=30.0, max_value=250.0))
    
    return {
        'age': age,
        'gender': gender,
        'weight': weight,
        'height': height
    }


@st.composite
def conditions_strategy(draw):
    """Generate list of medical conditions"""
    condition_pool = [
        'diabetes', 'hypertension', 'heart_disease', 'asthma',
        'copd', 'arthritis', 'depression', 'anxiety',
        'kidney_disease', 'liver_disease', 'cancer', 'stroke'
    ]
    
    num_conditions = draw(st.integers(min_value=0, max_value=5))
    conditions = draw(st.lists(
        st.sampled_from(condition_pool),
        min_size=num_conditions,
        max_size=num_conditions,
        unique=True
    ))
    
    return conditions


@st.composite
def medications_strategy(draw):
    """Generate list of medications"""
    medication_names = [
        'Lisinopril', 'Metformin', 'Aspirin', 'Atorvastatin',
        'Levothyroxine', 'Amlodipine', 'Metoprolol', 'Omeprazole',
        'Losartan', 'Gabapentin', 'Hydrochlorothiazide', 'Sertraline'
    ]
    
    dosages = ['5mg', '10mg', '20mg', '50mg', '100mg', '500mg', '1000mg']
    frequencies = ['daily', 'twice daily', 'three times daily', 'as needed']
    
    num_medications = draw(st.integers(min_value=0, max_value=10))
    medications = []
    
    for _ in range(num_medications):
        med = {
            'name': draw(st.sampled_from(medication_names)),
            'dosage': draw(st.sampled_from(dosages)),
            'frequency': draw(st.sampled_from(frequencies))
        }
        medications.append(med)
    
    return medications


@st.composite
def allergies_strategy(draw):
    """Generate list of drug allergies"""
    allergy_pool = [
        'penicillin', 'sulfa', 'aspirin', 'ibuprofen',
        'codeine', 'morphine', 'latex', 'shellfish'
    ]
    
    num_allergies = draw(st.integers(min_value=0, max_value=4))
    allergies = draw(st.lists(
        st.sampled_from(allergy_pool),
        min_size=num_allergies,
        max_size=num_allergies,
        unique=True
    ))
    
    return allergies


@st.composite
def risk_factors_strategy(draw):
    """Generate list of risk factors"""
    risk_pool = [
        'smoking', 'obesity', 'alcohol_use', 'sedentary_lifestyle',
        'family_history', 'high_cholesterol', 'high_blood_pressure'
    ]
    
    num_risks = draw(st.integers(min_value=0, max_value=5))
    risks = draw(st.lists(
        st.sampled_from(risk_pool),
        min_size=num_risks,
        max_size=num_risks,
        unique=True
    ))
    
    return risks


@st.composite
def patient_profile_strategy(draw):
    """Generate complete patient profile"""
    demographics = draw(demographics_strategy())
    conditions = draw(conditions_strategy())
    medications = draw(medications_strategy())
    allergies = draw(allergies_strategy())
    risk_factors = draw(risk_factors_strategy())
    
    return {
        'demographics': demographics,
        'conditions': conditions,
        'medications': medications,
        'allergies': allergies,
        'risk_factors': risk_factors
    }


@st.composite
def query_params_strategy(draw):
    """Generate base query parameters"""
    drug_ids = ['drug-001', 'drug-002', 'drug-003', 'drug-004']
    
    return {
        'drug_id': draw(st.sampled_from(drug_ids)),
        'max_results': draw(st.integers(min_value=1, max_value=100)),
        'include_interactions': draw(st.booleans())
    }


# Helper function to create mock database
def create_mock_database():
    """Create a mock database for testing"""
    db = MagicMock(spec=KnowledgeGraphDatabase)
    db.connection = MagicMock()
    db.connection.g = MagicMock()
    db.create_patient_vertex = AsyncMock(return_value="patient-test")
    return db


# Property-Based Tests

@settings(max_examples=100, deadline=None)
@given(profile=patient_profile_strategy())
def test_patient_characteristics_mapped_to_context_layer(profile):
    """
    Property 5: Patient Context Integration (Requirement 2.1)
    
    For any patient profile, the system should map patient characteristics to 
    knowledge graph entities and establish personalization context layers.
    
    Validates: Requirements 2.1
    """
    # Create patient context manager
    db = create_mock_database()
    manager = PatientContextManager(db)
    
    # Create patient context
    loop = asyncio.get_event_loop()
    context = loop.run_until_complete(
        manager.create_patient_context(
            demographics=profile['demographics'],
            conditions=profile['conditions'],
            medications=profile['medications'],
            allergies=profile['allergies'],
            risk_factors=profile['risk_factors']
        )
    )
    
    # Verify patient context was created
    assert context is not None, "Patient context should be created"
    assert context.id is not None, "Patient context should have an ID"
    
    # Verify characteristics are mapped
    assert context.demographics == profile['demographics'], (
        "Demographics should be mapped correctly"
    )
    assert set(context.conditions) == set(profile['conditions']), (
        "Conditions should be mapped correctly"
    )
    assert len(context.medications) == len(profile['medications']), (
        "Medications should be mapped correctly"
    )
    assert set(context.allergies) == set(profile['allergies']), (
        "Allergies should be mapped correctly"
    )
    assert set(context.risk_factors) == set(profile['risk_factors']), (
        "Risk factors should be mapped correctly"
    )
    
    # Verify context layer was established
    context_layer = manager.get_context_layer(context.id)
    assert context_layer is not None, (
        "Context layer should be established for patient"
    )
    assert context_layer.patient_id == context.id, (
        "Context layer should be associated with correct patient"
    )
    assert context_layer.active is True, (
        "Context layer should be active"
    )
    
    # Verify filters are created from patient characteristics
    assert isinstance(context_layer.filters, dict), (
        "Context layer should have filters dictionary"
    )
    assert isinstance(context_layer.weights, dict), (
        "Context layer should have weights dictionary"
    )


@settings(max_examples=100, deadline=None)
@given(
    profile=patient_profile_strategy(),
    query_params=query_params_strategy()
)
def test_contextualized_queries_incorporate_patient_filters(profile, query_params):
    """
    Property 5: Patient Context Integration (Requirement 2.2)
    
    For any patient profile and query parameters, the system should execute 
    knowledge graph queries that incorporate patient demographics, conditions, 
    and current medications as contextual filters.
    
    Validates: Requirements 2.2
    """
    # Create patient context manager
    db = create_mock_database()
    manager = PatientContextManager(db)
    
    # Create patient context
    loop = asyncio.get_event_loop()
    context = loop.run_until_complete(
        manager.create_patient_context(
            demographics=profile['demographics'],
            conditions=profile['conditions'],
            medications=profile['medications'],
            allergies=profile['allergies'],
            risk_factors=profile['risk_factors']
        )
    )
    
    # Apply context to query
    contextualized_params = manager.apply_context_to_query(
        query_params,
        context.id
    )
    
    # Verify original query params are preserved
    assert contextualized_params['drug_id'] == query_params['drug_id'], (
        "Original query parameters should be preserved"
    )
    assert contextualized_params['max_results'] == query_params['max_results'], (
        "Original query parameters should be preserved"
    )
    
    # Verify patient context is applied
    assert contextualized_params['patient_id'] == context.id, (
        "Patient ID should be added to query"
    )
    assert contextualized_params['context_applied'] is True, (
        "Context applied flag should be set"
    )
    
    # Verify filters are incorporated
    assert 'filters' in contextualized_params, (
        "Contextualized query should have filters"
    )
    
    # Verify demographics filters
    if profile['demographics'].get('age'):
        assert 'age' in contextualized_params['filters'], (
            "Age filter should be incorporated from demographics"
        )
        assert contextualized_params['filters']['age'] == profile['demographics']['age'], (
            "Age filter should match patient demographics"
        )
    
    if profile['demographics'].get('gender'):
        assert 'gender' in contextualized_params['filters'], (
            "Gender filter should be incorporated from demographics"
        )
    
    # Verify conditions filters
    if profile['conditions']:
        assert 'conditions' in contextualized_params['filters'], (
            "Conditions filter should be incorporated"
        )
        assert set(contextualized_params['filters']['conditions']) == set(profile['conditions']), (
            "Conditions filter should match patient conditions"
        )
    
    # Verify medications filters
    if profile['medications']:
        assert 'current_medications' in contextualized_params['filters'], (
            "Medications filter should be incorporated"
        )
    
    # Verify allergies filters
    if profile['allergies']:
        assert 'allergies' in contextualized_params['filters'], (
            "Allergies filter should be incorporated"
        )
        assert set(contextualized_params['filters']['allergies']) == set(profile['allergies']), (
            "Allergies filter should match patient allergies"
        )
    
    # Verify weights are incorporated
    assert 'weights' in contextualized_params, (
        "Contextualized query should have weights"
    )


@settings(max_examples=100, deadline=None)
@given(profile=patient_profile_strategy())
def test_context_layer_reflects_patient_risk_factors(profile):
    """
    Property 5: Patient Context Integration (Requirement 2.3)
    
    For any patient profile, the system should traverse knowledge graph 
    relationships between patient characteristics and drug response patterns,
    reflected in context layer weights.
    
    Validates: Requirements 2.3
    """
    # Create patient context manager
    db = create_mock_database()
    manager = PatientContextManager(db)
    
    # Create patient context
    loop = asyncio.get_event_loop()
    context = loop.run_until_complete(
        manager.create_patient_context(
            demographics=profile['demographics'],
            conditions=profile['conditions'],
            medications=profile['medications'],
            allergies=profile['allergies'],
            risk_factors=profile['risk_factors']
        )
    )
    
    # Get context layer
    context_layer = manager.get_context_layer(context.id)
    assert context_layer is not None
    
    # Verify age-based risk weighting
    age = profile['demographics'].get('age')
    if age:
        if age > 65:
            assert 'age_risk' in context_layer.weights, (
                "Elderly patients should have age risk weight"
            )
            assert context_layer.weights['age_risk'] >= 1.0, (
                "Elderly patients should have increased risk weight"
            )
        elif age < 18:
            assert 'age_risk' in context_layer.weights, (
                "Pediatric patients should have age risk weight"
            )
            assert context_layer.weights['age_risk'] >= 1.0, (
                "Pediatric patients should have increased risk weight"
            )
    
    # Verify condition-based risk weighting
    if len(profile['conditions']) > 0:
        assert 'condition_risk' in context_layer.weights, (
            "Patients with conditions should have condition risk weight"
        )
        assert context_layer.weights['condition_risk'] >= 1.0, (
            "Condition risk weight should be at least 1.0"
        )
        # More conditions = higher risk
        expected_min_weight = 1.0 + (len(profile['conditions']) * 0.05)
        assert context_layer.weights['condition_risk'] >= expected_min_weight, (
            f"Condition risk weight should increase with number of conditions. "
            f"Expected at least {expected_min_weight}, got {context_layer.weights['condition_risk']}"
        )
    
    # Verify polypharmacy risk weighting
    if len(profile['medications']) > 5:
        assert 'polypharmacy_risk' in context_layer.weights, (
            "Patients with >5 medications should have polypharmacy risk weight"
        )
        assert context_layer.weights['polypharmacy_risk'] > 1.0, (
            "Polypharmacy risk weight should be greater than 1.0"
        )
    
    # Verify allergy risk weighting
    if len(profile['allergies']) > 0:
        assert 'allergy_risk' in context_layer.weights, (
            "Patients with allergies should have allergy risk weight"
        )
        assert context_layer.weights['allergy_risk'] > 1.0, (
            "Allergy risk weight should be greater than 1.0"
        )
    
    # Verify risk factors weighting
    if len(profile['risk_factors']) > 0:
        assert 'risk_factors' in context_layer.weights, (
            "Patients with risk factors should have risk factors weight"
        )
        assert context_layer.weights['risk_factors'] >= 1.0, (
            "Risk factors weight should be at least 1.0"
        )


@settings(max_examples=100, deadline=None)
@given(
    initial_profile=patient_profile_strategy(),
    updated_conditions=conditions_strategy()
)
def test_context_updates_trigger_reevaluation(initial_profile, updated_conditions):
    """
    Property 5: Patient Context Integration (Dynamic Updates)
    
    For any patient profile update, the system should automatically update 
    context layers and trigger re-evaluation.
    
    Validates: Requirements 2.1, 2.2, 2.3
    """
    # Create patient context manager
    db = create_mock_database()
    manager = PatientContextManager(db)
    
    # Create initial patient context
    loop = asyncio.get_event_loop()
    context = loop.run_until_complete(
        manager.create_patient_context(
            demographics=initial_profile['demographics'],
            conditions=initial_profile['conditions'],
            medications=initial_profile['medications'],
            allergies=initial_profile['allergies'],
            risk_factors=initial_profile['risk_factors']
        )
    )
    
    # Get initial context layer
    initial_layer = manager.get_context_layer(context.id)
    initial_updated_at = initial_layer.updated_at
    
    # Update patient context with new conditions
    updated_context = loop.run_until_complete(
        manager.update_patient_context(
            context.id,
            {'conditions': updated_conditions}
        )
    )
    
    # Verify context was updated
    assert updated_context is not None, "Context should be updated"
    assert set(updated_context.conditions) == set(updated_conditions), (
        "Conditions should be updated"
    )
    
    # Verify context layer was re-evaluated
    updated_layer = manager.get_context_layer(context.id)
    assert updated_layer is not None, "Updated context layer should exist"
    assert updated_layer.updated_at > initial_updated_at, (
        "Context layer should be re-evaluated with newer timestamp"
    )
    
    # Verify filters reflect updated conditions
    if updated_conditions:
        assert 'conditions' in updated_layer.filters, (
            "Updated context layer should have conditions filter"
        )
        assert set(updated_layer.filters['conditions']) == set(updated_conditions), (
            "Updated context layer filters should reflect new conditions"
        )
    
    # Verify update history is maintained
    history = manager.get_update_history(context.id)
    assert len(history) > 0, "Update history should be maintained"
    assert any(u.field == 'conditions' for u in history), (
        "Update history should include conditions update"
    )


@settings(max_examples=50, deadline=None)
@given(profile=patient_profile_strategy())
def test_context_layer_consistency_across_retrievals(profile):
    """
    Property 5: Patient Context Integration (Consistency)
    
    For any patient profile, retrieving the context multiple times should 
    return consistent context layers.
    
    Validates: Requirements 2.1, 2.2
    """
    # Create patient context manager
    db = create_mock_database()
    manager = PatientContextManager(db)
    
    # Create patient context
    loop = asyncio.get_event_loop()
    context = loop.run_until_complete(
        manager.create_patient_context(
            demographics=profile['demographics'],
            conditions=profile['conditions'],
            medications=profile['medications'],
            allergies=profile['allergies'],
            risk_factors=profile['risk_factors']
        )
    )
    
    # Retrieve context layer multiple times
    layer1 = manager.get_context_layer(context.id)
    layer2 = manager.get_context_layer(context.id)
    
    # Verify consistency
    assert layer1.patient_id == layer2.patient_id, (
        "Context layer patient ID should be consistent"
    )
    assert layer1.filters == layer2.filters, (
        "Context layer filters should be consistent"
    )
    assert layer1.weights == layer2.weights, (
        "Context layer weights should be consistent"
    )
    assert layer1.active == layer2.active, (
        "Context layer active status should be consistent"
    )


@settings(max_examples=50, deadline=None)
@given(
    profile=patient_profile_strategy(),
    query_params=query_params_strategy()
)
def test_context_application_is_idempotent(profile, query_params):
    """
    Property 5: Patient Context Integration (Idempotence)
    
    For any patient profile and query, applying context multiple times should 
    produce the same result.
    
    Validates: Requirements 2.2
    """
    # Create patient context manager
    db = create_mock_database()
    manager = PatientContextManager(db)
    
    # Create patient context
    loop = asyncio.get_event_loop()
    context = loop.run_until_complete(
        manager.create_patient_context(
            demographics=profile['demographics'],
            conditions=profile['conditions'],
            medications=profile['medications'],
            allergies=profile['allergies'],
            risk_factors=profile['risk_factors']
        )
    )
    
    # Apply context multiple times
    contextualized1 = manager.apply_context_to_query(query_params, context.id)
    contextualized2 = manager.apply_context_to_query(query_params, context.id)
    
    # Verify idempotence
    assert contextualized1 == contextualized2, (
        "Applying context multiple times should produce identical results"
    )


@settings(max_examples=50, deadline=None)
@given(profile=patient_profile_strategy())
def test_empty_profile_creates_minimal_context_layer(profile):
    """
    Property 5: Patient Context Integration (Edge Case)
    
    For any patient profile with minimal data, the system should still create 
    a valid context layer.
    
    Validates: Requirements 2.1
    """
    # Create patient context manager
    db = create_mock_database()
    manager = PatientContextManager(db)
    
    # Create minimal patient context (only demographics)
    loop = asyncio.get_event_loop()
    context = loop.run_until_complete(
        manager.create_patient_context(
            demographics=profile['demographics']
        )
    )
    
    # Verify context was created
    assert context is not None, "Minimal context should be created"
    
    # Verify context layer was established
    context_layer = manager.get_context_layer(context.id)
    assert context_layer is not None, (
        "Context layer should be established even for minimal profile"
    )
    assert context_layer.active is True, (
        "Context layer should be active"
    )
    
    # Verify filters and weights are dictionaries (even if empty)
    assert isinstance(context_layer.filters, dict), (
        "Context layer should have filters dictionary"
    )
    assert isinstance(context_layer.weights, dict), (
        "Context layer should have weights dictionary"
    )
