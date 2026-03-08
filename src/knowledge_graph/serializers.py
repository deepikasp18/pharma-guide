"""
Serialization utilities for knowledge graph entities
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Union
from .models import (
    DrugEntity, SideEffectEntity, InteractionEntity, PatientContext,
    CausesRelationship, SemanticQuery, GraphResponse, EvidenceProvenance,
    DatasetMetadata, EntityMapping
)

class EntitySerializer:
    """Serialization utilities for knowledge graph entities"""
    
    @staticmethod
    def datetime_handler(obj: Any) -> str:
        """JSON serialization handler for datetime objects"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    @staticmethod
    def to_dict(entity: Union[DrugEntity, SideEffectEntity, InteractionEntity, 
                            PatientContext, CausesRelationship, SemanticQuery,
                            GraphResponse, EvidenceProvenance, DatasetMetadata,
                            EntityMapping]) -> Dict[str, Any]:
        """Convert entity to dictionary"""
        return entity.model_dump()
    
    @staticmethod
    def to_json(entity: Union[DrugEntity, SideEffectEntity, InteractionEntity,
                            PatientContext, CausesRelationship, SemanticQuery,
                            GraphResponse, EvidenceProvenance, DatasetMetadata,
                            EntityMapping]) -> str:
        """Convert entity to JSON string"""
        return entity.model_dump_json()
    
    @staticmethod
    def from_dict(data: Dict[str, Any], entity_type: str) -> Union[
        DrugEntity, SideEffectEntity, InteractionEntity, PatientContext,
        CausesRelationship, SemanticQuery, GraphResponse, EvidenceProvenance,
        DatasetMetadata, EntityMapping
    ]:
        """Create entity from dictionary"""
        entity_classes = {
            'drug': DrugEntity,
            'side_effect': SideEffectEntity,
            'interaction': InteractionEntity,
            'patient': PatientContext,
            'causes_relationship': CausesRelationship,
            'semantic_query': SemanticQuery,
            'graph_response': GraphResponse,
            'evidence_provenance': EvidenceProvenance,
            'dataset_metadata': DatasetMetadata,
            'entity_mapping': EntityMapping
        }
        
        if entity_type not in entity_classes:
            raise ValueError(f"Unknown entity type: {entity_type}")
        
        entity_class = entity_classes[entity_type]
        return entity_class(**data)
    
    @staticmethod
    def from_json(json_str: str, entity_type: str) -> Union[
        DrugEntity, SideEffectEntity, InteractionEntity, PatientContext,
        CausesRelationship, SemanticQuery, GraphResponse, EvidenceProvenance,
        DatasetMetadata, EntityMapping
    ]:
        """Create entity from JSON string"""
        data = json.loads(json_str)
        return EntitySerializer.from_dict(data, entity_type)
    
    @staticmethod
    def batch_to_dict(entities: List[Union[DrugEntity, SideEffectEntity, 
                                         InteractionEntity, PatientContext]]) -> List[Dict[str, Any]]:
        """Convert list of entities to list of dictionaries"""
        return [EntitySerializer.to_dict(entity) for entity in entities]
    
    @staticmethod
    def batch_to_json(entities: List[Union[DrugEntity, SideEffectEntity,
                                         InteractionEntity, PatientContext]]) -> str:
        """Convert list of entities to JSON string"""
        dicts = EntitySerializer.batch_to_dict(entities)
        return json.dumps(dicts, default=EntitySerializer.datetime_handler, indent=2)

class GraphSerializer:
    """Specialized serialization for graph structures"""
    
    @staticmethod
    def serialize_graph_node(entity: Union[DrugEntity, SideEffectEntity, PatientContext],
                           node_type: str) -> Dict[str, Any]:
        """Serialize entity as graph node"""
        base_data = EntitySerializer.to_dict(entity)
        return {
            'id': entity.id,
            'type': node_type,
            'properties': base_data
        }
    
    @staticmethod
    def serialize_graph_edge(relationship: Union[CausesRelationship, InteractionEntity],
                           edge_type: str) -> Dict[str, Any]:
        """Serialize relationship as graph edge"""
        base_data = EntitySerializer.to_dict(relationship)
        
        if isinstance(relationship, CausesRelationship):
            return {
                'source': relationship.drug_id,
                'target': relationship.side_effect_id,
                'type': edge_type,
                'properties': base_data
            }
        elif isinstance(relationship, InteractionEntity):
            return {
                'source': relationship.drug_a_id,
                'target': relationship.drug_b_id,
                'type': edge_type,
                'properties': base_data
            }
        else:
            raise ValueError(f"Unsupported relationship type: {type(relationship)}")
    
    @staticmethod
    def serialize_cypher_result(result: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize Cypher query result for API response"""
        serialized = {}
        
        for key, value in result.items():
            if hasattr(value, 'model_dump'):
                # Pydantic model
                serialized[key] = value.model_dump()
            elif isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, (list, tuple)):
                serialized[key] = [
                    item.model_dump() if hasattr(item, 'model_dump') else item
                    for item in value
                ]
            else:
                serialized[key] = value
        
        return serialized