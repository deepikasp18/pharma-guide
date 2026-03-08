"""
Knowledge graph database interface for Amazon Neptune
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from gremlin_python.driver import client, serializer
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from gremlin_python.process.traversal import T, P
from gremlin_python.structure.graph import Graph

from src.config import settings
from .models import DrugEntity, SideEffectEntity, InteractionEntity, PatientContext

logger = logging.getLogger(__name__)

class NeptuneConnectionError(Exception):
    """Neptune connection error"""
    pass

class NeptuneQueryError(Exception):
    """Neptune query execution error"""
    pass

class NeptuneConnection:
    """Neptune database connection manager"""
    
    def __init__(self):
        self.endpoint = settings.NEPTUNE_ENDPOINT
        self.port = settings.NEPTUNE_PORT
        self.connection = None
        self.g = None
        self._client = None
    
    async def connect(self) -> None:
        """Establish connection to Neptune"""
        if not self.endpoint:
            logger.warning("Neptune endpoint not configured, using mock connection")
            self.connection = MockNeptuneConnection()
            self.g = self.connection.g
            return
        
        try:
            connection_string = f"wss://{self.endpoint}:{self.port}/gremlin"
            self.connection = DriverRemoteConnection(
                connection_string,
                'g',
                pool_size=10,
                max_workers=4
            )
            
            # Create graph traversal source
            graph = Graph()
            self.g = graph.traversal().withRemote(self.connection)
            
            # Test connection
            await self._test_connection()
            
            logger.info(f"Connected to Neptune at {self.endpoint}:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Neptune: {e}")
            raise NeptuneConnectionError(f"Connection failed: {e}")
    
    async def _test_connection(self) -> None:
        """Test Neptune connection"""
        try:
            # Simple test query
            result = self.g.V().limit(1).toList()
            logger.info("Neptune connection test successful")
        except Exception as e:
            logger.error(f"Neptune connection test failed: {e}")
            raise NeptuneConnectionError(f"Connection test failed: {e}")
    
    async def close(self) -> None:
        """Close Neptune connection"""
        if self.connection and hasattr(self.connection, 'close'):
            try:
                self.connection.close()
                logger.info("Neptune connection closed")
            except Exception as e:
                logger.error(f"Error closing Neptune connection: {e}")

class MockNeptuneConnection:
    """Mock Neptune connection for development/testing"""
    
    def __init__(self):
        self.data = {
            'vertices': {},
            'edges': []
        }
        self.g = MockTraversal(self.data)
    
    def close(self):
        """Mock close method"""
        pass

class MockTraversal:
    """Mock Gremlin traversal for testing"""
    
    def __init__(self, data: Dict):
        self.data = data
        self._vertices = []
        self._edges = []
    
    def V(self, *args):
        """Mock vertex traversal"""
        if args:
            # Filter by vertex IDs
            self._vertices = [v for v in self.data['vertices'].values() if v.get('id') in args]
        else:
            self._vertices = list(self.data['vertices'].values())
        return self
    
    def E(self, *args):
        """Mock edge traversal"""
        if args:
            self._edges = [e for e in self.data['edges'] if e.get('id') in args]
        else:
            self._edges = self.data['edges']
        return self
    
    def hasLabel(self, label):
        """Mock hasLabel step"""
        self._vertices = [v for v in self._vertices if v.get('label') == label]
        return self
    
    def has(self, key, value=None):
        """Mock has step"""
        if value is None:
            # Just check if property exists
            self._vertices = [v for v in self._vertices if key in v.get('properties', {})]
        else:
            # Check property value
            self._vertices = [v for v in self._vertices if v.get('properties', {}).get(key) == value]
        return self
    
    def limit(self, count):
        """Mock limit step"""
        self._vertices = self._vertices[:count]
        return self
    
    def toList(self):
        """Mock toList terminal step"""
        return self._vertices
    
    def addV(self, label):
        """Mock addV step"""
        vertex_id = f"{label}_{len(self.data['vertices'])}"
        vertex = {
            'id': vertex_id,
            'label': label,
            'properties': {}
        }
        self.data['vertices'][vertex_id] = vertex
        self._current_vertex = vertex
        return self
    
    def property(self, key, value):
        """Mock property step"""
        if hasattr(self, '_current_vertex'):
            self._current_vertex['properties'][key] = value
        return self
    
    def outE(self, label):
        """Mock outE step"""
        # Filter edges by label and source vertex
        filtered_edges = []
        for edge in self.data['edges']:
            if edge.get('label') == label:
                # Check if any of our current vertices is the source
                for vertex in self._vertices:
                    if edge.get('from') == vertex.get('id'):
                        filtered_edges.append(edge)
        self._edges = filtered_edges
        return self
    
    def inV(self):
        """Mock inV step"""
        # Get target vertices from current edges
        target_vertices = []
        for edge in self._edges:
            target_id = edge.get('to')
            if target_id and target_id in self.data['vertices']:
                target_vertices.append(self.data['vertices'][target_id])
        self._vertices = target_vertices
        return self
    
    def addE(self, label):
        """Mock addE step"""
        edge = {
            'id': f"{label}_{len(self.data['edges'])}",
            'label': label,
            'properties': {}
        }
        self.data['edges'].append(edge)
        self._current_edge = edge
        return self
    
    def from_(self, vertex):
        """Mock from step"""
        if hasattr(self, '_current_edge'):
            self._current_edge['from'] = vertex
        return self
    
    def to(self, vertex):
        """Mock to step"""
        if hasattr(self, '_current_edge'):
            self._current_edge['to'] = vertex
        return self

class KnowledgeGraphDatabase:
    """Knowledge graph database interface"""
    
    def __init__(self):
        self.connection = NeptuneConnection()
        self.connected = False
    
    async def connect(self) -> None:
        """Connect to the database"""
        await self.connection.connect()
        self.connected = True
    
    async def disconnect(self) -> None:
        """Disconnect from the database"""
        await self.connection.close()
        self.connected = False
    
    async def create_drug_vertex(self, drug: DrugEntity) -> str:
        """Create a drug vertex in the knowledge graph"""
        try:
            g = self.connection.g
            
            # Create vertex with properties
            traversal = g.addV('Drug').property('id', drug.id)
            
            # Add all drug properties
            for field, value in drug.model_dump().items():
                if value is not None and field != 'id':
                    if isinstance(value, list):
                        # Handle list properties
                        for item in value:
                            traversal = traversal.property(field, str(item))
                    elif isinstance(value, dict):
                        # Handle dict properties as JSON string
                        import json
                        traversal = traversal.property(field, json.dumps(value))
                    else:
                        traversal = traversal.property(field, str(value))
            
            result = traversal.toList()
            logger.info(f"Created drug vertex: {drug.id}")
            return drug.id
            
        except Exception as e:
            logger.error(f"Error creating drug vertex: {e}")
            raise NeptuneQueryError(f"Failed to create drug vertex: {e}")
    
    async def create_side_effect_vertex(self, side_effect: SideEffectEntity) -> str:
        """Create a side effect vertex in the knowledge graph"""
        try:
            g = self.connection.g
            
            traversal = g.addV('SideEffect').property('id', side_effect.id)
            
            for field, value in side_effect.model_dump().items():
                if value is not None and field != 'id':
                    if isinstance(value, list):
                        for item in value:
                            traversal = traversal.property(field, str(item))
                    else:
                        traversal = traversal.property(field, str(value))
            
            result = traversal.toList()
            logger.info(f"Created side effect vertex: {side_effect.id}")
            return side_effect.id
            
        except Exception as e:
            logger.error(f"Error creating side effect vertex: {e}")
            raise NeptuneQueryError(f"Failed to create side effect vertex: {e}")
    
    async def create_patient_vertex(self, patient: PatientContext) -> str:
        """Create a patient vertex in the knowledge graph"""
        try:
            g = self.connection.g
            
            traversal = g.addV('Patient').property('id', patient.id)
            
            for field, value in patient.model_dump().items():
                if value is not None and field != 'id':
                    if isinstance(value, (list, dict)):
                        import json
                        traversal = traversal.property(field, json.dumps(value))
                    else:
                        traversal = traversal.property(field, str(value))
            
            result = traversal.toList()
            logger.info(f"Created patient vertex: {patient.id}")
            return patient.id
            
        except Exception as e:
            logger.error(f"Error creating patient vertex: {e}")
            raise NeptuneQueryError(f"Failed to create patient vertex: {e}")
    
    async def create_causes_edge(self, drug_id: str, side_effect_id: str, 
                               frequency: float, confidence: float, 
                               evidence_sources: List[str]) -> str:
        """Create a CAUSES edge between drug and side effect"""
        try:
            g = self.connection.g
            
            # Find source and target vertices
            drug_vertex = g.V().has('id', drug_id).toList()
            side_effect_vertex = g.V().has('id', side_effect_id).toList()
            
            if not drug_vertex or not side_effect_vertex:
                raise NeptuneQueryError("Source or target vertex not found")
            
            # Create edge
            edge_id = f"causes_{drug_id}_{side_effect_id}"
            traversal = (g.V().has('id', drug_id)
                        .addE('CAUSES')
                        .to(g.V().has('id', side_effect_id))
                        .property('id', edge_id)
                        .property('frequency', frequency)
                        .property('confidence', confidence)
                        .property('evidence_sources', ','.join(evidence_sources)))
            
            result = traversal.toList()
            logger.info(f"Created CAUSES edge: {edge_id}")
            return edge_id
            
        except Exception as e:
            logger.error(f"Error creating CAUSES edge: {e}")
            raise NeptuneQueryError(f"Failed to create CAUSES edge: {e}")
    
    async def find_drug_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find drug by name"""
        try:
            g = self.connection.g
            result = g.V().hasLabel('Drug').has('name', name).toList()
            
            if result:
                return result[0]
            return None
            
        except Exception as e:
            logger.error(f"Error finding drug by name: {e}")
            raise NeptuneQueryError(f"Failed to find drug: {e}")
    
    async def find_side_effects_for_drug(self, drug_id: str) -> List[Dict[str, Any]]:
        """Find side effects for a drug"""
        try:
            g = self.connection.g
            
            # Traverse from drug to side effects via CAUSES edges
            result = (g.V().has('id', drug_id)
                     .outE('CAUSES')
                     .inV()
                     .toList())
            
            return result
            
        except Exception as e:
            logger.error(f"Error finding side effects for drug: {e}")
            raise NeptuneQueryError(f"Failed to find side effects: {e}")
    
    async def execute_cypher_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a raw Cypher query (for future Cypher support)"""
        # Note: Neptune primarily uses Gremlin, but this method is for future compatibility
        # if Cypher support is added or for other graph databases
        logger.warning("Cypher queries not directly supported in Neptune. Use Gremlin instead.")
        return []
    
    async def health_check(self) -> bool:
        """Check database health"""
        try:
            if not self.connected:
                return False
            
            g = self.connection.g
            result = g.V().limit(1).toList()
            return True
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

# Global database instance
db = KnowledgeGraphDatabase()