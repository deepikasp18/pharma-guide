"""
Graph reasoning engine for PharmaGuide knowledge graph
Implements multi-hop traversal, probabilistic inference, and temporal reasoning
"""
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class TraversalStrategy(str, Enum):
    """Graph traversal strategies"""
    BREADTH_FIRST = "breadth_first"
    DEPTH_FIRST = "depth_first"
    BIDIRECTIONAL = "bidirectional"
    SHORTEST_PATH = "shortest_path"


class TemporalRelation(str, Enum):
    """Temporal relationships between events"""
    BEFORE = "before"
    AFTER = "after"
    DURING = "during"
    OVERLAPS = "overlaps"
    CONCURRENT = "concurrent"


@dataclass
class GraphPath:
    """Represents a path through the knowledge graph"""
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    path_length: int = 0
    total_weight: float = 0.0
    confidence: float = 1.0
    
    def add_node(self, node: Dict[str, Any]) -> None:
        """Add a node to the path"""
        self.nodes.append(node)
        self.path_length = len(self.nodes)
    
    def add_edge(self, edge: Dict[str, Any]) -> None:
        """Add an edge to the path"""
        self.edges.append(edge)
        # Update confidence based on edge confidence
        edge_confidence = edge.get('confidence', 1.0)
        self.confidence *= edge_confidence
        # Update total weight
        edge_weight = edge.get('weight', 1.0)
        self.total_weight += edge_weight


@dataclass
class RiskAssessment:
    """Risk assessment result"""
    risk_level: str  # low, moderate, high, critical
    risk_score: float  # 0.0 to 1.0
    contributing_factors: List[str] = field(default_factory=list)
    evidence_paths: List[GraphPath] = field(default_factory=list)
    confidence: float = 0.0
    recommendations: List[str] = field(default_factory=list)


@dataclass
class TemporalEvent:
    """Temporal event in the knowledge graph"""
    event_id: str
    event_type: str
    timestamp: datetime
    entity_id: str
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def time_delta_to(self, other: 'TemporalEvent') -> timedelta:
        """Calculate time difference to another event"""
        return other.timestamp - self.timestamp
    
    def temporal_relation_to(self, other: 'TemporalEvent') -> TemporalRelation:
        """Determine temporal relationship to another event"""
        if self.timestamp < other.timestamp:
            return TemporalRelation.BEFORE
        elif self.timestamp > other.timestamp:
            return TemporalRelation.AFTER
        else:
            return TemporalRelation.CONCURRENT


@dataclass
class TemporalPattern:
    """Pattern of temporal events"""
    pattern_id: str
    events: List[TemporalEvent] = field(default_factory=list)
    pattern_type: str = ""  # trend, cycle, anomaly
    confidence: float = 0.0
    description: str = ""


