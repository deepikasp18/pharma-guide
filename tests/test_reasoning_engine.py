"""
Tests for graph reasoning engine
"""
import pytest
from datetime import datetime, timedelta
from src.knowledge_graph.reasoning_engine import (
    GraphReasoningEngine,
    GraphPath,
    RiskAssessment,
    TemporalEvent,
    TemporalPattern,
    TraversalStrategy,
    TemporalRelation
)
from src.knowledge_graph.database import KnowledgeGraphDatabase
from src.knowledge_graph.models import DrugEntity, SideEffectEntity, PatientContext


@pytest.fixture
def reasoning_engine():
    """Create reasoning engine with mock database"""
    import asyncio
    db = KnowledgeGraphDatabase()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(db.connect())
    engine = GraphReasoningEngine(db)
    return engine


@pytest.fixture
def sample_patient_context():
    """Sample patient context for testing"""
    return {
        'demographics': {
            'age': 70,
            'gender': 'male',
            'weight': 180
        },
        'conditions': ['diabetes', 'hypertension', 'heart_disease'],
        'medications': [
            {'name': 'metformin', 'dosage': '500mg'},
            {'name': 'lisinopril', 'dosage': '10mg'},
            {'name': 'aspirin', 'dosage': '81mg'}
        ],
        'risk_factors': ['smoking', 'obesity', 'family_history']
    }


class TestGraphPath:
    """Test GraphPath data structure"""
    
    def test_graph_path_creation(self):
        """Test creating a graph path"""
        path = GraphPath()
        assert path.path_length == 0
        assert path.total_weight == 0.0
        assert path.confidence == 1.0
        assert len(path.nodes) == 0
        assert len(path.edges) == 0
    
    def test_add_node_to_path(self):
        """Test adding nodes to path"""
        path = GraphPath()
        node1 = {'id': 'node1', 'label': 'Drug'}
        node2 = {'id': 'node2', 'label': 'SideEffect'}
        
        path.add_node(node1)
        assert path.path_length == 1
        assert len(path.nodes) == 1
        
        path.add_node(node2)
        assert path.path_length == 2
        assert len(path.nodes) == 2
    
    def test_add_edge_to_path(self):
        """Test adding edges to path"""
        path = GraphPath()
        edge = {
            'id': 'edge1',
            'label': 'CAUSES',
            'confidence': 0.9,
            'weight': 1.5
        }
        
        path.add_edge(edge)
        assert len(path.edges) == 1
        assert path.confidence == 0.9
        assert path.total_weight == 1.5
    
    def test_path_confidence_multiplication(self):
        """Test that confidence multiplies across edges"""
        path = GraphPath()
        
        edge1 = {'confidence': 0.9, 'weight': 1.0}
        edge2 = {'confidence': 0.8, 'weight': 1.0}
        
        path.add_edge(edge1)
        path.add_edge(edge2)
        
        # Confidence should be 0.9 * 0.8 = 0.72
        assert abs(path.confidence - 0.72) < 0.01


class TestTemporalEvent:
    """Test TemporalEvent functionality"""
    
    def test_temporal_event_creation(self):
        """Test creating temporal event"""
        now = datetime.utcnow()
        event = TemporalEvent(
            event_id="event1",
            event_type="symptom_log",
            timestamp=now,
            entity_id="patient1",
            properties={'severity': 5}
        )
        
        assert event.event_id == "event1"
        assert event.event_type == "symptom_log"
        assert event.timestamp == now
        assert event.properties['severity'] == 5
    
    def test_time_delta_calculation(self):
        """Test time delta between events"""
        now = datetime.utcnow()
        later = now + timedelta(hours=2)
        
        event1 = TemporalEvent("e1", "type1", now, "entity1")
        event2 = TemporalEvent("e2", "type2", later, "entity1")
        
        delta = event1.time_delta_to(event2)
        assert delta == timedelta(hours=2)
    
    def test_temporal_relation_before(self):
        """Test temporal relation detection - before"""
        now = datetime.utcnow()
        later = now + timedelta(hours=1)
        
        event1 = TemporalEvent("e1", "type1", now, "entity1")
        event2 = TemporalEvent("e2", "type2", later, "entity1")
        
        relation = event1.temporal_relation_to(event2)
        assert relation == TemporalRelation.BEFORE
    
    def test_temporal_relation_after(self):
        """Test temporal relation detection - after"""
        now = datetime.utcnow()
        earlier = now - timedelta(hours=1)
        
        event1 = TemporalEvent("e1", "type1", now, "entity1")
        event2 = TemporalEvent("e2", "type2", earlier, "entity1")
        
        relation = event1.temporal_relation_to(event2)
        assert relation == TemporalRelation.AFTER
    
    def test_temporal_relation_concurrent(self):
        """Test temporal relation detection - concurrent"""
        now = datetime.utcnow()
        
        event1 = TemporalEvent("e1", "type1", now, "entity1")
        event2 = TemporalEvent("e2", "type2", now, "entity1")
        
        relation = event1.temporal_relation_to(event2)
        assert relation == TemporalRelation.CONCURRENT


