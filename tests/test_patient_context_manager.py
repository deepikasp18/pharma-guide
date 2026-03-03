"""
Tests for patient context management
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.knowledge_graph.patient_context_manager import (
    PatientContextManager,
    ContextLayer,
    ContextUpdate
)
from src.knowledge_graph.models import PatientContext
from src.knowledge_graph.database import KnowledgeGraphDatabase


@pytest.fixture
def mock_database():
    """Mock database for testing"""
    db = MagicMock(spec=KnowledgeGraphDatabase)
    db.connection = MagicMock()
    db.connection.g = MagicMock()
    
    # Mock create_patient_vertex
    db.create_patient_vertex = AsyncMock(return_value="patient-123")
    
    return db


@pytest.fixture
def patient_manager(mock_database):
    """Patient context manager instance"""
    return PatientContextManager(mock_database)


@pytest.fixture
def sample_demographics():
    """Sample patient demographics"""
    return {
        'age': 45,
        'gender': 'female',
        'weight': 70,
        'height': 165
    }


@pytest.fixture
def sample_medications():
    """Sample medications"""
    return [
        {'name': 'Lisinopril', 'dosage': '10mg', 'frequency': 'daily'},
        {'name': 'Metformin', 'dosage': '500mg', 'frequency': 'twice daily'}
    ]


class TestPatientContextManager:
    """Test patient context manager"""
    
    @pytest.mark.anyio
    async def test_create_patient_context(
        self, patient_manager, sample_demographics, sample_medications
    ):
        """Test creating a new patient context"""
        context = await patient_manager.create_patient_context(
            demographics=sample_demographics,
            conditions=['diabetes', 'hypertension'],
            medications=sample_medications,
            allergies=['penicillin'],
            risk_factors=['smoking']
        )
        
        assert context is not None
        assert context.id is not None
        assert context.demographics == sample_demographics
        assert 'diabetes' in context.conditions
        assert 'hypertension' in context.conditions
        assert len(context.medications) == 2
        assert 'penicillin' in context.allergies
        assert 'smoking' in context.risk_factors
        
        # Check that context is cached
        assert context.id in patient_manager._context_cache
        
        # Check that context layer was created
        assert context.id in patient_manager._context_layers
    
    @pytest.mark.anyio
    async def test_create_patient_context_minimal(self, patient_manager):
        """Test creating patient context with minimal data"""
        context = await patient_manager.create_patient_context(
            demographics={'age': 30}
        )
        
        assert context is not None
        assert context.demographics['age'] == 30
        assert context.conditions == []
        assert context.medications == []
        assert context.allergies == []
    
    @pytest.mark.anyio
    async def test_get_patient_context_from_cache(
        self, patient_manager, sample_demographics
    ):
        """Test retrieving patient context from cache"""
        # Create context
        context = await patient_manager.create_patient_context(
            demographics=sample_demographics
        )
        
        # Retrieve from cache
        retrieved = await patient_manager.get_patient_context(context.id)
        
        assert retrieved is not None
        assert retrieved.id == context.id
        assert retrieved.demographics == sample_demographics
    
    @pytest.mark.anyio
    async def test_get_patient_context_from_database(
        self, patient_manager, mock_database
    ):
        """Test retrieving patient context from database"""
        # Mock database response
        import json
        mock_data = {
            'id': 'patient-456',
            'demographics': json.dumps({'age': 50, 'gender': 'male'}),
            'conditions': json.dumps(['diabetes']),
            'medications': json.dumps([]),
            'allergies': json.dumps([]),
            'genetic_factors': json.dumps({}),
            'risk_factors': json.dumps([]),
            'preferences': json.dumps({})
        }
        
        mock_database.connection.g.V().has().hasLabel().valueMap().toList.return_value = [mock_data]
        
        # Retrieve context
        context = await patient_manager.get_patient_context('patient-456')
        
        assert context is not None
        assert context.id == 'patient-456'
        assert context.demographics['age'] == 50
        assert 'diabetes' in context.conditions
    
    @pytest.mark.anyio
    async def test_get_nonexistent_patient_context(self, patient_manager, mock_database):
        """Test retrieving non-existent patient context"""
        mock_database.connection.g.V().has().hasLabel().valueMap().toList.return_value = []
        
        context = await patient_manager.get_patient_context('nonexistent')
        
        assert context is None
    
    @pytest.mark.anyio
    async def test_update_patient_context(
        self, patient_manager, sample_demographics
    ):
        """Test updating patient context"""
        # Create context
        context = await patient_manager.create_patient_context(
            demographics=sample_demographics,
            conditions=['diabetes']
        )
        
        # Update context
        updated = await patient_manager.update_patient_context(
            context.id,
            {'conditions': ['diabetes', 'hypertension']}
        )
        
        assert updated is not None
        assert 'hypertension' in updated.conditions
        assert len(updated.conditions) == 2
        
        # Check update history
        history = patient_manager.get_update_history(context.id)
        assert len(history) > 0
        assert history[0].field == 'conditions'
    
    @pytest.mark.anyio
    async def test_update_triggers_reevaluation(
        self, patient_manager, sample_demographics
    ):
        """Test that critical updates trigger re-evaluation"""
        # Create context
        context = await patient_manager.create_patient_context(
            demographics=sample_demographics,
            medications=[]
        )
        
        original_layer = patient_manager.get_context_layer(context.id)
        
        # Update medications (critical field)
        await patient_manager.update_patient_context(
            context.id,
            {'medications': [{'name': 'Aspirin', 'dosage': '81mg'}]}
        )
        
        # Check that context layer was updated
        updated_layer = patient_manager.get_context_layer(context.id)
        assert updated_layer is not None
        assert updated_layer.updated_at > original_layer.updated_at
    
    @pytest.mark.anyio
    async def test_add_medication(self, patient_manager, sample_demographics):
        """Test adding medication to patient context"""
        # Create context
        context = await patient_manager.create_patient_context(
            demographics=sample_demographics,
            medications=[]
        )
        
        # Add medication
        success = await patient_manager.add_medication(
            context.id,
            {'name': 'Lisinopril', 'dosage': '10mg', 'frequency': 'daily'}
        )
        
        assert success is True
        
        # Verify medication was added
        updated_context = await patient_manager.get_patient_context(context.id)
        assert len(updated_context.medications) == 1
        assert updated_context.medications[0]['name'] == 'Lisinopril'
    
    @pytest.mark.anyio
    async def test_remove_medication(
        self, patient_manager, sample_demographics, sample_medications
    ):
        """Test removing medication from patient context"""
        # Create context with medications
        context = await patient_manager.create_patient_context(
            demographics=sample_demographics,
            medications=sample_medications
        )
        
        # Remove medication
        success = await patient_manager.remove_medication(
            context.id,
            'Lisinopril'
        )
        
        assert success is True
        
        # Verify medication was removed
        updated_context = await patient_manager.get_patient_context(context.id)
        assert len(updated_context.medications) == 1
        assert updated_context.medications[0]['name'] == 'Metformin'
    
    @pytest.mark.anyio
    async def test_add_condition(self, patient_manager, sample_demographics):
        """Test adding medical condition"""
        # Create context
        context = await patient_manager.create_patient_context(
            demographics=sample_demographics,
            conditions=[]
        )
        
        # Add condition
        success = await patient_manager.add_condition(context.id, 'diabetes')
        
        assert success is True
        
        # Verify condition was added
        updated_context = await patient_manager.get_patient_context(context.id)
        assert 'diabetes' in updated_context.conditions
    
    @pytest.mark.anyio
    async def test_add_duplicate_condition(
        self, patient_manager, sample_demographics
    ):
        """Test adding duplicate condition (should not duplicate)"""
        # Create context with condition
        context = await patient_manager.create_patient_context(
            demographics=sample_demographics,
            conditions=['diabetes']
        )
        
        # Try to add same condition
        success = await patient_manager.add_condition(context.id, 'diabetes')
        
        assert success is True
        
        # Verify no duplicate
        updated_context = await patient_manager.get_patient_context(context.id)
        assert updated_context.conditions.count('diabetes') == 1
    
    @pytest.mark.anyio
    async def test_remove_condition(self, patient_manager, sample_demographics):
        """Test removing medical condition"""
        # Create context with conditions
        context = await patient_manager.create_patient_context(
            demographics=sample_demographics,
            conditions=['diabetes', 'hypertension']
        )
        
        # Remove condition
        success = await patient_manager.remove_condition(context.id, 'diabetes')
        
        assert success is True
        
        # Verify condition was removed
        updated_context = await patient_manager.get_patient_context(context.id)
        assert 'diabetes' not in updated_context.conditions
        assert 'hypertension' in updated_context.conditions
    
    def test_get_context_layer(self, patient_manager):
        """Test getting context layer"""
        # Create a context layer manually
        layer = ContextLayer(
            patient_id='test-patient',
            filters={'age': 45},
            weights={'age_risk': 1.0}
        )
        patient_manager._context_layers['test-patient'] = layer
        
        # Retrieve layer
        retrieved = patient_manager.get_context_layer('test-patient')
        
        assert retrieved is not None
        assert retrieved.patient_id == 'test-patient'
        assert retrieved.filters['age'] == 45
    
    def test_apply_context_to_query(self, patient_manager):
        """Test applying context layer to query"""
        # Create a context layer
        layer = ContextLayer(
            patient_id='test-patient',
            filters={'age': 45, 'gender': 'female'},
            weights={'age_risk': 1.2}
        )
        patient_manager._context_layers['test-patient'] = layer
        
        # Base query params
        query_params = {
            'drug_id': 'drug-123',
            'max_results': 10
        }
        
        # Apply context
        contextualized = patient_manager.apply_context_to_query(
            query_params,
            'test-patient'
        )
        
        assert contextualized['drug_id'] == 'drug-123'
        assert contextualized['max_results'] == 10
        assert contextualized['filters']['age'] == 45
        assert contextualized['filters']['gender'] == 'female'
        assert contextualized['weights']['age_risk'] == 1.2
        assert contextualized['patient_id'] == 'test-patient'
        assert contextualized['context_applied'] is True
    
    def test_apply_context_no_layer(self, patient_manager):
        """Test applying context when no layer exists"""
        query_params = {'drug_id': 'drug-123'}
        
        # Apply context for non-existent patient
        contextualized = patient_manager.apply_context_to_query(
            query_params,
            'nonexistent'
        )
        
        # Should return original params
        assert contextualized == query_params
    
    def test_create_context_layer_with_age(self, patient_manager):
        """Test context layer creation with age-based weights"""
        # Elderly patient
        context = PatientContext(
            id='patient-1',
            demographics={'age': 70, 'gender': 'male'},
            conditions=[],
            medications=[],
            allergies=[],
            genetic_factors={},
            risk_factors=[],
            preferences={}
        )
        
        layer = patient_manager._create_context_layer(context)
        
        assert layer.filters['age'] == 70
        assert layer.weights['age_risk'] == 1.2  # Elderly adjustment
    
    def test_create_context_layer_with_conditions(self, patient_manager):
        """Test context layer creation with multiple conditions"""
        context = PatientContext(
            id='patient-1',
            demographics={'age': 50},
            conditions=['diabetes', 'hypertension', 'heart_disease'],
            medications=[],
            allergies=[],
            genetic_factors={},
            risk_factors=[],
            preferences={}
        )
        
        layer = patient_manager._create_context_layer(context)
        
        assert 'conditions' in layer.filters
        assert len(layer.filters['conditions']) == 3
        assert 'condition_risk' in layer.weights
        assert layer.weights['condition_risk'] > 1.0
    
    def test_create_context_layer_with_polypharmacy(self, patient_manager):
        """Test context layer creation with polypharmacy"""
        medications = [
            {'name': f'Drug{i}', 'dosage': '10mg'}
            for i in range(6)
        ]
        
        context = PatientContext(
            id='patient-1',
            demographics={'age': 60},
            conditions=[],
            medications=medications,
            allergies=[],
            genetic_factors={},
            risk_factors=[],
            preferences={}
        )
        
        layer = patient_manager._create_context_layer(context)
        
        assert 'current_medications' in layer.filters
        assert len(layer.filters['current_medications']) == 6
        assert 'polypharmacy_risk' in layer.weights
        assert layer.weights['polypharmacy_risk'] == 1.1
    
    def test_create_context_layer_with_allergies(self, patient_manager):
        """Test context layer creation with allergies"""
        context = PatientContext(
            id='patient-1',
            demographics={'age': 40},
            conditions=[],
            medications=[],
            allergies=['penicillin', 'sulfa'],
            genetic_factors={},
            risk_factors=[],
            preferences={}
        )
        
        layer = patient_manager._create_context_layer(context)
        
        assert 'allergies' in layer.filters
        assert 'penicillin' in layer.filters['allergies']
        assert 'allergy_risk' in layer.weights
        assert layer.weights['allergy_risk'] == 1.2
    
    def test_requires_reevaluation(self, patient_manager):
        """Test determining if field requires re-evaluation"""
        # Critical fields
        assert patient_manager._requires_reevaluation('medications') is True
        assert patient_manager._requires_reevaluation('conditions') is True
        assert patient_manager._requires_reevaluation('allergies') is True
        assert patient_manager._requires_reevaluation('demographics') is True
        assert patient_manager._requires_reevaluation('risk_factors') is True
        
        # Non-critical fields
        assert patient_manager._requires_reevaluation('preferences') is False
        assert patient_manager._requires_reevaluation('unknown_field') is False
    
    def test_get_update_history(self, patient_manager):
        """Test getting update history"""
        # Add some updates
        update1 = ContextUpdate(
            update_id='update-1',
            patient_id='patient-1',
            field='medications',
            old_value=[],
            new_value=[{'name': 'Aspirin'}]
        )
        update2 = ContextUpdate(
            update_id='update-2',
            patient_id='patient-1',
            field='conditions',
            old_value=[],
            new_value=['diabetes']
        )
        update3 = ContextUpdate(
            update_id='update-3',
            patient_id='patient-2',
            field='medications',
            old_value=[],
            new_value=[{'name': 'Metformin'}]
        )
        
        patient_manager._update_history = [update1, update2, update3]
        
        # Get all updates
        all_updates = patient_manager.get_update_history()
        assert len(all_updates) == 3
        
        # Get updates for specific patient
        patient1_updates = patient_manager.get_update_history('patient-1')
        assert len(patient1_updates) == 2
        assert all(u.patient_id == 'patient-1' for u in patient1_updates)
        
        # Get with limit
        limited_updates = patient_manager.get_update_history(limit=1)
        assert len(limited_updates) == 1
    
    def test_parse_patient_from_graph(self, patient_manager):
        """Test parsing patient context from graph data"""
        import json
        
        graph_data = {
            'id': 'patient-789',
            'demographics': json.dumps({'age': 55, 'gender': 'female'}),
            'conditions': json.dumps(['diabetes', 'hypertension']),
            'medications': json.dumps([{'name': 'Metformin', 'dosage': '500mg'}]),
            'allergies': json.dumps(['penicillin']),
            'genetic_factors': json.dumps({'cyp2d6': 'poor_metabolizer'}),
            'risk_factors': json.dumps(['smoking', 'obesity']),
            'preferences': json.dumps({'language': 'en'})
        }
        
        context = patient_manager._parse_patient_from_graph(graph_data)
        
        assert context.id == 'patient-789'
        assert context.demographics['age'] == 55
        assert 'diabetes' in context.conditions
        assert len(context.medications) == 1
        assert 'penicillin' in context.allergies
        assert context.genetic_factors['cyp2d6'] == 'poor_metabolizer'
        assert 'smoking' in context.risk_factors
        assert context.preferences['language'] == 'en'


class TestContextLayer:
    """Test ContextLayer dataclass"""
    
    def test_create_context_layer(self):
        """Test creating a context layer"""
        layer = ContextLayer(
            patient_id='patient-1',
            filters={'age': 45},
            weights={'age_risk': 1.0}
        )
        
        assert layer.patient_id == 'patient-1'
        assert layer.filters['age'] == 45
        assert layer.weights['age_risk'] == 1.0
        assert layer.active is True
        assert isinstance(layer.created_at, datetime)


class TestContextUpdate:
    """Test ContextUpdate dataclass"""
    
    def test_create_context_update(self):
        """Test creating a context update"""
        update = ContextUpdate(
            update_id='update-1',
            patient_id='patient-1',
            field='medications',
            old_value=[],
            new_value=[{'name': 'Aspirin'}]
        )
        
        assert update.update_id == 'update-1'
        assert update.patient_id == 'patient-1'
        assert update.field == 'medications'
        assert update.old_value == []
        assert len(update.new_value) == 1
        assert update.requires_reevaluation is True
        assert isinstance(update.timestamp, datetime)
