"""
Property-based tests for entity resolution and conflict management

**Validates: Requirements 3.2, 3.3**

Property 8: Entity Resolution and Conflict Management
For any knowledge graph construction, the system should perform entity resolution to link
identical entities across datasets and use evidence weighting algorithms to resolve conflicts.
"""
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from hypothesis.strategies import composite
from typing import List, Dict, Any
import difflib

from src.data_processing.entity_resolution import (
    EntityResolutionService, EntityMatcher, EntityType, MatchingMethod,
    DrugNameNormalizer, SideEffectNormalizer, MatchCandidate, ResolutionResult
)
from src.knowledge_graph.models import EntityMapping


# ============================================================================
# Strategy Generators for Property-Based Testing
# ============================================================================

@composite
def drug_name_strategy(draw):
    """Generate realistic drug names with variations"""
    # Common drug name patterns
    prefixes = ["Lis", "Met", "Ator", "Sim", "Prav", "Ros", "Amlod", "Losar", "Valsar"]
    suffixes = ["pril", "formin", "vastatin", "ipine", "tan", "olol"]
    
    prefix = draw(st.sampled_from(prefixes))
    suffix = draw(st.sampled_from(suffixes))
    
    return prefix + suffix


@composite
def drug_entity_dict_strategy(draw, base_name: str = None, entity_id: str = None):
    """Generate drug entity dictionaries for resolution testing"""
    if base_name is None:
        base_name = draw(drug_name_strategy())
    
    if entity_id is None:
        entity_id = f"drug_{draw(st.integers(min_value=1, max_value=100000))}"
    
    # Generate variations of the same drug
    variations = [
        base_name,
        base_name.upper(),
        base_name.lower(),
        f"{base_name} HCl",
        f"{base_name} Hydrochloride",
        f"{base_name} 10mg",
        f"{base_name} Tablet",
        f"{base_name} (Brand)"
    ]
    
    name = draw(st.sampled_from(variations))
    
    # Generate identifiers (may or may not match)
    has_drugbank = draw(st.booleans())
    has_rxcui = draw(st.booleans())
    
    entity = {
        'id': entity_id,
        'name': name,
        'generic_name': base_name.lower(),
        'source_dataset': draw(st.sampled_from(['DrugBank', 'SIDER', 'OnSIDES', 'FAERS']))
    }
    
    if has_drugbank:
        entity['drugbank_id'] = f"DB{draw(st.integers(min_value=10000, max_value=99999))}"
    
    if has_rxcui:
        entity['rxcui'] = str(draw(st.integers(min_value=1000, max_value=999999)))
    
    return entity


@composite
def side_effect_entity_dict_strategy(draw, base_name: str = None, entity_id: str = None):
    """Generate side effect entity dictionaries for resolution testing"""
    side_effects = [
        "Headache", "Nausea", "Dizziness", "Fatigue", "Dry cough",
        "Muscle pain", "Insomnia", "Diarrhea", "Rash", "Weakness"
    ]
    
    if base_name is None:
        base_name = draw(st.sampled_from(side_effects))
    
    if entity_id is None:
        entity_id = f"se_{draw(st.integers(min_value=1, max_value=100000))}"
    
    # Generate variations
    variations = [
        base_name,
        base_name.upper(),
        base_name.lower(),
        f"Severe {base_name}",
        f"Mild {base_name}",
        f"Chronic {base_name}"
    ]
    
    name = draw(st.sampled_from(variations))
    
    entity = {
        'id': entity_id,
        'name': name,
        'source_dataset': draw(st.sampled_from(['SIDER', 'OnSIDES', 'FAERS']))
    }
    
    return entity


@composite
def matching_drug_entities_strategy(draw):
    """Generate a list of drug entities that should match"""
    base_name = draw(drug_name_strategy())
    count = draw(st.integers(min_value=2, max_value=5))
    
    entities = []
    for i in range(count):
        entity_id = f"drug_{draw(st.integers(min_value=1, max_value=100000))}_{i}"
        entity = draw(drug_entity_dict_strategy(base_name=base_name, entity_id=entity_id))
        entities.append(entity)
    
    return entities


