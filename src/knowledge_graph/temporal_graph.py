"""
Temporal knowledge graph components for PharmaGuide
Implements temporal node creation and reasoning for symptom logs and medication schedules
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import statistics

from src.knowledge_graph.database import KnowledgeGraphDatabase
from src.knowledge_graph.models import PatientContext

logger = logging.getLogger(__name__)


class TemporalNodeType(str, Enum):
    """Types of temporal nodes"""
    SYMPTOM_LOG = "symptom_log"
    MEDICATION_SCHEDULE = "medication_schedule"
    DOSAGE_CHANGE = "dosage_change"
    EFFECTIVENESS_MEASUREMENT = "effectiveness_measurement"
    ADVERSE_EVENT = "adverse_event"


class TrendDirection(str, Enum):
    """Direction of trend"""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    FLUCTUATING = "fluctuating"


@dataclass
class TemporalNode:
    """Temporal node in knowledge graph"""
    id: str
    node_type: TemporalNodeType
    timestamp: datetime
    patient_id: str
    entity_id: str  # Drug, symptom, etc.
    value: Any  # Measurement value
    metadata: Dict[str, Any]
    created_at: datetime


@dataclass
class EffectivenessTrend:
    """Medication effectiveness trend"""
    medication_id: str
    patient_id: str
    start_time: datetime
    end_time: datetime
    trend_direction: TrendDirection
    trend_strength: float  # 0.0 to 1.0
    average_effectiveness: float
    data_points: int
    confidence: float
    significant_changes: List[Dict[str, Any]]


@dataclass
class ChangeDetection:
    """Detected change in patient data"""
    change_type: str
    detected_at: datetime
    entity_id: str
    previous_value: Any
    current_value: Any
    change_magnitude: float
    confidence: float
    potential_causes: List[str]
    recommendations: List[str]


class TemporalKnowledgeGraph:
    """
    Temporal knowledge graph component for tracking time-series medical data
    Implements temporal node creation, reasoning, and change detection
    """
    
    def __init__(self, database: KnowledgeGraphDatabase):
        self.database = database
        self.logger = logging.getLogger(__name__)
    
    async def create_symptom_log_node(
        self,
        patient_id: str,
        symptom_name: str,
        severity: float,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TemporalNode:
        """
        Create temporal node for symptom log
        
        Args:
            patient_id: Patient identifier
            symptom_name: Name of symptom
            severity: Severity score (0.0 to 10.0)
            timestamp: Optional timestamp (defaults to now)
            metadata: Optional additional metadata
        
        Returns:
            Created temporal node
        """
        try:
            if timestamp is None:
                timestamp = datetime.utcnow()
            
            if metadata is None:
                metadata = {}
            
            # Create unique node ID
            node_id = f"symptom_log_{patient_id}_{symptom_name}_{int(timestamp.timestamp())}"
            
            # Create temporal node
            node = TemporalNode(
                id=node_id,
                node_type=TemporalNodeType.SYMPTOM_LOG,
                timestamp=timestamp,
                patient_id=patient_id,
                entity_id=symptom_name,
                value=severity,
                metadata=metadata,
                created_at=datetime.utcnow()
            )
            
            # Store in knowledge graph
            await self._store_temporal_node(node)
            
            # Create temporal relationships
            await self._create_temporal_relationships(node)
            
            self.logger.info(f"Created symptom log node: {node_id}")
            return node
        
        except Exception as e:
            self.logger.error(f"Error creating symptom log node: {e}")
            raise
    
    async def create_medication_schedule_node(
        self,
        patient_id: str,
        medication_id: str,
        dosage: str,
        frequency: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TemporalNode:
        """
        Create temporal node for medication schedule
        
        Args:
            patient_id: Patient identifier
            medication_id: Medication identifier
            dosage: Dosage amount
            frequency: Dosing frequency
            start_time: Schedule start time
            end_time: Optional schedule end time
            metadata: Optional additional metadata
        
        Returns:
            Created temporal node
        """
        try:
            if metadata is None:
                metadata = {}
            
            metadata.update({
                'dosage': dosage,
                'frequency': frequency,
                'end_time': end_time.isoformat() if end_time else None
            })
            
            # Create unique node ID
            node_id = f"med_schedule_{patient_id}_{medication_id}_{int(start_time.timestamp())}"
            
            # Create temporal node
            node = TemporalNode(
                id=node_id,
                node_type=TemporalNodeType.MEDICATION_SCHEDULE,
                timestamp=start_time,
                patient_id=patient_id,
                entity_id=medication_id,
                value={'dosage': dosage, 'frequency': frequency},
                metadata=metadata,
                created_at=datetime.utcnow()
            )
            
            # Store in knowledge graph
            await self._store_temporal_node(node)
            
            # Create temporal relationships
            await self._create_temporal_relationships(node)
            
            self.logger.info(f"Created medication schedule node: {node_id}")
            return node
        
        except Exception as e:
            self.logger.error(f"Error creating medication schedule node: {e}")
            raise
    
    async def create_dosage_change_node(
        self,
        patient_id: str,
        medication_id: str,
        previous_dosage: str,
        new_dosage: str,
        timestamp: Optional[datetime] = None,
        reason: Optional[str] = None
    ) -> TemporalNode:
        """
        Create temporal node for dosage change
        
        Args:
            patient_id: Patient identifier
            medication_id: Medication identifier
            previous_dosage: Previous dosage
            new_dosage: New dosage
            timestamp: Optional timestamp (defaults to now)
            reason: Optional reason for change
        
        Returns:
            Created temporal node
        """
        try:
            if timestamp is None:
                timestamp = datetime.utcnow()
            
            metadata = {
                'previous_dosage': previous_dosage,
                'new_dosage': new_dosage,
                'reason': reason
            }
            
            node_id = f"dosage_change_{patient_id}_{medication_id}_{int(timestamp.timestamp())}"
            
            node = TemporalNode(
                id=node_id,
                node_type=TemporalNodeType.DOSAGE_CHANGE,
                timestamp=timestamp,
                patient_id=patient_id,
                entity_id=medication_id,
                value={'previous': previous_dosage, 'new': new_dosage},
                metadata=metadata,
                created_at=datetime.utcnow()
            )
            
            await self._store_temporal_node(node)
            await self._create_temporal_relationships(node)
            
            self.logger.info(f"Created dosage change node: {node_id}")
            return node
        
        except Exception as e:
            self.logger.error(f"Error creating dosage change node: {e}")
            raise
    
    async def _store_temporal_node(self, node: TemporalNode) -> None:
        """Store temporal node in knowledge graph"""
        try:
            g = self.database.connection.g
            
            # Create vertex with temporal properties
            traversal = (g.addV('TemporalNode')
                        .property('id', node.id)
                        .property('node_type', node.node_type.value)
                        .property('timestamp', node.timestamp.isoformat())
                        .property('patient_id', node.patient_id)
                        .property('entity_id', node.entity_id)
                        .property('value', str(node.value))
                        .property('created_at', node.created_at.isoformat()))
            
            # Add metadata properties
            for key, value in node.metadata.items():
                if value is not None:
                    traversal = traversal.property(f"meta_{key}", str(value))
            
            traversal.toList()
            
        except Exception as e:
            self.logger.error(f"Error storing temporal node: {e}")
            raise
    
    async def _create_temporal_relationships(self, node: TemporalNode) -> None:
        """Create temporal relationships for a node"""
        try:
            g = self.database.connection.g
            
            # Link to patient
            (g.V().has('id', node.id)
             .addE('BELONGS_TO_PATIENT')
             .to(g.V().has('id', node.patient_id))
             .toList())
            
            # Link to entity (drug, symptom, etc.)
            (g.V().has('id', node.id)
             .addE('RELATES_TO')
             .to(g.V().has('id', node.entity_id))
             .toList())
            
            # Find and link to previous temporal node of same type
            previous_nodes = await self._find_previous_temporal_nodes(
                node.patient_id,
                node.node_type,
                node.entity_id,
                node.timestamp
            )
            
            if previous_nodes:
                # Link to most recent previous node
                prev_node = previous_nodes[0]
                (g.V().has('id', prev_node['id'])
                 .addE('TEMPORAL_NEXT')
                 .to(g.V().has('id', node.id))
                 .property('time_delta', (node.timestamp - prev_node['timestamp']).total_seconds())
                 .toList())
            
        except Exception as e:
            self.logger.error(f"Error creating temporal relationships: {e}")
    
    async def _find_previous_temporal_nodes(
        self,
        patient_id: str,
        node_type: TemporalNodeType,
        entity_id: str,
        before_timestamp: datetime
    ) -> List[Dict[str, Any]]:
        """Find previous temporal nodes"""
        try:
            g = self.database.connection.g
            
            # Query for previous nodes
            results = (g.V()
                      .hasLabel('TemporalNode')
                      .has('patient_id', patient_id)
                      .has('node_type', node_type.value)
                      .has('entity_id', entity_id)
                      .toList())
            
            # Filter by timestamp and sort
            previous = []
            for node in results:
                node_time = datetime.fromisoformat(node.get('timestamp', ''))
                if node_time < before_timestamp:
                    previous.append({
                        'id': node.get('id'),
                        'timestamp': node_time,
                        'value': node.get('value')
                    })
            
            # Sort by timestamp descending
            previous.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return previous
        
        except Exception as e:
            self.logger.error(f"Error finding previous temporal nodes: {e}")
            return []
    
    async def analyze_effectiveness_trend(
        self,
        patient_id: str,
        medication_id: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        min_data_points: int = 3
    ) -> Optional[EffectivenessTrend]:
        """
        Analyze medication effectiveness trend over time
        
        Args:
            patient_id: Patient identifier
            medication_id: Medication identifier
            start_time: Start of analysis period
            end_time: Optional end of analysis period (defaults to now)
            min_data_points: Minimum data points required
        
        Returns:
            Effectiveness trend analysis or None if insufficient data
        """
        try:
            if end_time is None:
                end_time = datetime.utcnow()
            
            self.logger.info(
                f"Analyzing effectiveness trend for patient {patient_id}, "
                f"medication {medication_id}"
            )
            
            # Get temporal data points
            data_points = await self._get_effectiveness_data_points(
                patient_id, medication_id, start_time, end_time
            )
            
            if len(data_points) < min_data_points:
                self.logger.warning(
                    f"Insufficient data points: {len(data_points)} < {min_data_points}"
                )
                return None
            
            # Calculate trend
            trend_direction, trend_strength = self._calculate_trend(data_points)
            
            # Calculate average effectiveness
            values = [dp['value'] for dp in data_points]
            avg_effectiveness = statistics.mean(values)
            
            # Detect significant changes
            significant_changes = self._detect_significant_changes(data_points)
            
            # Calculate confidence based on data quality
            confidence = self._calculate_trend_confidence(
                data_points, trend_strength
            )
            
            trend = EffectivenessTrend(
                medication_id=medication_id,
                patient_id=patient_id,
                start_time=start_time,
                end_time=end_time,
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                average_effectiveness=avg_effectiveness,
                data_points=len(data_points),
                confidence=confidence,
                significant_changes=significant_changes
            )
            
            self.logger.info(
                f"Trend analysis complete: {trend_direction.value}, "
                f"strength={trend_strength:.2f}"
            )
            
            return trend
        
        except Exception as e:
            self.logger.error(f"Error analyzing effectiveness trend: {e}")
            return None
    
    async def _get_effectiveness_data_points(
        self,
        patient_id: str,
        medication_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """Get effectiveness data points for time period"""
        try:
            g = self.database.connection.g
            
            # Query temporal nodes for effectiveness measurements
            results = (g.V()
                      .hasLabel('TemporalNode')
                      .has('patient_id', patient_id)
                      .has('entity_id', medication_id)
                      .has('node_type', TemporalNodeType.EFFECTIVENESS_MEASUREMENT.value)
                      .toList())
            
            # Filter by time range and extract data
            data_points = []
            for node in results:
                timestamp = datetime.fromisoformat(node.get('timestamp', ''))
                if start_time <= timestamp <= end_time:
                    data_points.append({
                        'timestamp': timestamp,
                        'value': float(node.get('value', 0.0)),
                        'id': node.get('id')
                    })
            
            # Sort by timestamp
            data_points.sort(key=lambda x: x['timestamp'])
            
            return data_points
        
        except Exception as e:
            self.logger.error(f"Error getting effectiveness data points: {e}")
            return []
    
    def _calculate_trend(
        self,
        data_points: List[Dict[str, Any]]
    ) -> Tuple[TrendDirection, float]:
        """Calculate trend direction and strength"""
        if len(data_points) < 2:
            return TrendDirection.STABLE, 0.0
        
        # Extract values
        values = [dp['value'] for dp in data_points]
        n = len(values)
        
        # Simple linear regression
        x = list(range(n))
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)
        
        # Calculate slope
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return TrendDirection.STABLE, 0.0
        
        slope = numerator / denominator
        
        # Calculate R-squared for trend strength
        y_pred = [y_mean + slope * (x[i] - x_mean) for i in range(n)]
        ss_res = sum((values[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((values[i] - y_mean) ** 2 for i in range(n))
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        trend_strength = abs(r_squared)
        
        # Determine direction
        if abs(slope) < 0.05:
            direction = TrendDirection.STABLE
        elif slope > 0:
            direction = TrendDirection.INCREASING
        else:
            direction = TrendDirection.DECREASING
        
        # Check for fluctuation
        if trend_strength < 0.3 and statistics.stdev(values) > 0.5 * y_mean:
            direction = TrendDirection.FLUCTUATING
        
        return direction, trend_strength
    
    def _detect_significant_changes(
        self,
        data_points: List[Dict[str, Any]],
        threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Detect significant changes in data points"""
        changes = []
        
        for i in range(1, len(data_points)):
            prev_value = data_points[i-1]['value']
            curr_value = data_points[i]['value']
            
            if prev_value == 0:
                continue
            
            # Calculate relative change
            relative_change = abs(curr_value - prev_value) / prev_value
            
            if relative_change >= threshold:
                changes.append({
                    'timestamp': data_points[i]['timestamp'],
                    'previous_value': prev_value,
                    'current_value': curr_value,
                    'change_magnitude': relative_change,
                    'direction': 'increase' if curr_value > prev_value else 'decrease'
                })
        
        return changes
    
    def _calculate_trend_confidence(
        self,
        data_points: List[Dict[str, Any]],
        trend_strength: float
    ) -> float:
        """Calculate confidence in trend analysis"""
        # Base confidence on trend strength
        confidence = trend_strength
        
        # Adjust for number of data points
        n = len(data_points)
        if n < 5:
            confidence *= 0.7
        elif n < 10:
            confidence *= 0.85
        
        # Adjust for time span
        if n >= 2:
            time_span = (data_points[-1]['timestamp'] - data_points[0]['timestamp']).days
            if time_span < 7:
                confidence *= 0.8
            elif time_span < 14:
                confidence *= 0.9
        
        return min(confidence, 1.0)
    
    async def detect_changes(
        self,
        patient_id: str,
        entity_id: str,
        lookback_days: int = 30,
        change_threshold: float = 0.25
    ) -> List[ChangeDetection]:
        """
        Detect significant changes using knowledge graph inference
        
        Args:
            patient_id: Patient identifier
            entity_id: Entity to monitor (drug, symptom, etc.)
            lookback_days: Days to look back for comparison
            change_threshold: Threshold for significant change
        
        Returns:
            List of detected changes
        """
        try:
            self.logger.info(
                f"Detecting changes for patient {patient_id}, entity {entity_id}"
            )
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=lookback_days)
            
            # Get temporal data
            data_points = await self._get_temporal_data(
                patient_id, entity_id, start_time, end_time
            )
            
            if len(data_points) < 2:
                return []
            
            # Detect changes
            changes = []
            
            # Compare recent vs baseline
            baseline_period = data_points[:len(data_points)//2]
            recent_period = data_points[len(data_points)//2:]
            
            if baseline_period and recent_period:
                baseline_avg = statistics.mean([dp['value'] for dp in baseline_period])
                recent_avg = statistics.mean([dp['value'] for dp in recent_period])
                
                if baseline_avg > 0:
                    change_magnitude = abs(recent_avg - baseline_avg) / baseline_avg
                    
                    if change_magnitude >= change_threshold:
                        # Infer potential causes
                        potential_causes = await self._infer_change_causes(
                            patient_id, entity_id, data_points
                        )
                        
                        # Generate recommendations
                        recommendations = self._generate_change_recommendations(
                            change_magnitude, recent_avg, baseline_avg
                        )
                        
                        change = ChangeDetection(
                            change_type='significant_trend_change',
                            detected_at=end_time,
                            entity_id=entity_id,
                            previous_value=baseline_avg,
                            current_value=recent_avg,
                            change_magnitude=change_magnitude,
                            confidence=0.8,
                            potential_causes=potential_causes,
                            recommendations=recommendations
                        )
                        
                        changes.append(change)
            
            self.logger.info(f"Detected {len(changes)} significant changes")
            return changes
        
        except Exception as e:
            self.logger.error(f"Error detecting changes: {e}")
            return []
    
    async def _get_temporal_data(
        self,
        patient_id: str,
        entity_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """Get temporal data for entity"""
        try:
            g = self.database.connection.g
            
            results = (g.V()
                      .hasLabel('TemporalNode')
                      .has('patient_id', patient_id)
                      .has('entity_id', entity_id)
                      .toList())
            
            data_points = []
            for node in results:
                timestamp = datetime.fromisoformat(node.get('timestamp', ''))
                if start_time <= timestamp <= end_time:
                    data_points.append({
                        'timestamp': timestamp,
                        'value': float(node.get('value', 0.0)),
                        'node_type': node.get('node_type')
                    })
            
            data_points.sort(key=lambda x: x['timestamp'])
            return data_points
        
        except Exception as e:
            self.logger.error(f"Error getting temporal data: {e}")
            return []
    
    async def _infer_change_causes(
        self,
        patient_id: str,
        entity_id: str,
        data_points: List[Dict[str, Any]]
    ) -> List[str]:
        """Infer potential causes of changes using knowledge graph"""
        causes = []
        
        # Look for dosage changes
        dosage_changes = [
            dp for dp in data_points
            if dp.get('node_type') == TemporalNodeType.DOSAGE_CHANGE.value
        ]
        
        if dosage_changes:
            causes.append("Recent dosage adjustment")
        
        # Look for new medications
        # In real implementation, would query for medication schedule changes
        
        # Look for adverse events
        adverse_events = [
            dp for dp in data_points
            if dp.get('node_type') == TemporalNodeType.ADVERSE_EVENT.value
        ]
        
        if adverse_events:
            causes.append("Adverse event reported")
        
        if not causes:
            causes.append("Natural disease progression")
        
        return causes
    
    def _generate_change_recommendations(
        self,
        change_magnitude: float,
        current_value: float,
        previous_value: float
    ) -> List[str]:
        """Generate recommendations based on detected changes"""
        recommendations = []
        
        if change_magnitude > 0.5:
            recommendations.append("Consult healthcare provider immediately")
            recommendations.append("Review medication regimen")
        elif change_magnitude > 0.3:
            recommendations.append("Schedule follow-up appointment")
            recommendations.append("Monitor symptoms closely")
        else:
            recommendations.append("Continue current treatment plan")
            recommendations.append("Track symptoms regularly")
        
        if current_value > previous_value:
            recommendations.append("Symptoms appear to be worsening")
        else:
            recommendations.append("Symptoms appear to be improving")
        
        return recommendations


# Factory function
async def create_temporal_knowledge_graph(
    database: KnowledgeGraphDatabase
) -> TemporalKnowledgeGraph:
    """Create temporal knowledge graph"""
    return TemporalKnowledgeGraph(database)