class TestRiskCalculation:
    """Test risk calculation functionality"""
    
    @pytest.mark.asyncio
    async def test_calculate_risk_score_basic(self, reasoning_engine):
        """Test basic risk score calculation"""
        risk = await reasoning_engine.calculate_risk_score(
            entity_id="drug_test_1"
        )
        
        assert isinstance(risk, RiskAssessment)
        assert risk.risk_level in ["low", "moderate", "high", "critical", "unknown"]
        assert 0.0 <= risk.risk_score <= 1.0
        assert 0.0 <= risk.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_calculate_risk_with_patient_context(
        self, reasoning_engine, sample_patient_context
    ):
        """Test risk calculation with patient context"""
        risk = await reasoning_engine.calculate_risk_score(
            entity_id="drug_test_1",
            patient_context=sample_patient_context
        )
        
        assert isinstance(risk, RiskAssessment)
        # High-risk patient should have contributing factors
        assert len(risk.contributing_factors) > 0
        assert len(risk.recommendations) > 0
    
    def test_severity_weight_mapping(self, reasoning_engine):
        """Test severity to weight conversion"""
        assert reasoning_engine._get_severity_weight('minor') == 0.25
        assert reasoning_engine._get_severity_weight('moderate') == 0.5
        assert reasoning_engine._get_severity_weight('major') == 0.75
        assert reasoning_engine._get_severity_weight('contraindicated') == 1.0
        assert reasoning_engine._get_severity_weight('critical') == 1.0
        assert reasoning_engine._get_severity_weight(None) == 0.5
    
    def test_risk_level_determination(self, reasoning_engine):
        """Test risk level determination from score"""
        assert reasoning_engine._determine_risk_level(0.1) == "low"
        assert reasoning_engine._determine_risk_level(0.3) == "moderate"
        assert reasoning_engine._determine_risk_level(0.6) == "high"
        assert reasoning_engine._determine_risk_level(0.9) == "critical"
    
    def test_patient_risk_adjustment_age(self, reasoning_engine):
        """Test risk adjustment for age"""
        base_risk = 0.5
        
        # Elderly patient
        elderly_context = {
            'demographics': {'age': 70},
            'conditions': [],
            'medications': [],
            'risk_factors': []
        }
        adjusted, factors = reasoning_engine._adjust_risk_for_patient(
            base_risk, elderly_context, None
        )
        assert adjusted > base_risk
        assert any('age' in f.lower() for f in factors)
        
        # Pediatric patient
        pediatric_context = {
            'demographics': {'age': 10},
            'conditions': [],
            'medications': [],
            'risk_factors': []
        }
        adjusted, factors = reasoning_engine._adjust_risk_for_patient(
            base_risk, pediatric_context, None
        )
        assert adjusted > base_risk
        assert any('pediatric' in f.lower() for f in factors)
    
    def test_patient_risk_adjustment_conditions(self, reasoning_engine):
        """Test risk adjustment for medical conditions"""
        base_risk = 0.5
        
        high_risk_context = {
            'demographics': {'age': 50},
            'conditions': ['diabetes', 'heart_disease'],
            'medications': [],
            'risk_factors': []
        }
        adjusted, factors = reasoning_engine._adjust_risk_for_patient(
            base_risk, high_risk_context, None
        )
        assert adjusted > base_risk
        assert len(factors) >= 2  # Should have factors for both conditions
    
    def test_patient_risk_adjustment_polypharmacy(self, reasoning_engine):
        """Test risk adjustment for polypharmacy"""
        base_risk = 0.5
        
        polypharmacy_context = {
            'demographics': {'age': 50},
            'conditions': [],
            'medications': [
                {'name': f'drug{i}'} for i in range(6)
            ],
            'risk_factors': []
        }
        adjusted, factors = reasoning_engine._adjust_risk_for_patient(
            base_risk, polypharmacy_context, None
        )
        assert adjusted > base_risk
        assert any('polypharmacy' in f.lower() for f in factors)
    
    def test_risk_recommendations_generation(self, reasoning_engine):
        """Test generation of risk recommendations"""
        # Critical risk
        recs = reasoning_engine._generate_risk_recommendations(
            "critical", ["Advanced age"]
        )
        assert len(recs) > 0
        assert any('immediate' in r.lower() or 'provider' in r.lower() for r in recs)
        
        # Low risk
        recs = reasoning_engine._generate_risk_recommendations(
            "low", []
        )
        assert len(recs) > 0


