"""
Unit tests for patient context management
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.knowledge_graph.patient_context import (
    PatientContextManager,
    ContextFilter,
    ContextUpdate,
    create_patient_context_manager
)
from src.knowledge_graph.models import PatientContext
from src.knowledge_graph.database import KnowledgeGraphDatabase


@pytest.fixture
def mock_database():
    """Create a mock database"""
    db = MagicMock(spec=KnowledgeGraphDatabase)
    db.create_patient_vertex = AsyncMock(return_value="patient_vertex_id")
    return db


@pytest.fixture
def context_manager(mock_database):
    """Create a patient context manager"""
    return PatientContextManager(mock_database)


@pytest.fixture
def sample_patient_context():
    """Create a sample patient context"""
    return PatientContext(
        id="patient_001",
        demographics={
            'age': 65,
            'gender': 'male',
            'weight': 80,
            'height': 175
        },
        conditions=['hypertension', 'diabetes'],
        medications=[
            {'name': 'Lisinopril', 'dosage': '10mg', 'frequency': 'daily'},
            {'name': 'Metformin', 'dosage': '500mg', 'frequency': 'twice daily'}
        ],
        allergies=['penicillin'],
        genetic_factors={'CYP2D6': 'poor_metabolizer'},
        risk_factors=['smoking', 'obesity'],
        preferences={'language': 'en'}
    )


class TestPatientContextManager:
    """Test patient context manager functionality"""
    
    @pytest.mark.asyncio
    async def test_create_patient_context(self, context_manager, mock_database):
        """Test creating a new patient context"""
        demographics = {'age': 45, 'gender': 'female', 'weight': 65}
        conditions = ['asthma']
        medications = [{'name': 'Albuterol', 'dosage': '90mcg'}]
        
        context = await context_manager.create_patient_context(
            patient_id="patient_002",
            demographics=demographics,
            conditions=conditions,
            medications=medications
        )
        
        assert context.id == "patient_002"
        assert context.demographics == demographics
        assert context.conditions == conditions
        assert context.medications == medications
        assert mock_database.create_patient_vertex.called
    
    @pytest.mark.asyncio
    async def test_get_patient_context_from_cache(self, context_manager):
        """Test retrieving patient context from cache"""
        # Create a context first
        context = await context_manager.create_patient_context(
            patient_id="patient_003",
            demographics={'age': 30}
        )
        
        # Retrieve from cache
        retrieved = await context_manager.get_patient_context("patient_003")
        
        assert retrieved is not None
        assert retrieved.id == "patient_003"
        assert retrieved.demographics['age'] == 30
    
    @pytest.mark.asyncio
    async def test_update_patient_context(self, context_manager, sample_patient_context):
        """Test updating patient context"""
        # Add to cache
        context_manager._context_cache[sample_patient_context.id] = sample_patient_context
        
        # Update medications
        updates = {
            'medications': [
                {'name': 'Lisinopril', 'dosage': '20mg', 'frequency': 'daily'},
                {'name': 'Metformin', 'dosage': '500mg', 'frequency': 'twice daily'},
                {'name': 'Aspirin', 'dosage': '81mg', 'frequency': 'daily'}
            ]
        }
        
        update_result = await context_manager.update_patient_context(
            sample_patient_context.id,
            updates
        )
        
        assert update_result.update_type == 'modify'
        assert update_result.field == 'medications'
        assert update_result.requires_reevaluation is True
        
        # Verify context was updated
        updated_context = await context_manager.get_patient_context(sample_patient_context.id)
        assert len(updated_context.medications) == 3
    
    @pytest.mark.asyncio
    async def test_update_patient_context_not_found(self, context_manager):
        """Test updating non-existent patient context"""
        with pytest.raises(ValueError, match="Patient context not found"):
            await context_manager.update_patient_context(
                "nonexistent_patient",
                {'demographics': {'age': 50}}
            )
    
    def test_apply_context_to_query_age_filter(self, context_manager, sample_patient_context):
        """Test applying age-based context filters to query"""
        base_query = "g.V().hasLabel('Drug').has('name', 'Aspirin').outE('CAUSES').inV().toList()"
        
        modified_query = context_manager.apply_context_to_query(
            base_query,
            sample_patient_context,
            'side_effects'
        )
        
        # Should add age relevance filter
        assert 'age_relevance' in modified_query
        assert 'P.gte' in modified_query
        assert modified_query.endswith('.toList()')
    
    def test_apply_context_to_query_medication_filter(self, context_manager, sample_patient_context):
        """Test applying medication interaction filters"""
        base_query = "g.V().hasLabel('Drug').has('name', 'Aspirin').toList()"
        
        modified_query = context_manager.apply_context_to_query(
            base_query,
            sample_patient_context,
            'interactions'
        )
        
        # Should add interaction filters
        assert 'INTERACTS_WITH' in modified_query or 'interacting_drugs' in modified_query
    
    def test_apply_context_to_query_allergy_filter(self, context_manager, sample_patient_context):
        """Test applying allergy filters"""
        base_query = "g.V().hasLabel('Drug').toList()"
        
        modified_query = context_manager.apply_context_to_query(
            base_query,
            sample_patient_context,
            'alternatives'
        )
        
        # Should exclude allergenic drugs
        assert 'penicillin' in modified_query or 'not' in modified_query.lower()
    
    def test_extract_context_filters_age(self, context_manager, sample_patient_context):
        """Test extracting age-based filters"""
        filters = context_manager._extract_context_filters(
            sample_patient_context,
            'side_effects'
        )
        
        age_filters = [f for f in filters if f.filter_type == 'age']
        assert len(age_filters) > 0
        # Elderly patient (age 65) should have higher threshold
        assert age_filters[0].value == 0.5  # Exact value for elderly
    
    def test_extract_context_filters_conditions(self, context_manager, sample_patient_context):
        """Test extracting condition-based filters"""
        filters = context_manager._extract_context_filters(
            sample_patient_context,
            'contraindications'
        )
        
        condition_filters = [f for f in filters if f.filter_type == 'condition']
        assert len(condition_filters) > 0
        assert 'hypertension' in condition_filters[0].value
        assert 'diabetes' in condition_filters[0].value
    
    def test_extract_context_filters_medications(self, context_manager, sample_patient_context):
        """Test extracting medication interaction filters"""
        filters = context_manager._extract_context_filters(
            sample_patient_context,
            'interactions'
        )
        
        med_filters = [f for f in filters if f.filter_type == 'medication']
        assert len(med_filters) > 0
        assert 'Lisinopril' in med_filters[0].value
        assert 'Metformin' in med_filters[0].value
    
    def test_extract_context_filters_allergies(self, context_manager, sample_patient_context):
        """Test extracting allergy filters"""
        filters = context_manager._extract_context_filters(
            sample_patient_context,
            'alternatives'
        )
        
        allergy_filters = [f for f in filters if f.filter_type == 'allergy']
        assert len(allergy_filters) > 0
        assert 'penicillin' in allergy_filters[0].value
        assert allergy_filters[0].operator == 'not_in'
    
    def test_extract_context_filters_genetic(self, context_manager, sample_patient_context):
        """Test extracting genetic factor filters"""
        filters = context_manager._extract_context_filters(
            sample_patient_context,
            'dosing'
        )
        
        genetic_filters = [f for f in filters if f.filter_type == 'genetic']
        assert len(genetic_filters) > 0
        assert 'CYP2D6' in genetic_filters[0].property_name
    
    def test_extract_context_filters_risk_factors(self, context_manager, sample_patient_context):
        """Test extracting risk factor filters"""
        filters = context_manager._extract_context_filters(
            sample_patient_context,
            'side_effects'
        )
        
        risk_filters = [f for f in filters if f.filter_type == 'risk']
        assert len(risk_filters) > 0
        assert risk_filters[0].value >= 0.7  # Higher confidence threshold
    
    def test_is_significant_change_medications(self, context_manager):
        """Test detecting significant medication changes"""
        old_meds = [{'name': 'Aspirin', 'dosage': '81mg'}]
        new_meds = [
            {'name': 'Aspirin', 'dosage': '81mg'},
            {'name': 'Warfarin', 'dosage': '5mg'}
        ]
        
        is_significant = context_manager._is_significant_change(
            'medications',
            old_meds,
            new_meds
        )
        
        assert is_significant is True
    
    def test_is_significant_change_age_threshold(self, context_manager):
        """Test detecting significant age threshold changes"""
        old_demographics = {'age': 64, 'gender': 'male'}
        new_demographics = {'age': 65, 'gender': 'male'}
        
        is_significant = context_manager._is_significant_change(
            'demographics',
            old_demographics,
            new_demographics
        )
        
        assert is_significant is True  # Crossing 65 threshold
    
    def test_is_significant_change_minor_age(self, context_manager):
        """Test that minor age changes are not significant"""
        old_demographics = {'age': 45, 'gender': 'female'}
        new_demographics = {'age': 46, 'gender': 'female'}
        
        is_significant = context_manager._is_significant_change(
            'demographics',
            old_demographics,
            new_demographics
        )
        
        assert is_significant is False
    
    def test_is_significant_change_conditions(self, context_manager):
        """Test detecting significant condition changes"""
        old_conditions = ['hypertension']
        new_conditions = ['hypertension', 'diabetes']
        
        is_significant = context_manager._is_significant_change(
            'conditions',
            old_conditions,
            new_conditions
        )
        
        assert is_significant is True
    
    def test_register_active_query(self, context_manager):
        """Test registering an active query"""
        context_manager.register_active_query("patient_001", "query_123")
        
        assert "patient_001" in context_manager._active_queries
        assert "query_123" in context_manager._active_queries["patient_001"]
    
    def test_unregister_active_query(self, context_manager):
        """Test unregistering an active query"""
        context_manager.register_active_query("patient_001", "query_123")
        context_manager.unregister_active_query("patient_001", "query_123")
        
        assert "query_123" not in context_manager._active_queries.get("patient_001", [])
    
    @pytest.mark.asyncio
    async def test_trigger_reevaluation(self, context_manager, sample_patient_context):
        """Test triggering query re-evaluation"""
        # Register some active queries
        context_manager.register_active_query(sample_patient_context.id, "query_1")
        context_manager.register_active_query(sample_patient_context.id, "query_2")
        
        # Trigger re-evaluation (should not raise exception)
        await context_manager._trigger_reevaluation(
            sample_patient_context.id,
            sample_patient_context
        )
        
        # Verify it was called (no exception means success)
        assert True
    
    @pytest.mark.asyncio
    async def test_calculate_personalized_risk_factors_elderly(
        self,
        context_manager,
        sample_patient_context
    ):
        """Test calculating risk factors for elderly patient"""
        risk_factors = await context_manager.calculate_personalized_risk_factors(
            sample_patient_context,
            "drug_001"
        )
        
        assert 'age_risk' in risk_factors
        assert 'comorbidity_risk' in risk_factors
        assert 'polypharmacy_risk' in risk_factors
        assert 'overall_risk' in risk_factors
        
        # Elderly patient should have age risk
        assert risk_factors['age_risk'] > 0
        
        # Patient has 2 conditions
        assert risk_factors['comorbidity_risk'] > 0
        
        # Overall risk should be sum of components (capped at 1.0)
        assert 0 <= risk_factors['overall_risk'] <= 1.0
    
    @pytest.mark.asyncio
    async def test_calculate_personalized_risk_factors_polypharmacy(
        self,
        context_manager
    ):
        """Test calculating risk factors for polypharmacy"""
        context = PatientContext(
            id="patient_poly",
            demographics={'age': 50},
            conditions=[],
            medications=[
                {'name': f'Drug{i}', 'dosage': '10mg'}
                for i in range(8)  # 8 medications
            ],
            allergies=[],
            genetic_factors={},
            risk_factors=[],
            preferences={}
        )
        
        risk_factors = await context_manager.calculate_personalized_risk_factors(
            context,
            "drug_001"
        )
        
        # Should have polypharmacy risk (>5 medications)
        assert risk_factors['polypharmacy_risk'] > 0
    
    @pytest.mark.asyncio
    async def test_calculate_personalized_risk_factors_genetic(
        self,
        context_manager
    ):
        """Test calculating risk factors with genetic information"""
        context = PatientContext(
            id="patient_genetic",
            demographics={'age': 40},
            conditions=[],
            medications=[],
            allergies=[],
            genetic_factors={'CYP2C19': 'poor_metabolizer'},
            risk_factors=[],
            preferences={}
        )
        
        risk_factors = await context_manager.calculate_personalized_risk_factors(
            context,
            "drug_001"
        )
        
        # Should have genetic risk
        assert risk_factors['genetic_risk'] > 0
    
    @pytest.mark.asyncio
    async def test_calculate_personalized_risk_factors_low_risk(
        self,
        context_manager
    ):
        """Test calculating risk factors for low-risk patient"""
        context = PatientContext(
            id="patient_low_risk",
            demographics={'age': 30},
            conditions=[],
            medications=[{'name': 'Vitamin D', 'dosage': '1000IU'}],
            allergies=[],
            genetic_factors={},
            risk_factors=[],
            preferences={}
        )
        
        risk_factors = await context_manager.calculate_personalized_risk_factors(
            context,
            "drug_001"
        )
        
        # Should have low overall risk
        assert risk_factors['overall_risk'] < 0.3
    
    def test_apply_filters_to_query_gte_operator(self, context_manager):
        """Test applying >= operator filter"""
        base_query = "g.V().hasLabel('Drug').toList()"
        filters = [
            ContextFilter(
                filter_type='confidence',
                property_name='confidence',
                operator='gte',
                value=0.7,
                confidence=1.0
            )
        ]
        
        modified_query = context_manager._apply_filters_to_query(base_query, filters)
        
        assert "P.gte(0.7)" in modified_query
        assert "confidence" in modified_query
    
    def test_apply_filters_to_query_lte_operator(self, context_manager):
        """Test applying <= operator filter"""
        base_query = "g.V().hasLabel('Drug').toList()"
        filters = [
            ContextFilter(
                filter_type='age',
                property_name='max_age',
                operator='lte',
                value=65,
                confidence=1.0
            )
        ]
        
        modified_query = context_manager._apply_filters_to_query(base_query, filters)
        
        assert "P.lte(65)" in modified_query
        assert "max_age" in modified_query
    
    def test_apply_filters_to_query_eq_operator(self, context_manager):
        """Test applying = operator filter"""
        base_query = "g.V().hasLabel('Drug').toList()"
        filters = [
            ContextFilter(
                filter_type='genetic',
                property_name='cyp2d6_variant',
                operator='eq',
                value='poor_metabolizer',
                confidence=0.8
            )
        ]
        
        modified_query = context_manager._apply_filters_to_query(base_query, filters)
        
        assert "cyp2d6_variant" in modified_query
        assert "poor_metabolizer" in modified_query
    
    def test_apply_filters_to_query_multiple_filters(self, context_manager):
        """Test applying multiple filters"""
        base_query = "g.V().hasLabel('Drug').toList()"
        filters = [
            ContextFilter('age', 'age_relevance', 'gte', 0.5, 1.0),
            ContextFilter('confidence', 'confidence', 'gte', 0.7, 1.0)
        ]
        
        modified_query = context_manager._apply_filters_to_query(base_query, filters)
        
        assert "age_relevance" in modified_query
        assert "confidence" in modified_query
        assert modified_query.count("P.gte") == 2
    
    def test_apply_filters_to_query_no_terminal_step(self, context_manager):
        """Test applying filters to query without terminal step"""
        base_query = "g.V().hasLabel('Drug')"
        filters = [
            ContextFilter('confidence', 'confidence', 'gte', 0.5, 1.0)
        ]
        
        modified_query = context_manager._apply_filters_to_query(base_query, filters)
        
        assert "confidence" in modified_query
        assert "P.gte(0.5)" in modified_query


class TestContextFilter:
    """Test ContextFilter dataclass"""
    
    def test_context_filter_creation(self):
        """Test creating a context filter"""
        filter_obj = ContextFilter(
            filter_type='age',
            property_name='age_relevance',
            operator='gte',
            value=0.5,
            confidence=1.0
        )
        
        assert filter_obj.filter_type == 'age'
        assert filter_obj.property_name == 'age_relevance'
        assert filter_obj.operator == 'gte'
        assert filter_obj.value == 0.5
        assert filter_obj.confidence == 1.0


class TestContextUpdate:
    """Test ContextUpdate dataclass"""
    
    def test_context_update_creation(self):
        """Test creating a context update"""
        update = ContextUpdate(
            update_type='modify',
            field='medications',
            old_value=[],
            new_value=[{'name': 'Aspirin'}],
            timestamp=datetime.utcnow(),
            requires_reevaluation=True
        )
        
        assert update.update_type == 'modify'
        assert update.field == 'medications'
        assert update.requires_reevaluation is True


class TestFactoryFunction:
    """Test factory function"""
    
    @pytest.mark.asyncio
    async def test_create_patient_context_manager(self, mock_database):
        """Test creating patient context manager via factory"""
        manager = await create_patient_context_manager(mock_database)
        
        assert isinstance(manager, PatientContextManager)
        assert manager.database == mock_database
