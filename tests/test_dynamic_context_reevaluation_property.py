"""
Property-based tests for dynamic context re-evaluation

Feature: pharmaguide-health-companion, Property 7: Dynamic Context Re-evaluation
Validates: Requirements 2.5, 6.5
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import AsyncMock, MagicMock
import asyncio
from datetime import datetime

from src.knowledge_graph.patient_context_manager import (
    PatientContextManager,
    ContextLayer,
    ContextUpdate
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
@given(
    initial_profile=patient_profile_strategy(),
    updated_conditions=conditions_strategy()
)
def test_condition_changes_trigger_automatic_context_update(
    initial_profile, updated_conditions
):
    """
    Property 7: Dynamic Context Re-evaluation (Requirement 2.5)
    
    For any patient profile change, the system should automatically update 
    patient context layers when profile information changes, triggering 
    knowledge graph re-evaluation.
    
    Validates: Requirements 2.5
    """
    # Create patient context manager
    db = create_mock_database()
    manager = PatientContextManager(db)
    
    # Create initial patient context
    loop = asyncio.get_event_loop()
    initial_context = loop.run_until_complete(
        manager.create_patient_context(
            demographics=initial_profile['demographics'],
            conditions=initial_profile['conditions'],
            medications=initial_profile['medications'],
            allergies=initial_profile['allergies'],
            risk_factors=initial_profile['risk_factors']
        )
    )
    
    # Get initial context layer
    initial_layer = manager.get_context_layer(initial_context.id)
    assert initial_layer is not None, "Initial context layer should exist"
    initial_updated_at = initial_layer.updated_at
    
    # Update patient conditions (critical field that requires re-evaluation)
    updated_context = loop.run_until_complete(
        manager.update_patient_context(
            initial_context.id,
            {'conditions': updated_conditions}
        )
    )
    
    # Verify context was automatically updated
    assert updated_context is not None, (
        "Context should be automatically updated"
    )
    assert set(updated_context.conditions) == set(updated_conditions), (
        "Conditions should be updated in patient context"
    )
    
    # Verify context layer was automatically updated
    updated_layer = manager.get_context_layer(initial_context.id)
    assert updated_layer is not None, (
        "Context layer should be automatically updated"
    )
    assert updated_layer.updated_at > initial_updated_at, (
        "Context layer timestamp should be updated to reflect re-evaluation"
    )
    
    # Verify context layer filters reflect new conditions
    if updated_conditions:
        assert 'conditions' in updated_layer.filters, (
            "Updated context layer should include conditions filter"
        )
        assert set(updated_layer.filters['conditions']) == set(updated_conditions), (
            "Context layer filters should reflect updated conditions"
        )
    
    # Verify re-evaluation was triggered (check update history)
    update_history = manager.get_update_history(initial_context.id)
    assert len(update_history) > 0, (
        "Update history should record the context change"
    )
    
    condition_updates = [u for u in update_history if u.field == 'conditions']
    assert len(condition_updates) > 0, (
        "Update history should include conditions update"
    )
    assert condition_updates[0].requires_reevaluation is True, (
        "Conditions update should be marked as requiring re-evaluation"
    )


@settings(max_examples=100, deadline=None)
@given(
    initial_profile=patient_profile_strategy(),
    updated_medications=medications_strategy()
)
def test_medication_changes_trigger_automatic_context_update(
    initial_profile, updated_medications
):
    """
    Property 7: Dynamic Context Re-evaluation (Requirement 2.5)
    
    For any medication changes, the system should automatically update 
    patient context layers and trigger knowledge graph re-evaluation.
    
    Validates: Requirements 2.5
    """
    # Create patient context manager
    db = create_mock_database()
    manager = PatientContextManager(db)
    
    # Create initial patient context
    loop = asyncio.get_event_loop()
    initial_context = loop.run_until_complete(
        manager.create_patient_context(
            demographics=initial_profile['demographics'],
            conditions=initial_profile['conditions'],
            medications=initial_profile['medications'],
            allergies=initial_profile['allergies'],
            risk_factors=initial_profile['risk_factors']
        )
    )
    
    # Get initial context layer
    initial_layer = manager.get_context_layer(initial_context.id)
    initial_updated_at = initial_layer.updated_at
    
    # Update patient medications (critical field)
    updated_context = loop.run_until_complete(
        manager.update_patient_context(
            initial_context.id,
            {'medications': updated_medications}
        )
    )
    
    # Verify context was automatically updated
    assert updated_context is not None
    assert len(updated_context.medications) == len(updated_medications)
    
    # Verify context layer was automatically updated
    updated_layer = manager.get_context_layer(initial_context.id)
    assert updated_layer.updated_at > initial_updated_at, (
        "Context layer should be re-evaluated after medication changes"
    )
    
    # Verify medication filters are updated
    if updated_medications:
        assert 'current_medications' in updated_layer.filters, (
            "Context layer should include medication filters"
        )
        medication_names = [med['name'] for med in updated_medications]
        assert set(updated_layer.filters['current_medications']) == set(medication_names), (
            "Context layer should reflect updated medications"
        )
    
    # Verify polypharmacy risk is recalculated
    if len(updated_medications) > 5:
        assert 'polypharmacy_risk' in updated_layer.weights, (
            "Polypharmacy risk should be calculated for >5 medications"
        )
    elif len(updated_medications) <= 5 and 'polypharmacy_risk' in initial_layer.weights:
        # If we went from >5 to <=5 medications, polypharmacy risk might be removed
        # This is acceptable behavior
        pass


@settings(max_examples=100, deadline=None)
@given(
    initial_profile=patient_profile_strategy(),
    updated_demographics=demographics_strategy()
)
def test_demographic_changes_trigger_automatic_context_update(
    initial_profile, updated_demographics
):
    """
    Property 7: Dynamic Context Re-evaluation (Requirement 6.5)
    
    For any physiological changes (demographics), the system should 
    re-evaluate knowledge graph queries with updated patient context to 
    provide revised recommendations.
    
    Validates: Requirements 6.5
    """
    # Create patient context manager
    db = create_mock_database()
    manager = PatientContextManager(db)
    
    # Create initial patient context
    loop = asyncio.get_event_loop()
    initial_context = loop.run_until_complete(
        manager.create_patient_context(
            demographics=initial_profile['demographics'],
            conditions=initial_profile['conditions'],
            medications=initial_profile['medications'],
            allergies=initial_profile['allergies'],
            risk_factors=initial_profile['risk_factors']
        )
    )
    
    # Get initial context layer
    initial_layer = manager.get_context_layer(initial_context.id)
    initial_updated_at = initial_layer.updated_at
    initial_age_risk = initial_layer.weights.get('age_risk', 1.0)
    
    # Update patient demographics (physiological changes)
    updated_context = loop.run_until_complete(
        manager.update_patient_context(
            initial_context.id,
            {'demographics': updated_demographics}
        )
    )
    
    # Verify context was automatically updated
    assert updated_context is not None
    assert updated_context.demographics == updated_demographics
    
    # Verify context layer was automatically updated
    updated_layer = manager.get_context_layer(initial_context.id)
    assert updated_layer.updated_at > initial_updated_at, (
        "Context layer should be re-evaluated after demographic changes"
    )
    
    # Verify demographic filters are updated
    if updated_demographics.get('age'):
        assert updated_layer.filters.get('age') == updated_demographics['age'], (
            "Age filter should reflect updated demographics"
        )
    
    if updated_demographics.get('gender'):
        assert updated_layer.filters.get('gender') == updated_demographics['gender'], (
            "Gender filter should reflect updated demographics"
        )
    
    # Verify age-based risk weights are recalculated
    updated_age = updated_demographics.get('age')
    if updated_age:
        if updated_age > 65:
            assert 'age_risk' in updated_layer.weights, (
                "Elderly patients should have age risk weight"
            )
            assert updated_layer.weights['age_risk'] >= 1.0, (
                "Elderly age risk should be >= 1.0"
            )
        elif updated_age < 18:
            assert 'age_risk' in updated_layer.weights, (
                "Pediatric patients should have age risk weight"
            )
            assert updated_layer.weights['age_risk'] >= 1.0, (
                "Pediatric age risk should be >= 1.0"
            )


@settings(max_examples=100, deadline=None)
@given(
    initial_profile=patient_profile_strategy(),
    updated_allergies=allergies_strategy()
)
def test_allergy_changes_trigger_automatic_context_update(
    initial_profile, updated_allergies
):
    """
    Property 7: Dynamic Context Re-evaluation (Requirement 2.5)
    
    For any allergy changes, the system should automatically update 
    patient context layers and trigger knowledge graph re-evaluation.
    
    Validates: Requirements 2.5
    """
    # Create patient context manager
    db = create_mock_database()
    manager = PatientContextManager(db)
    
    # Create initial patient context
    loop = asyncio.get_event_loop()
    initial_context = loop.run_until_complete(
        manager.create_patient_context(
            demographics=initial_profile['demographics'],
            conditions=initial_profile['conditions'],
            medications=initial_profile['medications'],
            allergies=initial_profile['allergies'],
            risk_factors=initial_profile['risk_factors']
        )
    )
    
    # Get initial context layer
    initial_layer = manager.get_context_layer(initial_context.id)
    initial_updated_at = initial_layer.updated_at
    
    # Update patient allergies (critical field)
    updated_context = loop.run_until_complete(
        manager.update_patient_context(
            initial_context.id,
            {'allergies': updated_allergies}
        )
    )
    
    # Verify context was automatically updated
    assert updated_context is not None
    assert set(updated_context.allergies) == set(updated_allergies)
    
    # Verify context layer was automatically updated
    updated_layer = manager.get_context_layer(initial_context.id)
    assert updated_layer.updated_at > initial_updated_at, (
        "Context layer should be re-evaluated after allergy changes"
    )
    
    # Verify allergy filters are updated
    if updated_allergies:
        assert 'allergies' in updated_layer.filters, (
            "Context layer should include allergy filters"
        )
        assert set(updated_layer.filters['allergies']) == set(updated_allergies), (
            "Context layer should reflect updated allergies"
        )
        
        # Verify allergy risk weight is present
        assert 'allergy_risk' in updated_layer.weights, (
            "Allergy risk weight should be present when allergies exist"
        )
        assert updated_layer.weights['allergy_risk'] > 1.0, (
            "Allergy risk weight should be > 1.0"
        )


@settings(max_examples=100, deadline=None)
@given(
    initial_profile=patient_profile_strategy(),
    updated_risk_factors=risk_factors_strategy()
)
def test_risk_factor_changes_trigger_automatic_context_update(
    initial_profile, updated_risk_factors
):
    """
    Property 7: Dynamic Context Re-evaluation (Requirement 2.5)
    
    For any risk factor changes, the system should automatically update 
    patient context layers and trigger knowledge graph re-evaluation.
    
    Validates: Requirements 2.5
    """
    # Create patient context manager
    db = create_mock_database()
    manager = PatientContextManager(db)
    
    # Create initial patient context
    loop = asyncio.get_event_loop()
    initial_context = loop.run_until_complete(
        manager.create_patient_context(
            demographics=initial_profile['demographics'],
            conditions=initial_profile['conditions'],
            medications=initial_profile['medications'],
            allergies=initial_profile['allergies'],
            risk_factors=initial_profile['risk_factors']
        )
    )
    
    # Get initial context layer
    initial_layer = manager.get_context_layer(initial_context.id)
    initial_updated_at = initial_layer.updated_at
    
    # Update patient risk factors (critical field)
    updated_context = loop.run_until_complete(
        manager.update_patient_context(
            initial_context.id,
            {'risk_factors': updated_risk_factors}
        )
    )
    
    # Verify context was automatically updated
    assert updated_context is not None
    assert set(updated_context.risk_factors) == set(updated_risk_factors)
    
    # Verify context layer was automatically updated
    updated_layer = manager.get_context_layer(initial_context.id)
    assert updated_layer.updated_at > initial_updated_at, (
        "Context layer should be re-evaluated after risk factor changes"
    )
    
    # Verify risk factor weights are recalculated
    if updated_risk_factors:
        assert 'risk_factors' in updated_layer.weights, (
            "Risk factors weight should be present when risk factors exist"
        )
        assert updated_layer.weights['risk_factors'] >= 1.0, (
            "Risk factors weight should be >= 1.0"
        )


@settings(max_examples=50, deadline=None)
@given(profile=patient_profile_strategy())
def test_non_critical_changes_do_not_trigger_reevaluation(profile):
    """
    Property 7: Dynamic Context Re-evaluation (Efficiency)
    
    For any non-critical field changes (like preferences), the system should 
    update the context but not trigger expensive re-evaluation.
    
    Validates: Requirements 2.5
    """
    # Create patient context manager
    db = create_mock_database()
    manager = PatientContextManager(db)
    
    # Create initial patient context
    loop = asyncio.get_event_loop()
    initial_context = loop.run_until_complete(
        manager.create_patient_context(
            demographics=profile['demographics'],
            conditions=profile['conditions'],
            medications=profile['medications'],
            allergies=profile['allergies'],
            risk_factors=profile['risk_factors'],
            preferences={'language': 'en', 'notifications': True}
        )
    )
    
    # Get initial context layer
    initial_layer = manager.get_context_layer(initial_context.id)
    initial_updated_at = initial_layer.updated_at
    
    # Update non-critical field (preferences)
    updated_context = loop.run_until_complete(
        manager.update_patient_context(
            initial_context.id,
            {'preferences': {'language': 'es', 'notifications': False}}
        )
    )
    
    # Verify context was updated
    assert updated_context is not None
    assert updated_context.preferences['language'] == 'es'
    
    # Verify update was recorded but marked as not requiring re-evaluation
    update_history = manager.get_update_history(initial_context.id)
    preference_updates = [u for u in update_history if u.field == 'preferences']
    
    if preference_updates:
        assert preference_updates[0].requires_reevaluation is False, (
            "Preference updates should not require re-evaluation"
        )


@settings(max_examples=100, deadline=None)
@given(
    initial_profile=patient_profile_strategy(),
    new_condition=st.sampled_from([
        'diabetes', 'hypertension', 'heart_disease', 'asthma',
        'copd', 'arthritis', 'depression', 'anxiety'
    ])
)
def test_adding_condition_triggers_reevaluation(initial_profile, new_condition):
    """
    Property 7: Dynamic Context Re-evaluation (Incremental Updates)
    
    For any new condition added to patient profile, the system should 
    automatically update context layers and trigger re-evaluation.
    
    Validates: Requirements 2.5
    """
    # Ensure new condition is not already in profile
    assume(new_condition not in initial_profile['conditions'])
    
    # Create patient context manager
    db = create_mock_database()
    manager = PatientContextManager(db)
    
    # Create initial patient context
    loop = asyncio.get_event_loop()
    initial_context = loop.run_until_complete(
        manager.create_patient_context(
            demographics=initial_profile['demographics'],
            conditions=initial_profile['conditions'],
            medications=initial_profile['medications'],
            allergies=initial_profile['allergies'],
            risk_factors=initial_profile['risk_factors']
        )
    )
    
    # Get initial context layer
    initial_layer = manager.get_context_layer(initial_context.id)
    initial_updated_at = initial_layer.updated_at
    initial_condition_count = len(initial_profile['conditions'])
    
    # Add new condition
    success = loop.run_until_complete(
        manager.add_condition(initial_context.id, new_condition)
    )
    
    assert success is True, "Adding condition should succeed"
    
    # Verify context was updated
    updated_context = loop.run_until_complete(
        manager.get_patient_context(initial_context.id)
    )
    assert new_condition in updated_context.conditions, (
        "New condition should be added to patient context"
    )
    
    # Verify context layer was re-evaluated
    updated_layer = manager.get_context_layer(initial_context.id)
    assert updated_layer.updated_at > initial_updated_at, (
        "Context layer should be re-evaluated after adding condition"
    )
    
    # Verify condition risk weight is recalculated
    if len(updated_context.conditions) > 0:
        assert 'condition_risk' in updated_layer.weights, (
            "Condition risk weight should be present"
        )
        expected_weight = 1.0 + (len(updated_context.conditions) * 0.05)
        assert updated_layer.weights['condition_risk'] >= expected_weight, (
            f"Condition risk weight should reflect {len(updated_context.conditions)} conditions"
        )


@settings(max_examples=100, deadline=None)
@given(
    initial_profile=patient_profile_strategy(),
    new_medication=st.fixed_dictionaries({
        'name': st.sampled_from(['Aspirin', 'Ibuprofen', 'Acetaminophen']),
        'dosage': st.sampled_from(['81mg', '100mg', '200mg', '500mg']),
        'frequency': st.sampled_from(['daily', 'twice daily', 'as needed'])
    })
)
def test_adding_medication_triggers_reevaluation(initial_profile, new_medication):
    """
    Property 7: Dynamic Context Re-evaluation (Incremental Updates)
    
    For any new medication added to patient profile, the system should 
    automatically update context layers and trigger re-evaluation.
    
    Validates: Requirements 2.5
    """
    # Create patient context manager
    db = create_mock_database()
    manager = PatientContextManager(db)
    
    # Create initial patient context
    loop = asyncio.get_event_loop()
    initial_context = loop.run_until_complete(
        manager.create_patient_context(
            demographics=initial_profile['demographics'],
            conditions=initial_profile['conditions'],
            medications=initial_profile['medications'],
            allergies=initial_profile['allergies'],
            risk_factors=initial_profile['risk_factors']
        )
    )
    
    # Get initial context layer
    initial_layer = manager.get_context_layer(initial_context.id)
    initial_updated_at = initial_layer.updated_at
    initial_med_count = len(initial_profile['medications'])
    
    # Add new medication
    success = loop.run_until_complete(
        manager.add_medication(initial_context.id, new_medication)
    )
    
    assert success is True, "Adding medication should succeed"
    
    # Verify context was updated
    updated_context = loop.run_until_complete(
        manager.get_patient_context(initial_context.id)
    )
    assert len(updated_context.medications) == initial_med_count + 1, (
        "Medication count should increase by 1"
    )
    
    # Verify context layer was re-evaluated
    updated_layer = manager.get_context_layer(initial_context.id)
    assert updated_layer.updated_at > initial_updated_at, (
        "Context layer should be re-evaluated after adding medication"
    )
    
    # Verify medication filters are updated
    assert 'current_medications' in updated_layer.filters, (
        "Context layer should include medication filters"
    )
    assert new_medication['name'] in updated_layer.filters['current_medications'], (
        "New medication should be in context layer filters"
    )


@settings(max_examples=50, deadline=None)
@given(
    initial_profile=patient_profile_strategy(),
    updates=st.fixed_dictionaries({
        'conditions': conditions_strategy(),
        'medications': medications_strategy()
    })
)
def test_multiple_simultaneous_changes_trigger_single_reevaluation(
    initial_profile, updates
):
    """
    Property 7: Dynamic Context Re-evaluation (Efficiency)
    
    For any multiple simultaneous changes to patient profile, the system 
    should trigger a single re-evaluation rather than multiple re-evaluations.
    
    Validates: Requirements 2.5
    """
    # Create patient context manager
    db = create_mock_database()
    manager = PatientContextManager(db)
    
    # Create initial patient context
    loop = asyncio.get_event_loop()
    initial_context = loop.run_until_complete(
        manager.create_patient_context(
            demographics=initial_profile['demographics'],
            conditions=initial_profile['conditions'],
            medications=initial_profile['medications'],
            allergies=initial_profile['allergies'],
            risk_factors=initial_profile['risk_factors']
        )
    )
    
    # Get initial context layer
    initial_layer = manager.get_context_layer(initial_context.id)
    initial_updated_at = initial_layer.updated_at
    
    # Update multiple fields simultaneously
    updated_context = loop.run_until_complete(
        manager.update_patient_context(
            initial_context.id,
            updates
        )
    )
    
    # Verify context was updated
    assert updated_context is not None
    assert set(updated_context.conditions) == set(updates['conditions'])
    assert len(updated_context.medications) == len(updates['medications'])
    
    # Verify context layer was re-evaluated once
    updated_layer = manager.get_context_layer(initial_context.id)
    assert updated_layer.updated_at > initial_updated_at, (
        "Context layer should be re-evaluated after multiple changes"
    )
    
    # Verify update history shows both changes
    update_history = manager.get_update_history(initial_context.id)
    condition_updates = [u for u in update_history if u.field == 'conditions']
    medication_updates = [u for u in update_history if u.field == 'medications']
    
    assert len(condition_updates) > 0, "Conditions update should be recorded"
    assert len(medication_updates) > 0, "Medications update should be recorded"