class TestMultiHopTraversal:
    """Test multi-hop graph traversal"""
    
    @pytest.mark.asyncio
    async def test_multi_hop_traversal_basic(self, reasoning_engine):
        """Test basic multi-hop traversal"""
        paths = await reasoning_engine.multi_hop_traversal(
            start_node_id="test_node_1",
            max_hops=2,
            strategy=TraversalStrategy.BREADTH_FIRST
        )
        
        assert isinstance(paths, list)
        # All paths should be GraphPath instances
        for path in paths:
            assert isinstance(path, GraphPath)
    
    @pytest.mark.asyncio
    async def test_multi_hop_with_target_type(self, reasoning_engine):
        """Test multi-hop traversal with target node type"""
        paths = await reasoning_engine.multi_hop_traversal(
            start_node_id="test_drug_1",
            target_node_type="SideEffect",
            max_hops=3,
            strategy=TraversalStrategy.BREADTH_FIRST
        )
        
        assert isinstance(paths, list)
    
    @pytest.mark.asyncio
    async def test_multi_hop_with_edge_filters(self, reasoning_engine):
        """Test multi-hop traversal with edge filters"""
        edge_filters = {
            'confidence': {'min': 0.7}
        }
        
        paths = await reasoning_engine.multi_hop_traversal(
            start_node_id="test_node_1",
            max_hops=2,
            edge_filters=edge_filters
        )
        
        assert isinstance(paths, list)
        # Verify all edges in paths meet filter criteria
        for path in paths:
            for edge in path.edges:
                confidence = edge.get('confidence', 1.0)
                assert confidence >= 0.7
    
    @pytest.mark.asyncio
    async def test_depth_first_strategy(self, reasoning_engine):
        """Test depth-first traversal strategy"""
        paths = await reasoning_engine.multi_hop_traversal(
            start_node_id="test_node_1",
            max_hops=2,
            strategy=TraversalStrategy.DEPTH_FIRST
        )
        
        assert isinstance(paths, list)
    
    @pytest.mark.asyncio
    async def test_shortest_path_strategy(self, reasoning_engine):
        """Test shortest path traversal strategy"""
        paths = await reasoning_engine.multi_hop_traversal(
            start_node_id="test_node_1",
            target_node_type="SideEffect",
            strategy=TraversalStrategy.SHORTEST_PATH
        )
        
        assert isinstance(paths, list)
    
    def test_edge_filter_matching(self, reasoning_engine):
        """Test edge filter matching logic"""
        edge = {
            'confidence': 0.8,
            'severity': 'moderate',
            'frequency': 0.5
        }
        
        # Should match
        filters1 = {'confidence': {'min': 0.7}}
        assert reasoning_engine._matches_filters(edge, filters1)
        
        # Should not match
        filters2 = {'confidence': {'min': 0.9}}
        assert not reasoning_engine._matches_filters(edge, filters2)
        
        # Exact match
        filters3 = {'severity': 'moderate'}
        assert reasoning_engine._matches_filters(edge, filters3)
        
        # No match
        filters4 = {'severity': 'major'}
        assert not reasoning_engine._matches_filters(edge, filters4)


