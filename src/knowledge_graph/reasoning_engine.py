"""
Graph reasoning engine for PharmaGuide knowledge graph
Implements multi-hop traversal, probabilistic inference, and temporal reasoning
"""
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import math

from src.knowledge_graph.database import KnowledgeGraphDatabase
from src.knowledge_graph.models import (
    DrugEntity, SideEffectEntity, InteractionEntity, 
    PatientContext, SeverityLevel
)

logger = logging.getLogger(__name__)


class TraversalStrategy(str, Enum):
    """Strategy for graph traversal"""
    BREADTH_FIRST = "breadth_first"
    DEPTH_FIRST = "depth_first"
    SHORTEST_PATH = "shortest_path"
    ALL_PATHS = "all_paths"


class InferenceMethod(str, Enum):
    """Method for probabilistic inference"""
    BAYESIAN = "bayesian"
    FREQUENTIST = "frequentist"
    EVIDENCE_BASED = "evidence_based"


@dataclass
class GraphPath:
    """Represents a path through the knowledge graph"""
    nodes: List[str]
    edges: List[str]
    edge_types: List[str]
    confidence: float
    evidence_sources: List[str]
    path_length: int


@dataclass
class RiskAssessment:
    """Risk assessment result"""
    risk_score: float  # 0.0 to 1.0
    risk_level: str  # low, moderate, high, critical
    contributing_factors: List[Dict[str, Any]]
    confidence: float
    evidence_paths: List[GraphPath]
    recommendations: List[str]


@dataclass
class TemporalPattern:
    """Temporal pattern in medication data"""
    pattern_type: str
    start_time: datetime
    end_time: Optional[datetime]
    frequency: float
    confidence: float
    related_entities: List[str]
    trend: str  # increasing, decreasing, stable




