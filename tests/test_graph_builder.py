"""
Tests for knowledge graph builder
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.knowledge_graph.graph_builder import (
    KnowledgeGraphBuilder, BuildMode, BuildResult, GraphBuildError
)
from src.knowledge_graph.models import DrugEntity, SideEffectEntity, DatasetMetadata

class TestKnowledgeGraphBuilder:
    """Test knowledge graph builder"""
    
    @pytest.fixture
    def mock_database(self):
        """Mock database fixture"""
        db = AsyncMock()
        db.connected = True
        db.connect = AsyncMock()
        db.create_drug_vertex = AsyncMock(return_value="drug_id")
        db.create_side_effect_vertex = AsyncMock(return_value="se_id")
        db.create_causes_edge = AsyncMock(return_value="edge_id")
        db.find_drug_by_name = AsyncMock(return_value=None)
        return db
    
    @pytest.fixture
    def mock_entity_resolver(self):
        """Mock entity resolver fixture"""
        resolver = MagicMock()
        resolver.resolve_entities = MagicMock(return_value=[])
        return resolver
    
    @pytest.fixture
    def mock_metadata_manager(self):
        """Mock metadata manager fixture"""
        manager = MagicMock()
        manager.save_metadata = MagicMock()
        manager.load_metadata = MagicMock(return_value=None)
        manager.update_metadata = MagicMock()
        return manager
    
    @pytest.fixture
    def graph_builder(self, mock_database, mock_entity_resolver, mock_metadata_manager):
        """Graph builder fixture"""
        return KnowledgeGraphBuilder(
            database=mock_database,
            entity_resolver=mock_entity_resolver,
            metadata_manager=mock_metadata_manager
        )
    
    @pytest.mark.asyncio
    async def test_build_from_drug_entities(self, graph_builder):
        """Test building graph from drug entities"""
        entities = [
            {
                'type': 'drug',
                'id': 'drug1',
                'name': 'Aspirin',
                'generic_name': 'acetylsalicylic acid',
                'drugbank_id': 'DB00945'
            },
            {
                'type': 'drug',
                'id': 'drug2',
                'name': 'Ibuprofen',
                'generic_name': 'ibuprofen'
            }
        ]
        
        result = await graph_builder.build_from_entities(entities, "test_dataset")
        
        assert isinstance(result, BuildResult)
        assert result.entities_created == 2
        assert result.entities_updated == 0
        assert len(result.errors) == 0
        
        # Verify database calls
        assert graph_builder.database.create_drug_vertex.call_count == 2
    
    @pytest.mark.asyncio
    async def test_build_from_side_effect_entities(self, graph_builder):
        """Test building graph from side effect entities"""
        entities = [
            {
                'type': 'side_effect',
                'id': 'se1',
                'name': 'Headache',
                'meddra_code': '10019211'
            },
            {
                'type': 'side_effect',
                'id': 'se2',
                'name': 'Nausea'
            }
        ]
        
        result = await graph_builder.build_from_entities(entities, "test_dataset")
        
        assert result.entities_created == 2
        assert len(result.errors) == 0
        
        # Verify database calls
        assert graph_builder.database.create_side_effect_vertex.call_count == 2
    
    @pytest.mark.asyncio
    async def test_build_from_causes_relationships(self, graph_builder):
        """Test building graph from CAUSES relationships"""
        entities = [
            {
                'type': 'causes_relationship',
                'drug_name': 'Aspirin',
                'side_effect_name': 'Headache',
                'frequency': 0.15,
                'confidence': 0.85,
                'evidence_sources': ['SIDER']
            },
            {
                'type': 'causes_relationship',
                'drug_name': 'Ibuprofen',
                'side_effect_name': 'Nausea',
                'frequency': 0.08,
                'confidence': 0.75,
                'evidence_sources': ['FAERS']
            }
        ]
        
        result = await graph_builder.build_from_entities(entities, "test_dataset")
        
        assert result.relationships_created == 2
        assert len(result.errors) == 0
        
        # Verify database calls for creating entities and relationships
        assert graph_builder.database.create_drug_vertex.call_count == 2
        assert graph_builder.database.create_side_effect_vertex.call_count == 2
        assert graph_builder.database.create_causes_edge.call_count == 2
    
    @pytest.mark.asyncio
    async def test_build_mixed_entities(self, graph_builder):
        """Test building graph from mixed entity types"""
        entities = [
            {
                'type': 'drug',
                'id': 'drug1',
                'name': 'Aspirin'
            },
            {
                'type': 'side_effect',
                'id': 'se1',
                'name': 'Headache'
            },
            {
                'type': 'causes_relationship',
                'drug_name': 'Aspirin',
                'side_effect_name': 'Headache',
                'frequency': 0.1,
                'confidence': 0.8,
                'evidence_sources': ['SIDER']
            }
        ]
        
        result = await graph_builder.build_from_entities(entities, "test_dataset")
        
        assert result.entities_created == 2  # Drug and side effect
        assert result.relationships_created == 1  # CAUSES relationship
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_incremental_update(self, graph_builder):
        """Test incremental update functionality"""
        # Mock existing metadata
        existing_metadata = DatasetMetadata(
            name="test_dataset",
            version="1.0",
            last_updated=datetime.utcnow(),
            record_count=10,
            entity_types=["drug"],
            relationship_types=["CAUSES"],
            quality_score=0.9,
            authority_level="high"
        )
        graph_builder.metadata_manager.load_metadata.return_value = existing_metadata
        
        new_entities = [
            {
                'type': 'drug',
                'id': 'drug_new',
                'name': 'New Drug'
            }
        ]
        
        result = await graph_builder.incremental_update(new_entities, "test_dataset")
        
        assert result.mode == BuildMode.INCREMENTAL
        assert result.entities_created == 1
        
        # Verify metadata update was called
        graph_builder.metadata_manager.update_metadata.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_full_rebuild(self, graph_builder):
        """Test full rebuild functionality"""
        entities = [
            {
                'type': 'drug',
                'id': 'drug1',
                'name': 'Aspirin'
            },
            {
                'type': 'drug',
                'id': 'drug2',
                'name': 'Ibuprofen'
            }
        ]
        
        result = await graph_builder.full_rebuild(entities, "test_dataset")
        
        assert result.mode == BuildMode.FULL_REBUILD
        assert result.entities_created == 2
        
        # In full rebuild mode, entity resolution should be called
        # (though our mock returns empty list)
        assert graph_builder.entity_resolver.resolve_entities.called
    
    @pytest.mark.asyncio
    async def test_error_handling(self, graph_builder):
        """Test error handling during build"""
        # Make database operations fail
        graph_builder.database.create_drug_vertex.side_effect = Exception("Database error")
        
        entities = [
            {
                'type': 'drug',
                'id': 'drug1',
                'name': 'Aspirin'
            }
        ]
        
        result = await graph_builder.build_from_entities(entities, "test_dataset")
        
        assert result.entities_created == 0
        assert len(result.errors) > 0
        assert "Database error" in result.errors[0]
    
    @pytest.mark.asyncio
    async def test_find_or_create_drug(self, graph_builder):
        """Test finding or creating drug entities"""
        # Test creating new drug
        drug_id = await graph_builder._find_or_create_drug("New Drug", {"source_dataset": "test"})
        
        assert drug_id == "drug_new_drug"
        graph_builder.database.create_drug_vertex.assert_called_once()
        
        # Test finding existing drug in cache
        drug_id2 = await graph_builder._find_or_create_drug("New Drug", {"source_dataset": "test"})
        
        assert drug_id2 == drug_id  # Should return same ID from cache
        # Should not create another vertex
        assert graph_builder.database.create_drug_vertex.call_count == 1
    
    @pytest.mark.asyncio
    async def test_find_or_create_side_effect(self, graph_builder):
        """Test finding or creating side effect entities"""
        # Test creating new side effect
        se_id = await graph_builder._find_or_create_side_effect("New Side Effect", {"source_dataset": "test"})
        
        assert se_id == "se_new_side_effect"
        graph_builder.database.create_side_effect_vertex.assert_called_once()
        
        # Test finding existing side effect in cache
        se_id2 = await graph_builder._find_or_create_side_effect("New Side Effect", {"source_dataset": "test"})
        
        assert se_id2 == se_id  # Should return same ID from cache
        # Should not create another vertex
        assert graph_builder.database.create_side_effect_vertex.call_count == 1
    
    def test_group_entities_by_type(self, graph_builder):
        """Test grouping entities by type"""
        entities = [
            {'type': 'drug', 'name': 'Drug1'},
            {'type': 'side_effect', 'name': 'SE1'},
            {'type': 'drug', 'name': 'Drug2'},
            {'type': 'causes_relationship', 'drug_name': 'Drug1', 'side_effect_name': 'SE1'}
        ]
        
        groups = graph_builder._group_entities_by_type(entities)
        
        assert len(groups) == 3
        assert len(groups['drug']) == 2
        assert len(groups['side_effect']) == 1
        assert len(groups['causes_relationship']) == 1
    
    def test_get_build_statistics(self, graph_builder):
        """Test getting build statistics"""
        # Add some entities to cache
        graph_builder.entity_cache = {
            'drug1': {'type': 'drug', 'entity': None, 'data': {}},
            'drug2': {'type': 'drug', 'entity': None, 'data': {}},
            'se1': {'type': 'side_effect', 'entity': None, 'data': {}}
        }
        
        graph_builder.relationship_cache = {
            'rel1': {'type': 'causes', 'entity': None, 'data': {}}
        }
        
        stats = graph_builder.get_build_statistics()
        
        assert stats['cached_entities'] == 3
        assert stats['cached_relationships'] == 1
        assert stats['entity_types']['drug'] == 2
        assert stats['entity_types']['side_effect'] == 1
        assert stats['entity_types']['interaction'] == 0

class TestBuildResult:
    """Test BuildResult dataclass"""
    
    def test_build_result_creation(self):
        """Test creating BuildResult"""
        result = BuildResult(
            mode=BuildMode.INCREMENTAL,
            entities_created=5,
            entities_updated=2,
            relationships_created=10,
            relationships_updated=1,
            conflicts_resolved=0,
            errors=[],
            build_time=1.5
        )
        
        assert result.mode == BuildMode.INCREMENTAL
        assert result.entities_created == 5
        assert result.entities_updated == 2
        assert result.relationships_created == 10
        assert result.relationships_updated == 1
        assert result.conflicts_resolved == 0
        assert len(result.errors) == 0
        assert result.build_time == 1.5
        assert result.metadata is None

class TestIntegration:
    """Integration tests for graph builder"""
    
    @pytest.mark.asyncio
    async def test_create_graph_builder_factory(self):
        """Test factory function for creating graph builder"""
        with patch('src.knowledge_graph.database.db') as mock_db, \
             patch('src.data_processing.entity_resolution.entity_resolution_service') as mock_resolver, \
             patch('src.data_processing.metadata_manager.metadata_manager') as mock_manager:
            
            from src.knowledge_graph.graph_builder import create_graph_builder
            
            builder = await create_graph_builder()
            
            assert isinstance(builder, KnowledgeGraphBuilder)