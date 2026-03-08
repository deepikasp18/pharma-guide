"""
Property-based tests for dynamic context re-evaluation

**Validates: Requirements 2.5, 6.5**

Property 7: Dynamic Context Re-evaluation
For any patient profile change, the system should automatically update context layers
and trigger knowledge graph re-evaluation.
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite
from typing import List, Dict, Any

from src.knowledge_graph.patient_context import PatientContextManager, ContextUpdate
from src.knowledge_graph.models import PatientContext
from src.knowledge_graph.database import KnowledgeGraphDatabase
from unittest.mock import AsyncMock, MagicMock


# ============================================================================
# Strategy Generators for Property-Based Testing
# ============================================================================

@composite
def patient_context_strategy(draw):
    """Generate patient context"""
    age = draw(st.integers(min_value=18, max_value=90))
    weight = draw(st.floats(min_value=40.0, max_value=150.0))
    gender = draw(st.sampled_from(['male', 'female']))
    
    conditions = ['hypertension', 'diabetes', 'asthma']
    num_conditions = draw(st.integers(min_value=0, max_value=2))
    selected_conditions = draw(st.lists(
        st.sampled_from(conditions),
        min_size=num_conditions,
        max_size=num_conditions,
        unique=True
    )) if num_conditions > 0 else []
    
    drugs = ['Lisinopril', 'Metformin', 'Aspirin']
    num_meds = draw(st.integers(min_value=0, max_value=3))
    medications = []
    if num_meds > 0:
        selected_drugs = draw(st.lists(
            st.sampled_from(drugs),
            min_size=num_meds,
            max_size=num_meds,
            unique=True
        ))
        medications = [{'name': drug, 'dosage': '10mg'} for drug in selected_drugs]
    
    return PatientContext(
        id=f"patient_{draw(st.integers(min_value=1, max_value=10000))}",
        demographics={'age': age, 'weight': weight, 'gender': gender},
        conditions=selected_conditions,
        medications=medications,
        allergies=[],
        genetic_factors={},
        risk_factors=[],
        preferences={}
    )


@composite
def medication_update_strategy(draw):
    """Generate medication updates"""
    drugs = ['Warfarin', 'Atorvastatin', 'Amlodipine', 'Losartan']
    num_meds = draw(st.integers(min_value=1, max_value=4))
    
    medications = []
    selected_drugs = draw(st.lists(
        st.sampled_from(drugs),
        min_size=num_meds,
        max_size=num_meds,
        unique=True
    ))
    
    for drug in selected_drugs:
        medications.append({
            'name': drug,
            'dosage': draw(st.sampled_from(['5mg', '10mg', '20mg'])),
            'frequency': draw(st.sampled_from(['once daily', 'twice daily']))
        })
    
    return medications


@composite
def condition_update_strategy(draw):
    """Generate condition updates"""
    conditions = ['heart_failure', 'chronic_kidney_disease', 'copd', 'depression']
    num_conditions = draw(st.integers(min_value=1, max_value=3))
    
    return draw(st.lists(
        st.sampled_from(conditions),
        min_size=num_conditions,
        max_size=num_conditions,
        unique=True
    ))


@composite
def demographics_update_strategy(draw):
    """Generate demographics updates"""
    return {
        'age': draw(st.integers(min_value=18, max_value=90)),
        'weight': draw(st.floats(min_value=40.0, max_value=150.0)),
        'gender': draw(st.sampled_from(['male', 'female']))
    }


# ============================================================================
# Property-Based Tests for Dynamic Context Re-evaluation
# ============================================================================

class TestDynamicContextReevaluationProperties:
    """
    Property-based tests for dynamic context re-evaluation
    
    **Validates: Requirements 2.5, 6.5**
    """
    
    @given(
        patient=patient_context_strategy(),
        new_medications=medication_update_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_medication_changes_trigger_reevaluation(
        self,
        patient: PatientContext,
        new_medications: List[Dict]
    ):
        """
        Property: Medication changes trigger context re-evaluation
        
        **Validates: Requirements 2.5, 6.5**
        
        For any patient context, when medications are updated,
        the system should trigger re-evaluation.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.create_patient_vertex = AsyncMock(return_value=f"vertex_{patient.id}")
        
        # Create context manager
        manager = PatientContextManager(mock_db)
        
        # Create initial context
        await manager.create_patient_context(
            patient_id=patient.id,
            demographics=patient.demographics,
            conditions=patient.conditions,
            medications=patient.medications,
            allergies=patient.allergies,
            genetic_factors=patient.genetic_factors,
            risk_factors=patient.risk_factors
        )
        
        # Update medications
        update_result = await manager.update_patient_context(
            patient.id,
            {'medications': new_medications}
        )
        
        # Verify update result
        assert isinstance(update_result, ContextUpdate)
        assert update_result.update_type in ['add', 'modify', 'remove']
        assert update_result.field == 'medications'
        
        # Medication changes should require re-evaluation
        assert update_result.requires_reevaluation is True, \
            "Medication changes should trigger re-evaluation"
        
        # Verify context was updated
        updated_context = await manager.get_patient_context(patient.id)
        assert updated_context.medications == new_medications
    
    @given(
        patient=patient_context_strategy(),
        new_conditions=condition_update_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_condition_changes_trigger_reevaluation(
        self,
        patient: PatientContext,
        new_conditions: List[str]
    ):
        """
        Property: Condition changes trigger context re-evaluation
        
        **Validates: Requirements 2.5, 6.5**
        
        For any patient context, when conditions are updated,
        the system should trigger re-evaluation.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.create_patient_vertex = AsyncMock(return_value=f"vertex_{patient.id}")
        
        # Create context manager
        manager = PatientContextManager(mock_db)
        
        # Create initial context
        await manager.create_patient_context(
            patient_id=patient.id,
            demographics=patient.demographics,
            conditions=patient.conditions,
            medications=patient.medications,
            allergies=patient.allergies,
            genetic_factors=patient.genetic_factors,
            risk_factors=patient.risk_factors
        )
        
        # Update conditions
        update_result = await manager.update_patient_context(
            patient.id,
            {'conditions': new_conditions}
        )
        
        # Verify update result
        assert isinstance(update_result, ContextUpdate)
        assert update_result.field == 'conditions'
        
        # Condition changes should require re-evaluation
        assert update_result.requires_reevaluation is True, \
            "Condition changes should trigger re-evaluation"
        
        # Verify context was updated
        updated_context = await manager.get_patient_context(patient.id)
        assert updated_context.conditions == new_conditions
    
    @given(patient=patient_context_strategy())
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_age_threshold_crossing_triggers_reevaluation(self, patient: PatientContext):
        """
        Property: Crossing age thresholds triggers re-evaluation
        
        **Validates: Requirements 2.5, 6.5**
        
        For any patient context, when age crosses significant thresholds
        (18, 65), the system should trigger re-evaluation.
        """
        # Test crossing 65 threshold
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.create_patient_vertex = AsyncMock(return_value=f"vertex_{patient.id}")
        
        # Create context manager
        manager = PatientContextManager(mock_db)
        
        # Create initial context with age 64
        initial_demographics = {'age': 64, 'weight': 70, 'gender': 'male'}
        await manager.create_patient_context(
            patient_id=patient.id,
            demographics=initial_demographics,
            conditions=patient.conditions,
            medications=patient.medications,
            allergies=patient.allergies,
            genetic_factors=patient.genetic_factors,
            risk_factors=patient.risk_factors
        )
        
        # Update to age 65 (crossing elderly threshold)
        new_demographics = {'age': 65, 'weight': 70, 'gender': 'male'}
        update_result = await manager.update_patient_context(
            patient.id,
            {'demographics': new_demographics}
        )
        
        # Crossing age threshold should require re-evaluation
        assert update_result.requires_reevaluation is True, \
            "Crossing age threshold (65) should trigger re-evaluation"
    
    @given(patient=patient_context_strategy())
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_minor_weight_changes_do_not_trigger_reevaluation(
        self,
        patient: PatientContext
    ):
        """
        Property: Minor weight changes do not trigger re-evaluation
        
        **Validates: Requirements 2.5, 6.5**
        
        For any patient context, minor weight changes (< 5kg) should not
        trigger re-evaluation.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.create_patient_vertex = AsyncMock(return_value=f"vertex_{patient.id}")
        
        # Create context manager
        manager = PatientContextManager(mock_db)
        
        # Create initial context
        initial_weight = 70.0
        initial_demographics = {
            'age': patient.demographics.get('age', 40),
            'weight': initial_weight,
            'gender': patient.demographics.get('gender', 'male')
        }
        
        await manager.create_patient_context(
            patient_id=patient.id,
            demographics=initial_demographics,
            conditions=patient.conditions,
            medications=patient.medications,
            allergies=patient.allergies,
            genetic_factors=patient.genetic_factors,
            risk_factors=patient.risk_factors
        )
        
        # Update with minor weight change (< 5kg)
        new_demographics = initial_demographics.copy()
        new_demographics['weight'] = initial_weight + 3.0  # 3kg change
        
        update_result = await manager.update_patient_context(
            patient.id,
            {'demographics': new_demographics}
        )
        
        # Minor weight change should not require re-evaluation
        assert update_result.requires_reevaluation is False, \
            "Minor weight changes (< 5kg) should not trigger re-evaluation"
    
    @given(
        patient=patient_context_strategy(),
        new_demographics=demographics_update_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_context_updates_are_tracked(
        self,
        patient: PatientContext,
        new_demographics: Dict
    ):
        """
        Property: Context updates are properly tracked
        
        **Validates: Requirements 2.5, 6.5**
        
        For any context update, the system should track old and new values
        and timestamp the change.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.create_patient_vertex = AsyncMock(return_value=f"vertex_{patient.id}")
        
        # Create context manager
        manager = PatientContextManager(mock_db)
        
        # Create initial context
        await manager.create_patient_context(
            patient_id=patient.id,
            demographics=patient.demographics,
            conditions=patient.conditions,
            medications=patient.medications,
            allergies=patient.allergies,
            genetic_factors=patient.genetic_factors,
            risk_factors=patient.risk_factors
        )
        
        # Update demographics
        update_result = await manager.update_patient_context(
            patient.id,
            {'demographics': new_demographics}
        )
        
        # Verify update tracking
        assert update_result.field == 'demographics'
        assert update_result.old_value == patient.demographics
        assert update_result.new_value == new_demographics
        assert update_result.timestamp is not None
    
    @given(patient=patient_context_strategy())
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_multiple_updates_maintain_consistency(self, patient: PatientContext):
        """
        Property: Multiple updates maintain context consistency
        
        **Validates: Requirements 2.5, 6.5**
        
        For any sequence of updates, the context should remain consistent
        and reflect all changes.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.create_patient_vertex = AsyncMock(return_value=f"vertex_{patient.id}")
        
        # Create context manager
        manager = PatientContextManager(mock_db)
        
        # Create initial context
        await manager.create_patient_context(
            patient_id=patient.id,
            demographics=patient.demographics,
            conditions=patient.conditions,
            medications=patient.medications,
            allergies=patient.allergies,
            genetic_factors=patient.genetic_factors,
            risk_factors=patient.risk_factors
        )
        
        # Perform multiple updates
        new_medications = [{'name': 'Warfarin', 'dosage': '5mg'}]
        await manager.update_patient_context(
            patient.id,
            {'medications': new_medications}
        )
        
        new_conditions = ['heart_failure']
        await manager.update_patient_context(
            patient.id,
            {'conditions': new_conditions}
        )
        
        # Verify final context reflects all changes
        final_context = await manager.get_patient_context(patient.id)
        assert final_context.medications == new_medications
        assert final_context.conditions == new_conditions
        assert final_context.demographics == patient.demographics  # Unchanged
    
    @given(
        patient=patient_context_strategy(),
        new_medications=medication_update_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_reevaluation_flag_is_deterministic(
        self,
        patient: PatientContext,
        new_medications: List[Dict]
    ):
        """
        Property: Re-evaluation flag is deterministic
        
        **Validates: Requirements 2.5, 6.5**
        
        For the same update, the re-evaluation flag should be consistent
        across multiple calls.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.create_patient_vertex = AsyncMock(return_value=f"vertex_{patient.id}")
        
        # Create context manager
        manager = PatientContextManager(mock_db)
        
        # Create initial context
        await manager.create_patient_context(
            patient_id=patient.id,
            demographics=patient.demographics,
            conditions=patient.conditions,
            medications=patient.medications,
            allergies=patient.allergies,
            genetic_factors=patient.genetic_factors,
            risk_factors=patient.risk_factors
        )
        
        # Check if change is significant
        is_significant = manager._is_significant_change(
            'medications',
            patient.medications,
            new_medications
        )
        
        # Check again - should be same result
        is_significant_2 = manager._is_significant_change(
            'medications',
            patient.medications,
            new_medications
        )
        
        assert is_significant == is_significant_2, \
            "Re-evaluation determination should be deterministic"
    
    @given(patient=patient_context_strategy())
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_context_cache_updated_after_changes(self, patient: PatientContext):
        """
        Property: Context cache is updated after changes
        
        **Validates: Requirements 2.5, 6.5**
        
        For any context update, the cached context should reflect
        the new values immediately.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.create_patient_vertex = AsyncMock(return_value=f"vertex_{patient.id}")
        
        # Create context manager
        manager = PatientContextManager(mock_db)
        
        # Create initial context
        await manager.create_patient_context(
            patient_id=patient.id,
            demographics=patient.demographics,
            conditions=patient.conditions,
            medications=patient.medications,
            allergies=patient.allergies,
            genetic_factors=patient.genetic_factors,
            risk_factors=patient.risk_factors
        )
        
        # Update medications
        new_medications = [{'name': 'Warfarin', 'dosage': '5mg'}]
        await manager.update_patient_context(
            patient.id,
            {'medications': new_medications}
        )
        
        # Retrieve from cache
        cached_context = await manager.get_patient_context(patient.id)
        
        # Cache should reflect update
        assert cached_context.medications == new_medications, \
            "Context cache should be updated immediately after changes"
    
    @given(patient=patient_context_strategy())
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_adding_first_medication_triggers_reevaluation(
        self,
        patient: PatientContext
    ):
        """
        Property: Adding first medication triggers re-evaluation
        
        **Validates: Requirements 2.5, 6.5**
        
        For a patient with no medications, adding the first medication
        should trigger re-evaluation.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.create_patient_vertex = AsyncMock(return_value=f"vertex_{patient.id}")
        
        # Create context manager
        manager = PatientContextManager(mock_db)
        
        # Create initial context with no medications
        await manager.create_patient_context(
            patient_id=patient.id,
            demographics=patient.demographics,
            conditions=patient.conditions,
            medications=[],  # No medications
            allergies=patient.allergies,
            genetic_factors=patient.genetic_factors,
            risk_factors=patient.risk_factors
        )
        
        # Add first medication
        new_medications = [{'name': 'Aspirin', 'dosage': '81mg'}]
        update_result = await manager.update_patient_context(
            patient.id,
            {'medications': new_medications}
        )
        
        # Adding first medication should trigger re-evaluation
        assert update_result.requires_reevaluation is True, \
            "Adding first medication should trigger re-evaluation"
    
    @given(patient=patient_context_strategy())
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_removing_all_medications_triggers_reevaluation(
        self,
        patient: PatientContext
    ):
        """
        Property: Removing all medications triggers re-evaluation
        
        **Validates: Requirements 2.5, 6.5**
        
        For a patient with medications, removing all medications
        should trigger re-evaluation.
        """
        # Skip if patient has no medications
        assume(len(patient.medications) > 0)
        
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.create_patient_vertex = AsyncMock(return_value=f"vertex_{patient.id}")
        
        # Create context manager
        manager = PatientContextManager(mock_db)
        
        # Create initial context with medications
        await manager.create_patient_context(
            patient_id=patient.id,
            demographics=patient.demographics,
            conditions=patient.conditions,
            medications=patient.medications,
            allergies=patient.allergies,
            genetic_factors=patient.genetic_factors,
            risk_factors=patient.risk_factors
        )
        
        # Remove all medications
        update_result = await manager.update_patient_context(
            patient.id,
            {'medications': []}
        )
        
        # Removing all medications should trigger re-evaluation
        assert update_result.requires_reevaluation is True, \
            "Removing all medications should trigger re-evaluation"
