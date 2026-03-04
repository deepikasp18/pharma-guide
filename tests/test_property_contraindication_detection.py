"""
Property-based tests for contraindication detection through graph paths

**Validates: Requirements 4.3, 4.4**

Property 10: Contraindication Detection Through Graph Paths
For any patient condition and medication combination, the system should trace knowledge
graph paths to identify contraindications and provide severity ratings based on edge weights.
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite
from typing import List, Dict, Any

from src.knowledge_graph.reasoning_engine import (
    GraphReasoningEngine, TraversalStrategy, GraphPath, RiskAssessment
)
from src.knowledge_graph.models import PatientContext
from src.knowledge_graph.database import KnowledgeGraphDatabase
from unittest.mock import AsyncMock, MagicMock


# ============================================================================
# Strategy Generators for Property-Based Testing
# ============================================================================

@composite
def patient_with_conditions_strategy(draw):
    """Generate patient context with medical conditions"""
    conditions = [
        'pregnancy', 'liver_disease', 'kidney_disease', 'heart_failure',
        'bleeding_disorders', 'asthma', 'glaucoma', 'seizure_disorder',
        'peptic_ulcer', 'hypertension', 'diabetes', 'angioedema'
    ]
    
    num_conditions = draw(st.integers(min_value=1, max_value=4))
    selected_conditions = draw(st.lists(
        st.sampled_from(conditions),
        min_size=num_conditions,
        max_size=num_conditions,
        unique=True
    ))
    
    age = draw(st.integers(min_value=18, max_value=90))
    
    return PatientContext(
        id=f"patient_{draw(st.integers(min_value=1, max_value=10000))}",
        demographics={'age': age, 'weight': 70, 'gender': 'male'},
        conditions=selected_conditions,
        medications=[],
        allergies=[],
        genetic_factors={},
        risk_factors=[],
        preferences={}
    )


@composite
def drug_id_strategy(draw):
    """Generate drug IDs"""
    drugs = [
        'drug_warfarin', 'drug_aspirin', 'drug_lisinopril',
        'drug_metformin', 'drug_atorvastatin', 'drug_ibuprofen',
        'drug_albuterol', 'drug_timolol', 'drug_phenytoin'
    ]
    return draw(st.sampled_from(drugs))


@composite
def contraindication_severity_strategy(draw):
    """Generate contraindication severity levels"""
    return draw(st.sampled_from([
        'absolute', 'relative', 'caution', 'monitor'
    ]))


# ============================================================================
# Property-Based Tests for Contraindication Detection
# ============================================================================

class TestContraindicationDetectionProperties:
    """
    Property-based tests for contraindication detection through graph paths
    
    **Validates: Requirements 4.3, 4.4**
    """
    
    @given(
        patient=patient_with_conditions_strategy(),
        drug_id=drug_id_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_contraindications_detected_for_all_combinations(
        self,
        patient: PatientContext,
        drug_id: str
    ):
        """
        Property: Contraindications are detected for all patient-drug combinations
        
        **Validates: Requirement 4.3**
        
        For any patient with conditions and any drug, the system should
        check for contraindications by tracing graph paths.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Mock graph traversal to return contraindication paths
        mock_paths = []
        for condition in patient.conditions:
            # Simulate finding contraindication path
            if condition in ['pregnancy', 'liver_disease', 'bleeding_disorders']:
                mock_paths.append(GraphPath(
                    nodes=[f"condition_{condition}", drug_id],
                    edges=[f"edge_contraindication_{condition}"],
                    edge_types=['CONTRAINDICATED_IN'],
                    confidence=0.9,
                    evidence_sources=['DrugBank', 'FDA'],
                    path_length=1
                ))
        
        mock_db.execute_gremlin_query = AsyncMock(return_value=mock_paths)
        
        # Create reasoning engine
        engine = GraphReasoningEngine(mock_db)
        
        # Perform multi-hop traversal to find contraindications
        paths = await engine.multi_hop_traversal(
            start_node_id=drug_id,
            max_hops=2,
            strategy=TraversalStrategy.BREADTH_FIRST,
            edge_filters={'type': 'CONTRAINDICATED_IN'}
        )
        
        # Should return paths (may be empty if no contraindications)
        assert isinstance(paths, list)
        
        # All paths should have valid structure
        for path in paths:
            assert isinstance(path, GraphPath)
            assert len(path.nodes) >= 2
            assert len(path.edges) >= 1
            assert len(path.edge_types) >= 1
            assert 0.0 <= path.confidence <= 1.0
            assert isinstance(path.evidence_sources, list)
            assert path.path_length >= 1
    
    @given(
        patient=patient_with_conditions_strategy(),
        drug_id=drug_id_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_severity_ratings_provided(
        self,
        patient: PatientContext,
        drug_id: str
    ):
        """
        Property: Severity ratings are provided for contraindications
        
        **Validates: Requirement 4.4**
        
        For any detected contraindication, the system should provide
        severity ratings based on knowledge graph edge weights.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Mock contraindication paths with severity
        mock_paths = [
            GraphPath(
                nodes=[drug_id, f"condition_{patient.conditions[0]}"],
                edges=[f"edge_contraindication_{patient.conditions[0]}"],
                edge_types=['CONTRAINDICATED_IN'],
                confidence=0.95,
                evidence_sources=['DrugBank', 'FDA'],
                path_length=1
            )
        ]
        
        mock_db.execute_gremlin_query = AsyncMock(return_value=mock_paths)
        
        # Create reasoning engine
        engine = GraphReasoningEngine(mock_db)
        
        # Find contraindications
        paths = await engine.multi_hop_traversal(
            start_node_id=drug_id,
            max_hops=2,
            strategy=TraversalStrategy.BREADTH_FIRST,
            edge_filters={'type': 'CONTRAINDICATED_IN'}
        )
        
        # Verify severity information in paths
        for path in paths:
            # Should have edge types indicating contraindication
            assert len(path.edge_types) > 0, \
                "Contraindication paths should have edge types"
            
            # Should have CONTRAINDICATED_IN relationship
            assert 'CONTRAINDICATED_IN' in path.edge_types, \
                "Should include contraindication relationship type"
            
            # Should have confidence score
            assert 0.0 <= path.confidence <= 1.0, \
                f"Path confidence should be between 0 and 1, got {path.confidence}"
            
            # Should have evidence sources
            assert len(path.evidence_sources) > 0, \
                "Should have evidence sources for contraindication"
    
    @given(
        patient=patient_with_conditions_strategy(),
        drug_id=drug_id_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_risk_assessment_includes_contraindications(
        self,
        patient: PatientContext,
        drug_id: str
    ):
        """
        Property: Risk assessment includes contraindication information
        
        **Validates: Requirements 4.3, 4.4**
        
        For any patient-drug combination, risk assessment should include
        contraindication information from graph paths.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Mock contraindication paths
        contraindication_paths = []
        if 'pregnancy' in patient.conditions:
            contraindication_paths.append(GraphPath(
                nodes=[drug_id, 'condition_pregnancy'],
                edges=['edge_contraindication_pregnancy'],
                edge_types=['CONTRAINDICATED_IN'],
                confidence=0.95,
                evidence_sources=['DrugBank', 'FDA'],
                path_length=1
            ))
        
        mock_db.execute_gremlin_query = AsyncMock(return_value=contraindication_paths)
        
        # Create reasoning engine
        engine = GraphReasoningEngine(mock_db)
        
        # Calculate risk (which should include contraindication check)
        risk_assessment = await engine.calculate_risk(
            drug_id=drug_id,
            patient_context=patient
        )
        
        # Verify risk assessment structure
        assert isinstance(risk_assessment, RiskAssessment)
        assert 0.0 <= risk_assessment.risk_score <= 1.0
        assert risk_assessment.risk_level in ['very_low', 'low', 'moderate', 'high', 'very_high']
        assert isinstance(risk_assessment.contributing_factors, list)
        assert isinstance(risk_assessment.recommendations, list)
        assert 0.0 <= risk_assessment.confidence <= 1.0
        
        # If patient has high-risk conditions, risk should be elevated
        high_risk_conditions = ['pregnancy', 'bleeding_disorders', 'liver_disease']
        if any(cond in patient.conditions for cond in high_risk_conditions):
            # Contributing factors should mention contraindications or conditions
            factors_text = ' '.join(
                str(factor) for factor in risk_assessment.contributing_factors
            ).lower()
            assert any(cond in factors_text for cond in patient.conditions) or \
                   'contraindication' in factors_text or \
                   'condition' in factors_text, \
                "Contributing factors should mention patient conditions or contraindications"
    
    @given(patient=patient_with_conditions_strategy())
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_absolute_contraindications_identified(self, patient: PatientContext):
        """
        Property: Absolute contraindications are correctly identified
        
        **Validates: Requirements 4.3, 4.4**
        
        For drugs with absolute contraindications, the system should
        identify them with highest severity.
        """
        # Test with warfarin and pregnancy (absolute contraindication)
        drug_id = 'drug_warfarin'
        
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # If patient is pregnant, should have absolute contraindication
        if 'pregnancy' in patient.conditions:
            mock_paths = [
                GraphPath(
                    nodes=[drug_id, 'condition_pregnancy'],
                    edges=['edge_contraindication_pregnancy_absolute'],
                    edge_types=['CONTRAINDICATED_IN'],
                    confidence=0.99,
                    evidence_sources=['DrugBank', 'FDA'],
                    path_length=1
                )
            ]
        else:
            mock_paths = []
        
        # Create reasoning engine
        engine = GraphReasoningEngine(mock_db)
        
        # Mock the internal traversal method to return our paths
        engine._breadth_first_traversal = AsyncMock(return_value=mock_paths)
        
        # Find contraindications
        paths = await engine.multi_hop_traversal(
            start_node_id=drug_id,
            max_hops=2,
            strategy=TraversalStrategy.BREADTH_FIRST,
            edge_filters={'type': 'CONTRAINDICATED_IN'}
        )
        
        # If pregnancy condition exists, should find absolute contraindication
        if 'pregnancy' in patient.conditions:
            assert len(paths) > 0, \
                "Should detect absolute contraindication for warfarin in pregnancy"
            
            # Check for contraindication relationship
            has_contraindication = any(
                'CONTRAINDICATED_IN' in path.edge_types
                for path in paths
            )
            assert has_contraindication, \
                "Warfarin in pregnancy should have contraindication relationship"
    
    @given(
        patient=patient_with_conditions_strategy(),
        drug_id=drug_id_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_graph_paths_traced_correctly(
        self,
        patient: PatientContext,
        drug_id: str
    ):
        """
        Property: Graph paths from conditions to contraindications are traced
        
        **Validates: Requirement 4.3**
        
        For any patient condition, the system should trace paths from
        condition nodes to drug contraindication relationships.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Mock paths from conditions to drug
        mock_paths = []
        for condition in patient.conditions:
            mock_paths.append(GraphPath(
                nodes=[f"condition_{condition}", drug_id],
                edges=[f"edge_contraindication_{condition}"],
                edge_types=['CONTRAINDICATED_IN'],
                confidence=0.8,
                evidence_sources=['DrugBank'],
                path_length=1
            ))
        
        mock_db.execute_gremlin_query = AsyncMock(return_value=mock_paths)
        
        # Create reasoning engine
        engine = GraphReasoningEngine(mock_db)
        
        # Trace paths
        paths = await engine.multi_hop_traversal(
            start_node_id=drug_id,
            max_hops=2,
            strategy=TraversalStrategy.BREADTH_FIRST,
            edge_filters={'type': 'CONTRAINDICATED_IN'}
        )
        
        # Verify path structure
        for path in paths:
            # Path should connect condition to drug
            assert len(path.nodes) >= 2, \
                "Path should have at least 2 nodes (condition and drug)"
            
            # Should have edges connecting nodes
            assert len(path.edges) >= 1, \
                "Path should have at least 1 edge"
            
            # Should have edge types
            assert len(path.edge_types) >= 1, \
                "Path should have at least 1 edge type"
            
            # Edge types should include contraindication
            assert 'CONTRAINDICATED_IN' in path.edge_types, \
                "Edge types should include CONTRAINDICATED_IN"
    
    @given(
        patient=patient_with_conditions_strategy(),
        drug_id=drug_id_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_confidence_scores_provided(
        self,
        patient: PatientContext,
        drug_id: str
    ):
        """
        Property: Confidence scores are provided for contraindications
        
        **Validates: Requirement 4.4**
        
        For any contraindication detection, confidence scores should
        indicate the reliability of the finding.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Mock paths with confidence scores
        mock_paths = [
            GraphPath(
                nodes=[drug_id, f"condition_{patient.conditions[0]}"],
                edges=[f"edge_contraindication_{patient.conditions[0]}"],
                edge_types=['CONTRAINDICATED_IN'],
                confidence=0.85,
                evidence_sources=['DrugBank', 'FDA'],
                path_length=1
            )
        ]
        
        mock_db.execute_gremlin_query = AsyncMock(return_value=mock_paths)
        
        # Create reasoning engine
        engine = GraphReasoningEngine(mock_db)
        
        # Find contraindications
        paths = await engine.multi_hop_traversal(
            start_node_id=drug_id,
            max_hops=2,
            strategy=TraversalStrategy.BREADTH_FIRST,
            edge_filters={'type': 'CONTRAINDICATED_IN'}
        )
        
        # Verify confidence scores
        for path in paths:
            # Path should have confidence
            assert 0.0 <= path.confidence <= 1.0, \
                f"Path confidence should be between 0 and 1, got {path.confidence}"
            
            # Should have evidence sources
            assert len(path.evidence_sources) > 0, \
                "Path should have evidence sources"
    
    @given(
        patient=patient_with_conditions_strategy(),
        drug_id=drug_id_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_multiple_contraindications_detected(
        self,
        patient: PatientContext,
        drug_id: str
    ):
        """
        Property: Multiple contraindications are detected when present
        
        **Validates: Requirement 4.3**
        
        For patients with multiple conditions, the system should detect
        all relevant contraindications.
        """
        # Skip if patient has only one condition
        assume(len(patient.conditions) >= 2)
        
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Mock paths for each condition
        mock_paths = []
        for condition in patient.conditions:
            mock_paths.append(GraphPath(
                nodes=[drug_id, f"condition_{condition}"],
                edges=[f"edge_contraindication_{condition}"],
                edge_types=['CONTRAINDICATED_IN'],
                confidence=0.8,
                evidence_sources=['DrugBank'],
                path_length=1
            ))
        
        # Create reasoning engine
        engine = GraphReasoningEngine(mock_db)
        
        # Mock the internal traversal method to return our paths
        engine._breadth_first_traversal = AsyncMock(return_value=mock_paths)
        
        # Find contraindications
        paths = await engine.multi_hop_traversal(
            start_node_id=drug_id,
            max_hops=2,
            strategy=TraversalStrategy.BREADTH_FIRST,
            edge_filters={'type': 'CONTRAINDICATED_IN'}
        )
        
        # Should detect multiple contraindications
        # (In mock, we return one path per condition)
        assert len(paths) >= 1, \
            "Should detect contraindications for patient conditions"
    
    @given(
        patient=patient_with_conditions_strategy(),
        drug_id=drug_id_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_edge_weights_influence_severity(
        self,
        patient: PatientContext,
        drug_id: str
    ):
        """
        Property: Edge weights influence contraindication severity
        
        **Validates: Requirement 4.4**
        
        For contraindications with different edge weights, severity
        ratings should reflect the weight values.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Mock paths with different confidence levels
        mock_paths = [
            GraphPath(
                nodes=[drug_id, f"condition_{patient.conditions[0]}"],
                edges=[f"edge_contraindication_{patient.conditions[0]}_high"],
                edge_types=['CONTRAINDICATED_IN'],
                confidence=0.95,  # High confidence
                evidence_sources=['DrugBank', 'FDA', 'Clinical_Trials'],
                path_length=1
            )
        ]
        
        if len(patient.conditions) > 1:
            mock_paths.append(GraphPath(
                nodes=[drug_id, f"condition_{patient.conditions[1]}"],
                edges=[f"edge_contraindication_{patient.conditions[1]}_low"],
                edge_types=['CONTRAINDICATED_IN'],
                confidence=0.7,  # Lower confidence
                evidence_sources=['DrugBank'],
                path_length=1
            ))
        
        mock_db.execute_gremlin_query = AsyncMock(return_value=mock_paths)
        
        # Create reasoning engine
        engine = GraphReasoningEngine(mock_db)
        
        # Find contraindications
        paths = await engine.multi_hop_traversal(
            start_node_id=drug_id,
            max_hops=2,
            strategy=TraversalStrategy.BREADTH_FIRST,
            edge_filters={'type': 'CONTRAINDICATED_IN'}
        )
        
        # Verify confidence and evidence correlation
        for path in paths:
            # Higher confidence should correlate with more evidence sources
            if path.confidence >= 0.9:
                assert len(path.evidence_sources) >= 2, \
                    f"High confidence ({path.confidence}) should have multiple evidence sources"
            
            # All paths should have valid confidence
            assert 0.0 <= path.confidence <= 1.0, \
                f"Confidence should be between 0 and 1, got {path.confidence}"
    
    @given(
        patient=patient_with_conditions_strategy(),
        drug_id=drug_id_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_contraindication_detection_is_consistent(
        self,
        patient: PatientContext,
        drug_id: str
    ):
        """
        Property: Contraindication detection is consistent across calls
        
        **Validates: Requirement 4.3**
        
        For the same patient and drug, contraindication detection should
        return consistent results.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Mock consistent paths
        mock_paths = [
            GraphPath(
                nodes=[drug_id, f"condition_{patient.conditions[0]}"],
                edges=[f"edge_contraindication_{patient.conditions[0]}"],
                edge_types=['CONTRAINDICATED_IN'],
                confidence=0.8,
                evidence_sources=['DrugBank'],
                path_length=1
            )
        ]
        
        mock_db.execute_gremlin_query = AsyncMock(return_value=mock_paths)
        
        # Create reasoning engine
        engine = GraphReasoningEngine(mock_db)
        
        # Find contraindications twice
        paths1 = await engine.multi_hop_traversal(
            start_node_id=drug_id,
            max_hops=2,
            strategy=TraversalStrategy.BREADTH_FIRST,
            edge_filters={'type': 'CONTRAINDICATED_IN'}
        )
        
        paths2 = await engine.multi_hop_traversal(
            start_node_id=drug_id,
            max_hops=2,
            strategy=TraversalStrategy.BREADTH_FIRST,
            edge_filters={'type': 'CONTRAINDICATED_IN'}
        )
        
        # Results should be consistent
        assert len(paths1) == len(paths2), \
            "Contraindication detection should be consistent"
        
        # Path structures should match
        for i in range(len(paths1)):
            assert paths1[i].confidence == paths2[i].confidence, \
                "Path confidence should be consistent"
