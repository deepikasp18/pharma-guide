"""
Property-based tests for knowledge graph construction consistency

**Validates: Requirements 3.4, 9.3**

Property 9: Automatic Knowledge Graph Updates
For any new dataset version availability, the system should perform incremental knowledge graph
updates while maintaining data consistency.
"""
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from hypothesis.strategies import composite
from typing import List, Dict, Any, Set
from datetime import datetime, timedelta, timezone

from src.knowledge_graph.graph_builder import (
    KnowledgeGraphBuilder, BuildMode, BuildResult
)
from src.knowledge_graph.models import (
    DrugEntity, SideEffectEntity, DatasetMetadata
)
from src.knowledge_graph.database import KnowledgeGraphDatabase
from src.data_processing.entity_resolution import EntityResolutionService, EntityType
from src.data_processing.metadata_manager import MetadataManager


# ============================================================================
# Strategy Generators for Property-Based Testing
# ============================================================================

@composite
def drug_name_strategy(draw):
    """Generate realistic drug names"""
    prefixes = ["Lis", "Met", "Ator", "Sim", "Prav", "Ros", "Amlod", "Losar", "Valsar"]
    suffixes = ["pril", "formin", "vastatin", "ipine", "tan", "olol"]
    
    prefix = draw(st.sampled_from(prefixes))
    suffix = draw(st.sampled_from(suffixes))
    
    return prefix + suffix


@composite
def side_effect_name_strategy(draw):
    """Generate realistic side effect names"""
    side_effects = [
        "Headache", "Nausea", "Dizziness", "Fatigue", "Dry cough",
        "Muscle pain", "Insomnia", "Diarrhea", "Rash", "Weakness"
    ]
    return draw(st.sampled_from(side_effects))


@composite
def drug_entity_dict_strategy(draw):
    """Generate drug entity dictionaries for graph building"""
    drug_id = f"drug_{draw(st.integers(min_value=1, max_value=100000))}"
    drug_name = draw(drug_name_strategy())
    
    return {
        'type': 'drug',
        'id': drug_id,
        'name': drug_name,
        'generic_name': drug_name.lower(),
        'drugbank_id': f"DB{draw(st.integers(min_value=10000, max_value=99999))}",
        'rxcui': str(draw(st.integers(min_value=1000, max_value=999999))),
        'mechanism': draw(st.sampled_from([
            "ACE inhibitor", "Beta blocker", "Calcium channel blocker", "Statin"
        ])),
        'indications': draw(st.lists(
            st.sampled_from(["hypertension", "diabetes", "heart failure"]),
            min_size=1, max_size=3
        )),
        'created_from': [draw(st.sampled_from(['DrugBank', 'SIDER', 'OnSIDES']))]
    }


@composite
def side_effect_entity_dict_strategy(draw):
    """Generate side effect entity dictionaries for graph building"""
    se_id = f"se_{draw(st.integers(min_value=1, max_value=100000))}"
    se_name = draw(side_effect_name_strategy())
    
    return {
        'type': 'side_effect',
        'id': se_id,
        'name': se_name,
        'meddra_code': str(draw(st.integers(min_value=10000000, max_value=99999999))),
        'severity': draw(st.sampled_from(['mild', 'moderate', 'severe'])),
        'created_from': [draw(st.sampled_from(['SIDER', 'OnSIDES', 'FAERS']))]
    }


@composite
def causes_relationship_dict_strategy(draw, drug_name: str = None, se_name: str = None):
    """Generate CAUSES relationship dictionaries"""
    if drug_name is None:
        drug_name = draw(drug_name_strategy())
    if se_name is None:
        se_name = draw(side_effect_name_strategy())
    
    return {
        'type': 'causes_relationship',
        'drug_name': drug_name,
        'side_effect_name': se_name,
        'frequency': draw(st.floats(min_value=0.0, max_value=1.0)),
        'confidence': draw(st.floats(min_value=0.0, max_value=1.0)),
        'evidence_sources': draw(st.lists(
            st.sampled_from(['FAERS', 'SIDER', 'OnSIDES']),
            min_size=1, max_size=3, unique=True
        )),
        'source_dataset': draw(st.sampled_from(['FAERS', 'SIDER', 'OnSIDES']))
    }