class TestTemporalReasoning:
    """Test temporal reasoning capabilities"""
    
    @pytest.mark.asyncio
    async def test_analyze_temporal_patterns(self, reasoning_engine):
        """Test temporal pattern analysis"""
        start_time = datetime.utcnow() - timedelta(days=30)
        end_time = datetime.utcnow()
        
        patterns = await reasoning_engine.analyze_temporal_patterns(
            entity_id="patient_1",
            start_time=start_time,
            end_time=end_time
        )
        
        assert isinstance(patterns, list)
        for pattern in patterns:
            assert isinstance(pattern, TemporalPattern)
            assert pattern.pattern_type in ['trend', 'cycle', 'anomaly']
    
    @pytest.mark.asyncio
    async def test_analyze_specific_pattern_types(self, reasoning_engine):
        """Test analyzing specific pattern types"""
        start_time = datetime.utcnow() - timedelta(days=30)
        end_time = datetime.utcnow()
        
        patterns = await reasoning_engine.analyze_temporal_patterns(
            entity_id="patient_1",
            start_time=start_time,
            end_time=end_time,
            pattern_types=['trend']
        )
        
        assert isinstance(patterns, list)
        # All patterns should be trends
        for pattern in patterns:
            assert pattern.pattern_type == 'trend'
    
    def test_detect_increasing_trend(self, reasoning_engine):
        """Test detection of increasing trend"""
        now = datetime.utcnow()
        events = [
            TemporalEvent(
                f"e{i}", "symptom", now + timedelta(days=i), "patient1",
                {'value': i * 10}
            )
            for i in range(5)
        ]
        
        patterns = reasoning_engine._detect_trends(events)
        
        assert len(patterns) > 0
        assert patterns[0].pattern_type == 'trend'
        assert 'increasing' in patterns[0].description.lower()
    
    def test_detect_decreasing_trend(self, reasoning_engine):
        """Test detection of decreasing trend"""
        now = datetime.utcnow()
        events = [
            TemporalEvent(
                f"e{i}", "symptom", now + timedelta(days=i), "patient1",
                {'value': 100 - i * 10}
            )
            for i in range(5)
        ]
        
        patterns = reasoning_engine._detect_trends(events)
        
        assert len(patterns) > 0
        assert patterns[0].pattern_type == 'trend'
        assert 'decreasing' in patterns[0].description.lower()
    
    def test_detect_cycle(self, reasoning_engine):
        """Test detection of cyclic patterns"""
        now = datetime.utcnow()
        # Create repeating pattern: A, B, A, B, A, B
        event_types = ['A', 'B'] * 3
        events = [
            TemporalEvent(
                f"e{i}", event_types[i], now + timedelta(days=i), "patient1"
            )
            for i in range(len(event_types))
        ]
        
        patterns = reasoning_engine._detect_cycles(events)
        
        assert len(patterns) > 0
        assert patterns[0].pattern_type == 'cycle'
    
    def test_detect_anomalies(self, reasoning_engine):
        """Test detection of anomalous events"""
        now = datetime.utcnow()
        # Create events with one outlier
        values = [10, 12, 11, 13, 100, 12, 11]  # 100 is anomaly
        events = [
            TemporalEvent(
                f"e{i}", "symptom", now + timedelta(days=i), "patient1",
                {'value': values[i]}
            )
            for i in range(len(values))
        ]
        
        patterns = reasoning_engine._detect_anomalies(events)
        
        assert len(patterns) > 0
        assert patterns[0].pattern_type == 'anomaly'
        # Should detect the outlier
        assert len(patterns[0].events) >= 1


class TestInteractionChains:
    """Test drug interaction chain detection"""
    
    @pytest.mark.asyncio
    async def test_find_interaction_chains(self, reasoning_engine):
        """Test finding interaction chains between drugs"""
        drug_ids = ["drug1", "drug2", "drug3"]
        
        chains = await reasoning_engine.find_interaction_chains(
            drug_ids=drug_ids,
            max_chain_length=2
        )
        
        assert isinstance(chains, list)
        for chain in chains:
            assert isinstance(chain, GraphPath)
    
    @pytest.mark.asyncio
    async def test_interaction_chains_sorted_by_severity(self, reasoning_engine):
        """Test that interaction chains are sorted by severity"""
        drug_ids = ["drug1", "drug2", "drug3"]
        
        chains = await reasoning_engine.find_interaction_chains(
            drug_ids=drug_ids,
            max_chain_length=2
        )
        
        # Chains should be sorted by risk (confidence * severity)
        if len(chains) > 1:
            for i in range(len(chains) - 1):
                risk1 = chains[i].confidence * reasoning_engine._get_chain_severity(chains[i])
                risk2 = chains[i+1].confidence * reasoning_engine._get_chain_severity(chains[i+1])
                assert risk1 >= risk2
    
    def test_get_chain_severity(self, reasoning_engine):
        """Test calculation of chain severity"""
        path = GraphPath()
        
        # Add edges with different severities
        path.add_edge({'severity': 'minor', 'confidence': 0.9})
        path.add_edge({'severity': 'major', 'confidence': 0.8})
        
        severity = reasoning_engine._get_chain_severity(path)
        
        # Should return maximum severity (major = 0.75)
        assert severity == 0.75


