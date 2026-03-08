"""
Tests for alternative medication recommendation engine
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.knowledge_graph.recommendation_engine import (
    AlternativeMedicationEngine,
    InteractionManagementService,
    RecommendationStrategy,
    AlternativeMedication,
    ManagementStrategy,
    RecommendationResult
)
from src.knowledge_graph.database import KnowledgeGraphDatabase


@pytest.fixture
def mock_database():
    """Create mock database"""
    db = Mock(spec=KnowledgeGraphDatabase)
    db.find_drug_by_name = AsyncMock()
    return db


@pytest.fixture
def recommendation_engine(mock_database):
    """Create recommendation engine with mock database"""
    return AlternativeMedicationEngine(mock_database)


@pytest.fixture
def interaction_service(mock_database):
    """Create interaction management service"""
    return InteractionManagementService(mock_database)


@pytest.fixture
def sample_drug_info():
    """Sample drug information"""
    return {
        'id': 'drug_lisinopril',
        'name': 'Lisinopril',
        'generic_name': 'lisinopril',
        'drugbank_id': 'DB00722',
        'atc_codes': ['C09AA03'],
        'mechanism': 'ACE inhibitor',
        'indications': ['hypertension', 'heart failure'],
        'contraindications': ['pregnancy', 'angioedema']
    }


@pytest.fixture
def sample_interaction_context():
    """Sample interaction context"""
    return {
        'severity': 'moderate',
        'mechanism': 'Potassium-sparing effect',
        'clinical_effect': 'Hyperkalemia risk',
        'interacting_drug_id': 'drug_spironolactone'
    }


class TestAlternativeMedicationEngine:
    """Tests for AlternativeMedicationEngine"""
    
    @pytest.mark.asyncio
    async def test_find_alternatives_success(
        self, recommendation_engine, mock_database, sample_drug_info
    ):
        """Test successful alternative medication finding"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        
        # Execute
        result = await recommendation_engine.find_alternatives('drug_lisinopril')
        
        # Verify
        assert isinstance(result, RecommendationResult)
        assert result.original_drug_id == 'drug_lisinopril'
        assert result.original_drug_name == 'Lisinopril'
        assert isinstance(result.alternatives, list)
        assert isinstance(result.management_strategies, list)
        assert 0.0 <= result.overall_confidence <= 1.0
        assert isinstance(result.requires_provider_consultation, bool)
    
    @pytest.mark.asyncio
    async def test_find_alternatives_with_patient_context(
        self, recommendation_engine, mock_database, sample_drug_info
    ):
        """Test alternative finding with patient context"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        patient_context = {
            'age': 65,
            'conditions': ['diabetes', 'hypertension'],
            'medications': ['metformin']
        }
        
        # Execute
        result = await recommendation_engine.find_alternatives(
            'drug_lisinopril',
            patient_context=patient_context
        )
        
        # Verify
        assert result is not None
        assert result.original_drug_id == 'drug_lisinopril'
    
    @pytest.mark.asyncio
    async def test_find_alternatives_with_interaction_context(
        self, recommendation_engine, mock_database, sample_drug_info, sample_interaction_context
    ):
        """Test alternative finding with interaction context"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        
        # Execute
        result = await recommendation_engine.find_alternatives(
            'drug_lisinopril',
            interaction_context=sample_interaction_context
        )
        
        # Verify
        assert result is not None
        assert result.interaction_context == sample_interaction_context
        assert len(result.management_strategies) > 0
    
    @pytest.mark.asyncio
    async def test_find_alternatives_drug_not_found(
        self, recommendation_engine, mock_database
    ):
        """Test alternative finding when drug is not found"""
        # Setup
        mock_database.find_drug_by_name.return_value = None
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Drug not found"):
            await recommendation_engine.find_alternatives('nonexistent_drug')
    
    @pytest.mark.asyncio
    async def test_generate_management_strategies_minor_interaction(
        self, recommendation_engine, sample_drug_info
    ):
        """Test management strategy generation for minor interaction"""
        # Setup
        interaction_context = {
            'severity': 'minor',
            'mechanism': 'Absorption interference'
        }
        
        # Execute
        strategies = await recommendation_engine._generate_management_strategies(
            sample_drug_info, interaction_context
        )
        
        # Verify
        assert len(strategies) > 0
        assert any(s.strategy_type == 'dosage_adjustment' for s in strategies)
    
    @pytest.mark.asyncio
    async def test_generate_management_strategies_moderate_interaction(
        self, recommendation_engine, sample_drug_info
    ):
        """Test management strategy generation for moderate interaction"""
        # Setup
        interaction_context = {
            'severity': 'moderate',
            'mechanism': 'CYP450 enzyme inhibition'
        }
        
        # Execute
        strategies = await recommendation_engine._generate_management_strategies(
            sample_drug_info, interaction_context
        )
        
        # Verify
        assert len(strategies) > 0
        assert any(s.strategy_type == 'enhanced_monitoring' for s in strategies)
        for strategy in strategies:
            assert isinstance(strategy, ManagementStrategy)
            assert strategy.confidence > 0
            assert len(strategy.implementation_steps) > 0
            assert len(strategy.monitoring_requirements) > 0
    
    @pytest.mark.asyncio
    async def test_generate_management_strategies_absorption_mechanism(
        self, recommendation_engine, sample_drug_info
    ):
        """Test timing adjustment strategy for absorption-related interactions"""
        # Setup
        interaction_context = {
            'severity': 'moderate',
            'mechanism': 'Reduced absorption due to chelation'
        }
        
        # Execute
        strategies = await recommendation_engine._generate_management_strategies(
            sample_drug_info, interaction_context
        )
        
        # Verify
        assert any(s.strategy_type == 'timing_adjustment' for s in strategies)
        timing_strategy = next(s for s in strategies if s.strategy_type == 'timing_adjustment')
        assert 'separate' in timing_strategy.description.lower()
    
    def test_calculate_overall_confidence_with_alternatives_and_strategies(
        self, recommendation_engine
    ):
        """Test confidence calculation with both alternatives and strategies"""
        # Setup
        alternatives = [
            AlternativeMedication(
                drug_id='alt1', drug_name='Alt1', generic_name='alt1',
                reason='test', strategy=RecommendationStrategy.THERAPEUTIC_EQUIVALENT,
                confidence=0.8, evidence_sources=[], considerations=[],
                contraindications=[]
            ),
            AlternativeMedication(
                drug_id='alt2', drug_name='Alt2', generic_name='alt2',
                reason='test', strategy=RecommendationStrategy.SAME_CLASS_ALTERNATIVE,
                confidence=0.6, evidence_sources=[], considerations=[],
                contraindications=[]
            )
        ]
        
        strategies = [
            ManagementStrategy(
                strategy_type='dosage_adjustment', description='test',
                implementation_steps=[], monitoring_requirements=[],
                confidence=0.7, evidence_level='moderate'
            )
        ]
        
        # Execute
        confidence = recommendation_engine._calculate_overall_confidence(
            alternatives, strategies
        )
        
        # Verify
        assert 0.0 <= confidence <= 1.0
        # Should be weighted average: (0.7 * 0.7) + (0.7 * 0.3) = 0.7
        assert abs(confidence - 0.7) < 0.01
    
    def test_calculate_overall_confidence_alternatives_only(
        self, recommendation_engine
    ):
        """Test confidence calculation with only alternatives"""
        # Setup
        alternatives = [
            AlternativeMedication(
                drug_id='alt1', drug_name='Alt1', generic_name='alt1',
                reason='test', strategy=RecommendationStrategy.THERAPEUTIC_EQUIVALENT,
                confidence=0.9, evidence_sources=[], considerations=[],
                contraindications=[]
            )
        ]
        
        # Execute
        confidence = recommendation_engine._calculate_overall_confidence(alternatives, [])
        
        # Verify
        assert confidence == 0.9
    
    def test_calculate_overall_confidence_strategies_only(
        self, recommendation_engine
    ):
        """Test confidence calculation with only strategies"""
        # Setup
        strategies = [
            ManagementStrategy(
                strategy_type='timing_adjustment', description='test',
                implementation_steps=[], monitoring_requirements=[],
                confidence=0.8, evidence_level='high'
            )
        ]
        
        # Execute
        confidence = recommendation_engine._calculate_overall_confidence([], strategies)
        
        # Verify
        assert confidence == 0.8
    
    def test_calculate_overall_confidence_empty(self, recommendation_engine):
        """Test confidence calculation with no alternatives or strategies"""
        # Execute
        confidence = recommendation_engine._calculate_overall_confidence([], [])
        
        # Verify
        assert confidence == 0.0
    
    def test_requires_provider_consultation_major_interaction(
        self, recommendation_engine, sample_drug_info
    ):
        """Test provider consultation requirement for major interaction"""
        # Setup
        interaction_context = {'severity': 'major'}
        alternatives = []
        
        # Execute
        requires = recommendation_engine._requires_provider_consultation(
            sample_drug_info, interaction_context, alternatives
        )
        
        # Verify
        assert requires is True
    
    def test_requires_provider_consultation_contraindicated(
        self, recommendation_engine, sample_drug_info
    ):
        """Test provider consultation requirement for contraindicated interaction"""
        # Setup
        interaction_context = {'severity': 'contraindicated'}
        alternatives = []
        
        # Execute
        requires = recommendation_engine._requires_provider_consultation(
            sample_drug_info, interaction_context, alternatives
        )
        
        # Verify
        assert requires is True
    
    def test_requires_provider_consultation_no_alternatives(
        self, recommendation_engine, sample_drug_info
    ):
        """Test provider consultation requirement when no alternatives found"""
        # Setup
        interaction_context = {'severity': 'moderate'}
        alternatives = []
        
        # Execute
        requires = recommendation_engine._requires_provider_consultation(
            sample_drug_info, interaction_context, alternatives
        )
        
        # Verify
        assert requires is True
    
    def test_requires_provider_consultation_with_alternatives(
        self, recommendation_engine, sample_drug_info
    ):
        """Test provider consultation not required with alternatives"""
        # Setup
        interaction_context = {'severity': 'minor'}
        alternatives = [
            AlternativeMedication(
                drug_id='alt1', drug_name='Alt1', generic_name='alt1',
                reason='test', strategy=RecommendationStrategy.THERAPEUTIC_EQUIVALENT,
                confidence=0.9, evidence_sources=[], considerations=[],
                contraindications=[]
            )
        ]
        
        # Execute
        requires = recommendation_engine._requires_provider_consultation(
            sample_drug_info, interaction_context, alternatives
        )
        
        # Verify
        assert requires is False