class GraphReasoningEngine:
    """
    Graph reasoning engine for complex knowledge graph operations
    Implements multi-hop traversal, probabilistic inference, and temporal reasoning
    """
    
    def __init__(self, database_connection):
        """
        Initialize reasoning engine
        
        Args:
            database_connection: Knowledge graph database connection
        """
        self.db = database_connection
        self.logger = logging.getLogger(__name__)
        self.max_traversal_depth = 5
        self.min_confidence_threshold = 0.5
    
    async def multi_hop_traversal(
        self,
        start_node_id: str,
        target_node_type: Optional[str] = None,
        max_hops: int = 3,
        strategy: TraversalStrategy = TraversalStrategy.BREADTH_FIRST,
        edge_filters: Optional[Dict[str, Any]] = None
    ) -> List[GraphPath]:
        """
        Perform multi-hop graph traversal
        
        Args:
            start_node_id: Starting node ID
            target_node_type: Optional target node type to find
            max_hops: Maximum number of hops
            strategy: Traversal strategy
            edge_filters: Optional filters for edges
            
        Returns:
            List of graph paths found
        """
        try:
            self.logger.info(
                f"Starting multi-hop traversal from {start_node_id} "
                f"with max_hops={max_hops}, strategy={strategy}"
            )
            
            if strategy == TraversalStrategy.BREADTH_FIRST:
                return await self._breadth_first_traversal(
                    start_node_id, target_node_type, max_hops, edge_filters
                )
            elif strategy == TraversalStrategy.DEPTH_FIRST:
                return await self._depth_first_traversal(
                    start_node_id, target_node_type, max_hops, edge_filters
                )
            elif strategy == TraversalStrategy.SHORTEST_PATH:
                return await self._shortest_path_traversal(
                    start_node_id, target_node_type, edge_filters
                )
            else:
                self.logger.warning(f"Unknown strategy {strategy}, using BFS")
                return await self._breadth_first_traversal(
                    start_node_id, target_node_type, max_hops, edge_filters
                )
                
        except Exception as e:
            self.logger.error(f"Error in multi-hop traversal: {e}")
            return []
    
    async def _breadth_first_traversal(
        self,
        start_node_id: str,
        target_node_type: Optional[str],
        max_hops: int,
        edge_filters: Optional[Dict[str, Any]]
    ) -> List[GraphPath]:
        """Breadth-first traversal implementation"""
        paths = []
        visited = set()
        queue = [(start_node_id, GraphPath(), 0)]  # (node_id, path, depth)
        
        while queue:
            current_id, current_path, depth = queue.pop(0)
            
            if current_id in visited or depth > max_hops:
                continue
            
            visited.add(current_id)
            
            # Get current node
            try:
                g = self.db.connection.g
                node_result = g.V().has('id', current_id).valueMap(True).toList()
                
                if not node_result:
                    continue
                
                current_node = node_result[0]
                current_path.add_node(current_node)
                
                # Check if we reached target type
                node_label = current_node.get('label', '')
                if target_node_type and node_label == target_node_type:
                    paths.append(current_path)
                    continue
                
                # Get outgoing edges
                edges_result = g.V().has('id', current_id).outE().valueMap(True).toList()
                
                for edge in edges_result:
                    # Apply edge filters
                    if edge_filters and not self._matches_filters(edge, edge_filters):
                        continue
                    
                    # Get target node
                    target_id = edge.get('inV', edge.get('to'))
                    if not target_id or target_id in visited:
                        continue
                    
                    # Create new path
                    new_path = GraphPath(
                        nodes=current_path.nodes.copy(),
                        edges=current_path.edges.copy(),
                        path_length=current_path.path_length,
                        total_weight=current_path.total_weight,
                        confidence=current_path.confidence
                    )
                    new_path.add_edge(edge)
                    
                    queue.append((target_id, new_path, depth + 1))
                    
            except Exception as e:
                self.logger.error(f"Error traversing from {current_id}: {e}")
                continue
        
        return paths
    
    async def _depth_first_traversal(
        self,
        start_node_id: str,
        target_node_type: Optional[str],
        max_hops: int,
        edge_filters: Optional[Dict[str, Any]]
    ) -> List[GraphPath]:
        """Depth-first traversal implementation"""
        paths = []
        visited = set()
        
        async def dfs_helper(node_id: str, current_path: GraphPath, depth: int):
            if node_id in visited or depth > max_hops:
                return
            
            visited.add(node_id)
            
            try:
                g = self.db.connection.g
                node_result = g.V().has('id', node_id).valueMap(True).toList()
                
                if not node_result:
                    return
                
                current_node = node_result[0]
                current_path.add_node(current_node)
                
                # Check if target reached
                node_label = current_node.get('label', '')
                if target_node_type and node_label == target_node_type:
                    paths.append(current_path)
                    return
                
                # Get outgoing edges
                edges_result = g.V().has('id', node_id).outE().valueMap(True).toList()
                
                for edge in edges_result:
                    if edge_filters and not self._matches_filters(edge, edge_filters):
                        continue
                    
                    target_id = edge.get('inV', edge.get('to'))
                    if not target_id or target_id in visited:
                        continue
                    
                    new_path = GraphPath(
                        nodes=current_path.nodes.copy(),
                        edges=current_path.edges.copy(),
                        path_length=current_path.path_length,
                        total_weight=current_path.total_weight,
                        confidence=current_path.confidence
                    )
                    new_path.add_edge(edge)
                    
                    await dfs_helper(target_id, new_path, depth + 1)
                    
            except Exception as e:
                self.logger.error(f"Error in DFS from {node_id}: {e}")
        
        await dfs_helper(start_node_id, GraphPath(), 0)
        return paths
    
    async def _shortest_path_traversal(
        self,
        start_node_id: str,
        target_node_type: Optional[str],
        edge_filters: Optional[Dict[str, Any]]
    ) -> List[GraphPath]:
        """Find shortest paths using Dijkstra-like algorithm"""
        paths = []
        distances = {start_node_id: 0}
        previous = {}
        unvisited = {start_node_id}
        
        try:
            g = self.db.connection.g
            
            while unvisited:
                # Get node with minimum distance
                current_id = min(unvisited, key=lambda x: distances.get(x, float('inf')))
                unvisited.remove(current_id)
                
                # Get current node
                node_result = g.V().has('id', current_id).valueMap(True).toList()
                if not node_result:
                    continue
                
                current_node = node_result[0]
                
                # Check if target reached
                if target_node_type and current_node.get('label') == target_node_type:
                    # Reconstruct path
                    path = self._reconstruct_path(start_node_id, current_id, previous)
                    paths.append(path)
                    continue
                
                # Get neighbors
                edges_result = g.V().has('id', current_id).outE().valueMap(True).toList()
                
                for edge in edges_result:
                    if edge_filters and not self._matches_filters(edge, edge_filters):
                        continue
                    
                    neighbor_id = edge.get('inV', edge.get('to'))
                    if not neighbor_id:
                        continue
                    
                    # Calculate distance (using edge weight)
                    edge_weight = edge.get('weight', 1.0)
                    distance = distances[current_id] + edge_weight
                    
                    if neighbor_id not in distances or distance < distances[neighbor_id]:
                        distances[neighbor_id] = distance
                        previous[neighbor_id] = (current_id, edge)
                        unvisited.add(neighbor_id)
            
        except Exception as e:
            self.logger.error(f"Error in shortest path traversal: {e}")
        
        return paths
    
    def _reconstruct_path(
        self,
        start_id: str,
        end_id: str,
        previous: Dict[str, Tuple[str, Dict[str, Any]]]
    ) -> GraphPath:
        """Reconstruct path from previous nodes dictionary"""
        path = GraphPath()
        current_id = end_id
        nodes_list = []
        edges_list = []
        
        while current_id != start_id:
            if current_id not in previous:
                break
            prev_id, edge = previous[current_id]
            nodes_list.insert(0, {'id': current_id})
            edges_list.insert(0, edge)
            current_id = prev_id
        
        nodes_list.insert(0, {'id': start_id})
        
        for node in nodes_list:
            path.add_node(node)
        for edge in edges_list:
            path.add_edge(edge)
        
        return path
    
    def _matches_filters(self, edge: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if edge matches filters"""
        for key, value in filters.items():
            edge_value = edge.get(key)
            
            if isinstance(value, dict):
                # Handle comparison operators
                if 'min' in value and edge_value < value['min']:
                    return False
                if 'max' in value and edge_value > value['max']:
                    return False
            elif edge_value != value:
                return False
        
        return True
    
    async def calculate_risk_score(
        self,
        entity_id: str,
        patient_context: Optional[Dict[str, Any]] = None,
        risk_factors: Optional[List[str]] = None
    ) -> RiskAssessment:
        """
        Calculate probabilistic risk score for an entity
        
        Args:
            entity_id: Entity to assess risk for
            patient_context: Optional patient context
            risk_factors: Optional list of risk factors to consider
            
        Returns:
            RiskAssessment with risk level and contributing factors
        """
        try:
            self.logger.info(f"Calculating risk score for entity {entity_id}")
            
            # Find all risk-related paths
            risk_paths = await self.multi_hop_traversal(
                start_node_id=entity_id,
                target_node_type="SideEffect",
                max_hops=3,
                edge_filters={'confidence': {'min': self.min_confidence_threshold}}
            )
            
            # Calculate base risk score from paths
            base_risk = self._calculate_base_risk(risk_paths)
            
            # Adjust for patient context
            adjusted_risk = base_risk
            contributing_factors = []
            
            if patient_context:
                risk_adjustment, factors = self._adjust_risk_for_patient(
                    base_risk, patient_context, risk_factors
                )
                adjusted_risk = risk_adjustment
                contributing_factors.extend(factors)
            
            # Determine risk level
            risk_level = self._determine_risk_level(adjusted_risk)
            
            # Generate recommendations
            recommendations = self._generate_risk_recommendations(
                risk_level, contributing_factors
            )
            
            # Calculate overall confidence
            confidence = self._calculate_path_confidence(risk_paths)
            
            return RiskAssessment(
                risk_level=risk_level,
                risk_score=adjusted_risk,
                contributing_factors=contributing_factors,
                evidence_paths=risk_paths,
                confidence=confidence,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk score: {e}")
            return RiskAssessment(
                risk_level="unknown",
                risk_score=0.0,
                confidence=0.0
            )
    
    def _calculate_base_risk(self, paths: List[GraphPath]) -> float:
        """Calculate base risk from graph paths"""
        if not paths:
            return 0.0
        
        # Aggregate risk from all paths
        total_risk = 0.0
        for path in paths:
            # Risk increases with path confidence and decreases with path length
            path_risk = path.confidence / max(path.path_length, 1)
            
            # Weight by edge properties (severity, frequency)
            for edge in path.edges:
                severity_weight = self._get_severity_weight(edge.get('severity'))
                frequency = edge.get('frequency', 0.5)
                path_risk *= (severity_weight * frequency)
            
            total_risk += path_risk
        
        # Normalize to 0-1 range
        normalized_risk = min(total_risk / len(paths), 1.0)
        return normalized_risk
    
    def _get_severity_weight(self, severity: Optional[str]) -> float:
        """Get numeric weight for severity level"""
        severity_weights = {
            'minor': 0.25,
            'moderate': 0.5,
            'major': 0.75,
            'contraindicated': 1.0,
            'critical': 1.0
        }
        return severity_weights.get(severity, 0.5) if severity else 0.5
    
    def _adjust_risk_for_patient(
        self,
        base_risk: float,
        patient_context: Dict[str, Any],
        risk_factors: Optional[List[str]]
    ) -> Tuple[float, List[str]]:
        """Adjust risk based on patient context"""
        adjusted_risk = base_risk
        contributing_factors = []
        
        # Age adjustment
        demographics = patient_context.get('demographics', {})
        age = demographics.get('age', 0)
        if age > 65:
            adjusted_risk *= 1.2
            contributing_factors.append("Advanced age (>65)")
        elif age < 18:
            adjusted_risk *= 1.15
            contributing_factors.append("Pediatric patient")
        
        # Condition adjustments
        conditions = patient_context.get('conditions', [])
        high_risk_conditions = ['diabetes', 'heart_disease', 'kidney_disease', 'liver_disease']
        for condition in conditions:
            if condition.lower() in high_risk_conditions:
                adjusted_risk *= 1.1
                contributing_factors.append(f"Pre-existing condition: {condition}")
        
        # Risk factor adjustments
        patient_risk_factors = patient_context.get('risk_factors', [])
        if risk_factors:
            for factor in risk_factors:
                if factor in patient_risk_factors:
                    adjusted_risk *= 1.05
                    contributing_factors.append(f"Risk factor: {factor}")
        
        # Medication interactions
        medications = patient_context.get('medications', [])
        if len(medications) > 5:
            adjusted_risk *= 1.1
            contributing_factors.append("Polypharmacy (>5 medications)")
        
        # Cap at 1.0
        adjusted_risk = min(adjusted_risk, 1.0)
        
        return adjusted_risk, contributing_factors
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """Determine risk level from score"""
        if risk_score < 0.25:
            return "low"
        elif risk_score < 0.5:
            return "moderate"
        elif risk_score < 0.75:
            return "high"
        else:
            return "critical"
    
    def _generate_risk_recommendations(
        self,
        risk_level: str,
        contributing_factors: List[str]
    ) -> List[str]:
        """Generate recommendations based on risk level"""
        recommendations = []
        
        if risk_level == "critical":
            recommendations.append("Immediate consultation with healthcare provider required")
            recommendations.append("Consider alternative medications")
        elif risk_level == "high":
            recommendations.append("Consult healthcare provider before use")
            recommendations.append("Close monitoring recommended")
        elif risk_level == "moderate":
            recommendations.append("Discuss with healthcare provider")
            recommendations.append("Monitor for side effects")
        else:
            recommendations.append("Standard monitoring recommended")
        
        # Add specific recommendations based on factors
        if any("age" in f.lower() for f in contributing_factors):
            recommendations.append("Age-appropriate dosing may be required")
        
        if any("polypharmacy" in f.lower() for f in contributing_factors):
            recommendations.append("Review all medications for interactions")
        
        return recommendations
    
    def _calculate_path_confidence(self, paths: List[GraphPath]) -> float:
        """Calculate overall confidence from paths"""
        if not paths:
            return 0.0
        
        # Average confidence across all paths
        total_confidence = sum(path.confidence for path in paths)
        return total_confidence / len(paths)
    
    async def analyze_temporal_patterns(
        self,
        entity_id: str,
        start_time: datetime,
        end_time: datetime,
        pattern_types: Optional[List[str]] = None
    ) -> List[TemporalPattern]:
        """
        Analyze temporal patterns in the knowledge graph
        
        Args:
            entity_id: Entity to analyze
            start_time: Start of time window
            end_time: End of time window
            pattern_types: Optional list of pattern types to detect
            
        Returns:
            List of detected temporal patterns
        """
        try:
            self.logger.info(
                f"Analyzing temporal patterns for {entity_id} "
                f"from {start_time} to {end_time}"
            )
            
            # Get temporal events for entity
            events = await self._get_temporal_events(entity_id, start_time, end_time)
            
            if not events:
                return []
            
            patterns = []
            
            # Detect trends
            if not pattern_types or 'trend' in pattern_types:
                trend_patterns = self._detect_trends(events)
                patterns.extend(trend_patterns)
            
            # Detect cycles
            if not pattern_types or 'cycle' in pattern_types:
                cycle_patterns = self._detect_cycles(events)
                patterns.extend(cycle_patterns)
            
            # Detect anomalies
            if not pattern_types or 'anomaly' in pattern_types:
                anomaly_patterns = self._detect_anomalies(events)
                patterns.extend(anomaly_patterns)
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Error analyzing temporal patterns: {e}")
            return []
    
    async def _get_temporal_events(
        self,
        entity_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[TemporalEvent]:
        """Get temporal events for entity within time window"""
        events = []
        
        try:
            g = self.db.connection.g
            
            # Query temporal nodes connected to entity
            results = g.V().has('id', entity_id).outE('HAS_EVENT').inV().valueMap(True).toList()
            
            for result in results:
                # Parse timestamp
                timestamp_str = result.get('timestamp')
                if not timestamp_str:
                    continue
                
                try:
                    timestamp = datetime.fromisoformat(str(timestamp_str))
                except (ValueError, TypeError):
                    continue
                
                # Filter by time window
                if start_time <= timestamp <= end_time:
                    event = TemporalEvent(
                        event_id=result.get('id', ''),
                        event_type=result.get('event_type', ''),
                        timestamp=timestamp,
                        entity_id=entity_id,
                        properties=result
                    )
                    events.append(event)
            
            # Sort by timestamp
            events.sort(key=lambda e: e.timestamp)
            
        except Exception as e:
            self.logger.error(f"Error getting temporal events: {e}")
        
        return events
    
    def _detect_trends(self, events: List[TemporalEvent]) -> List[TemporalPattern]:
        """Detect trends in temporal events"""
        patterns = []
        
        if len(events) < 3:
            return patterns
        
        # Simple trend detection: check if values are increasing/decreasing
        values = []
        for event in events:
            value = event.properties.get('value', event.properties.get('severity', 0))
            if isinstance(value, (int, float)):
                values.append(value)
        
        if len(values) < 3:
            return patterns
        
        # Calculate trend direction
        increasing = sum(1 for i in range(len(values)-1) if values[i+1] > values[i])
        decreasing = sum(1 for i in range(len(values)-1) if values[i+1] < values[i])
        
        if increasing > len(values) * 0.6:
            pattern = TemporalPattern(
                pattern_id=f"trend_{events[0].entity_id}",
                events=events,
                pattern_type="trend",
                confidence=increasing / (len(values) - 1),
                description="Increasing trend detected"
            )
            patterns.append(pattern)
        elif decreasing > len(values) * 0.6:
            pattern = TemporalPattern(
                pattern_id=f"trend_{events[0].entity_id}",
                events=events,
                pattern_type="trend",
                confidence=decreasing / (len(values) - 1),
                description="Decreasing trend detected"
            )
            patterns.append(pattern)
        
        return patterns
    
    def _detect_cycles(self, events: List[TemporalEvent]) -> List[TemporalPattern]:
        """Detect cyclic patterns in temporal events"""
        patterns = []
        
        if len(events) < 4:
            return patterns
        
        # Simple cycle detection: look for repeating patterns
        event_types = [e.event_type for e in events]
        
        # Check for repeating sequences
        for cycle_length in range(2, len(event_types) // 2 + 1):
            is_cycle = True
            for i in range(cycle_length, len(event_types)):
                if event_types[i] != event_types[i % cycle_length]:
                    is_cycle = False
                    break
            
            if is_cycle:
                pattern = TemporalPattern(
                    pattern_id=f"cycle_{events[0].entity_id}",
                    events=events,
                    pattern_type="cycle",
                    confidence=0.8,
                    description=f"Cyclic pattern detected with period {cycle_length}"
                )
                patterns.append(pattern)
                break
        
        return patterns
    
    def _detect_anomalies(self, events: List[TemporalEvent]) -> List[TemporalPattern]:
        """Detect anomalies in temporal events"""
        patterns = []
        
        if len(events) < 5:
            return patterns
        
        # Extract numeric values
        values = []
        for event in events:
            value = event.properties.get('value', event.properties.get('severity', 0))
            if isinstance(value, (int, float)):
                values.append((event, value))
        
        if len(values) < 5:
            return patterns
        
        # Calculate mean and standard deviation
        mean = sum(v for _, v in values) / len(values)
        variance = sum((v - mean) ** 2 for _, v in values) / len(values)
        std_dev = variance ** 0.5
        
        # Detect outliers (values > 2 standard deviations from mean)
        anomalous_events = []
        for event, value in values:
            if abs(value - mean) > 2 * std_dev:
                anomalous_events.append(event)
        
        if anomalous_events:
            pattern = TemporalPattern(
                pattern_id=f"anomaly_{events[0].entity_id}",
                events=anomalous_events,
                pattern_type="anomaly",
                confidence=0.7,
                description=f"Detected {len(anomalous_events)} anomalous events"
            )
            patterns.append(pattern)
        
        return patterns
    
    async def find_interaction_chains(
        self,
        drug_ids: List[str],
        max_chain_length: int = 3
    ) -> List[GraphPath]:
        """
        Find interaction chains between multiple drugs
        
        Args:
            drug_ids: List of drug IDs to check
            max_chain_length: Maximum length of interaction chains
            
        Returns:
            List of interaction paths
        """
        try:
            self.logger.info(f"Finding interaction chains for {len(drug_ids)} drugs")
            
            all_chains = []
            
            # Check pairwise interactions
            for i, drug_a in enumerate(drug_ids):
                for drug_b in drug_ids[i+1:]:
                    chains = await self.multi_hop_traversal(
                        start_node_id=drug_a,
                        target_node_type="Drug",
                        max_hops=max_chain_length,
                        edge_filters={'label': 'INTERACTS_WITH'}
                    )
                    
                    # Filter chains that end at drug_b
                    relevant_chains = [
                        chain for chain in chains
                        if chain.nodes and chain.nodes[-1].get('id') == drug_b
                    ]
                    
                    all_chains.extend(relevant_chains)
            
            # Sort by risk (confidence * severity)
            all_chains.sort(
                key=lambda c: c.confidence * self._get_chain_severity(c),
                reverse=True
            )
            
            return all_chains
            
        except Exception as e:
            self.logger.error(f"Error finding interaction chains: {e}")
            return []
    
    def _get_chain_severity(self, chain: GraphPath) -> float:
        """Calculate overall severity of interaction chain"""
        if not chain.edges:
            return 0.0
        
        severities = []
        for edge in chain.edges:
            severity = edge.get('severity', 'minor')
            severities.append(self._get_severity_weight(severity))
        
        # Return maximum severity in chain
        return max(severities) if severities else 0.0
    
    async def infer_missing_relationships(
        self,
        entity_id: str,
        relationship_type: str,
        confidence_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Infer missing relationships using graph patterns
        
        Args:
            entity_id: Entity to infer relationships for
            relationship_type: Type of relationship to infer
            confidence_threshold: Minimum confidence for inference
            
        Returns:
            List of inferred relationships with confidence scores
        """
        try:
            self.logger.info(
                f"Inferring {relationship_type} relationships for {entity_id}"
            )
            
            inferred = []
            
            # Find similar entities
            similar_entities = await self._find_similar_entities(entity_id)
            
            # Check what relationships similar entities have
            for similar_entity in similar_entities:
                similarity_score = similar_entity.get('similarity', 0.0)
                
                if similarity_score < confidence_threshold:
                    continue
                
                # Get relationships of similar entity
                g = self.db.connection.g
                relationships = g.V().has('id', similar_entity['id']).outE(relationship_type).valueMap(True).toList()
                
                for rel in relationships:
                    target_id = rel.get('inV', rel.get('to'))
                    
                    # Infer this relationship for original entity
                    inferred.append({
                        'source_id': entity_id,
                        'target_id': target_id,
                        'relationship_type': relationship_type,
                        'confidence': similarity_score * rel.get('confidence', 1.0),
                        'inferred_from': similar_entity['id'],
                        'method': 'similarity_based'
                    })
            
            return inferred
            
        except Exception as e:
            self.logger.error(f"Error inferring relationships: {e}")
            return []
    
    async def _find_similar_entities(
        self,
        entity_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find entities similar to given entity"""
        try:
            g = self.db.connection.g
            
            # Get entity properties
            entity_result = g.V().has('id', entity_id).valueMap(True).toList()
            if not entity_result:
                return []
            
            entity = entity_result[0]
            entity_label = entity.get('label', '')
            
            # Find entities with same label
            similar = g.V().hasLabel(entity_label).limit(limit).valueMap(True).toList()
            
            # Calculate similarity scores (simplified)
            similar_with_scores = []
            for other in similar:
                if other.get('id') == entity_id:
                    continue
                
                similarity = self._calculate_similarity(entity, other)
                similar_with_scores.append({
                    'id': other.get('id'),
                    'similarity': similarity,
                    'properties': other
                })
            
            # Sort by similarity
            similar_with_scores.sort(key=lambda x: x['similarity'], reverse=True)
            
            return similar_with_scores
            
        except Exception as e:
            self.logger.error(f"Error finding similar entities: {e}")
            return []
    
    def _calculate_similarity(
        self,
        entity1: Dict[str, Any],
        entity2: Dict[str, Any]
    ) -> float:
        """Calculate similarity between two entities"""
        # Simple similarity based on shared properties
        shared_props = 0
        total_props = 0
        
        all_keys = set(entity1.keys()) | set(entity2.keys())
        
        for key in all_keys:
            if key in ['id', 'label', 'created_at', 'updated_at']:
                continue
            
            total_props += 1
            
            val1 = entity1.get(key)
            val2 = entity2.get(key)
            
            if val1 == val2:
                shared_props += 1
        
        if total_props == 0:
            return 0.0
        
        return shared_props / total_props


# Global reasoning engine instance (will be initialized with database connection)
reasoning_engine = None


def initialize_reasoning_engine(database_connection):
    """Initialize global reasoning engine instance"""
    global reasoning_engine
    reasoning_engine = GraphReasoningEngine(database_connection)
    return reasoning_engine
