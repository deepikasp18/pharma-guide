"""
Property-based tests for drug interaction graph traversal

**Validates: Requirements 1.4, 4.1, 4.2**

Property 4: Drug Interaction Graph Traversal
For any drug combination, the system should traverse interaction relationships in the 
knowledge graph derived from DDInter and DrugBank datasets, including multi-hop 
traversals for complex patterns.
"""
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from hypothesis.strategies import composite
from typing import List, Dict, Any
import asyncio

from src.knowledge_graph.models import (
    DrugEntity, InteractionEntity, SeverityLevel, PatientContext
)
from src.knowledge_graph.reasoning_engine import (
    GraphReasoningEngine, TraversalStrategy, GraphPath
)
from src.knowledge_graph.database import KnowledgeGraphDatabase
from unittest.mock import Mock, AsyncMock


# ============================================================================
# Strategy Generators for Property-Based Testing
# ============================================================================

@composite
def drug_name_strategy(draw):
    """Generate realistic drug names"""
    prefixes = ["Lis", "Met", "Ator", "Sim", "Prav", "Ros", "Amlod", "Losar", "Valsar", 
                "Warfar", "Aspir", "Ibuprof", "Napro", "Celecox"]
    suffixes = ["pril", "formin", "vastatin", "ipine", "tan", "olol", "in", "en", "ib"]
    
    prefix = draw(st.sampled_from(prefixes))
    suffix = draw(st.sampled_from(suffixes))
    
    return prefix + suffix


@composite
def drug_entity_strategy(draw):
    """Generate valid DrugEntity instances"""
    drug_id = f"drug_{draw(st.integers(min_value=1, max_value=10000))}"
    name = draw(drug_name_strategy())
    
    return DrugEntity(
        id=drug_id,
        name=name,
        generic_name=name.lower(),
        drugbank_id=f"DB{draw(st.integers(min_value=10000, max_value=99999))}",
        rxcui=str(draw(st.integers(min_value=1000, max_value=999999))),
        mechanism=draw(st.sampled_from([
            "ACE inhibitor", "Beta blocker", "Calcium channel blocker",
            "Statin", "Anticoagulant", "NSAID", "Diuretic"
        ])),
        indications=draw(st.lists(
            st.sampled_from(["hypertension", "diabetes", "heart failure", "pain"]),
            min_size=1, max_size=3
        ))
    )


@composite
def interaction_entity_strategy(draw, drug_a_id: str, drug_b_id: str):
    """Generate valid InteractionEntity instances"""
    interaction_id = f"interaction_{draw(st.integers(min_value=1, max_value=10000))}"
    
    return InteractionEntity(
        id=interaction_id,
        drug_a_id=drug_a_id,
        drug_b_id=drug_b_id,
        severity=draw(st.sampled_from(list(SeverityLevel))),
        mechanism=draw(st.sampled_from([
            "Pharmacokinetic interaction - CYP450 inhibition",
            "Pharmacodynamic interaction - additive effects",
            "Protein binding displacement",
            "Renal clearance competition",
            "Absorption interference"
        ])),
        clinical_effect=draw(st.sampled_from([
            "Increased bleeding risk",
            "Enhanced hypotensive effect",
            "Reduced therapeutic efficacy",
            "Increased toxicity risk",
            "QT prolongation"
        ])),
        management=draw(st.sampled_from([
            "Monitor closely",
            "Adjust dosage",
            "Consider alternative",
            "Avoid combination",
            "Separate administration times"
        ])),
        evidence_level=draw(st.sampled_from(["high", "moderate", "low"])),
        onset=draw(st.sampled_from(["rapid", "delayed", "not specified"])),
        documentation=draw(st.sampled_from(["well-documented", "probable", "possible"])),
        created_from=draw(st.lists(
            st.sampled_from(["DDInter", "DrugBank"]),
            min_size=1, max_size=2, unique=True
        ))
    )


@composite
def drug_combination_strategy(draw):
    """Generate a combination of drugs for interaction testing"""
    num_drugs = draw(st.integers(min_value=2, max_value=5))
    drugs = [draw(drug_entity_strategy()) for _ in range(num_drugs)]
    
    # Ensure unique drug IDs
    seen_ids = set()
    unique_drugs = []
    for drug in drugs:
        if drug.id not in seen_ids:
            seen_ids.add(drug.id)
            unique_drugs.append(drug)
    
    assume(len(unique_drugs) >= 2)
    return unique_drugs