class TestInteractionManagementService:
    """Tests for InteractionManagementService"""
    
    @pytest.mark.asyncio
    async def test_get_interaction_recommendations_success(
        self, interaction_service, mock_database, sample_drug_info
    ):
        """Test successful interaction recommendation retrieval"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        
        # Execute
        result = await interaction_service.get_interaction_recommendations(
            'drug_lisinopril', 'drug_spironolactone'
        )
        
        # Verify
        assert 'drug_a_recommendations' in result
        assert 'drug_b_recommendations' in result
        assert 'interaction_severity' in result
        assert 'interaction_mechanism' in result
        assert isinstance(result['drug_a_recommendations'], RecommendationResult)
        assert isinstance(result['drug_b_recommendations'], RecommendationResult)
    
    @pytest.mark.asyncio
    async def test_get_interaction_recommendations_with_patient_context(
        self, interaction_service, mock_database, sample_drug_info
    ):
        """Test interaction recommendations with patient context"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        patient_context = {
            'age': 70,
            'conditions': ['hypertension', 'heart failure']
        }
        
        # Execute
        result = await interaction_service.get_interaction_recommendations(
            'drug_lisinopril', 'drug_spironolactone',
            patient_context=patient_context
        )
        
        # Verify
        assert result is not None
        assert 'drug_a_recommendations' in result
    
    @pytest.mark.asyncio
    async def test_get_interaction_info(self, interaction_service):
        """Test interaction information retrieval"""
        # Execute
        interaction = await interaction_service._get_interaction_info(
            'drug_a', 'drug_b'
        )
        
        # Verify
        assert interaction is not None
        assert 'severity' in interaction
        assert 'mechanism' in interaction
        assert 'clinical_effect' in interaction


class TestIntegration:
    """Integration tests for recommendation engine"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_recommendation_flow(
        self, recommendation_engine, mock_database, sample_drug_info, sample_interaction_context
    ):
        """Test complete recommendation flow from drug to alternatives"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        
        # Execute
        result = await recommendation_engine.find_alternatives(
            'drug_lisinopril',
            patient_context={'age': 65, 'conditions': ['hypertension']},
            interaction_context=sample_interaction_context
        )
        
        # Verify complete result structure
        assert result.original_drug_id == 'drug_lisinopril'
        assert result.original_drug_name == 'Lisinopril'
        assert result.interaction_context == sample_interaction_context
        assert isinstance(result.alternatives, list)
        assert isinstance(result.management_strategies, list)
        assert len(result.management_strategies) > 0
        assert 0.0 <= result.overall_confidence <= 1.0
        assert isinstance(result.requires_provider_consultation, bool)
        
        # Verify management strategies have required fields
        for strategy in result.management_strategies:
            assert strategy.strategy_type
            assert strategy.description
            assert len(strategy.implementation_steps) > 0
            assert len(strategy.monitoring_requirements) > 0
            assert 0.0 <= strategy.confidence <= 1.0
            assert strategy.evidence_level
