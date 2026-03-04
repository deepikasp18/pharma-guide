"""
Property-based tests for patient context integration

**Validates: Requirements 2.1, 2.2, 2.3**

Property 5: Patient Context Integration
For any patient profile, the system should map characteristics to knowledge graph entities,
establish personalization context layers, and execute contextualized graph queries.
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite
from typing import List, Dict, Any, Optional

from src.knowledge_graph.patient_context import PatientContextManager
from src.knowledge_graph.models import PatientContext
from src.knowledge_graph.database import KnowledgeGraphDatabase
from unittest.mock import AsyncMock, MagicMock


# ============================================================================
# Strategy Generators for Property-Based Testing
# ============================================================================

@composite
def patient_demographics_strategy(draw):
    """Generate valid patient demographics"""
    age = draw(st.integers(min_value=0, max_value=120))
    weight = draw(st.floats(min_value=2.0, max_value=300.0))
    height = draw(st.floats(min_value=30.0, max_value=250.0))
    gender = draw(st.sampled_from(['male', 'female', 'other']))
    
    return {
        'age': age,
        'weight': weight,
        'height': height,
        'gender': gender
    }


@composite
def medical_conditions_strategy(draw):
    """Generate list of medical conditions"""
    conditions = [
        'hypertension', 'diabetes', 'asthma', 'copd', 'heart_failure',
        'chronic_kidney_disease', 'cirrhosis', 'depression', 'anxiety',
        'arthritis', 'osteoporosis', 'hyperlipidemia', 'atrial_fibrillation'
    ]
    
    num_conditions = draw(st.integers(min_value=0, max_value=5))
    if num_conditions == 0:
        return []
    
    return draw(st.lists(
        st.sampled_from(conditions),
        min_size=num_conditions,
        max_size=num_conditions,
        unique=True
    ))


@composite
def medications_strategy(draw):
    """Generate list of medications"""
    drugs = [
        'Lisinopril', 'Metformin', 'Atorvastatin', 'Amlodipine',
        'Aspirin', 'Warfarin', 'Levothyroxine', 'Omeprazole',
        'Albuterol', 'Losartan', 'Simvastatin', 'Gabapentin'
    ]
    
    dosages = ['5mg', '10mg', '20mg', '40mg', '50mg', '100mg', '500mg']
    frequencies = ['once daily', 'twice daily', 'three times daily', 'as needed']
    
    num_meds = draw(st.integers(min_value=0, max_value=8))
    if num_meds == 0:
        return []
    
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
            'dosage': draw(st.sampled_from(dosages)),
            'frequency': draw(st.sampled_from(frequencies))
        })
    
    return medications


@composite
def allergies_strategy(draw):
    """Generate list of drug allergies"""
    common_allergies = [
        'penicillin', 'sulfa', 'aspirin', 'codeine', 'morphine',
        'latex', 'iodine', 'shellfish'
    ]
    
    num_allergies = draw(st.integers(min_value=0, max_value=3))
    if num_allergies == 0:
        return []
    
    return draw(st.lists(
        st.sampled_from(common_allergies),
        min_size=num_allergies,
        max_size=num_allergies,
        unique=True
    ))


@composite
def genetic_factors_strategy(draw):
    """Generate genetic factors"""
    genes = ['CYP2D6', 'CYP2C19', 'CYP2C9', 'CYP3A4']
    statuses = ['poor_metabolizer', 'intermediate_metabolizer', 'normal_metabolizer', 'rapid_metabolizer']
    
    num_factors = draw(st.integers(min_value=0, max_value=3))
    if num_factors == 0:
        return {}
    
    factors = {}
    selected_genes = draw(st.lists(
        st.sampled_from(genes),
        min_size=num_factors,
        max_size=num_factors,
        unique=True
    ))
    
    for gene in selected_genes:
        factors[gene] = draw(st.sampled_from(statuses))
    
    return factors


@composite
def risk_factors_strategy(draw):
    """Generate risk factors"""
    risks = [
        'smoking', 'obesity', 'alcohol_use', 'sedentary_lifestyle',
        'family_history', 'frailty', 'falls_risk'
    ]
    
    num_risks = draw(st.integers(min_value=0, max_value=4))
    if num_risks == 0:
        return []
    
    return draw(st.lists(
        st.sampled_from(risks),
        min_size=num_risks,
        max_size=num_risks,
        unique=True
    ))


@composite
def patient_context_strategy(draw):
    """Generate complete patient context"""
    patient_id = f"patient_{draw(st.integers(min_value=1, max_value=10000))}"
    
    return PatientContext(
        id=patient_id,
        demographics=draw(patient_demographics_strategy()),
        conditions=draw(medical_conditions_strategy()),
        medications=draw(medications_strategy()),
        allergies=draw(allergies_strategy()),
        genetic_factors=draw(genetic_factors_strategy()),
        risk_factors=draw(risk_factors_strategy()),
        preferences={}
    )


@composite
def query_type_strategy(draw):
    """Generate query types"""
    return draw(st.sampled_from([
        'side_effects', 'interactions', 'contraindications',
        'dosing', 'alternatives', 'general'
    ]))


# ============================================================================
# Property-Based Tests for Patient Context Integration
# ============================================================================

class TestPatientContextIntegrationProperties:
    """
    Property-based tests for patient context integration
    
    **Validates: Requirements 2.1, 2.2, 2.3**
    """
    
    @given(patient=patient_context_strategy())
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_patient_context_creation_maps_characteristics(self, patient: PatientContext):
        """
        Property: Patient context creation maps all characteristics to entities
        
        **Validates: Requirement 2.1**
        
        For any patient profile, the system should successfully create a context
        that maps patient characteristics to knowledge graph entities.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.create_patient_vertex = AsyncMock(return_value=f"vertex_{patient.id}")
        
        # Create context manager
        manager = PatientContextManager(mock_db)
        
        # Create patient context
        created_context = await manager.create_patient_context(
            patient_id=patient.id,
            demographics=patient.demographics,
            conditions=patient.conditions,
            medications=patient.medications,
            allergies=patient.allergies,
            genetic_factors=patient.genetic_factors,
            risk_factors=patient.risk_factors
        )
        
        # Verify all characteristics are mapped
        assert created_context.id == patient.id
        assert created_context.demographics == patient.demographics
        assert created_context.conditions == patient.conditions
        assert created_context.medications == patient.medications
        assert created_context.allergies == patient.allergies
        assert created_context.genetic_factors == patient.genetic_factors
        assert created_context.risk_factors == patient.risk_factors
        
        # Verify database vertex creation was called
        assert mock_db.create_patient_vertex.called
    
    @given(
        patient=patient_context_strategy(),
        query_type=query_type_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_context_filters_are_extracted_for_all_query_types(
        self,
        patient: PatientContext,
        query_type: str
    ):
        """
        Property: Context filters are extracted for all query types
        
        **Validates: Requirement 2.2**
        
        For any patient context and query type, the system should extract
        appropriate context filters to apply to graph queries.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Create context manager
        manager = PatientContextManager(mock_db)
        
        # Extract context filters
        filters = manager._extract_context_filters(patient, query_type)
        
        # Should return a list of filters
        assert isinstance(filters, list)
        
        # Filters should be relevant to patient characteristics
        # If patient has conditions, should have condition filters for contraindications
        if patient.conditions and query_type == 'contraindications':
            condition_filters = [f for f in filters if f.filter_type == 'condition']
            assert len(condition_filters) > 0
        
        # If patient has medications, should have medication filters for interactions
        if patient.medications and query_type == 'interactions':
            med_filters = [f for f in filters if f.filter_type == 'medication']
            assert len(med_filters) > 0
        
        # If patient has allergies, should have allergy filters for alternatives
        if patient.allergies and query_type == 'alternatives':
            allergy_filters = [f for f in filters if f.filter_type == 'allergy']
            assert len(allergy_filters) > 0
        
        # All filters should have valid structure
        for filter_obj in filters:
            assert filter_obj.filter_type is not None
            assert filter_obj.property_name is not None
            assert filter_obj.operator is not None
            assert filter_obj.value is not None
            assert 0.0 <= filter_obj.confidence <= 1.0
    
    @given(
        patient=patient_context_strategy(),
        query_type=query_type_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_context_application_modifies_queries(
        self,
        patient: PatientContext,
        query_type: str
    ):
        """
        Property: Patient context application modifies graph queries
        
        **Validates: Requirement 2.2**
        
        For any patient context and base query, applying the context
        should modify the query to include personalization filters.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Create context manager
        manager = PatientContextManager(mock_db)
        
        # Base query
        base_query = "g.V().hasLabel('Drug').has('name', 'Aspirin').toList()"
        
        # Apply context to query
        modified_query = manager.apply_context_to_query(
            base_query,
            patient,
            query_type
        )
        
        # Modified query should be different from base query (if patient has relevant characteristics)
        has_relevant_characteristics = (
            (query_type == 'side_effects' and patient.demographics.get('age')) or
            (query_type == 'interactions' and patient.medications) or
            (query_type == 'contraindications' and patient.conditions) or
            (query_type == 'alternatives' and patient.allergies) or
            (query_type == 'dosing' and patient.genetic_factors)
        )
        
        if has_relevant_characteristics:
            # Query should be modified
            assert modified_query != base_query, \
                f"Query should be modified for patient with relevant characteristics"
        
        # Modified query should still be valid Gremlin syntax
        assert modified_query.startswith("g.V()")
        assert "toList()" in modified_query or modified_query.endswith(")")
    
    @given(patient=patient_context_strategy())
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_context_retrieval_is_consistent(self, patient: PatientContext):
        """
        Property: Context retrieval returns consistent results
        
        **Validates: Requirement 2.1**
        
        For any patient context, retrieving it multiple times should
        return the same context data.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.create_patient_vertex = AsyncMock(return_value=f"vertex_{patient.id}")
        
        # Create context manager
        manager = PatientContextManager(mock_db)
        
        # Create patient context
        await manager.create_patient_context(
            patient_id=patient.id,
            demographics=patient.demographics,
            conditions=patient.conditions,
            medications=patient.medications,
            allergies=patient.allergies,
            genetic_factors=patient.genetic_factors,
            risk_factors=patient.risk_factors
        )
        
        # Retrieve context multiple times
        context1 = await manager.get_patient_context(patient.id)
        context2 = await manager.get_patient_context(patient.id)
        
        # Should return same context
        assert context1.id == context2.id
        assert context1.demographics == context2.demographics
        assert context1.conditions == context2.conditions
        assert context1.medications == context2.medications
        assert context1.allergies == context2.allergies
        assert context1.genetic_factors == context2.genetic_factors
        assert context1.risk_factors == context2.risk_factors
    
    @given(patient=patient_context_strategy())
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_personalized_risk_factors_calculated_for_all_patients(
        self,
        patient: PatientContext
    ):
        """
        Property: Personalized risk factors are calculated for all patients
        
        **Validates: Requirement 2.3**
        
        For any patient context, the system should calculate personalized
        risk factors based on patient characteristics.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Create context manager
        manager = PatientContextManager(mock_db)
        
        # Calculate personalized risk factors
        risk_factors = await manager.calculate_personalized_risk_factors(
            patient,
            "drug_test_001"
        )
        
        # Should return risk factor dictionary
        assert isinstance(risk_factors, dict)
        assert 'overall_risk' in risk_factors
        assert 'age_risk' in risk_factors
        assert 'comorbidity_risk' in risk_factors
        assert 'polypharmacy_risk' in risk_factors
        
        # All risk values should be between 0 and 1
        for risk_type, risk_value in risk_factors.items():
            assert 0.0 <= risk_value <= 1.0, \
                f"Risk factor {risk_type} should be between 0 and 1, got {risk_value}"
        
        # Overall risk should be sum of components (capped at 1.0)
        component_sum = (
            risk_factors['age_risk'] +
            risk_factors['comorbidity_risk'] +
            risk_factors['polypharmacy_risk'] +
            risk_factors.get('genetic_risk', 0.0)
        )
        expected_overall = min(component_sum, 1.0)
        
        assert abs(risk_factors['overall_risk'] - expected_overall) < 0.01, \
            f"Overall risk should be sum of components (capped at 1.0)"
    
    @given(
        patient=patient_context_strategy(),
        query_type=query_type_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_age_based_filtering_applied_correctly(
        self,
        patient: PatientContext,
        query_type: str
    ):
        """
        Property: Age-based filtering is applied correctly
        
        **Validates: Requirement 2.2**
        
        For any patient with age information, age-based filters should
        be applied appropriately to queries.
        """
        # Skip if no age information
        assume('age' in patient.demographics)
        
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Create context manager
        manager = PatientContextManager(mock_db)
        
        # Extract filters
        filters = manager._extract_context_filters(patient, query_type)
        
        # Check for age-related filters
        age_filters = [f for f in filters if f.filter_type == 'age']
        
        age = patient.demographics['age']
        
        # Elderly patients (>= 65) should have age filters for side effects
        if age >= 65 and query_type == 'side_effects':
            assert len(age_filters) > 0, \
                "Elderly patients should have age filters for side effects"
            
            # Age filter should have appropriate threshold
            for age_filter in age_filters:
                assert age_filter.value >= 0.5, \
                    "Elderly patients should have higher age relevance threshold"
        
        # Pediatric patients (< 18) should have age filters
        if age < 18 and query_type == 'side_effects':
            assert len(age_filters) > 0, \
                "Pediatric patients should have age filters for side effects"
    
    @given(patient=patient_context_strategy())
    @settings(max_examples=100, deadline=None)
    def test_medication_interaction_filtering(self, patient: PatientContext):
        """
        Property: Medication interaction filtering is applied
        
        **Validates: Requirement 2.2**
        
        For any patient with current medications, interaction filters
        should be applied to interaction queries.
        """
        # Skip if no medications
        assume(len(patient.medications) > 0)
        
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Create context manager
        manager = PatientContextManager(mock_db)
        
        # Extract filters for interactions
        filters = manager._extract_context_filters(patient, 'interactions')
        
        # Should have medication filters
        med_filters = [f for f in filters if f.filter_type == 'medication']
        assert len(med_filters) > 0, \
            "Patients with medications should have medication filters for interactions"
        
        # Medication filter should include patient's medications
        for med_filter in med_filters:
            assert isinstance(med_filter.value, list)
            # At least some of patient's medications should be in filter
            patient_med_names = [m['name'] for m in patient.medications]
            assert any(med in med_filter.value for med in patient_med_names), \
                "Medication filter should include patient's medications"
    
    @given(patient=patient_context_strategy())
    @settings(max_examples=100, deadline=None)
    def test_allergy_exclusion_filtering(self, patient: PatientContext):
        """
        Property: Allergy exclusion filtering is applied
        
        **Validates: Requirement 2.2**
        
        For any patient with allergies, allergy exclusion filters
        should be applied to alternative medication queries.
        """
        # Skip if no allergies
        assume(len(patient.allergies) > 0)
        
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Create context manager
        manager = PatientContextManager(mock_db)
        
        # Extract filters for alternatives
        filters = manager._extract_context_filters(patient, 'alternatives')
        
        # Should have allergy filters
        allergy_filters = [f for f in filters if f.filter_type == 'allergy']
        assert len(allergy_filters) > 0, \
            "Patients with allergies should have allergy filters for alternatives"
        
        # Allergy filter should use 'not_in' operator
        for allergy_filter in allergy_filters:
            assert allergy_filter.operator == 'not_in', \
                "Allergy filters should use 'not_in' operator"
            
            # Should include patient's allergies
            assert isinstance(allergy_filter.value, list)
            assert any(allergy in allergy_filter.value for allergy in patient.allergies), \
                "Allergy filter should include patient's allergies"
    
    @given(patient=patient_context_strategy())
    @settings(max_examples=100, deadline=None)
    def test_genetic_factor_filtering(self, patient: PatientContext):
        """
        Property: Genetic factor filtering is applied
        
        **Validates: Requirement 2.2**
        
        For any patient with genetic factors, genetic filters
        should be applied to dosing queries.
        """
        # Skip if no genetic factors
        assume(len(patient.genetic_factors) > 0)
        
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Create context manager
        manager = PatientContextManager(mock_db)
        
        # Extract filters for dosing
        filters = manager._extract_context_filters(patient, 'dosing')
        
        # Should have genetic filters
        genetic_filters = [f for f in filters if f.filter_type == 'genetic']
        assert len(genetic_filters) > 0, \
            "Patients with genetic factors should have genetic filters for dosing"
        
        # Genetic filters should reference patient's genetic factors
        for genetic_filter in genetic_filters:
            # Property name should be one of the patient's genes
            gene_name = genetic_filter.property_name.split('_')[0].upper()
            assert any(gene in genetic_filter.property_name for gene in patient.genetic_factors.keys()), \
                f"Genetic filter should reference patient's genetic factors"
    
    @given(
        patient=patient_context_strategy(),
        base_query=st.sampled_from([
            "g.V().hasLabel('Drug').toList()",
            "g.V().hasLabel('Drug').has('name', 'Aspirin').outE('CAUSES').inV().toList()",
            "g.V().hasLabel('Drug').has('name', 'Warfarin').outE('INTERACTS_WITH').inV().toList()"
        ])
    )
    @settings(max_examples=100, deadline=None)
    def test_query_modification_preserves_syntax(
        self,
        patient: PatientContext,
        base_query: str
    ):
        """
        Property: Query modification preserves valid Gremlin syntax
        
        **Validates: Requirement 2.2**
        
        For any base query and patient context, the modified query
        should maintain valid Gremlin syntax.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Create context manager
        manager = PatientContextManager(mock_db)
        
        # Apply context to query
        query_types = ['side_effects', 'interactions', 'contraindications', 'dosing', 'alternatives']
        
        for query_type in query_types:
            modified_query = manager.apply_context_to_query(
                base_query,
                patient,
                query_type
            )
            
            # Should start with g.V()
            assert modified_query.startswith("g.V()"), \
                f"Modified query should start with g.V()"
            
            # Should have balanced parentheses
            assert modified_query.count('(') == modified_query.count(')'), \
                f"Modified query should have balanced parentheses"
            
            # Should end with terminal step
            assert modified_query.endswith('.toList()') or modified_query.endswith(')'), \
                f"Modified query should end with terminal step"