@composite
def conflicting_drug_entities_strategy(draw):
    """Generate drug entities with potential conflicts"""
    base_name = draw(drug_name_strategy())
    
    # Create two entities with same name but different identifiers
    drugbank_id1 = f"DB{draw(st.integers(min_value=10000, max_value=99999))}"
    drugbank_id2 = f"DB{draw(st.integers(min_value=10000, max_value=99999))}"
    
    # Ensure they're different
    assume(drugbank_id1 != drugbank_id2)
    
    id1 = draw(st.integers(min_value=1, max_value=100000))
    id2 = draw(st.integers(min_value=1, max_value=100000))
    # Ensure unique IDs
    assume(id1 != id2)
    
    entity1 = {
        'id': f"drug_{id1}",
        'name': base_name,
        'generic_name': base_name.lower(),
        'drugbank_id': drugbank_id1,
        'source_dataset': 'DrugBank'
    }
    
    entity2 = {
        'id': f"drug_{id2}",
        'name': base_name,
        'generic_name': base_name.lower(),
        'drugbank_id': drugbank_id2,
        'source_dataset': 'SIDER'
    }
    
    return [entity1, entity2]


@composite
def mixed_entity_list_strategy(draw):
    """Generate a mixed list of matching and non-matching entities"""
    # Generate 2-3 groups of matching entities
    num_groups = draw(st.integers(min_value=2, max_value=3))
    
    all_entities = []
    base_id = draw(st.integers(min_value=1, max_value=10000))
    
    for group_idx in range(num_groups):
        base_name = draw(drug_name_strategy())
        group_size = draw(st.integers(min_value=2, max_value=3))
        
        for entity_idx in range(group_size):
            entity_id = f"drug_{base_id}_{group_idx}_{entity_idx}"
            entity = draw(drug_entity_dict_strategy(base_name=base_name, entity_id=entity_id))
            all_entities.append(entity)
    
    # Shuffle the list using hypothesis-compatible method
    return draw(st.permutations(all_entities))


# ============================================================================
# Property-Based Tests for Entity Resolution
# ============================================================================

