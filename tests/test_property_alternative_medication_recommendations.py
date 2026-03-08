"""
Property-based tests for alternative medication recommendations

**Validates: Requirements 4.5**

Property 11: Alternative Medication Recommendations
For any identified interaction risk, the system should generate management 
recommendations by querying knowledge graph paths to alternative medications
"""
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from unittest.mock import Mock, AsyncMock
from src.knowledge_graph.recommendation_engine import (
    AlternativeMedicationEngine,
    InteractionManagementService,
    RecommendationResult,
    AlternativeMedication,
    ManagementStrategy,
    RecommendationStrategy
)
from src.knowledge_graph.database import KnowledgeGraphDatabase


# Hypothesis strategies
@st.composite
def drug_info_strategy(draw):
    """Generate valid drug information"""
    drug_id = draw(st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    return {
        'id': f'drug_{drug_id}',
        'name': draw(st.text(min_size=3, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))),
        'generic_name': draw(st.text(min_size=3, max_size=30, alphabet=st.characters(whitelist_categories=('Ll',)))),
        'drugbank_id': f'DB{draw(st.integers(min_value=10000, max_value=99999))}',
        'atc_codes': draw(st.lists(
            st.text(min_size=7, max_size=7, alphabet=st.characters(whitelist_categories=('Lu', 'Nd'))),
            min_size=1, max_size=3
        )),
        'mechanism': draw(st.sampled_from([
            'ACE inhibitor', 'Beta blocker', 'Calcium channel blocker',
            'Diuretic', 'Anticoagulant', 'Antiplatelet'
        ])),
        'indications': draw(st.lists(
            st.sampled_from(['hypertension', 'heart failure', 'diabetes', 'pain', 'infection']),
            min_size=1, max_size=3
        )),
        'contraindications': draw(st.lists(
            st.sampled_from(['pregnancy', 'liver disease', 'kidney disease', 'allergy']),
            min_size=0, max_size=2
        ))
    }


@st.composite
def interaction_context_strategy(draw):
    """Generate valid interaction context"""
    severity = draw(st.sampled_from(['minor', 'moderate', 'major', 'contraindicated']))
    mechanisms = [
        'CYP450 enzyme inhibition',
        'CYP450 enzyme induction',
        'Absorption interference',
        'Protein binding displacement',
        'Renal excretion competition',
        'Additive pharmacological effect',
        'Antagonistic effect'
    ]
    
    return {
        'severity': severity,
        'mechanism': draw(st.sampled_from(mechanisms)),
        'clinical_effect': draw(st.text(min_size=10, max_size=100)),
        'interacting_drug_id': f'drug_{draw(st.text(min_size=5, max_size=15))}'
    }


@st.composite
def patient_context_strategy(draw):
    """Generate valid patient context"""
    return {
        'age': draw(st.integers(min_value=18, max_value=100)),
        'gender': draw(st.sampled_from(['male', 'female', 'other'])),
        'weight': draw(st.floats(min_value=40.0, max_value=200.0)),
        'conditions': draw(st.lists(
            st.sampled_from(['hypertension', 'diabetes', 'heart failure', 'asthma', 'arthritis']),
            min_size=0, max_size=5
        )),
        'medications': draw(st.lists(
            st.text(min_size=3, max_size=20),
            min_size=0, max_size=10
        ))
    }