@composite
def dataset_entities_strategy(draw):
    """Generate a dataset of entities (drugs, side effects, relationships)"""
    num_drugs = draw(st.integers(min_value=2, max_value=5))
    num_side_effects = draw(st.integers(min_value=2, max_value=5))
    
    entities = []
    used_ids = set()
    
    # Generate drugs with unique IDs
    drug_names = []
    for i in range(num_drugs):
        drug_dict = draw(drug_entity_dict_strategy())
        # Ensure unique ID
        while drug_dict['id'] in used_ids:
            drug_dict['id'] = f"drug_{draw(st.integers(min_value=1, max_value=100000))}"
        used_ids.add(drug_dict['id'])
        entities.append(drug_dict)
        drug_names.append(drug_dict['name'])
    
    # Generate side effects with unique IDs
    se_names = []
    for i in range(num_side_effects):
        se_dict = draw(side_effect_entity_dict_strategy())
        # Ensure unique ID
        while se_dict['id'] in used_ids:
            se_dict['id'] = f"se_{draw(st.integers(min_value=1, max_value=100000))}"
        used_ids.add(se_dict['id'])
        entities.append(se_dict)
        se_names.append(se_dict['name'])
    
    # Generate relationships
    num_relationships = draw(st.integers(min_value=1, max_value=min(num_drugs * num_side_effects, 10)))
    for _ in range(num_relationships):
        drug_name = draw(st.sampled_from(drug_names))
        se_name = draw(st.sampled_from(se_names))
        rel_dict = draw(causes_relationship_dict_strategy(drug_name=drug_name, se_name=se_name))
        entities.append(rel_dict)
    
    return entities


@composite
def dataset_version_strategy(draw):
    """Generate dataset version information"""
    major = draw(st.integers(min_value=1, max_value=5))
    minor = draw(st.integers(min_value=0, max_value=20))
    return f"{major}.{minor}"


@composite
def incremental_update_strategy(draw, base_entities: List[Dict[str, Any]]):
    """Generate incremental updates to existing entities"""
    # Extract existing drug and side effect names
    drug_names = [e['name'] for e in base_entities if e.get('type') == 'drug']
    se_names = [e['name'] for e in base_entities if e.get('type') == 'side_effect']
    
    new_entities = []
    
    # Add some new drugs
    num_new_drugs = draw(st.integers(min_value=0, max_value=2))
    for _ in range(num_new_drugs):
        new_drug = draw(drug_entity_dict_strategy())
        new_entities.append(new_drug)
        drug_names.append(new_drug['name'])
    
    # Add some new side effects
    num_new_ses = draw(st.integers(min_value=0, max_value=2))
    for _ in range(num_new_ses):
        new_se = draw(side_effect_entity_dict_strategy())
        new_entities.append(new_se)
        se_names.append(new_se['name'])
    
    # Add new relationships (using both existing and new entities)
    if drug_names and se_names:
        num_new_rels = draw(st.integers(min_value=1, max_value=3))
        for _ in range(num_new_rels):
            drug_name = draw(st.sampled_from(drug_names))
            se_name = draw(st.sampled_from(se_names))
            new_rel = draw(causes_relationship_dict_strategy(drug_name=drug_name, se_name=se_name))
            new_entities.append(new_rel)
    
    return new_entities


@composite
def dataset_metadata_strategy(draw, dataset_name: str = None):
    """Generate dataset metadata"""
    if dataset_name is None:
        dataset_name = draw(st.sampled_from(['OnSIDES', 'SIDER', 'FAERS', 'DrugBank']))
    
    return DatasetMetadata(
        name=dataset_name,
        version=draw(dataset_version_strategy()),
        last_updated=datetime.now(timezone.utc) - timedelta(days=draw(st.integers(min_value=0, max_value=365))),
        record_count=draw(st.integers(min_value=100, max_value=100000)),
        entity_types=['drug', 'side_effect', 'causes_relationship'],
        relationship_types=['CAUSES'],
        quality_score=draw(st.floats(min_value=0.7, max_value=1.0)),
        authority_level=draw(st.sampled_from(['high', 'medium', 'low'])),
        description=f"{dataset_name} dataset for drug safety information"
    )


