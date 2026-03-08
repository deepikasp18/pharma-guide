"""
Knowledge graph builder for constructing graph from processed datasets
"""
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from src.knowledge_graph.database import KnowledgeGraphDatabase
from src.knowledge_graph.models import (
    DrugEntity, SideEffectEntity, InteractionEntity, PatientContext,
    CausesRelationship, DatasetMetadata
)
from src.data_processing.entity_resolution import EntityResolutionService, EntityType
from src.data_processing.metadata_manager import MetadataManager

logger = logging.getLogger(__name__)

class BuildMode(str, Enum):
    """Graph building modes"""
    FULL_REBUILD = "full_rebuild"
    INCREMENTAL = "incremental"
    MERGE_ONLY = "merge_only"

@dataclass
class BuildResult:
    """Result of graph building operation"""
    mode: BuildMode
    entities_created: int
    entities_updated: int
    relationships_created: int
    relationships_updated: int
    conflicts_resolved: int
    errors: List[str]
    build_time: float
    metadata: Optional[DatasetMetadata] = None

class GraphBuildError(Exception):
    """Graph building error"""
    pass

class KnowledgeGraphBuilder:
    """Builds knowledge graph from processed dataset entities"""
    
    def __init__(self, database: KnowledgeGraphDatabase, 
                 entity_resolver: EntityResolutionService,
                 metadata_manager: MetadataManager):
        self.database = database
        self.entity_resolver = entity_resolver
        self.metadata_manager = metadata_manager
        self.logger = logging.getLogger(__name__)
        
        # Track entities during build
        self.entity_cache: Dict[str, Dict[str, Any]] = {}
        self.relationship_cache: Dict[str, Dict[str, Any]] = {}
    
    async def build_from_entities(self, entities: List[Dict[str, Any]], 
                                dataset_name: str, 
                                mode: BuildMode = BuildMode.INCREMENTAL) -> BuildResult:
        """Build knowledge graph from a list of entities"""
        start_time = datetime.utcnow()
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
        
        try:
            self.logger.info(f"Starting graph build for {dataset_name} with {len(entities)} entities")
            
            # Ensure database connection
            if not self.database.connected:
                await self.database.connect()
            
            # Group entities by type
            entity_groups = self._group_entities_by_type(entities)
            
            # Process each entity type
            for entity_type, type_entities in entity_groups.items():
                if entity_type == 'drug':
                    await self._process_drug_entities(type_entities, result)
                elif entity_type == 'side_effect':
                    await self._process_side_effect_entities(type_entities, result)
                elif entity_type == 'causes_relationship':
                    await self._process_causes_relationships(type_entities, result)
                elif entity_type == 'interaction':
                    await self._process_interaction_entities(type_entities, result)
                else:
                    self.logger.warning(f"Unknown entity type: {entity_type}")
            
            # Resolve entity duplicates if in full rebuild mode
            if mode == BuildMode.FULL_REBUILD:
                await self._resolve_entity_duplicates(result)
            
            # Update metadata
            await self._update_dataset_metadata(dataset_name, result)
            
            build_time = (datetime.utcnow() - start_time).total_seconds()
            result.build_time = build_time
            
            self.logger.info(f"Graph build completed in {build_time:.2f}s: "
                           f"{result.entities_created} entities created, "
                           f"{result.relationships_created} relationships created")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Graph build failed: {e}")
            result.errors.append(str(e))
            result.build_time = (datetime.utcnow() - start_time).total_seconds()
            return result
    
    def _group_entities_by_type(self, entities: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group entities by their type"""
        groups = {}
        
        for entity in entities:
            entity_type = entity.get('type', 'unknown')
            if entity_type not in groups:
                groups[entity_type] = []
            groups[entity_type].append(entity)
        
        return groups
    
    async def _process_drug_entities(self, entities: List[Dict[str, Any]], result: BuildResult):
        """Process drug entities"""
        self.logger.info(f"Processing {len(entities)} drug entities")
        
        for entity_data in entities:
            try:
                # Create DrugEntity
                drug = DrugEntity(
                    id=entity_data.get('id', f"drug_{len(self.entity_cache)}"),
                    name=entity_data['name'],
                    generic_name=entity_data.get('generic_name', ''),
                    drugbank_id=entity_data.get('drugbank_id'),
                    rxcui=entity_data.get('rxcui'),
                    atc_codes=entity_data.get('atc_codes', []),
                    mechanism=entity_data.get('mechanism'),
                    pharmacokinetics=entity_data.get('pharmacokinetics', {}),
                    indications=entity_data.get('indications', []),
                    contraindications=entity_data.get('contraindications', []),
                    dosage_forms=entity_data.get('dosage_forms', []),
                    created_from=entity_data.get('created_from', [])
                )
                
                # Check if entity already exists
                existing = await self.database.find_drug_by_name(drug.name)
                
                if existing:
                    # Update existing entity
                    await self._update_drug_entity(drug, existing)
                    result.entities_updated += 1
                else:
                    # Create new entity
                    await self.database.create_drug_vertex(drug)
                    result.entities_created += 1
                
                # Cache for relationship processing
                self.entity_cache[drug.id] = {
                    'type': 'drug',
                    'entity': drug,
                    'data': entity_data
                }
                
            except Exception as e:
                error_msg = f"Failed to process drug entity {entity_data.get('name', 'unknown')}: {e}"
                self.logger.error(error_msg)
                result.errors.append(error_msg)
    
    async def _process_side_effect_entities(self, entities: List[Dict[str, Any]], result: BuildResult):
        """Process side effect entities"""
        self.logger.info(f"Processing {len(entities)} side effect entities")
        
        for entity_data in entities:
            try:
                # Create SideEffectEntity
                side_effect = SideEffectEntity(
                    id=entity_data.get('id', f"se_{len(self.entity_cache)}"),
                    name=entity_data['name'],
                    meddra_code=entity_data.get('meddra_code'),
                    severity=entity_data.get('severity'),
                    frequency_category=entity_data.get('frequency_category'),
                    system_organ_class=entity_data.get('system_organ_class'),
                    description=entity_data.get('description'),
                    created_from=entity_data.get('created_from', [])
                )
                
                # Create vertex in database
                await self.database.create_side_effect_vertex(side_effect)
                result.entities_created += 1
                
                # Cache for relationship processing
                self.entity_cache[side_effect.id] = {
                    'type': 'side_effect',
                    'entity': side_effect,
                    'data': entity_data
                }
                
            except Exception as e:
                error_msg = f"Failed to process side effect entity {entity_data.get('name', 'unknown')}: {e}"
                self.logger.error(error_msg)
                result.errors.append(error_msg)
    
    async def _process_causes_relationships(self, relationships: List[Dict[str, Any]], result: BuildResult):
        """Process CAUSES relationships between drugs and side effects"""
        self.logger.info(f"Processing {len(relationships)} CAUSES relationships")
        
        for rel_data in relationships:
            try:
                # Find or create drug entity
                drug_name = rel_data.get('drug_name')
                side_effect_name = rel_data.get('side_effect_name')
                
                if not drug_name or not side_effect_name:
                    result.errors.append("Missing drug or side effect name in relationship")
                    continue
                
                # Find or create entities
                drug_id = await self._find_or_create_drug(drug_name, rel_data)
                side_effect_id = await self._find_or_create_side_effect(side_effect_name, rel_data)
                
                # Create relationship
                await self.database.create_causes_edge(
                    drug_id=drug_id,
                    side_effect_id=side_effect_id,
                    frequency=rel_data.get('frequency', 0.0),
                    confidence=rel_data.get('confidence', 0.5),
                    evidence_sources=rel_data.get('evidence_sources', [])
                )
                
                result.relationships_created += 1
                
            except Exception as e:
                error_msg = f"Failed to process CAUSES relationship: {e}"
                self.logger.error(error_msg)
                result.errors.append(error_msg)
    
    async def _process_interaction_entities(self, entities: List[Dict[str, Any]], result: BuildResult):
        """Process drug interaction entities"""
        self.logger.info(f"Processing {len(entities)} interaction entities")
        
        for entity_data in entities:
            try:
                # Create InteractionEntity
                interaction = InteractionEntity(
                    id=entity_data.get('id', f"int_{len(self.entity_cache)}"),
                    drug_a_id=entity_data['drug_a_id'],
                    drug_b_id=entity_data['drug_b_id'],
                    severity=entity_data.get('severity', 'moderate'),
                    mechanism=entity_data.get('mechanism'),
                    clinical_effect=entity_data.get('clinical_effect'),
                    management=entity_data.get('management'),
                    evidence_level=entity_data.get('evidence_level'),
                    onset=entity_data.get('onset'),
                    documentation=entity_data.get('documentation'),
                    created_from=entity_data.get('created_from', [])
                )
                
                # Store interaction (would create edge in real implementation)
                self.relationship_cache[interaction.id] = {
                    'type': 'interaction',
                    'entity': interaction,
                    'data': entity_data
                }
                
                result.relationships_created += 1
                
            except Exception as e:
                error_msg = f"Failed to process interaction entity: {e}"
                self.logger.error(error_msg)
                result.errors.append(error_msg)
    
    async def _find_or_create_drug(self, drug_name: str, context_data: Dict[str, Any]) -> str:
        """Find existing drug or create new one"""
        # Check cache first
        for entity_id, cached in self.entity_cache.items():
            if (cached['type'] == 'drug' and 
                cached['entity'].name.lower() == drug_name.lower()):
                return entity_id
        
        # Check database
        existing = await self.database.find_drug_by_name(drug_name)
        if existing:
            return existing.get('id', drug_name)
        
        # Create new drug entity
        drug = DrugEntity(
            id=f"drug_{drug_name.lower().replace(' ', '_')}",
            name=drug_name,
            generic_name=drug_name.lower(),
            created_from=[context_data.get('source_dataset', 'unknown')]
        )
        
        await self.database.create_drug_vertex(drug)
        
        # Cache the new entity
        self.entity_cache[drug.id] = {
            'type': 'drug',
            'entity': drug,
            'data': {'name': drug_name}
        }
        
        return drug.id
    
    async def _find_or_create_side_effect(self, side_effect_name: str, context_data: Dict[str, Any]) -> str:
        """Find existing side effect or create new one"""
        # Check cache first
        for entity_id, cached in self.entity_cache.items():
            if (cached['type'] == 'side_effect' and 
                cached['entity'].name.lower() == side_effect_name.lower()):
                return entity_id
        
        # Create new side effect entity
        side_effect = SideEffectEntity(
            id=f"se_{side_effect_name.lower().replace(' ', '_')}",
            name=side_effect_name,
            meddra_code=context_data.get('meddra_code'),
            created_from=[context_data.get('source_dataset', 'unknown')]
        )
        
        await self.database.create_side_effect_vertex(side_effect)
        
        # Cache the new entity
        self.entity_cache[side_effect.id] = {
            'type': 'side_effect',
            'entity': side_effect,
            'data': {'name': side_effect_name}
        }
        
        return side_effect.id
    
    async def _update_drug_entity(self, new_drug: DrugEntity, existing_data: Dict[str, Any]):
        """Update existing drug entity with new information"""
        # In a real implementation, this would merge the data and update the database
        # For now, we'll just log the update
        self.logger.info(f"Updating existing drug entity: {new_drug.name}")
    
    async def _resolve_entity_duplicates(self, result: BuildResult):
        """Resolve duplicate entities using entity resolution service"""
        self.logger.info("Resolving entity duplicates")
        
        try:
            # Group cached entities by type
            drugs = []
            side_effects = []
            
            for entity_id, cached in self.entity_cache.items():
                if cached['type'] == 'drug':
                    drug_dict = cached['entity'].model_dump()
                    drug_dict['id'] = entity_id
                    drugs.append(drug_dict)
                elif cached['type'] == 'side_effect':
                    se_dict = cached['entity'].model_dump()
                    se_dict['id'] = entity_id
                    side_effects.append(se_dict)
            
            # Resolve drug duplicates
            if drugs:
                drug_resolutions = self.entity_resolver.resolve_entities(drugs, EntityType.DRUG)
                conflicts_resolved = sum(len(r.conflicts) for r in drug_resolutions)
                result.conflicts_resolved += conflicts_resolved
                self.logger.info(f"Resolved {len(drug_resolutions)} drug entity groups")
            
            # Resolve side effect duplicates
            if side_effects:
                se_resolutions = self.entity_resolver.resolve_entities(side_effects, EntityType.SIDE_EFFECT)
                conflicts_resolved = sum(len(r.conflicts) for r in se_resolutions)
                result.conflicts_resolved += conflicts_resolved
                self.logger.info(f"Resolved {len(se_resolutions)} side effect entity groups")
                
        except Exception as e:
            error_msg = f"Failed to resolve entity duplicates: {e}"
            self.logger.error(error_msg)
            result.errors.append(error_msg)
    
    async def _update_dataset_metadata(self, dataset_name: str, result: BuildResult):
        """Update dataset metadata after build"""
        try:
            metadata = DatasetMetadata(
                name=dataset_name,
                version="1.0",
                last_updated=datetime.utcnow(),
                record_count=result.entities_created + result.entities_updated,
                entity_types=["drug", "side_effect", "interaction"],
                relationship_types=["CAUSES", "INTERACTS_WITH"],
                quality_score=1.0 - (len(result.errors) / max(result.entities_created + result.entities_updated, 1)),
                authority_level="high" if "drugbank" in dataset_name.lower() else "medium",
                description=f"Knowledge graph built from {dataset_name} dataset"
            )
            
            self.metadata_manager.save_metadata(metadata)
            result.metadata = metadata
            
        except Exception as e:
            error_msg = f"Failed to update metadata: {e}"
            self.logger.error(error_msg)
            result.errors.append(error_msg)
    
    async def incremental_update(self, new_entities: List[Dict[str, Any]], 
                               dataset_name: str) -> BuildResult:
        """Perform incremental update of knowledge graph"""
        self.logger.info(f"Performing incremental update for {dataset_name}")
        
        # Load existing metadata to understand current state
        existing_metadata = self.metadata_manager.load_metadata(dataset_name)
        
        # Build with incremental mode
        result = await self.build_from_entities(
            new_entities, 
            dataset_name, 
            BuildMode.INCREMENTAL
        )
        
        # Update version if successful
        if existing_metadata and len(result.errors) == 0:
            version_parts = existing_metadata.version.split('.')
            if len(version_parts) >= 2:
                minor_version = int(version_parts[1]) + 1
                new_version = f"{version_parts[0]}.{minor_version}"
            else:
                new_version = "1.1"
            
            self.metadata_manager.update_metadata(dataset_name, {
                'version': new_version,
                'record_count': existing_metadata.record_count + result.entities_created
            })
        
        return result
    
    async def full_rebuild(self, all_entities: List[Dict[str, Any]], 
                         dataset_name: str) -> BuildResult:
        """Perform full rebuild of knowledge graph"""
        self.logger.info(f"Performing full rebuild for {dataset_name}")
        
        # Clear caches
        self.entity_cache.clear()
        self.relationship_cache.clear()
        
        # Build with full rebuild mode
        result = await self.build_from_entities(
            all_entities, 
            dataset_name, 
            BuildMode.FULL_REBUILD
        )
        
        return result
    
    def get_build_statistics(self) -> Dict[str, Any]:
        """Get current build statistics"""
        return {
            'cached_entities': len(self.entity_cache),
            'cached_relationships': len(self.relationship_cache),
            'entity_types': {
                entity_type: sum(1 for cached in self.entity_cache.values() 
                               if cached['type'] == entity_type)
                for entity_type in ['drug', 'side_effect', 'interaction']
            }
        }

# Factory function to create graph builder with dependencies
async def create_graph_builder() -> KnowledgeGraphBuilder:
    """Create knowledge graph builder with all dependencies"""
    from src.knowledge_graph.database import db
    from src.data_processing.entity_resolution import entity_resolution_service
    from src.data_processing.metadata_manager import metadata_manager
    
    return KnowledgeGraphBuilder(
        database=db,
        entity_resolver=entity_resolution_service,
        metadata_manager=metadata_manager
    )