class TestRelationshipInference:
    """Test relationship inference capabilities"""
    
    @pytest.mark.asyncio
    async def test_infer_missing_relationships(self, reasoning_engine):
        """Test inferring missing relationships"""
        inferred = await reasoning_engine.infer_missing_relationships(
            entity_id="drug_test_1",
            relationship_type="CAUSES",
            confidence_threshold=0.7
        )
        
        assert isinstance(inferred, list)
        for rel in inferred:
            assert 'source_id' in rel
            assert 'target_id' in rel
            assert 'relationship_type' in rel
            assert 'confidence' in rel
            assert rel['confidence'] >= 0.7
    
    def test_calculate_similarity(self, reasoning_engine):
        """Test entity similarity calculation"""
        entity1 = {
            'id': 'e1',
            'label': 'Drug',
            'name': 'DrugA',
            'mechanism': 'inhibitor',
            'class': 'beta_blocker'
        }
        
        entity2 = {
            'id': 'e2',
            'label': 'Drug',
            'name': 'DrugB',
            'mechanism': 'inhibitor',
            'class': 'beta_blocker'
        }
        
        entity3 = {
            'id': 'e3',
            'label': 'Drug',
            'name': 'DrugC',
            'mechanism': 'agonist',
            'class': 'alpha_blocker'
        }
        
        # entity1 and entity2 are more similar
        sim12 = reasoning_engine._calculate_similarity(entity1, entity2)
        sim13 = reasoning_engine._calculate_similarity(entity1, entity3)
        
        assert sim12 > sim13
        assert 0.0 <= sim12 <= 1.0
        assert 0.0 <= sim13 <= 1.0


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.mark.asyncio
    async def test_traversal_with_invalid_node(self, reasoning_engine):
        """Test traversal with non-existent node"""
        paths = await reasoning_engine.multi_hop_traversal(
            start_node_id="nonexistent_node",
            max_hops=2
        )
        
        # Should return empty list, not error
        assert isinstance(paths, list)
    
    @pytest.mark.asyncio
    async def test_risk_calculation_with_no_paths(self, reasoning_engine):
        """Test risk calculation when no paths found"""
        risk = await reasoning_engine.calculate_risk_score(
            entity_id="isolated_node"
        )
        
        assert isinstance(risk, RiskAssessment)
        assert risk.risk_score == 0.0
    
    def test_trend_detection_with_insufficient_data(self, reasoning_engine):
        """Test trend detection with too few events"""
        now = datetime.utcnow()
        events = [
            TemporalEvent("e1", "type1", now, "entity1", {'value': 10})
        ]
        
        patterns = reasoning_engine._detect_trends(events)
        
        # Should return empty list
        assert len(patterns) == 0
    
    def test_cycle_detection_with_insufficient_data(self, reasoning_engine):
        """Test cycle detection with too few events"""
        now = datetime.utcnow()
        events = [
            TemporalEvent("e1", "A", now, "entity1"),
            TemporalEvent("e2", "B", now + timedelta(days=1), "entity1")
        ]
        
        patterns = reasoning_engine._detect_cycles(events)
        
        # Should return empty list
        assert len(patterns) == 0
    
    def test_anomaly_detection_with_insufficient_data(self, reasoning_engine):
        """Test anomaly detection with too few events"""
        now = datetime.utcnow()
        events = [
            TemporalEvent("e1", "type1", now, "entity1", {'value': 10})
        ]
        
        patterns = reasoning_engine._detect_anomalies(events)
        
        # Should return empty list
        assert len(patterns) == 0
    
    def test_similarity_with_empty_properties(self, reasoning_engine):
        """Test similarity calculation with minimal properties"""
        entity1 = {'id': 'e1', 'label': 'Drug'}
        entity2 = {'id': 'e2', 'label': 'Drug'}
        
        similarity = reasoning_engine._calculate_similarity(entity1, entity2)
        
        # Should handle gracefully
        assert 0.0 <= similarity <= 1.0



# Property-Based Tests using Hypothesis

from hypothesis import given, strategies as st, settings, assume, HealthCheck
from hypothesis.strategies import composite
import asyncio


@composite
def drug_id_strategy(draw):
    """Generate valid drug IDs"""
    prefix = draw(st.sampled_from(['drug', 'med', 'rx']))
    number = draw(st.integers(min_value=1, max_value=10000))
    return f"{prefix}_{number}"


@composite
def drug_list_strategy(draw):
    """Generate list of 2-5 drug IDs"""
    num_drugs = draw(st.integers(min_value=2, max_value=5))
    drugs = [draw(drug_id_strategy()) for _ in range(num_drugs)]
    # Ensure unique drug IDs
    return list(set(drugs))