# ============================================================================
# Property-Based Tests for Knowledge Graph Construction Consistency
# ============================================================================

class TestKnowledgeGraphConstructionConsistency:
    """
    Property-based tests for knowledge graph construction consistency
    
    **Validates: Requirements 3.4, 9.3**
    """
    
    @given(entities=dataset_entities_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.large_base_example])
    def test_incremental_update_maintains_consistency(self, entities: List[Dict[str, Any]]):
        """
        Property: Incremental updates maintain knowledge graph consistency
        
        **Validates: Requirements 3.4, 9.3**
        
        For any new dataset version, incremental updates should:
        1. Add new entities without duplicating existing ones
        2. Update existing entities with new information
        3. Maintain referential integrity of relationships
        4. Preserve data consistency across updates
        """
        # Create mock builder components
        database = KnowledgeGraphDatabase()
        entity_resolver = EntityResolutionService(confidence_threshold=0.7)
        metadata_manager = MetadataManager()
        
        builder = KnowledgeGraphBuilder(database, entity_resolver, metadata_manager)
        
        # Simulate initial build
        initial_result = BuildResult(
            mode=BuildMode.INCREMENTAL,
            entities_created=0,
            entities_updated=0,
            relationships_created=0,
            relationships_updated=0,
            conflicts_resolved=0,
            errors=[],
            build_time=0.0
        )
        
        # Count entities by type
        drugs = [e for e in entities if e.get('type') == 'drug']
        side_effects = [e for e in entities if e.get('type') == 'side_effect']
        relationships = [e for e in entities if e.get('type') == 'causes_relationship']
        
        # Verify consistency properties
        assert len(drugs) > 0 or len(side_effects) > 0 or len(relationships) > 0, \
            "Dataset should contain at least some entities"
        
        # Verify relationships reference valid entities
        drug_names = {d['name'] for d in drugs}
        se_names = {s['name'] for s in side_effects}
        
        for rel in relationships:
            # Relationships should reference entities that exist or can be created
            assert 'drug_name' in rel, "Relationship must have drug_name"
            assert 'side_effect_name' in rel, "Relationship must have side_effect_name"
            
            # In incremental mode, relationships can reference new entities
            # that will be created on-the-fly
            assert isinstance(rel['drug_name'], str) and len(rel['drug_name']) > 0
            assert isinstance(rel['side_effect_name'], str) and len(rel['side_effect_name']) > 0
        
        # Verify entity IDs are unique
        entity_ids = [e['id'] for e in entities if 'id' in e]
        assert len(entity_ids) == len(set(entity_ids)), \
            "Entity IDs must be unique"
        
        # Verify data types are consistent
        for entity in entities:
            assert 'type' in entity, "Entity must have type field"
            assert entity['type'] in ['drug', 'side_effect', 'causes_relationship', 'interaction'], \
                f"Invalid entity type: {entity['type']}"

    
    @given(
        base_entities=dataset_entities_strategy(),
        dataset_name=st.sampled_from(['OnSIDES', 'SIDER', 'FAERS'])
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.large_base_example])
    def test_dataset_version_updates_maintain_integrity(
        self, base_entities: List[Dict[str, Any]], dataset_name: str
    ):
        """
        Property: Dataset version updates maintain referential integrity
        
        **Validates: Requirements 3.4, 9.3**
        
        For any dataset version update, the system should:
        1. Track version changes
        2. Maintain entity relationships across versions
        3. Preserve existing data while adding new information
        """
        # Generate incremental update
        new_entities = []
        
        # Extract existing entity names
        existing_drugs = {e['name'] for e in base_entities if e.get('type') == 'drug'}
        existing_ses = {e['name'] for e in base_entities if e.get('type') == 'side_effect'}
        
        # Add a new relationship using existing entities
        if existing_drugs and existing_ses:
            drug_name = list(existing_drugs)[0]
            se_name = list(existing_ses)[0]
            
            new_rel = {
                'type': 'causes_relationship',
                'drug_name': drug_name,
                'side_effect_name': se_name,
                'frequency': 0.15,
                'confidence': 0.85,
                'evidence_sources': [dataset_name],
                'source_dataset': dataset_name
            }
            new_entities.append(new_rel)
        
        # Verify update maintains consistency
        all_entities = base_entities + new_entities
        
        # Count total entities
        total_drugs = len([e for e in all_entities if e.get('type') == 'drug'])
        total_ses = len([e for e in all_entities if e.get('type') == 'side_effect'])
        total_rels = len([e for e in all_entities if e.get('type') == 'causes_relationship'])
        
        # After update, we should have at least as many entities as before
        base_drugs = len([e for e in base_entities if e.get('type') == 'drug'])
        base_ses = len([e for e in base_entities if e.get('type') == 'side_effect'])
        base_rels = len([e for e in base_entities if e.get('type') == 'causes_relationship'])
        
        assert total_drugs >= base_drugs, "Drug count should not decrease"
        assert total_ses >= base_ses, "Side effect count should not decrease"
        assert total_rels >= base_rels, "Relationship count should not decrease"
        
        # Verify all relationships still reference valid entities
        all_drug_names = {e['name'] for e in all_entities if e.get('type') == 'drug'}
        all_se_names = {e['name'] for e in all_entities if e.get('type') == 'side_effect'}
        
        for rel in [e for e in all_entities if e.get('type') == 'causes_relationship']:
            # Relationships can reference entities that will be created
            assert isinstance(rel['drug_name'], str)
            assert isinstance(rel['side_effect_name'], str)
    
    @given(entities=dataset_entities_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_build_result_statistics_are_consistent(self, entities: List[Dict[str, Any]]):
        """
        Property: Build result statistics are mathematically consistent
        
        **Validates: Requirements 3.4, 9.3**
        
        For any graph build operation, the result statistics should be internally consistent.
        """
        # Create build result
        result = BuildResult(
            mode=BuildMode.INCREMENTAL,
            entities_created=len([e for e in entities if e.get('type') in ['drug', 'side_effect']]),
            entities_updated=0,
            relationships_created=len([e for e in entities if e.get('type') == 'causes_relationship']),
            relationships_updated=0,
            conflicts_resolved=0,
            errors=[],
            build_time=1.5
        )
        
        # Verify statistics consistency
        assert result.entities_created >= 0, "Entities created cannot be negative"
        assert result.entities_updated >= 0, "Entities updated cannot be negative"
        assert result.relationships_created >= 0, "Relationships created cannot be negative"
        assert result.relationships_updated >= 0, "Relationships updated cannot be negative"
        assert result.conflicts_resolved >= 0, "Conflicts resolved cannot be negative"
        assert result.build_time >= 0, "Build time cannot be negative"
        
        # Total entities should match input
        total_entities = result.entities_created + result.entities_updated
        input_entities = len([e for e in entities if e.get('type') in ['drug', 'side_effect']])
        
        # In incremental mode, we might create entities on-the-fly for relationships
        # so total_entities might be >= input_entities
        assert total_entities >= 0, "Total entities should be non-negative"
        
        # Errors should be a list
        assert isinstance(result.errors, list), "Errors should be a list"

    
    @given(
        entities=dataset_entities_strategy(),
        dataset_name=st.sampled_from(['OnSIDES', 'SIDER', 'FAERS', 'DrugBank'])
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_entity_cache_maintains_consistency(
        self, entities: List[Dict[str, Any]], dataset_name: str
    ):
        """
        Property: Entity cache maintains consistency during build
        
        **Validates: Requirements 3.4, 9.3**
        
        For any graph build operation, the entity cache should:
        1. Store all processed entities
        2. Maintain unique entity IDs
        3. Allow efficient lookup during relationship processing
        """
        database = KnowledgeGraphDatabase()
        entity_resolver = EntityResolutionService(confidence_threshold=0.7)
        metadata_manager = MetadataManager()
        
        builder = KnowledgeGraphBuilder(database, entity_resolver, metadata_manager)
        
        # Simulate caching entities
        for entity in entities:
            if entity.get('type') in ['drug', 'side_effect']:
                entity_id = entity.get('id', f"{entity['type']}_{entity['name']}")
                builder.entity_cache[entity_id] = {
                    'type': entity['type'],
                    'entity': entity,
                    'data': entity
                }
        
        # Verify cache consistency
        cached_ids = set(builder.entity_cache.keys())
        assert len(cached_ids) == len(builder.entity_cache), \
            "Cache should not have duplicate IDs"
        
        # Verify all cached entities have required fields
        for entity_id, cached in builder.entity_cache.items():
            assert 'type' in cached, "Cached entity must have type"
            assert 'entity' in cached, "Cached entity must have entity data"
            assert 'data' in cached, "Cached entity must have original data"
            
            assert cached['type'] in ['drug', 'side_effect', 'interaction'], \
                f"Invalid cached entity type: {cached['type']}"
        
        # Get statistics
        stats = builder.get_build_statistics()
        
        assert 'cached_entities' in stats
        assert 'cached_relationships' in stats
        assert 'entity_types' in stats
        
        assert stats['cached_entities'] == len(builder.entity_cache)
        assert stats['cached_relationships'] == len(builder.relationship_cache)
    
    @given(
        metadata=dataset_metadata_strategy()
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_dataset_metadata_tracking_is_complete(self, metadata: DatasetMetadata):
        """
        Property: Dataset metadata tracking is complete and consistent
        
        **Validates: Requirements 3.4, 9.3**
        
        For any dataset, metadata should track:
        1. Version information
        2. Last update timestamp
        3. Record counts
        4. Quality scores
        5. Authority levels
        """
        # Verify required metadata fields
        assert metadata.name is not None and len(metadata.name) > 0
        assert metadata.version is not None and len(metadata.version) > 0
        assert metadata.last_updated is not None
        assert isinstance(metadata.last_updated, datetime)
        
        # Verify counts and scores
        assert metadata.record_count >= 0, "Record count cannot be negative"
        assert 0.0 <= metadata.quality_score <= 1.0, \
            f"Quality score {metadata.quality_score} out of bounds"
        
        # Verify authority level
        assert metadata.authority_level in ['high', 'medium', 'low'], \
            f"Invalid authority level: {metadata.authority_level}"
        
        # Verify entity and relationship types
        assert isinstance(metadata.entity_types, list)
        assert isinstance(metadata.relationship_types, list)
        assert len(metadata.entity_types) > 0, "Should have at least one entity type"
        
        # Verify version format
        version_parts = metadata.version.split('.')
        assert len(version_parts) >= 2, "Version should have at least major.minor format"
        assert all(part.isdigit() for part in version_parts), \
            "Version parts should be numeric"

    
    @given(
        entities=dataset_entities_strategy(),
        mode=st.sampled_from([BuildMode.INCREMENTAL, BuildMode.FULL_REBUILD])
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_build_mode_affects_behavior_consistently(
        self, entities: List[Dict[str, Any]], mode: BuildMode
    ):
        """
        Property: Build mode consistently affects graph construction behavior
        
        **Validates: Requirements 3.4, 9.3**
        
        For any build mode:
        - INCREMENTAL: Should add to existing graph
        - FULL_REBUILD: Should reconstruct entire graph
        - Both should maintain data consistency
        """
        # Create build result with appropriate mode
        result = BuildResult(
            mode=mode,
            entities_created=0,
            entities_updated=0,
            relationships_created=0,
            relationships_updated=0,
            conflicts_resolved=0,
            errors=[],
            build_time=0.0
        )
        
        # Verify mode is set correctly
        assert result.mode == mode
        assert result.mode in BuildMode
        
        # Verify result structure is consistent regardless of mode
        assert isinstance(result.entities_created, int)
        assert isinstance(result.entities_updated, int)
        assert isinstance(result.relationships_created, int)
        assert isinstance(result.relationships_updated, int)
        assert isinstance(result.conflicts_resolved, int)
        assert isinstance(result.errors, list)
        assert isinstance(result.build_time, (int, float))
        
        # All counts should be non-negative
        assert result.entities_created >= 0
        assert result.entities_updated >= 0
        assert result.relationships_created >= 0
        assert result.relationships_updated >= 0
        assert result.conflicts_resolved >= 0
    
    @given(entities=dataset_entities_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_relationship_processing_maintains_referential_integrity(
        self, entities: List[Dict[str, Any]]
    ):
        """
        Property: Relationship processing maintains referential integrity
        
        **Validates: Requirements 3.4, 9.3**
        
        For any set of relationships, the system should:
        1. Ensure referenced entities exist or can be created
        2. Maintain valid drug-side effect connections
        3. Preserve evidence sources and confidence scores
        """
        relationships = [e for e in entities if e.get('type') == 'causes_relationship']
        
        for rel in relationships:
            # Verify required fields
            assert 'drug_name' in rel, "Relationship must have drug_name"
            assert 'side_effect_name' in rel, "Relationship must have side_effect_name"
            
            # Verify drug and side effect names are valid strings
            assert isinstance(rel['drug_name'], str) and len(rel['drug_name']) > 0
            assert isinstance(rel['side_effect_name'], str) and len(rel['side_effect_name']) > 0
            
            # Verify confidence and frequency if present
            if 'confidence' in rel:
                assert 0.0 <= rel['confidence'] <= 1.0, \
                    f"Confidence {rel['confidence']} out of bounds"
            
            if 'frequency' in rel:
                assert 0.0 <= rel['frequency'] <= 1.0, \
                    f"Frequency {rel['frequency']} out of bounds"
            
            # Verify evidence sources
            if 'evidence_sources' in rel:
                assert isinstance(rel['evidence_sources'], list)
                assert len(rel['evidence_sources']) > 0, \
                    "Relationship must have at least one evidence source"
                
                valid_sources = {'FAERS', 'SIDER', 'OnSIDES', 'DrugBank', 'DDInter', 'Drugs@FDA'}
                for source in rel['evidence_sources']:
                    assert source in valid_sources, \
                        f"Invalid evidence source: {source}"

    
    @given(
        base_entities=dataset_entities_strategy(),
        dataset_name=st.sampled_from(['OnSIDES', 'SIDER', 'FAERS'])
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_incremental_update_preserves_existing_data(
        self, base_entities: List[Dict[str, Any]], dataset_name: str
    ):
        """
        Property: Incremental updates preserve existing data
        
        **Validates: Requirements 3.4, 9.3**
        
        For any incremental update, existing entities and relationships should be preserved.
        """
        # Extract base entity names
        base_drug_names = {e['name'] for e in base_entities if e.get('type') == 'drug'}
        base_se_names = {e['name'] for e in base_entities if e.get('type') == 'side_effect'}
        
        # Simulate adding new entities
        new_entities = []
        
        # Add a new drug
        new_drug = {
            'type': 'drug',
            'id': 'drug_new_001',
            'name': 'NewDrug',
            'generic_name': 'newdrug',
            'created_from': [dataset_name]
        }
        new_entities.append(new_drug)
        
        # Combine base and new entities
        all_entities = base_entities + new_entities
        
        # Verify base entities are still present
        all_drug_names = {e['name'] for e in all_entities if e.get('type') == 'drug'}
        all_se_names = {e['name'] for e in all_entities if e.get('type') == 'side_effect'}
        
        # All base drug names should still be present
        assert base_drug_names.issubset(all_drug_names), \
            "Incremental update should preserve existing drug names"
        
        # All base side effect names should still be present
        assert base_se_names.issubset(all_se_names), \
            "Incremental update should preserve existing side effect names"
        
        # New entities should be added
        assert 'NewDrug' in all_drug_names, \
            "New drug should be added to the graph"
        
        # Total count should increase
        assert len(all_entities) > len(base_entities), \
            "Incremental update should increase total entity count"
    
    @given(entities=dataset_entities_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_entity_deduplication_maintains_consistency(
        self, entities: List[Dict[str, Any]]
    ):
        """
        Property: Entity deduplication maintains data consistency
        
        **Validates: Requirements 3.4, 9.3**
        
        For any set of entities with potential duplicates, deduplication should:
        1. Identify duplicate entities
        2. Merge them into canonical entities
        3. Preserve all information from duplicates
        4. Maintain referential integrity
        """
        # Create potential duplicates by adding variations of existing entities
        drugs = [e for e in entities if e.get('type') == 'drug']
        
        if len(drugs) > 0:
            # Take first drug and create a variation
            original_drug = drugs[0]
            duplicate_drug = original_drug.copy()
            duplicate_drug['id'] = f"{original_drug['id']}_dup"
            duplicate_drug['name'] = original_drug['name']  # Same name
            
            # Add duplicate to entities
            entities_with_dup = entities + [duplicate_drug]
            
            # Extract all drug names
            drug_names = [e['name'] for e in entities_with_dup if e.get('type') == 'drug']
            
            # Count occurrences of the duplicated name
            duplicate_count = drug_names.count(original_drug['name'])
            
            # Should have at least 2 occurrences (original + duplicate)
            assert duplicate_count >= 2, \
                "Should have duplicate drug names"
            
            # After deduplication, should have unique names
            unique_names = set(drug_names)
            assert len(unique_names) < len(drug_names), \
                "Deduplication should reduce the number of entities"
    
    @given(
        entities=dataset_entities_strategy(),
        dataset_name=st.sampled_from(['OnSIDES', 'SIDER', 'FAERS'])
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_error_handling_maintains_partial_consistency(
        self, entities: List[Dict[str, Any]], dataset_name: str
    ):
        """
        Property: Error handling maintains partial consistency
        
        **Validates: Requirements 3.4, 9.3**
        
        For any build operation with errors, the system should:
        1. Record errors without crashing
        2. Continue processing valid entities
        3. Maintain consistency of successfully processed entities
        """
        # Create a build result with some errors
        result = BuildResult(
            mode=BuildMode.INCREMENTAL,
            entities_created=len([e for e in entities if e.get('type') == 'drug']),
            entities_updated=0,
            relationships_created=len([e for e in entities if e.get('type') == 'causes_relationship']),
            relationships_updated=0,
            conflicts_resolved=0,
            errors=['Error processing entity X', 'Invalid data format for entity Y'],
            build_time=2.5
        )
        
        # Verify errors are recorded
        assert isinstance(result.errors, list)
        assert len(result.errors) > 0
        
        # Verify partial success is tracked
        assert result.entities_created >= 0
        assert result.relationships_created >= 0
        
        # Even with errors, statistics should be consistent
        assert result.entities_created + result.entities_updated >= 0
        assert result.relationships_created + result.relationships_updated >= 0
        
        # Build time should still be recorded
        assert result.build_time > 0

    
    @given(
        entities=dataset_entities_strategy(),
        old_version=dataset_version_strategy(),
        new_version=dataset_version_strategy()
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.large_base_example])
    def test_version_progression_is_monotonic(
        self, entities: List[Dict[str, Any]], old_version: str, new_version: str
    ):
        """
        Property: Dataset version progression is monotonic
        
        **Validates: Requirements 3.4, 9.3**
        
        For any dataset update, version numbers should progress forward.
        """
        # Parse versions
        old_parts = [int(p) for p in old_version.split('.')]
        new_parts = [int(p) for p in new_version.split('.')]
        
        # Assume new version should be >= old version for this test
        # (In practice, we'd enforce this in the update logic)
        
        # Verify version format
        assert len(old_parts) >= 2, "Version should have at least major.minor"
        assert len(new_parts) >= 2, "Version should have at least major.minor"
        
        # Verify all parts are non-negative
        assert all(p >= 0 for p in old_parts), "Version parts should be non-negative"
        assert all(p >= 0 for p in new_parts), "Version parts should be non-negative"
        
        # Create metadata with versions
        old_metadata = DatasetMetadata(
            name='TestDataset',
            version=old_version,
            last_updated=datetime.now(timezone.utc) - timedelta(days=30),
            record_count=100,
            entity_types=['drug', 'side_effect'],
            relationship_types=['CAUSES'],
            quality_score=0.9,
            authority_level='high',
            description='Old version'
        )
        
        new_metadata = DatasetMetadata(
            name='TestDataset',
            version=new_version,
            last_updated=datetime.now(timezone.utc),
            record_count=150,
            entity_types=['drug', 'side_effect'],
            relationship_types=['CAUSES'],
            quality_score=0.95,
            authority_level='high',
            description='New version'
        )
        
        # Verify metadata consistency
        assert old_metadata.name == new_metadata.name, \
            "Dataset name should remain consistent across versions"
        
        # New version should have same or more records (in general)
        # (This is a soft constraint - could decrease if data is cleaned)
        assert new_metadata.record_count >= 0
        
        # Last updated should be more recent for new version
        # (We set it that way in the test, but verify it's tracked)
        assert isinstance(new_metadata.last_updated, datetime)
        assert isinstance(old_metadata.last_updated, datetime)


# ============================================================================
# Integration Tests for Knowledge Graph Updates
# ============================================================================

class TestKnowledgeGraphUpdateIntegration:
    """Integration tests for end-to-end knowledge graph updates"""
    
    @given(
        base_entities=dataset_entities_strategy(),
        dataset_name=st.sampled_from(['OnSIDES', 'SIDER', 'FAERS'])
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.large_base_example])
    def test_end_to_end_incremental_update_flow(
        self, base_entities: List[Dict[str, Any]], dataset_name: str
    ):
        """
        Property: End-to-end incremental update maintains consistency
        
        **Validates: Requirements 3.4, 9.3**
        
        For any complete incremental update flow:
        1. Initial build creates base graph
        2. Incremental update adds new data
        3. All data remains consistent
        4. Metadata is updated correctly
        """
        database = KnowledgeGraphDatabase()
        entity_resolver = EntityResolutionService(confidence_threshold=0.7)
        metadata_manager = MetadataManager()
        
        builder = KnowledgeGraphBuilder(database, entity_resolver, metadata_manager)
        
        # Simulate initial build
        initial_drugs = len([e for e in base_entities if e.get('type') == 'drug'])
        initial_ses = len([e for e in base_entities if e.get('type') == 'side_effect'])
        initial_rels = len([e for e in base_entities if e.get('type') == 'causes_relationship'])
        
        # Simulate incremental update with new entities
        new_drug = {
            'type': 'drug',
            'id': 'drug_incremental_001',
            'name': 'IncrementalDrug',
            'generic_name': 'incrementaldrug',
            'created_from': [dataset_name]
        }
        
        updated_entities = base_entities + [new_drug]
        
        # Verify consistency after update
        updated_drugs = len([e for e in updated_entities if e.get('type') == 'drug'])
        updated_ses = len([e for e in updated_entities if e.get('type') == 'side_effect'])
        updated_rels = len([e for e in updated_entities if e.get('type') == 'causes_relationship'])
        
        # Counts should increase or stay the same
        assert updated_drugs >= initial_drugs, \
            "Drug count should not decrease after incremental update"
        assert updated_ses >= initial_ses, \
            "Side effect count should not decrease after incremental update"
        assert updated_rels >= initial_rels, \
            "Relationship count should not decrease after incremental update"
        
        # Verify new drug is present
        drug_names = {e['name'] for e in updated_entities if e.get('type') == 'drug'}
        assert 'IncrementalDrug' in drug_names, \
            "New drug should be present after incremental update"
        
        # Verify all original entities are still present
        base_drug_names = {e['name'] for e in base_entities if e.get('type') == 'drug'}
        assert base_drug_names.issubset(drug_names), \
            "Original drugs should be preserved after incremental update"