class TestAlternativeMedicationRecommendationsProperty:
    """Property-based tests for alternative medication recommendations"""
    
    @pytest.mark.asyncio
    @given(
        drug_info=drug_info_strategy(),
        interaction_context=interaction_context_strategy()
    )
    @settings(max_examples=100, deadline=None)
    async def test_property_interaction_risk_generates_recommendations(
        self, drug_info, interaction_context
    ):
        """
        Property: For any identified interaction risk, the system should generate 
        management recommendations (for manageable severities)
        
        **Validates: Requirements 4.5**
        """
        # Only test manageable severities (not contraindicated)
        # Contraindicated interactions should not have management strategies
        assume(interaction_context['severity'] != 'contraindicated')
        
        # Setup mock database
        mock_db = Mock(spec=KnowledgeGraphDatabase)
        mock_db.find_drug_by_name = AsyncMock(return_value=drug_info)
        
        engine = AlternativeMedicationEngine(mock_db)
        
        # Execute
        result = await engine.find_alternatives(
            drug_info['id'],
            interaction_context=interaction_context
        )
        
        # Verify: System should generate recommendations for any interaction risk
        assert isinstance(result, RecommendationResult)
        assert result.original_drug_id == drug_info['id']
        
        # Should have management strategies for manageable interactions
        assert len(result.management_strategies) > 0, \
            f"System must generate management strategies for {interaction_context['severity']} interactions"
        
        # Verify interaction context is preserved
        assert result.interaction_context == interaction_context
    
    @pytest.mark.asyncio
    @given(
        drug_info=drug_info_strategy(),
        interaction_context=interaction_context_strategy()
    )
    @settings(max_examples=100, deadline=None)
    async def test_property_management_strategies_have_required_fields(
        self, drug_info, interaction_context
    ):
        """
        Property: All management strategies should have complete information
        including implementation steps and monitoring requirements
        
        **Validates: Requirements 4.5**
        """
        # Setup
        mock_db = Mock(spec=KnowledgeGraphDatabase)
        mock_db.find_drug_by_name = AsyncMock(return_value=drug_info)
        
        engine = AlternativeMedicationEngine(mock_db)
        
        # Execute
        result = await engine.find_alternatives(
            drug_info['id'],
            interaction_context=interaction_context
        )
        
        # Verify: All management strategies must have complete information
        for strategy in result.management_strategies:
            assert isinstance(strategy, ManagementStrategy)
            assert strategy.strategy_type, "Strategy must have a type"
            assert strategy.description, "Strategy must have a description"
            assert len(strategy.implementation_steps) > 0, "Strategy must have implementation steps"
            assert len(strategy.monitoring_requirements) > 0, "Strategy must have monitoring requirements"
            assert 0.0 <= strategy.confidence <= 1.0, "Confidence must be between 0 and 1"
            assert strategy.evidence_level, "Strategy must have evidence level"
    
    @pytest.mark.asyncio
    @given(
        drug_info=drug_info_strategy(),
        interaction_context=interaction_context_strategy()
    )
    @settings(max_examples=100, deadline=None)
    async def test_property_severe_interactions_require_consultation(
        self, drug_info, interaction_context
    ):
        """
        Property: Major or contraindicated interactions should always require 
        provider consultation
        
        **Validates: Requirements 4.5**
        """
        # Setup
        mock_db = Mock(spec=KnowledgeGraphDatabase)
        mock_db.find_drug_by_name = AsyncMock(return_value=drug_info)
        
        engine = AlternativeMedicationEngine(mock_db)
        
        # Execute
        result = await engine.find_alternatives(
            drug_info['id'],
            interaction_context=interaction_context
        )
        
        # Verify: Severe interactions must require provider consultation
        if interaction_context['severity'] in ['major', 'contraindicated']:
            assert result.requires_provider_consultation, \
                f"Severity {interaction_context['severity']} must require provider consultation"
    
    @pytest.mark.asyncio
    @given(
        drug_info=drug_info_strategy(),
        interaction_context=interaction_context_strategy()
    )
    @settings(max_examples=100, deadline=None)
    async def test_property_confidence_scores_are_valid(
        self, drug_info, interaction_context
    ):
        """
        Property: All confidence scores should be between 0 and 1
        
        **Validates: Requirements 4.5**
        """
        # Setup
        mock_db = Mock(spec=KnowledgeGraphDatabase)
        mock_db.find_drug_by_name = AsyncMock(return_value=drug_info)
        
        engine = AlternativeMedicationEngine(mock_db)
        
        # Execute
        result = await engine.find_alternatives(
            drug_info['id'],
            interaction_context=interaction_context
        )
        
        # Verify: All confidence scores must be valid
        assert 0.0 <= result.overall_confidence <= 1.0, \
            "Overall confidence must be between 0 and 1"
        
        for alt in result.alternatives:
            assert 0.0 <= alt.confidence <= 1.0, \
                f"Alternative {alt.drug_name} confidence must be between 0 and 1"
        
        for strategy in result.management_strategies:
            assert 0.0 <= strategy.confidence <= 1.0, \
                f"Strategy {strategy.strategy_type} confidence must be between 0 and 1"
    
    @pytest.mark.asyncio
    @given(
        drug_info=drug_info_strategy(),
        interaction_context=interaction_context_strategy()
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.filter_too_much])
    async def test_property_absorption_interactions_suggest_timing_adjustment(
        self, drug_info, interaction_context
    ):
        """
        Property: Interactions involving absorption should include timing 
        adjustment strategies
        
        **Validates: Requirements 4.5**
        """
        # Only test when mechanism involves absorption
        assume('absorption' in interaction_context['mechanism'].lower() or 
               'bioavailability' in interaction_context['mechanism'].lower())
        
        # Setup
        mock_db = Mock(spec=KnowledgeGraphDatabase)
        mock_db.find_drug_by_name = AsyncMock(return_value=drug_info)
        
        engine = AlternativeMedicationEngine(mock_db)
        
        # Execute
        result = await engine.find_alternatives(
            drug_info['id'],
            interaction_context=interaction_context
        )
        
        # Verify: Should include timing adjustment strategy
        strategy_types = [s.strategy_type for s in result.management_strategies]
        assert 'timing_adjustment' in strategy_types, \
            "Absorption-related interactions should include timing adjustment strategy"
    
    @pytest.mark.asyncio
    @given(
        drug_info=drug_info_strategy(),
        interaction_context=interaction_context_strategy(),
        patient_context=patient_context_strategy()
    )
    @settings(max_examples=100, deadline=None)
    async def test_property_recommendations_with_patient_context(
        self, drug_info, interaction_context, patient_context
    ):
        """
        Property: Recommendations should be generated successfully with patient context
        
        **Validates: Requirements 4.5**
        """
        # Only test manageable severities
        assume(interaction_context['severity'] != 'contraindicated')
        
        # Setup
        mock_db = Mock(spec=KnowledgeGraphDatabase)
        mock_db.find_drug_by_name = AsyncMock(return_value=drug_info)
        
        engine = AlternativeMedicationEngine(mock_db)
        
        # Execute
        result = await engine.find_alternatives(
            drug_info['id'],
            patient_context=patient_context,
            interaction_context=interaction_context
        )
        
        # Verify: Should generate valid recommendations with patient context
        assert isinstance(result, RecommendationResult)
        assert result.original_drug_id == drug_info['id']
        
        # Should have management strategies for manageable interactions
        assert len(result.management_strategies) > 0
    
    @pytest.mark.asyncio
    @given(
        drug_a_info=drug_info_strategy(),
        drug_b_info=drug_info_strategy()
    )
    @settings(max_examples=50, deadline=None)
    async def test_property_interaction_service_generates_bidirectional_recommendations(
        self, drug_a_info, drug_b_info
    ):
        """
        Property: Interaction management service should generate recommendations 
        for both drugs in an interaction
        
        **Validates: Requirements 4.5**
        """
        # Ensure drugs are different
        assume(drug_a_info['id'] != drug_b_info['id'])
        
        # Setup
        mock_db = Mock(spec=KnowledgeGraphDatabase)
        
        async def mock_find_drug(drug_id):
            if drug_id == drug_a_info['id']:
                return drug_a_info
            elif drug_id == drug_b_info['id']:
                return drug_b_info
            return None
        
        mock_db.find_drug_by_name = AsyncMock(side_effect=mock_find_drug)
        
        service = InteractionManagementService(mock_db)
        
        # Execute
        result = await service.get_interaction_recommendations(
            drug_a_info['id'],
            drug_b_info['id']
        )
        
        # Verify: Should have recommendations for both drugs
        assert 'drug_a_recommendations' in result
        assert 'drug_b_recommendations' in result
        assert isinstance(result['drug_a_recommendations'], RecommendationResult)
        assert isinstance(result['drug_b_recommendations'], RecommendationResult)
        
        # Both should have the original drug IDs
        assert result['drug_a_recommendations'].original_drug_id == drug_a_info['id']
        assert result['drug_b_recommendations'].original_drug_id == drug_b_info['id']
    
    @pytest.mark.asyncio
    @given(
        drug_info=drug_info_strategy(),
        interaction_context=interaction_context_strategy()
    )
    @settings(max_examples=100, deadline=None)
    async def test_property_moderate_interactions_include_monitoring(
        self, drug_info, interaction_context
    ):
        """
        Property: Moderate or major interactions should include enhanced 
        monitoring strategies
        
        **Validates: Requirements 4.5**
        """
        # Only test moderate or major interactions
        assume(interaction_context['severity'] in ['moderate', 'major'])
        
        # Setup
        mock_db = Mock(spec=KnowledgeGraphDatabase)
        mock_db.find_drug_by_name = AsyncMock(return_value=drug_info)
        
        engine = AlternativeMedicationEngine(mock_db)
        
        # Execute
        result = await engine.find_alternatives(
            drug_info['id'],
            interaction_context=interaction_context
        )
        
        # Verify: Should include enhanced monitoring
        strategy_types = [s.strategy_type for s in result.management_strategies]
        assert 'enhanced_monitoring' in strategy_types, \
            f"Severity {interaction_context['severity']} should include enhanced monitoring"
    
    @pytest.mark.asyncio
    @given(
        drug_info=drug_info_strategy(),
        interaction_context=interaction_context_strategy()
    )
    @settings(max_examples=100, deadline=None)
    async def test_property_recommendations_are_deterministic(
        self, drug_info, interaction_context
    ):
        """
        Property: Same inputs should produce same recommendations (deterministic)
        
        **Validates: Requirements 4.5**
        """
        # Setup
        mock_db = Mock(spec=KnowledgeGraphDatabase)
        mock_db.find_drug_by_name = AsyncMock(return_value=drug_info)
        
        engine = AlternativeMedicationEngine(mock_db)
        
        # Execute twice with same inputs
        result1 = await engine.find_alternatives(
            drug_info['id'],
            interaction_context=interaction_context
        )
        
        result2 = await engine.find_alternatives(
            drug_info['id'],
            interaction_context=interaction_context
        )
        
        # Verify: Results should be identical
        assert result1.original_drug_id == result2.original_drug_id
        assert result1.overall_confidence == result2.overall_confidence
        assert result1.requires_provider_consultation == result2.requires_provider_consultation
        assert len(result1.alternatives) == len(result2.alternatives)
        assert len(result1.management_strategies) == len(result2.management_strategies)