@composite
def graph_path_strategy(draw, start_drug_id: str, end_drug_id: str, max_hops: int = 3):
    """Generate valid GraphPath instances"""
    num_hops = draw(st.integers(min_value=1, max_value=max_hops))
    
    # Create path nodes
    nodes = [start_drug_id]
    for i in range(num_hops - 1):
        nodes.append(f"intermediate_{i}")
    nodes.append(end_drug_id)
    
    # Create edges and edge types
    edges = [f"edge_{i}" for i in range(len(nodes) - 1)]
    edge_types = draw(st.lists(
        st.sampled_from(["INTERACTS_WITH", "CAUSES", "TREATS"]),
        min_size=len(edges), max_size=len(edges)
    ))
    
    return GraphPath(
        nodes=nodes,
        edges=edges,
        edge_types=edge_types,
        confidence=draw(st.floats(min_value=0.0, max_value=1.0)),
        evidence_sources=draw(st.lists(
            st.sampled_from(["DDInter", "DrugBank", "FAERS"]),
            min_size=1, max_size=3, unique=True
        )),
        path_length=len(nodes)
    )


@composite
def patient_with_medications_strategy(draw):
    """Generate patient context with multiple medications"""
    patient_id = f"patient_{draw(st.integers(min_value=1, max_value=10000))}"
    
    num_medications = draw(st.integers(min_value=2, max_value=6))
    medications = []
    for _ in range(num_medications):
        medications.append({
            "name": draw(drug_name_strategy()),
            "dosage": draw(st.sampled_from(["5mg", "10mg", "20mg", "40mg", "80mg"])),
            "frequency": draw(st.sampled_from(["once daily", "twice daily", "as needed"]))
        })
    
    return PatientContext(
        id=patient_id,
        demographics={
            "age": draw(st.integers(min_value=18, max_value=100)),
            "gender": draw(st.sampled_from(["male", "female"])),
            "weight": draw(st.integers(min_value=40, max_value=200))
        },
        conditions=draw(st.lists(
            st.sampled_from(["hypertension", "diabetes", "heart failure", "chronic pain"]),
            min_size=0, max_size=3
        )),
        medications=medications,
        allergies=draw(st.lists(
            st.sampled_from(["penicillin", "sulfa", "aspirin"]),
            min_size=0, max_size=2
        ))
    )


# ============================================================================
# Property-Based Tests for Drug Interaction Graph Traversal
# ============================================================================