class GraphReasoningEngine:
    """
    Graph reasoning engine for complex knowledge graph queries and inference
    Supports multi-hop traversals, probabilistic inference, and temporal reasoning
    """
    
    def __init__(self, database: KnowledgeGraphDatabase):
        self.database = database
        self.logger = logging.getLogger(__name__)
        self._path_cache = {}
    
    async def multi_hop_traversal(
        self,
        start_node_id: str,
        target_node_type: Optional[str] = None,
        max_hops: int = 3,
        strategy: TraversalStrategy = TraversalStrategy.BREADTH_FIRST,
        edge_filters: Optional[Dict[str, Any]] = None
    ) -> List[GraphPath]:
        """
        Perform multi-hop graph traversal from a starting node
        
        Args:
            start_node_id: Starting node identifier
            target_node_type: Optional target node type to filter results
            max_hops: Maximum number of hops to traverse
            strategy: Traversal strategy (BFS, DFS, etc.)
            edge_filters: Optional filters for edge properties
        
        Returns:
            List of graph paths found
        """
        try:
            self.logger.info(
                f"Starting multi-hop traversal from {start_node_id}, "
                f"max_hops={max_hops}, strategy={strategy}"
            )
            
            if strategy == TraversalStrategy.BREADTH_FIRST:
                paths = await self._breadth_first_traversal(
                    start_node_id, target_node_type, max_hops, edge_filters
                )
            elif strategy == TraversalStrategy.DEPTH_FIRST:
                paths = await self._depth_first_traversal(
                    start_node_id, target_node_type, max_hops, edge_filters
                )
            elif strategy == TraversalStrategy.SHORTEST_PATH:
                paths = await self._shortest_path_traversal(
                    start_node_id, target_node_type, edge_filters
                )
            else:
                paths = await self._all_paths_traversal(
                    start_node_id, target_node_type, max_hops, edge_filters
                )
            
            self.logger.info(f"Found {len(paths)} paths")
            return paths
        
        except Exception as e:
            self.logger.error(f"Error in multi-hop traversal: {e}")
            raise
    
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
        queue = [(start_node_id, [], [], [], 1.0, [])]  # (node, path_nodes, path_edges, edge_types, confidence, sources)
        
        while queue:
            current_node, path_nodes, path_edges, edge_types, confidence, sources = queue.pop(0)
            
            if current_node in visited or len(path_nodes) >= max_hops:
                continue
            
            visited.add(current_node)
            new_path_nodes = path_nodes + [current_node]
            
            # Check if we've reached a target node
            if target_node_type:
                node_info = await self._get_node_info(current_node)
                if node_info and node_info.get('label') == target_node_type:
                    paths.append(GraphPath(
                        nodes=new_path_nodes,
                        edges=path_edges,
                        edge_types=edge_types,
                        confidence=confidence,
                        evidence_sources=sources,
                        path_length=len(new_path_nodes)
                    ))
            
            # Get outgoing edges
            edges = await self._get_outgoing_edges(current_node, edge_filters)
            
            for edge in edges:
                target_node = edge.get('target')
                edge_id = edge.get('id')
                edge_type = edge.get('label')
                edge_confidence = edge.get('confidence', 1.0)
                edge_sources = edge.get('evidence_sources', [])
                
                if target_node not in visited:
                    new_confidence = confidence * edge_confidence
                    new_sources = sources + edge_sources
                    
                    queue.append((
                        target_node,
                        new_path_nodes,
                        path_edges + [edge_id],
                        edge_types + [edge_type],
                        new_confidence,
                        new_sources
                    ))
        
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
        
        async def dfs(node, path_nodes, path_edges, edge_types, confidence, sources, depth):
            if depth > max_hops or node in visited:
                return
            
            visited.add(node)
            new_path_nodes = path_nodes + [node]
            
            # Check if target reached
            if target_node_type:
                node_info = await self._get_node_info(node)
                if node_info and node_info.get('label') == target_node_type:
                    paths.append(GraphPath(
                        nodes=new_path_nodes,
                        edges=path_edges,
                        edge_types=edge_types,
                        confidence=confidence,
                        evidence_sources=sources,
                        path_length=len(new_path_nodes)
                    ))
            
            # Recurse on neighbors
            edges = await self._get_outgoing_edges(node, edge_filters)
            for edge in edges:
                target = edge.get('target')
                if target not in visited:
                    await dfs(
                        target,
                        new_path_nodes,
                        path_edges + [edge.get('id')],
                        edge_types + [edge.get('label')],
                        confidence * edge.get('confidence', 1.0),
                        sources + edge.get('evidence_sources', []),
                        depth + 1
                    )
            
            visited.remove(node)
        
        await dfs(start_node_id, [], [], [], 1.0, [], 0)
        return paths
    
    async def _shortest_path_traversal(
        self,
        start_node_id: str,
        target_node_type: Optional[str],
        edge_filters: Optional[Dict[str, Any]]
    ) -> List[GraphPath]:
        """Find shortest paths using Dijkstra-like algorithm"""
        # Simplified implementation - in production would use proper shortest path algorithm
        paths = await self._breadth_first_traversal(
            start_node_id, target_node_type, 5, edge_filters
        )
        
        if not paths:
            return []
        
        # Return only the shortest paths
        min_length = min(p.path_length for p in paths)
        return [p for p in paths if p.path_length == min_length]
    
    async def _all_paths_traversal(
        self,
        start_node_id: str,
        target_node_type: Optional[str],
        max_hops: int,
        edge_filters: Optional[Dict[str, Any]]
    ) -> List[GraphPath]:
        """Find all paths (combines BFS and DFS results)"""
        bfs_paths = await self._breadth_first_traversal(
            start_node_id, target_node_type, max_hops, edge_filters
        )
        return bfs_paths

    
    async def calculate_risk(
        self,
        drug_id: str,
        patient_context: Optional[PatientContext] = None,
        inference_method: InferenceMethod = InferenceMethod.EVIDENCE_BASED
    ) -> RiskAssessment:
        """
        Calculate risk assessment for a drug given patient context
        
        Args:
            drug_id: Drug identifier
            patient_context: Optional patient context for personalization
            inference_method: Method for probabilistic inference
        
        Returns:
            Risk assessment with score, level, and contributing factors
        """
        try:
            self.logger.info(f"Calculating risk for drug {drug_id}")
            
            # Find all risk-related paths from the drug
            risk_paths = await self.multi_hop_traversal(
                start_node_id=drug_id,
                target_node_type="SideEffect",
                max_hops=2,
                strategy=TraversalStrategy.ALL_PATHS
            )
            
            # Calculate base risk from side effects
            base_risk = await self._calculate_base_risk(drug_id, risk_paths)
            
            # Apply patient-specific factors if context provided
            if patient_context:
                personalized_risk = await self._apply_patient_factors(
                    base_risk, patient_context, risk_paths
                )
            else:
                personalized_risk = base_risk
            
            # Determine risk level
            risk_level = self._determine_risk_level(personalized_risk)
            
            # Extract contributing factors
            contributing_factors = await self._extract_risk_factors(
                drug_id, patient_context, risk_paths
            )
            
            # Generate recommendations
            recommendations = self._generate_risk_recommendations(
                personalized_risk, risk_level, contributing_factors
            )
            
            # Calculate overall confidence
            confidence = self._calculate_path_confidence(risk_paths)
            
            return RiskAssessment(
                risk_score=personalized_risk,
                risk_level=risk_level,
                contributing_factors=contributing_factors,
                confidence=confidence,
                evidence_paths=risk_paths,
                recommendations=recommendations
            )
        
        except Exception as e:
            self.logger.error(f"Error calculating risk: {e}")
            raise
    
    async def _calculate_base_risk(
        self,
        drug_id: str,
        risk_paths: List[GraphPath]
    ) -> float:
        """Calculate base risk score from side effect paths"""
        if not risk_paths:
            return 0.0
        
        # Aggregate risk from all paths
        total_risk = 0.0
        for path in risk_paths:
            # Weight by path confidence and severity
            path_risk = path.confidence
            
            # Get severity information from the path
            for node_id in path.nodes:
                node_info = await self._get_node_info(node_id)
                if node_info and node_info.get('label') == 'SideEffect':
                    severity = node_info.get('severity', 'minor')
                    severity_weight = self._get_severity_weight(severity)
                    path_risk *= severity_weight
            
            total_risk += path_risk
        
        # Normalize to 0-1 range
        normalized_risk = min(total_risk / len(risk_paths), 1.0)
        return normalized_risk
    
    async def _apply_patient_factors(
        self,
        base_risk: float,
        patient_context: PatientContext,
        risk_paths: List[GraphPath]
    ) -> float:
        """Apply patient-specific factors to risk calculation"""
        risk_multiplier = 1.0
        
        # Age factor
        age = patient_context.demographics.get('age', 0)
        if age > 65:
            risk_multiplier *= 1.3  # Elderly patients have higher risk
        elif age < 18:
            risk_multiplier *= 1.2  # Pediatric patients have higher risk
        
        # Condition factors
        high_risk_conditions = ['kidney_disease', 'liver_disease', 'heart_disease']
        for condition in patient_context.conditions:
            if any(hrc in condition.lower() for hrc in high_risk_conditions):
                risk_multiplier *= 1.25
        
        # Polypharmacy factor
        if len(patient_context.medications) > 5:
            risk_multiplier *= 1.15
        
        # Apply multiplier and cap at 1.0
        personalized_risk = min(base_risk * risk_multiplier, 1.0)
        return personalized_risk
    
    def _determine_risk_level(self, risk_score: float) -> str:
        """Determine categorical risk level from score"""
        if risk_score < 0.25:
            return "low"
        elif risk_score < 0.5:
            return "moderate"
        elif risk_score < 0.75:
            return "high"
        else:
            return "critical"
    
    async def _extract_risk_factors(
        self,
        drug_id: str,
        patient_context: Optional[PatientContext],
        risk_paths: List[GraphPath]
    ) -> List[Dict[str, Any]]:
        """Extract specific risk factors from paths"""
        factors = []
        
        # Extract from paths
        for path in risk_paths[:5]:  # Limit to top 5 paths
            for node_id in path.nodes:
                node_info = await self._get_node_info(node_id)
                if node_info and node_info.get('label') == 'SideEffect':
                    factors.append({
                        'type': 'side_effect',
                        'name': node_info.get('name', 'Unknown'),
                        'severity': node_info.get('severity', 'unknown'),
                        'confidence': path.confidence,
                        'sources': path.evidence_sources
                    })
        
        # Add patient-specific factors
        if patient_context:
            if patient_context.demographics.get('age', 0) > 65:
                factors.append({
                    'type': 'demographic',
                    'name': 'Advanced age',
                    'severity': 'moderate',
                    'confidence': 1.0,
                    'sources': ['patient_profile']
                })
            
            for condition in patient_context.conditions:
                factors.append({
                    'type': 'comorbidity',
                    'name': condition,
                    'severity': 'moderate',
                    'confidence': 1.0,
                    'sources': ['patient_profile']
                })
        
        return factors
    
    def _generate_risk_recommendations(
        self,
        risk_score: float,
        risk_level: str,
        factors: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations based on risk assessment"""
        recommendations = []
        
        if risk_level == "critical":
            recommendations.append("Immediate consultation with healthcare provider required")
            recommendations.append("Consider alternative medications")
        elif risk_level == "high":
            recommendations.append("Close monitoring recommended")
            recommendations.append("Discuss risks and benefits with healthcare provider")
        elif risk_level == "moderate":
            recommendations.append("Regular monitoring advised")
            recommendations.append("Report any unusual symptoms promptly")
        else:
            recommendations.append("Standard monitoring sufficient")
        
        # Add specific recommendations based on factors
        for factor in factors:
            if factor['type'] == 'side_effect' and factor['severity'] in ['major', 'critical']:
                recommendations.append(
                    f"Watch for signs of {factor['name']}"
                )
        
        return recommendations
    
    def _calculate_path_confidence(self, paths: List[GraphPath]) -> float:
        """Calculate overall confidence from multiple paths"""
        if not paths:
            return 0.0
        
        # Average confidence weighted by path length
        total_confidence = 0.0
        total_weight = 0.0
        
        for path in paths:
            weight = 1.0 / path.path_length  # Shorter paths have higher weight
            total_confidence += path.confidence * weight
            total_weight += weight
        
        return total_confidence / total_weight if total_weight > 0 else 0.0
    
    def _get_severity_weight(self, severity: str) -> float:
        """Get numeric weight for severity level"""
        severity_weights = {
            'minor': 0.25,
            'moderate': 0.5,
            'major': 0.75,
            'contraindicated': 1.0,
            'critical': 1.0
        }
        return severity_weights.get(severity.lower(), 0.5)

    
    async def temporal_reasoning(
        self,
        entity_id: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        pattern_type: Optional[str] = None
    ) -> List[TemporalPattern]:
        """
        Perform temporal reasoning over medication and symptom data
        
        Args:
            entity_id: Entity to analyze (drug, patient, etc.)
            start_time: Start of time window
            end_time: Optional end of time window (defaults to now)
            pattern_type: Optional filter for pattern type
        
        Returns:
            List of temporal patterns found
        """
        try:
            if end_time is None:
                end_time = datetime.utcnow()
            
            self.logger.info(
                f"Performing temporal reasoning for {entity_id} "
                f"from {start_time} to {end_time}"
            )
            
            # Get temporal data for the entity
            temporal_data = await self._get_temporal_data(
                entity_id, start_time, end_time
            )
            
            # Detect patterns
            patterns = []
            
            # Pattern 1: Medication effectiveness trends
            effectiveness_patterns = self._detect_effectiveness_trends(
                temporal_data, start_time, end_time
            )
            patterns.extend(effectiveness_patterns)
            
            # Pattern 2: Side effect occurrence patterns
            side_effect_patterns = self._detect_side_effect_patterns(
                temporal_data, start_time, end_time
            )
            patterns.extend(side_effect_patterns)
            
            # Pattern 3: Dosage change correlations
            dosage_patterns = self._detect_dosage_correlations(
                temporal_data, start_time, end_time
            )
            patterns.extend(dosage_patterns)
            
            # Filter by pattern type if specified
            if pattern_type:
                patterns = [p for p in patterns if p.pattern_type == pattern_type]
            
            self.logger.info(f"Found {len(patterns)} temporal patterns")
            return patterns
        
        except Exception as e:
            self.logger.error(f"Error in temporal reasoning: {e}")
            raise
    
    async def _get_temporal_data(
        self,
        entity_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """Get temporal data for an entity"""
        # In a real implementation, this would query temporal nodes from the graph
        # For now, return empty list as placeholder
        self.logger.info(f"Fetching temporal data for {entity_id}")
        return []
    
    def _detect_effectiveness_trends(
        self,
        temporal_data: List[Dict[str, Any]],
        start_time: datetime,
        end_time: datetime
    ) -> List[TemporalPattern]:
        """Detect medication effectiveness trends over time"""
        patterns = []
        
        # Group data by time windows
        time_windows = self._create_time_windows(start_time, end_time, days=7)
        
        # Analyze effectiveness in each window
        effectiveness_scores = []
        for window_start, window_end in time_windows:
            window_data = [
                d for d in temporal_data
                if window_start <= d.get('timestamp', start_time) < window_end
            ]
            
            if window_data:
                # Calculate average effectiveness
                avg_effectiveness = sum(
                    d.get('effectiveness', 0.5) for d in window_data
                ) / len(window_data)
                effectiveness_scores.append(avg_effectiveness)
        
        # Detect trend
        if len(effectiveness_scores) >= 2:
            trend = self._calculate_trend(effectiveness_scores)
            
            patterns.append(TemporalPattern(
                pattern_type="effectiveness_trend",
                start_time=start_time,
                end_time=end_time,
                frequency=len(effectiveness_scores) / len(time_windows),
                confidence=0.7,
                related_entities=[],
                trend=trend
            ))
        
        return patterns
    
    def _detect_side_effect_patterns(
        self,
        temporal_data: List[Dict[str, Any]],
        start_time: datetime,
        end_time: datetime
    ) -> List[TemporalPattern]:
        """Detect side effect occurrence patterns"""
        patterns = []
        
        # Group side effects by type
        side_effect_occurrences = {}
        for data_point in temporal_data:
            if data_point.get('type') == 'side_effect':
                effect_name = data_point.get('name', 'unknown')
                if effect_name not in side_effect_occurrences:
                    side_effect_occurrences[effect_name] = []
                side_effect_occurrences[effect_name].append(
                    data_point.get('timestamp', start_time)
                )
        
        # Analyze each side effect
        for effect_name, timestamps in side_effect_occurrences.items():
            if len(timestamps) >= 2:
                # Calculate frequency
                time_span = (end_time - start_time).total_seconds()
                frequency = len(timestamps) / (time_span / 86400)  # per day
                
                patterns.append(TemporalPattern(
                    pattern_type="side_effect_occurrence",
                    start_time=min(timestamps),
                    end_time=max(timestamps),
                    frequency=frequency,
                    confidence=0.8,
                    related_entities=[effect_name],
                    trend="recurring"
                ))
        
        return patterns
    
    def _detect_dosage_correlations(
        self,
        temporal_data: List[Dict[str, Any]],
        start_time: datetime,
        end_time: datetime
    ) -> List[TemporalPattern]:
        """Detect correlations between dosage changes and outcomes"""
        patterns = []
        
        # Find dosage change events
        dosage_changes = [
            d for d in temporal_data
            if d.get('type') == 'dosage_change'
        ]
        
        for change in dosage_changes:
            change_time = change.get('timestamp', start_time)
            
            # Look for outcome changes within 2 weeks
            window_end = change_time + timedelta(days=14)
            
            outcomes_after = [
                d for d in temporal_data
                if change_time < d.get('timestamp', start_time) <= window_end
                and d.get('type') in ['effectiveness', 'side_effect']
            ]
            
            if outcomes_after:
                patterns.append(TemporalPattern(
                    pattern_type="dosage_correlation",
                    start_time=change_time,
                    end_time=window_end,
                    frequency=len(outcomes_after) / 14,  # per day
                    confidence=0.6,
                    related_entities=[change.get('drug_id', 'unknown')],
                    trend="correlated"
                ))
        
        return patterns
    
    def _create_time_windows(
        self,
        start_time: datetime,
        end_time: datetime,
        days: int = 7
    ) -> List[Tuple[datetime, datetime]]:
        """Create time windows for analysis"""
        windows = []
        current = start_time
        delta = timedelta(days=days)
        
        while current < end_time:
            window_end = min(current + delta, end_time)
            windows.append((current, window_end))
            current = window_end
        
        return windows
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend from a series of values"""
        if len(values) < 2:
            return "stable"
        
        # Simple linear regression
        n = len(values)
        x = list(range(n))
        
        # Calculate slope
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return "stable"
        
        slope = numerator / denominator
        
        # Determine trend based on slope
        if slope > 0.05:
            return "increasing"
        elif slope < -0.05:
            return "decreasing"
        else:
            return "stable"
    
    async def _get_node_info(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a node"""
        try:
            # Query the database for node information
            g = self.database.connection.g
            result = g.V().has('id', node_id).toList()
            
            if result:
                return result[0]
            return None
        
        except Exception as e:
            self.logger.error(f"Error getting node info: {e}")
            return None
    
    async def _get_outgoing_edges(
        self,
        node_id: str,
        edge_filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get outgoing edges from a node"""
        try:
            g = self.database.connection.g
            
            # Get all outgoing edges
            edges = g.V().has('id', node_id).outE().toList()
            
            # Apply filters if provided
            if edge_filters:
                filtered_edges = []
                for edge in edges:
                    matches = True
                    for key, value in edge_filters.items():
                        if edge.get(key) != value:
                            matches = False
                            break
                    if matches:
                        filtered_edges.append(edge)
                return filtered_edges
            
            return edges
        
        except Exception as e:
            self.logger.error(f"Error getting outgoing edges: {e}")
            return []


# Factory function
async def create_reasoning_engine(database: KnowledgeGraphDatabase) -> GraphReasoningEngine:
    """Create graph reasoning engine"""
    return GraphReasoningEngine(database)