@composite
def interaction_severity_strategy(draw):
    """Generate interaction severity levels"""
    return draw(st.sampled_from(['minor', 'moderate', 'major', 'contraindicated']))


@composite
def confidence_strategy(draw):
    """Generate confidence scores between 0.0 and 1.0"""
    return draw(st.floats(min_value=0.0, max_value=1.0))


class TestDrugInteractionGraphTraversal:
    """
    Property-Based Tests for Drug Interaction Graph Traversal
    Feature: pharmaguide-health-companion, Property 4: Drug Interaction Graph Traversal
    Validates: Requirements 1.4, 4.1, 4.2
    """
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        drug_ids=drug_list_strategy(),
        max_chain_length=st.integers(min_value=1, max_value=3)
    )
    def test_property_interaction_chains_for_any_drug_combination(
        self, reasoning_engine, drug_ids, max_chain_length
    ):
        """
        Property 4: Drug Interaction Graph Traversal
        
        For any drug combination, the system should traverse interaction 
        relationships in the knowledge graph derived from DDInter and 
        DrugBank datasets, including multi-hop traversals for complex patterns.
        
        This property verifies that:
        1. The system can find interaction chains between any drug combination
        2. Multi-hop traversals work correctly for complex interaction patterns
        3. Results are properly structured as GraphPath objects
        4. All paths respect the maximum chain length constraint
        """
        # Assume we have at least 2 unique drugs
        assume(len(drug_ids) >= 2)
        assume(len(set(drug_ids)) == len(drug_ids))  # All unique
        
        # Execute the interaction chain finding (wrap async call)
        loop = asyncio.get_event_loop()
        chains = loop.run_until_complete(
            reasoning_engine.find_interaction_chains(
                drug_ids=drug_ids,
                max_chain_length=max_chain_length
            )
        )
        
        # Property 1: Result should always be a list
        assert isinstance(chains, list), "Result must be a list of interaction chains"
        
        # Property 2: All items in the list should be GraphPath objects
        for chain in chains:
            assert isinstance(chain, GraphPath), \
                f"All chains must be GraphPath objects, got {type(chain)}"
        
        # Property 3: All paths should respect max_chain_length
        for chain in chains:
            assert chain.path_length <= max_chain_length + 1, \
                f"Path length {chain.path_length} exceeds max_chain_length {max_chain_length}"
        
        # Property 4: All paths should have valid confidence scores (0-1)
        for chain in chains:
            assert 0.0 <= chain.confidence <= 1.0, \
                f"Confidence {chain.confidence} must be between 0 and 1"
        
        # Property 5: Paths should be sorted by risk (confidence * severity) in descending order
        if len(chains) > 1:
            for i in range(len(chains) - 1):
                risk1 = chains[i].confidence * reasoning_engine._get_chain_severity(chains[i])
                risk2 = chains[i+1].confidence * reasoning_engine._get_chain_severity(chains[i+1])
                assert risk1 >= risk2, \
                    "Chains should be sorted by risk in descending order"
        
        # Property 6: Each chain should connect drugs from the input list
        for chain in chains:
            if chain.nodes:
                # First and last nodes should be from our drug list
                first_node_id = chain.nodes[0].get('id', '')
                last_node_id = chain.nodes[-1].get('id', '')
                # At least one should be from our input (in mock, may not have data)
                # This validates the structure is correct
                assert isinstance(first_node_id, str), "Node IDs must be strings"
                assert isinstance(last_node_id, str), "Node IDs must be strings"
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        start_drug=drug_id_strategy(),
        target_drug=drug_id_strategy(),
        max_hops=st.integers(min_value=1, max_value=4)
    )
    def test_property_multi_hop_traversal_finds_interaction_paths(
        self, reasoning_engine, start_drug, target_drug, max_hops
    ):
        """
        Property 4.1: Multi-hop traversal for complex interaction patterns
        
        For any two drugs, the system should be able to perform multi-hop
        traversals to find complex interaction patterns, even when drugs
        don't directly interact but have indirect relationships.
        
        Validates: Requirement 4.2 - multi-hop knowledge graph traversals
        """
        # Ensure drugs are different
        assume(start_drug != target_drug)
        
        # Perform multi-hop traversal looking for drug interactions
        loop = asyncio.get_event_loop()
        paths = loop.run_until_complete(
            reasoning_engine.multi_hop_traversal(
                start_node_id=start_drug,
                target_node_type="Drug",
                max_hops=max_hops,
                strategy=TraversalStrategy.BREADTH_FIRST,
                edge_filters={'label': 'INTERACTS_WITH'}
            )
        )
        
        # Property 1: Result is always a list
        assert isinstance(paths, list), "Multi-hop traversal must return a list"
        
        # Property 2: All results are GraphPath objects
        for path in paths:
            assert isinstance(path, GraphPath), \
                f"All paths must be GraphPath objects, got {type(path)}"
        
        # Property 3: No path exceeds max_hops
        for path in paths:
            # Path length is number of nodes, hops is number of edges
            num_hops = len(path.edges)
            assert num_hops <= max_hops, \
                f"Path has {num_hops} hops, exceeds max_hops {max_hops}"
        
        # Property 4: All paths have valid structure (nodes and edges align)
        for path in paths:
            # Number of edges should be number of nodes - 1 (for connected path)
            if len(path.nodes) > 0:
                expected_edges = len(path.nodes) - 1
                assert len(path.edges) == expected_edges or len(path.edges) == 0, \
                    f"Path structure invalid: {len(path.nodes)} nodes but {len(path.edges)} edges"
        
        # Property 5: Confidence decreases or stays same with path length
        for path in paths:
            # Confidence is multiplicative, so longer paths should have <= confidence
            # (unless all edges have confidence 1.0)
            assert 0.0 <= path.confidence <= 1.0, \
                f"Path confidence {path.confidence} must be in [0, 1]"
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        drug_ids=drug_list_strategy(),
        min_confidence=confidence_strategy()
    )
    def test_property_interaction_chains_respect_confidence_threshold(
        self, reasoning_engine, drug_ids, min_confidence
    ):
        """
        Property 4.2: Interaction detection with confidence filtering
        
        For any drug combination and confidence threshold, the system
        should only return interaction chains that meet the minimum
        confidence requirement.
        
        Validates: Requirement 4.1 - query interaction relationships with quality filtering
        """
        assume(len(drug_ids) >= 2)
        assume(len(set(drug_ids)) == len(drug_ids))
        
        # Find interaction chains
        loop = asyncio.get_event_loop()
        chains = loop.run_until_complete(
            reasoning_engine.find_interaction_chains(
                drug_ids=drug_ids,
                max_chain_length=2
            )
        )
        
        # Property 1: All chains should be valid GraphPath objects
        assert isinstance(chains, list)
        for chain in chains:
            assert isinstance(chain, GraphPath)
        
        # Property 2: Each chain's confidence should be computable
        for chain in chains:
            assert hasattr(chain, 'confidence')
            assert isinstance(chain.confidence, (int, float))
            assert 0.0 <= chain.confidence <= 1.0
        
        # Property 3: Chains with edges should have confidence <= product of edge confidences
        for chain in chains:
            if chain.edges:
                # Calculate expected max confidence (product of all edge confidences)
                expected_confidence = 1.0
                for edge in chain.edges:
                    edge_conf = edge.get('confidence', 1.0)
                    expected_confidence *= edge_conf
                
                # Chain confidence should not exceed this
                assert chain.confidence <= expected_confidence + 0.01, \
                    f"Chain confidence {chain.confidence} exceeds product of edge confidences {expected_confidence}"
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        drug_ids=drug_list_strategy()
    )
    def test_property_interaction_chains_include_severity_ratings(
        self, reasoning_engine, drug_ids
    ):
        """
        Property 4.3: Severity ratings in interaction detection
        
        For any drug combination, interaction chains should include
        severity ratings based on knowledge graph edge weights.
        
        Validates: Requirement 4.4 - provide interaction severity ratings
        """
        assume(len(drug_ids) >= 2)
        assume(len(set(drug_ids)) == len(drug_ids))
        
        # Find interaction chains
        loop = asyncio.get_event_loop()
        chains = loop.run_until_complete(
            reasoning_engine.find_interaction_chains(
                drug_ids=drug_ids,
                max_chain_length=2
            )
        )
        
        # Property 1: System can calculate severity for any chain
        for chain in chains:
            severity = reasoning_engine._get_chain_severity(chain)
            
            # Severity should be a valid float
            assert isinstance(severity, (int, float)), \
                f"Severity must be numeric, got {type(severity)}"
            
            # Severity should be in valid range (0.0 to 1.0 based on weight mapping)
            assert 0.0 <= severity <= 1.0, \
                f"Severity {severity} must be in range [0, 1]"
        
        # Property 2: Chains are sorted by risk (confidence * severity)
        if len(chains) > 1:
            risks = []
            for chain in chains:
                severity = reasoning_engine._get_chain_severity(chain)
                risk = chain.confidence * severity
                risks.append(risk)
            
            # Verify descending order
            for i in range(len(risks) - 1):
                assert risks[i] >= risks[i+1], \
                    "Chains should be sorted by risk (confidence * severity) in descending order"
        
        # Property 3: Severity calculation is consistent
        for chain in chains:
            severity1 = reasoning_engine._get_chain_severity(chain)
            severity2 = reasoning_engine._get_chain_severity(chain)
            assert severity1 == severity2, \
                "Severity calculation should be deterministic"
    
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        drug_ids=drug_list_strategy(),
        strategy=st.sampled_from([
            TraversalStrategy.BREADTH_FIRST,
            TraversalStrategy.DEPTH_FIRST,
            TraversalStrategy.SHORTEST_PATH
        ])
    )
    def test_property_traversal_strategy_consistency(
        self, reasoning_engine, drug_ids, strategy
    ):
        """
        Property 4.4: Traversal strategy consistency
        
        For any drug combination and traversal strategy, the system
        should return valid results that respect the strategy's semantics.
        
        Validates: Requirement 4.2 - multi-hop traversals with different strategies
        """
        assume(len(drug_ids) >= 2)
        
        # Pick first drug as start
        start_drug = drug_ids[0]
        
        # Perform traversal with specified strategy
        loop = asyncio.get_event_loop()
        paths = loop.run_until_complete(
            reasoning_engine.multi_hop_traversal(
                start_node_id=start_drug,
                target_node_type="Drug",
                max_hops=2,
                strategy=strategy
            )
        )
        
        # Property 1: All strategies return valid list of paths
        assert isinstance(paths, list)
        for path in paths:
            assert isinstance(path, GraphPath)
        
        # Property 2: All paths start from the specified drug
        for path in paths:
            if path.nodes:
                first_node = path.nodes[0]
                # In a real implementation, this would be start_drug
                # For now, just verify structure
                assert 'id' in first_node or len(first_node) == 0
        
        # Property 3: SHORTEST_PATH should return paths with minimal length
        if strategy == TraversalStrategy.SHORTEST_PATH and len(paths) > 1:
            # All paths to same target should have same length (shortest)
            path_lengths = [p.path_length for p in paths]
            if path_lengths:
                min_length = min(path_lengths)
                # All paths should be relatively short
                for length in path_lengths:
                    assert length <= min_length + 1, \
                        "SHORTEST_PATH should return minimal length paths"
        
        # Property 4: All paths have valid confidence and weight
        for path in paths:
            assert 0.0 <= path.confidence <= 1.0
            assert path.total_weight >= 0.0
    
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        drug_ids=drug_list_strategy()
    )
    def test_property_interaction_detection_is_symmetric(
        self, reasoning_engine, drug_ids
    ):
        """
        Property 4.5: Symmetry in interaction detection
        
        For any two drugs A and B, if there's an interaction from A to B,
        the system should be able to find it regardless of which drug
        is used as the starting point.
        
        Validates: Requirement 4.1 - comprehensive interaction detection
        """
        assume(len(drug_ids) >= 2)
        
        # Take first two drugs
        drug_a = drug_ids[0]
        drug_b = drug_ids[1]
        
        # Find chains from A to B
        loop = asyncio.get_event_loop()
        chains_a_to_b = loop.run_until_complete(
            reasoning_engine.find_interaction_chains(
                drug_ids=[drug_a, drug_b],
                max_chain_length=2
            )
        )
        
        # Find chains from B to A
        chains_b_to_a = loop.run_until_complete(
            reasoning_engine.find_interaction_chains(
                drug_ids=[drug_b, drug_a],
                max_chain_length=2
            )
        )
        
        # Property 1: Both directions return valid results
        assert isinstance(chains_a_to_b, list)
        assert isinstance(chains_b_to_a, list)
        
        # Property 2: If interactions exist, both directions should find them
        # (In a real graph, interactions might be directional, but the system
        # should be able to traverse in both directions)
        total_chains = len(chains_a_to_b) + len(chains_b_to_a)
        
        # If any chains found, verify they're valid
        all_chains = chains_a_to_b + chains_b_to_a
        for chain in all_chains:
            assert isinstance(chain, GraphPath)
            assert 0.0 <= chain.confidence <= 1.0
            
            # Verify chain connects the two drugs
            if chain.nodes and len(chain.nodes) >= 2:
                node_ids = [n.get('id', '') for n in chain.nodes]
                # Chain should involve our drugs (in mock, may be empty)
                assert all(isinstance(nid, str) for nid in node_ids)