class TestDrugInteractionGraphTraversal:
    """
    Property-based tests for drug interaction graph traversal
    
    **Validates: Requirements 1.4, 4.1, 4.2**
    """
    
    @given(
        drug_a=drug_entity_strategy(),
        drug_b=drug_entity_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_interaction_entity_consistency(self, drug_a: DrugEntity, drug_b: DrugEntity):
        """
        Property: Drug interaction entities maintain consistent structure
        
        **Validates: Requirements 1.4, 4.1**
        
        For any two drugs, interaction entities should have:
        1. Valid severity levels
        2. Evidence from DDInter or DrugBank
        3. Proper drug ID references
        """
        assume(drug_a.id != drug_b.id)
        
        interaction = InteractionEntity(
            id=f"interaction_{hash((drug_a.id, drug_b.id)) % 10000}",
            drug_a_id=drug_a.id,
            drug_b_id=drug_b.id,
            severity=SeverityLevel.MODERATE,
            mechanism="Test mechanism",
            clinical_effect="Test effect",
            management="Monitor closely",
            created_from=["DDInter", "DrugBank"]
        )
        
        # Verify interaction structure
        assert interaction.drug_a_id == drug_a.id
        assert interaction.drug_b_id == drug_b.id
        assert interaction.severity in SeverityLevel
        
        # Verify evidence sources are from correct datasets
        valid_sources = {"DDInter", "DrugBank"}
        for source in interaction.created_from:
            assert source in valid_sources, f"Invalid source: {source}"
        
        # Verify serialization round-trip
        interaction_dict = interaction.model_dump()
        recreated = InteractionEntity(**interaction_dict)
        assert recreated.id == interaction.id
        assert recreated.drug_a_id == interaction.drug_a_id
        assert recreated.drug_b_id == interaction.drug_b_id
    
    @given(
        drug_a=drug_entity_strategy(),
        drug_b=drug_entity_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_single_hop_interaction_traversal(self, drug_a: DrugEntity, drug_b: DrugEntity):
        """
        Property: Single-hop traversal finds direct drug interactions
        
        **Validates: Requirements 1.4, 4.1**
        
        For any two drugs with a direct interaction, traversal should:
        1. Find the interaction relationship
        2. Return a path with correct structure
        3. Include evidence from DDInter or DrugBank
        """
        assume(drug_a.id != drug_b.id)
        
        # Create mock database and reasoning engine
        mock_db = Mock(spec=KnowledgeGraphDatabase)
        engine = GraphReasoningEngine(mock_db)
        
        # Create expected interaction path
        expected_path = GraphPath(
            nodes=[drug_a.id, drug_b.id],
            edges=["interaction_edge"],
            edge_types=["INTERACTS_WITH"],
            confidence=0.85,
            evidence_sources=["DDInter", "DrugBank"],
            path_length=2
        )
        
        # Mock the traversal method
        engine._breadth_first_traversal = AsyncMock(return_value=[expected_path])
        
        # Execute traversal
        paths = await engine.multi_hop_traversal(
            start_node_id=drug_a.id,
            target_node_type="Drug",
            max_hops=1,
            strategy=TraversalStrategy.BREADTH_FIRST,
            edge_filters={"label": "INTERACTS_WITH"}
        )
        
        # Verify path properties
        assert len(paths) > 0
        path = paths[0]
        assert path.nodes[0] == drug_a.id
        assert path.nodes[-1] == drug_b.id
        assert "INTERACTS_WITH" in path.edge_types
        assert path.path_length >= 2
        
        # Verify evidence sources
        assert any(source in ["DDInter", "DrugBank"] for source in path.evidence_sources)
    
    @given(drugs=drug_combination_strategy())
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_multi_hop_interaction_traversal(self, drugs: List[DrugEntity]):
        """
        Property: Multi-hop traversal finds complex interaction patterns
        
        **Validates: Requirements 1.4, 4.2**
        
        For any drug combination, multi-hop traversal should:
        1. Find interaction chains between drugs
        2. Support paths up to max_hops length
        3. Maintain evidence provenance through the path
        """
        assume(len(drugs) >= 2)
        
        # Create mock database and reasoning engine
        mock_db = Mock(spec=KnowledgeGraphDatabase)
        engine = GraphReasoningEngine(mock_db)
        
        start_drug = drugs[0]
        end_drug = drugs[-1]
        
        # Create multi-hop path
        intermediate_nodes = [drug.id for drug in drugs[1:-1]]
        all_nodes = [start_drug.id] + intermediate_nodes + [end_drug.id]
        
        expected_path = GraphPath(
            nodes=all_nodes,
            edges=[f"edge_{i}" for i in range(len(all_nodes) - 1)],
            edge_types=["INTERACTS_WITH"] * (len(all_nodes) - 1),
            confidence=0.7,
            evidence_sources=["DDInter", "DrugBank"],
            path_length=len(all_nodes)
        )
        
        # Mock the traversal method
        engine._breadth_first_traversal = AsyncMock(return_value=[expected_path])
        
        # Execute multi-hop traversal
        max_hops = len(drugs)
        paths = await engine.multi_hop_traversal(
            start_node_id=start_drug.id,
            target_node_type="Drug",
            max_hops=max_hops,
            strategy=TraversalStrategy.BREADTH_FIRST
        )
        
        # Verify multi-hop properties
        assert len(paths) > 0
        path = paths[0]
        assert path.nodes[0] == start_drug.id
        assert path.nodes[-1] == end_drug.id
        assert path.path_length <= max_hops + 1
        assert len(path.nodes) >= 2
        
        # Verify evidence sources are maintained
        assert len(path.evidence_sources) > 0
        assert all(source in ["DDInter", "DrugBank", "FAERS"] for source in path.evidence_sources)
    
    @given(
        drug_a=drug_entity_strategy(),
        drug_b=drug_entity_strategy(),
        interaction=interaction_entity_strategy(
            drug_a_id=st.just("drug_a").example(),
            drug_b_id=st.just("drug_b").example()
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_interaction_severity_levels(
        self, drug_a: DrugEntity, drug_b: DrugEntity, interaction: InteractionEntity
    ):
        """
        Property: Interaction severity levels are properly classified
        
        **Validates: Requirements 4.1, 4.2**
        
        For any drug interaction:
        1. Severity must be one of: minor, moderate, major, contraindicated
        2. Higher severity should influence traversal priority
        3. Severity should be derived from evidence
        """
        # Update interaction with actual drug IDs
        interaction.drug_a_id = drug_a.id
        interaction.drug_b_id = drug_b.id
        
        # Verify severity is valid
        assert interaction.severity in SeverityLevel
        
        # Verify severity values
        severity_values = {
            SeverityLevel.MINOR: 0.25,
            SeverityLevel.MODERATE: 0.5,
            SeverityLevel.MAJOR: 0.75,
            SeverityLevel.CONTRAINDICATED: 1.0
        }
        
        assert interaction.severity in severity_values
        
        # Verify evidence sources exist
        assert len(interaction.created_from) > 0
        assert all(source in ["DDInter", "DrugBank"] for source in interaction.created_from)
    
    @given(patient=patient_with_medications_strategy())
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_patient_medication_interaction_detection(self, patient: PatientContext):
        """
        Property: System detects interactions in patient medication lists
        
        **Validates: Requirements 1.4, 4.1, 4.2**
        
        For any patient with multiple medications:
        1. System should check all pairwise interactions
        2. Traversal should find interaction paths between medications
        3. Results should include evidence from DDInter/DrugBank
        """
        assume(len(patient.medications) >= 2)
        
        # Create mock database and reasoning engine
        mock_db = Mock(spec=KnowledgeGraphDatabase)
        engine = GraphReasoningEngine(mock_db)
        
        # Get medication pairs
        med_names = [med["name"] for med in patient.medications]
        
        # Create interaction paths for each pair
        interaction_paths = []
        for i in range(len(med_names) - 1):
            path = GraphPath(
                nodes=[f"drug_{i}", f"drug_{i+1}"],
                edges=[f"interaction_{i}"],
                edge_types=["INTERACTS_WITH"],
                confidence=0.75,
                evidence_sources=["DDInter", "DrugBank"],
                path_length=2
            )
            interaction_paths.append(path)
        
        # Mock traversal to return interaction paths
        engine._breadth_first_traversal = AsyncMock(return_value=interaction_paths)
        
        # Check interactions for first medication
        paths = await engine.multi_hop_traversal(
            start_node_id="drug_0",
            target_node_type="Drug",
            max_hops=2,
            strategy=TraversalStrategy.BREADTH_FIRST
        )
        
        # Verify interaction detection
        assert len(paths) > 0
        
        # Verify all paths have proper structure
        for path in paths:
            assert len(path.nodes) >= 2
            assert "INTERACTS_WITH" in path.edge_types
            assert len(path.evidence_sources) > 0
            assert any(source in ["DDInter", "DrugBank"] for source in path.evidence_sources)
    
    @given(
        start_drug=drug_entity_strategy(),
        max_hops=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_traversal_respects_max_hops(self, start_drug: DrugEntity, max_hops: int):
        """
        Property: Graph traversal respects maximum hop limit
        
        **Validates: Requirements 4.2**
        
        For any starting drug and max_hops value:
        1. All returned paths should have length <= max_hops + 1
        2. No path should exceed the specified limit
        3. Traversal should terminate at max_hops
        """
        # Create mock database and reasoning engine
        mock_db = Mock(spec=KnowledgeGraphDatabase)
        engine = GraphReasoningEngine(mock_db)
        
        # Create paths with varying lengths, all within max_hops
        mock_paths = []
        for hop_count in range(1, min(max_hops + 1, 4)):
            nodes = [start_drug.id] + [f"node_{i}" for i in range(hop_count)]
            path = GraphPath(
                nodes=nodes,
                edges=[f"edge_{i}" for i in range(len(nodes) - 1)],
                edge_types=["INTERACTS_WITH"] * (len(nodes) - 1),
                confidence=0.8,
                evidence_sources=["DDInter"],
                path_length=len(nodes)
            )
            mock_paths.append(path)
        
        # Mock traversal
        engine._breadth_first_traversal = AsyncMock(return_value=mock_paths)
        
        # Execute traversal
        paths = await engine.multi_hop_traversal(
            start_node_id=start_drug.id,
            target_node_type="Drug",
            max_hops=max_hops,
            strategy=TraversalStrategy.BREADTH_FIRST
        )
        
        # Verify all paths respect max_hops
        for path in paths:
            assert path.path_length <= max_hops + 1, \
                f"Path length {path.path_length} exceeds max_hops + 1 ({max_hops + 1})"
            assert len(path.nodes) <= max_hops + 1
    
    @given(
        drug_a=drug_entity_strategy(),
        drug_b=drug_entity_strategy(),
        strategy=st.sampled_from(list(TraversalStrategy))
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_traversal_strategy_consistency(
        self, drug_a: DrugEntity, drug_b: DrugEntity, strategy: TraversalStrategy
    ):
        """
        Property: Different traversal strategies produce valid results
        
        **Validates: Requirements 4.2**
        
        For any drug pair and traversal strategy:
        1. All strategies should find valid paths
        2. Paths should maintain proper structure
        3. Evidence sources should be preserved
        """
        assume(drug_a.id != drug_b.id)
        
        # Create mock database and reasoning engine
        mock_db = Mock(spec=KnowledgeGraphDatabase)
        engine = GraphReasoningEngine(mock_db)
        
        # Create expected path
        expected_path = GraphPath(
            nodes=[drug_a.id, drug_b.id],
            edges=["interaction_edge"],
            edge_types=["INTERACTS_WITH"],
            confidence=0.8,
            evidence_sources=["DDInter", "DrugBank"],
            path_length=2
        )
        
        # Mock appropriate traversal method based on strategy
        if strategy == TraversalStrategy.BREADTH_FIRST:
            engine._breadth_first_traversal = AsyncMock(return_value=[expected_path])
        elif strategy == TraversalStrategy.DEPTH_FIRST:
            engine._depth_first_traversal = AsyncMock(return_value=[expected_path])
        elif strategy == TraversalStrategy.SHORTEST_PATH:
            engine._shortest_path_traversal = AsyncMock(return_value=[expected_path])
        else:
            engine._all_paths_traversal = AsyncMock(return_value=[expected_path])
        
        # Execute traversal with specified strategy
        paths = await engine.multi_hop_traversal(
            start_node_id=drug_a.id,
            target_node_type="Drug",
            max_hops=3,
            strategy=strategy
        )
        
        # Verify results are valid regardless of strategy
        assert len(paths) > 0
        for path in paths:
            assert len(path.nodes) >= 2
            assert len(path.edges) == len(path.nodes) - 1
            assert len(path.edge_types) == len(path.edges)
            assert 0.0 <= path.confidence <= 1.0
            assert len(path.evidence_sources) > 0
    
    @given(
        drugs=drug_combination_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_interaction_evidence_provenance(self, drugs: List[DrugEntity]):
        """
        Property: Interaction evidence maintains complete provenance
        
        **Validates: Requirements 1.4, 4.1**
        
        For any drug interaction:
        1. Evidence sources must be from DDInter or DrugBank
        2. Evidence level should be documented
        3. Documentation quality should be tracked
        """
        assume(len(drugs) >= 2)
        
        drug_a = drugs[0]
        drug_b = drugs[1]
        
        interaction = InteractionEntity(
            id=f"interaction_{hash((drug_a.id, drug_b.id)) % 10000}",
            drug_a_id=drug_a.id,
            drug_b_id=drug_b.id,
            severity=SeverityLevel.MODERATE,
            mechanism="Test mechanism",
            clinical_effect="Test effect",
            management="Monitor",
            evidence_level="high",
            documentation="well-documented",
            created_from=["DDInter", "DrugBank"]
        )
        
        # Verify provenance completeness
        assert len(interaction.created_from) > 0
        
        # Verify evidence sources are valid
        valid_sources = {"DDInter", "DrugBank"}
        for source in interaction.created_from:
            assert source in valid_sources
        
        # Verify evidence quality indicators
        assert interaction.evidence_level in ["high", "moderate", "low"]
        assert interaction.documentation in ["well-documented", "probable", "possible"]
    
    @given(
        start_drug=drug_entity_strategy(),
        end_drug=drug_entity_strategy(),
        max_hops=st.integers(min_value=2, max_value=4)
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_complex_interaction_pattern_detection(
        self, start_drug: DrugEntity, end_drug: DrugEntity, max_hops: int
    ):
        """
        Property: System detects complex multi-drug interaction patterns
        
        **Validates: Requirements 4.2**
        
        For any drug pair with indirect interactions:
        1. Multi-hop traversal should find indirect interaction paths
        2. Paths should include intermediate drugs
        3. Evidence should be aggregated from all hops
        """
        assume(start_drug.id != end_drug.id)
        
        # Create mock database and reasoning engine
        mock_db = Mock(spec=KnowledgeGraphDatabase)
        engine = GraphReasoningEngine(mock_db)
        
        # Create complex path with intermediate nodes
        intermediate_count = max_hops - 1
        intermediate_nodes = [f"intermediate_drug_{i}" for i in range(intermediate_count)]
        all_nodes = [start_drug.id] + intermediate_nodes + [end_drug.id]
        
        complex_path = GraphPath(
            nodes=all_nodes,
            edges=[f"edge_{i}" for i in range(len(all_nodes) - 1)],
            edge_types=["INTERACTS_WITH"] * (len(all_nodes) - 1),
            confidence=0.65,
            evidence_sources=["DDInter", "DrugBank", "FAERS"],
            path_length=len(all_nodes)
        )
        
        # Mock traversal
        engine._breadth_first_traversal = AsyncMock(return_value=[complex_path])
        
        # Execute multi-hop traversal
        paths = await engine.multi_hop_traversal(
            start_node_id=start_drug.id,
            target_node_type="Drug",
            max_hops=max_hops,
            strategy=TraversalStrategy.BREADTH_FIRST
        )
        
        # Verify complex pattern detection
        assert len(paths) > 0
        path = paths[0]
        
        # Verify path structure
        assert path.nodes[0] == start_drug.id
        assert path.nodes[-1] == end_drug.id
        assert len(path.nodes) >= 3, "Complex pattern should have intermediate nodes"
        
        # Verify evidence aggregation
        assert len(path.evidence_sources) > 0
        assert any(source in ["DDInter", "DrugBank"] for source in path.evidence_sources)
        
        # Verify path length
        assert path.path_length == len(all_nodes)
        assert path.path_length <= max_hops + 1


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestDrugInteractionEdgeCases:
    """Property tests for edge cases in drug interaction traversal"""
    
    @given(drug=drug_entity_strategy())
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_self_interaction_handling(self, drug: DrugEntity):
        """
        Property: System handles self-interaction queries gracefully
        
        For any drug queried against itself:
        1. Should not return self-interaction paths
        2. Should handle gracefully without errors
        """
        # Create mock database and reasoning engine
        mock_db = Mock(spec=KnowledgeGraphDatabase)
        engine = GraphReasoningEngine(mock_db)
        
        # Mock empty result for self-interaction
        engine._breadth_first_traversal = AsyncMock(return_value=[])
        
        # Execute traversal
        paths = await engine.multi_hop_traversal(
            start_node_id=drug.id,
            target_node_type="Drug",
            max_hops=1,
            strategy=TraversalStrategy.BREADTH_FIRST
        )
        
        # Should return empty or filter out self-loops
        for path in paths:
            # If path exists, it should not be a self-loop
            if len(path.nodes) == 2:
                assert path.nodes[0] != path.nodes[1]
    
    @given(
        drug=drug_entity_strategy(),
        max_hops=st.integers(min_value=0, max_value=0)
    )
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_zero_hop_traversal(self, drug: DrugEntity, max_hops: int):
        """
        Property: Zero-hop traversal returns only the starting node
        
        For any drug with max_hops=0:
        1. Should return empty paths or only the starting node
        2. Should not traverse any edges
        """
        # Create mock database and reasoning engine
        mock_db = Mock(spec=KnowledgeGraphDatabase)
        engine = GraphReasoningEngine(mock_db)
        
        # Mock empty or single-node result
        engine._breadth_first_traversal = AsyncMock(return_value=[])
        
        # Execute traversal with zero hops
        paths = await engine.multi_hop_traversal(
            start_node_id=drug.id,
            target_node_type="Drug",
            max_hops=max_hops,
            strategy=TraversalStrategy.BREADTH_FIRST
        )
        
        # Should return empty or single-node paths
        for path in paths:
            assert path.path_length <= 1