class TestEntityResolutionProperties:
    """
    Property-based tests for entity resolution and conflict management
    
    **Validates: Requirements 3.2, 3.3**
    """
    
    @given(entities=matching_drug_entities_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_identical_entities_are_linked(self, entities: List[Dict[str, Any]]):
        """
        Property: Identical entities from different datasets are linked together
        
        **Validates: Requirement 3.2**
        
        For any set of entities representing the same drug across datasets,
        the entity resolution service should link them into a single canonical entity.
        """
        service = EntityResolutionService(confidence_threshold=0.7)
        
        # Resolve entities
        results = service.resolve_entities(entities, EntityType.DRUG)
        
        # Should create at least one group
        assert len(results) > 0, "Entity resolution should create at least one group"
        
        # All entities should be in the results
        total_resolved = sum(len(r.matched_entities) for r in results)
        assert total_resolved == len(entities), \
            f"All {len(entities)} entities should be resolved, but got {total_resolved}"
        
        # For matching entities, they should be grouped together
        # Note: Due to name variations (e.g., "Drug" vs "Drug HCl"), not all may match
        # But entities with identical or very similar names should be linked
        
        # Check if any entities have exact name matches
        names = [e['name'].lower() for e in entities]
        has_exact_duplicates = len(names) != len(set(names))
        
        if has_exact_duplicates:
            # If there are exact duplicate names, they should definitely be linked
            assert len(results) < len(entities), \
                "Entities with identical names should be linked together"
        
        # Verify each result has valid structure
        for result in results:
            assert result.canonical_id is not None
            assert len(result.matched_entities) > 0
            assert 0.0 <= result.confidence <= 1.0
    
    @given(base_name=drug_name_strategy())
    @settings(max_examples=100, deadline=None)
    def test_name_normalization_consistency(self, base_name: str):
        """
        Property: Name normalization produces consistent results
        
        **Validates: Requirement 3.2**
        
        For any drug name, normalization should be idempotent and consistent.
        """
        normalizer = DrugNameNormalizer()
        
        # Normalize the name
        normalized1 = normalizer.normalize(base_name)
        normalized2 = normalizer.normalize(base_name)
        
        # Should be consistent
        assert normalized1 == normalized2, \
            "Normalization should produce consistent results"
        
        # Normalizing the normalized name should be idempotent
        normalized3 = normalizer.normalize(normalized1)
        assert normalized1 == normalized3, \
            "Normalization should be idempotent"
        
        # Should handle variations consistently
        variations = [
            base_name.upper(),
            base_name.lower(),
            f"  {base_name}  ",  # Extra whitespace
        ]
        
        for variation in variations:
            norm_var = normalizer.normalize(variation)
            # All variations should normalize to similar forms
            similarity = difflib.SequenceMatcher(None, normalized1, norm_var).ratio()
            assert similarity >= 0.8, \
                f"Variations should normalize similarly: '{normalized1}' vs '{norm_var}'"
    
    @given(entities=conflicting_drug_entities_strategy())
    @settings(max_examples=100, deadline=None)
    def test_conflicts_are_detected(self, entities: List[Dict[str, Any]]):
        """
        Property: Conflicting information between datasets is detected
        
        **Validates: Requirement 3.3**
        
        For any entities with conflicting identifiers, the system should detect
        and report the conflicts.
        """
        service = EntityResolutionService(confidence_threshold=0.7)
        
        # Resolve entities
        results = service.resolve_entities(entities, EntityType.DRUG)
        
        # Should create groups
        assert len(results) > 0
        
        # Check if conflicts were detected
        total_conflicts = sum(len(r.conflicts) for r in results)
        
        # If entities have different DrugBank IDs but same name, conflicts should be detected
        drugbank_ids = set()
        for entity in entities:
            if 'drugbank_id' in entity:
                drugbank_ids.add(entity['drugbank_id'])
        
        if len(drugbank_ids) > 1:
            # We have conflicting DrugBank IDs
            assert total_conflicts > 0, \
                "Conflicting DrugBank IDs should be detected"
    
    @given(entities=mixed_entity_list_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_entity_groups_are_disjoint(self, entities: List[Dict[str, Any]]):
        """
        Property: Resolved entity groups are disjoint (no entity in multiple groups)
        
        **Validates: Requirement 3.2**
        
        For any set of entities, each entity should appear in exactly one resolution group.
        """
        service = EntityResolutionService(confidence_threshold=0.7)
        
        # Resolve entities
        results = service.resolve_entities(entities, EntityType.DRUG)
        
        # Collect all entity IDs from results
        seen_ids = set()
        for result in results:
            for entity in result.matched_entities:
                entity_id = entity['id']
                assert entity_id not in seen_ids, \
                    f"Entity {entity_id} appears in multiple groups"
                seen_ids.add(entity_id)
        
        # All original entities should be accounted for
        original_ids = {e['id'] for e in entities}
        assert seen_ids == original_ids, \
            "All entities should be in exactly one group"
    
    @given(entities=matching_drug_entities_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_canonical_entity_selection_is_deterministic(self, entities: List[Dict[str, Any]]):
        """
        Property: Canonical entity selection is deterministic
        
        **Validates: Requirement 3.3**
        
        For any set of matching entities, selecting the canonical entity multiple times
        should produce the same result.
        """
        service = EntityResolutionService(confidence_threshold=0.7)
        
        # Select canonical entity multiple times
        canonical1 = service._select_canonical_entity(entities)
        canonical2 = service._select_canonical_entity(entities)
        
        # Should be the same entity
        assert canonical1['id'] == canonical2['id'], \
            "Canonical entity selection should be deterministic"
    
    @given(entities=matching_drug_entities_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_evidence_weighting_prioritizes_authoritative_sources(self, entities: List[Dict[str, Any]]):
        """
        Property: Evidence weighting prioritizes more authoritative sources
        
        **Validates: Requirement 3.3**
        
        For any set of matching entities, the canonical entity should be selected
        from the most authoritative source when available.
        """
        # Add DrugBank entity (most authoritative)
        drugbank_entity = entities[0].copy()
        drugbank_entity['source_dataset'] = 'DrugBank'
        drugbank_entity['drugbank_id'] = 'DB12345'
        drugbank_entity['mechanism'] = 'Test mechanism'
        drugbank_entity['indications'] = ['hypertension', 'heart failure']
        
        # Add less authoritative entity
        faers_entity = entities[1].copy() if len(entities) > 1 else entities[0].copy()
        faers_entity['source_dataset'] = 'FAERS'
        faers_entity['id'] = f"drug_{hash(faers_entity['name']) % 100000}"
        
        test_entities = [drugbank_entity, faers_entity]
        
        service = EntityResolutionService(confidence_threshold=0.7)
        
        # Select canonical entity
        canonical = service._select_canonical_entity(test_entities)
        
        # Should prefer DrugBank entity due to higher authority
        assert canonical['source_dataset'] == 'DrugBank', \
            "Should prioritize DrugBank as most authoritative source"
    
    @given(
        name1=drug_name_strategy(),
        name2=drug_name_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_matching_confidence_is_bounded(self, name1: str, name2: str):
        """
        Property: Matching confidence scores are always in [0, 1]
        
        **Validates: Requirement 3.2**
        
        For any two entity names, the matching confidence should be between 0 and 1.
        """
        matcher = EntityMatcher()
        
        # Test exact match
        exact_score = matcher.exact_match(name1, name2, EntityType.DRUG)
        assert 0.0 <= exact_score <= 1.0, \
            f"Exact match score {exact_score} is out of bounds"
        
        # Test fuzzy match
        fuzzy_score = matcher.fuzzy_match(name1, name2, EntityType.DRUG)
        assert 0.0 <= fuzzy_score <= 1.0, \
            f"Fuzzy match score {fuzzy_score} is out of bounds"
        
        # Test composite match
        composite_score, evidence = matcher.composite_match(name1, name2, EntityType.DRUG)
        assert 0.0 <= composite_score <= 1.0, \
            f"Composite match score {composite_score} is out of bounds"
        
        # All evidence scores should also be bounded
        for key, value in evidence.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                assert 0.0 <= value <= 1.0, \
                    f"Evidence score {key}={value} is out of bounds"
    
    @given(entities=matching_drug_entities_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_resolution_preserves_all_entity_data(self, entities: List[Dict[str, Any]]):
        """
        Property: Entity resolution preserves all original entity data
        
        **Validates: Requirement 3.2**
        
        For any set of entities, resolution should preserve all entities in the results,
        not lose any data.
        """
        service = EntityResolutionService(confidence_threshold=0.7)
        
        # Resolve entities
        results = service.resolve_entities(entities, EntityType.DRUG)
        
        # Collect all entities from results
        resolved_entities = []
        for result in results:
            resolved_entities.extend(result.matched_entities)
        
        # Should have same number of entities
        assert len(resolved_entities) == len(entities), \
            "Resolution should preserve all entities"
        
        # All original entity IDs should be present
        original_ids = {e['id'] for e in entities}
        resolved_ids = {e['id'] for e in resolved_entities}
        assert original_ids == resolved_ids, \
            "All original entity IDs should be preserved"
    
    @given(entities=matching_drug_entities_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_entity_mappings_maintain_referential_integrity(self, entities: List[Dict[str, Any]]):
        """
        Property: Entity mappings maintain referential integrity
        
        **Validates: Requirement 3.2**
        
        For any resolution results, the created entity mappings should correctly
        reference both source and canonical entities.
        """
        service = EntityResolutionService(confidence_threshold=0.7)
        
        # Resolve entities
        results = service.resolve_entities(entities, EntityType.DRUG)
        
        # Create mappings
        mappings = service.create_entity_mappings(results, EntityType.DRUG)
        
        # Should have one mapping per entity
        assert len(mappings) == len(entities), \
            "Should create one mapping per entity"
        
        # Each mapping should reference a valid canonical ID
        canonical_ids = {r.canonical_id for r in results}
        for mapping in mappings:
            assert mapping.canonical_id in canonical_ids, \
                f"Mapping references invalid canonical ID: {mapping.canonical_id}"
            
            # Source ID should be from original entities
            original_ids = {e['id'] for e in entities}
            assert mapping.source_id in original_ids, \
                f"Mapping references invalid source ID: {mapping.source_id}"
            
            # Confidence should be bounded
            assert 0.0 <= mapping.confidence <= 1.0, \
                f"Mapping confidence {mapping.confidence} is out of bounds"
    
    @given(entities=mixed_entity_list_strategy())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_resolution_statistics_are_consistent(self, entities: List[Dict[str, Any]]):
        """
        Property: Resolution statistics are mathematically consistent
        
        **Validates: Requirements 3.2, 3.3**
        
        For any resolution results, the statistics should be internally consistent.
        """
        service = EntityResolutionService(confidence_threshold=0.7)
        
        # Resolve entities
        results = service.resolve_entities(entities, EntityType.DRUG)
        
        # Get statistics
        stats = service.get_resolution_stats(results)
        
        # Verify consistency
        assert stats['total_entities'] == len(entities), \
            "Total entities should match input"
        
        assert stats['total_groups'] == len(results), \
            "Total groups should match results"
        
        assert stats['entities_merged'] == stats['total_entities'] - stats['total_groups'], \
            "Entities merged calculation should be correct"
        
        if stats['total_entities'] > 0:
            expected_merge_rate = stats['entities_merged'] / stats['total_entities']
            assert abs(stats['merge_rate'] - expected_merge_rate) < 0.001, \
                "Merge rate calculation should be correct"
        
        assert 0.0 <= stats['average_confidence'] <= 1.0, \
            "Average confidence should be bounded"
        
        assert stats['high_confidence_groups'] + stats['low_confidence_groups'] <= stats['total_groups'], \
            "Confidence group counts should not exceed total groups"


# ============================================================================
# Property Tests for Side Effect Resolution
# ============================================================================

class TestSideEffectResolutionProperties:
    """Property tests specific to side effect entity resolution"""
    
    @given(base_name=st.sampled_from(["Headache", "Nausea", "Dizziness", "Fatigue"]))
    @settings(max_examples=100, deadline=None)
    def test_side_effect_normalization_handles_severity_prefixes(self, base_name: str):
        """
        Property: Side effect normalization handles severity prefixes consistently
        
        **Validates: Requirement 3.2**
        
        For any side effect name with severity prefixes, normalization should
        extract the core side effect.
        """
        normalizer = SideEffectNormalizer()
        
        # Test with different severity prefixes
        variations = [
            base_name,
            f"Severe {base_name}",
            f"Mild {base_name}",
            f"Moderate {base_name}",
            f"Acute {base_name}",
            f"Chronic {base_name}"
        ]
        
        normalized_forms = [normalizer.normalize(v) for v in variations]
        
        # All should normalize to similar forms (removing severity prefixes)
        base_normalized = normalizer.normalize(base_name)
        for norm in normalized_forms:
            # Should be similar to base (severity prefix removed)
            similarity = difflib.SequenceMatcher(None, base_normalized, norm).ratio()
            assert similarity >= 0.7, \
                f"Severity variations should normalize similarly: '{base_normalized}' vs '{norm}'"
    
    @given(base_name=st.sampled_from(["Headache", "Nausea", "Dizziness", "Fatigue"]))
    @settings(max_examples=100, deadline=None)
    def test_side_effect_resolution_maintains_consistency(self, base_name: str):
        """
        Property: Side effect resolution maintains consistency
        
        **Validates: Requirement 3.2**
        
        For any set of side effect entities, resolution should produce consistent groups.
        """
        service = EntityResolutionService(confidence_threshold=0.7)
        
        # Create entities with unique IDs
        entities = []
        for i in range(3):
            entity_id = f"se_{base_name}_{i}"
            entity = {
                'id': entity_id,
                'name': base_name if i == 0 else f"Severe {base_name}",
                'source_dataset': ['SIDER', 'OnSIDES', 'FAERS'][i]
            }
            entities.append(entity)
        
        # Resolve entities
        results = service.resolve_entities(entities, EntityType.SIDE_EFFECT)
        
        # Should create at least one group
        assert len(results) > 0
        
        # All entities should be accounted for
        total_resolved = sum(len(r.matched_entities) for r in results)
        assert total_resolved == len(entities)
        
        # Each result should have valid structure
        for result in results:
            assert result.canonical_id is not None
            assert len(result.matched_entities) > 0
            assert 0.0 <= result.confidence <= 1.0


# ============================================================================
# Integration Property Tests
# ============================================================================

class TestEntityResolutionIntegration:
    """Integration property tests for entity resolution with database operations"""
    
    @given(entities=matching_drug_entities_strategy())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_resolution_to_mapping_round_trip(self, entities: List[Dict[str, Any]]):
        """
        Property: Resolution to mapping conversion maintains data integrity
        
        **Validates: Requirements 3.2, 3.3**
        
        For any resolution results, converting to entity mappings and back
        should preserve all essential information.
        """
        service = EntityResolutionService(confidence_threshold=0.7)
        
        # Resolve entities
        results = service.resolve_entities(entities, EntityType.DRUG)
        
        # Create mappings
        mappings = service.create_entity_mappings(results, EntityType.DRUG)
        
        # Verify mappings preserve resolution information
        for result in results:
            # Find mappings for this result
            result_mappings = [m for m in mappings if m.canonical_id == result.canonical_id]
            
            # Should have one mapping per entity in the group
            assert len(result_mappings) == len(result.matched_entities), \
                "Should have one mapping per matched entity"
            
            # All mappings should have same canonical ID
            canonical_ids = {m.canonical_id for m in result_mappings}
            assert len(canonical_ids) == 1, \
                "All mappings in group should have same canonical ID"
            
            # Mappings should reference all entities in the group
            mapped_source_ids = {m.source_id for m in result_mappings}
            entity_ids = {e['id'] for e in result.matched_entities}
            assert mapped_source_ids == entity_ids, \
                "Mappings should reference all entities in the group"
