"""
Drug interaction and contraindication detection service
Implements drug-drug interaction analysis using DDInter and DrugBank data
"""
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime

try:
    from gremlin_python.process.graph_traversal import __
except ImportError:
    # Mock for testing without Gremlin
    class MockGremlinStep:
        def inV(self):
            return self
        def has(self, *args):
            return self
    __ = MockGremlinStep()

from .models import InteractionEntity, SeverityLevel, PatientContext
from .reasoning_engine import GraphPath, GraphReasoningEngine, TraversalStrategy

logger = logging.getLogger(__name__)


@dataclass
class InteractionResult:
    """Result of interaction detection"""
    drug_a_id: str
    drug_b_id: str
    drug_a_name: str
    drug_b_name: str
    severity: SeverityLevel
    mechanism: Optional[str] = None
    clinical_effect: Optional[str] = None
    management: Optional[str] = None
    evidence_level: Optional[str] = None
    confidence: float = 0.0
    evidence_paths: List[GraphPath] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)


@dataclass
class ContraindicationResult:
    """Result of contraindication detection"""
    drug_id: str
    drug_name: str
    condition_id: str
    condition_name: str
    severity: SeverityLevel
    reason: Optional[str] = None
    alternative_recommendations: List[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence_paths: List[GraphPath] = field(default_factory=list)


@dataclass
class InteractionAnalysis:
    """Complete interaction analysis result"""
    patient_id: Optional[str] = None
    analyzed_drugs: List[str] = field(default_factory=list)
    interactions: List[InteractionResult] = field(default_factory=list)
    contraindications: List[ContraindicationResult] = field(default_factory=list)
    risk_summary: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    analysis_timestamp: datetime = field(default_factory=datetime.utcnow)


class InteractionDetector:
    """
    Drug interaction and contraindication detection service
    Uses knowledge graph traversal to identify drug-drug interactions
    and drug-condition contraindications
    """
    
    def __init__(self, reasoning_engine: GraphReasoningEngine):
        """
        Initialize interaction detector
        
        Args:
            reasoning_engine: Graph reasoning engine instance
        """
        self.reasoning_engine = reasoning_engine
        self.db = reasoning_engine.db
        self.logger = logging.getLogger(__name__)
        self.min_confidence = 0.5
    
    async def detect_drug_interactions(
        self,
        drug_ids: List[str],
        patient_context: Optional[PatientContext] = None,
        include_minor: bool = False
    ) -> List[InteractionResult]:
        """
        Detect drug-drug interactions for a list of drugs
        
        Args:
            drug_ids: List of drug IDs to check for interactions
            patient_context: Optional patient context for personalization
            include_minor: Whether to include minor interactions
            
        Returns:
            List of detected interactions
        """
        try:
            self.logger.info(f"Detecting interactions for {len(drug_ids)} drugs")
            
            if len(drug_ids) < 2:
                self.logger.warning("Need at least 2 drugs to detect interactions")
                return []
            
            interactions = []
            
            # Check pairwise interactions
            for i, drug_a_id in enumerate(drug_ids):
                for drug_b_id in drug_ids[i+1:]:
                    interaction = await self._detect_pairwise_interaction(
                        drug_a_id, drug_b_id, patient_context
                    )
                    
                    if interaction:
                        # Filter by severity if needed
                        if not include_minor and interaction.severity == SeverityLevel.MINOR:
                            continue
                        
                        interactions.append(interaction)
            
            # Check for complex multi-hop interactions
            complex_interactions = await self._detect_complex_interactions(
                drug_ids, patient_context
            )
            interactions.extend(complex_interactions)
            
            # Sort by severity
            interactions.sort(
                key=lambda x: self._severity_to_numeric(x.severity),
                reverse=True
            )
            
            self.logger.info(f"Found {len(interactions)} interactions")
            return interactions
            
        except Exception as e:
            self.logger.error(f"Error detecting drug interactions: {e}")
            return []
    
    async def _detect_pairwise_interaction(
        self,
        drug_a_id: str,
        drug_b_id: str,
        patient_context: Optional[PatientContext] = None
    ) -> Optional[InteractionResult]:
        """Detect direct interaction between two drugs"""
        try:
            g = self.db.connection.g
            
            # Get drug names
            drug_a_result = g.V().has('id', drug_a_id).valueMap(True).toList()
            drug_b_result = g.V().has('id', drug_b_id).valueMap(True).toList()
            
            if not drug_a_result or not drug_b_result:
                return None
            
            drug_a_name = drug_a_result[0].get('name', drug_a_id)
            drug_b_name = drug_b_result[0].get('name', drug_b_id)
            
            # Check for direct INTERACTS_WITH edge
            interaction_edges = (
                g.V().has('id', drug_a_id)
                .outE('INTERACTS_WITH')
                .where(__.inV().has('id', drug_b_id))
                .valueMap(True)
                .toList()
            )
            
            # Also check reverse direction
            if not interaction_edges:
                interaction_edges = (
                    g.V().has('id', drug_b_id)
                    .outE('INTERACTS_WITH')
                    .where(__.inV().has('id', drug_a_id))
                    .valueMap(True)
                    .toList()
                )
            
            if not interaction_edges:
                return None
            
            # Use the first (highest confidence) interaction
            edge = interaction_edges[0]
            
            # Extract interaction properties
            severity_str = edge.get('severity', 'moderate')
            severity = self._parse_severity(severity_str)
            
            confidence = float(edge.get('confidence', 0.7))
            
            # Adjust confidence based on patient context
            if patient_context:
                confidence = self._adjust_confidence_for_patient(
                    confidence, severity, patient_context
                )
            
            # Filter by minimum confidence
            if confidence < self.min_confidence:
                return None
            
            # Extract data sources
            sources_str = edge.get('created_from', edge.get('evidence_sources', ''))
            if isinstance(sources_str, str):
                data_sources = [s.strip() for s in sources_str.split(',') if s.strip()]
            elif isinstance(sources_str, list):
                data_sources = sources_str
            else:
                data_sources = ['DrugBank', 'DDInter']  # Default sources
            
            return InteractionResult(
                drug_a_id=drug_a_id,
                drug_b_id=drug_b_id,
                drug_a_name=drug_a_name,
                drug_b_name=drug_b_name,
                severity=severity,
                mechanism=edge.get('mechanism'),
                clinical_effect=edge.get('clinical_effect'),
                management=edge.get('management'),
                evidence_level=edge.get('evidence_level'),
                confidence=confidence,
                data_sources=data_sources
            )
            
        except Exception as e:
            self.logger.error(f"Error detecting pairwise interaction: {e}")
            return None
    
    async def _detect_complex_interactions(
        self,
        drug_ids: List[str],
        patient_context: Optional[PatientContext] = None
    ) -> List[InteractionResult]:
        """
        Detect complex multi-hop interactions
        
        Identifies interaction patterns that involve intermediate entities
        (e.g., Drug A affects enzyme X, which metabolizes Drug B)
        """
        try:
            complex_interactions = []
            
            # Use reasoning engine to find interaction chains
            chains = await self.reasoning_engine.find_interaction_chains(
                drug_ids=drug_ids,
                max_chain_length=3
            )
            
            # Convert chains to interaction results
            for chain in chains:
                if len(chain.nodes) < 2:
                    continue
                
                # Get first and last drugs in chain
                first_drug = chain.nodes[0]
                last_drug = chain.nodes[-1]
                
                # Calculate overall severity from chain
                severity = self._calculate_chain_severity(chain)
                
                # Only include if confidence is high enough
                if chain.confidence < self.min_confidence:
                    continue
                
                interaction = InteractionResult(
                    drug_a_id=first_drug.get('id', ''),
                    drug_b_id=last_drug.get('id', ''),
                    drug_a_name=first_drug.get('name', ''),
                    drug_b_name=last_drug.get('name', ''),
                    severity=severity,
                    mechanism=f"Multi-hop interaction via {len(chain.nodes) - 2} intermediate entities",
                    clinical_effect="Complex interaction pattern detected",
                    confidence=chain.confidence,
                    evidence_paths=[chain],
                    data_sources=['DrugBank', 'DDInter']
                )
                
                complex_interactions.append(interaction)
            
            return complex_interactions
            
        except Exception as e:
            self.logger.error(f"Error detecting complex interactions: {e}")
            return []
    
    async def detect_contraindications(
        self,
        drug_ids: List[str],
        patient_context: PatientContext
    ) -> List[ContraindicationResult]:
        """
        Detect contraindications between drugs and patient conditions
        
        Args:
            drug_ids: List of drug IDs to check
            patient_context: Patient context with conditions
            
        Returns:
            List of detected contraindications
        """
        try:
            self.logger.info(
                f"Detecting contraindications for {len(drug_ids)} drugs "
                f"and {len(patient_context.conditions)} conditions"
            )
            
            if not patient_context.conditions:
                return []
            
            contraindications = []
            
            for drug_id in drug_ids:
                for condition in patient_context.conditions:
                    contraindication = await self._detect_drug_condition_contraindication(
                        drug_id, condition, patient_context
                    )
                    
                    if contraindication:
                        contraindications.append(contraindication)
            
            # Sort by severity
            contraindications.sort(
                key=lambda x: self._severity_to_numeric(x.severity),
                reverse=True
            )
            
            self.logger.info(f"Found {len(contraindications)} contraindications")
            return contraindications
            
        except Exception as e:
            self.logger.error(f"Error detecting contraindications: {e}")
            return []
    
    async def _detect_drug_condition_contraindication(
        self,
        drug_id: str,
        condition: str,
        patient_context: PatientContext
    ) -> Optional[ContraindicationResult]:
        """Detect contraindication between drug and condition"""
        try:
            g = self.db.connection.g
            
            # Get drug info
            drug_result = g.V().has('id', drug_id).valueMap(True).toList()
            if not drug_result:
                return None
            
            drug = drug_result[0]
            drug_name = drug.get('name', drug_id)
            
            # Check drug's contraindications property
            contraindications_str = drug.get('contraindications', '')
            if isinstance(contraindications_str, str):
                contraindications_list = [c.strip().lower() for c in contraindications_str.split(',')]
            elif isinstance(contraindications_str, list):
                contraindications_list = [str(c).lower() for c in contraindications_str]
            else:
                contraindications_list = []
            
            # Check if condition is in contraindications
            condition_lower = condition.lower()
            is_contraindicated = any(
                condition_lower in contra or contra in condition_lower
                for contra in contraindications_list
            )
            
            if not is_contraindicated:
                # Also check for graph path from drug to condition via CONTRAINDICATED_FOR edge
                paths = await self.reasoning_engine.multi_hop_traversal(
                    start_node_id=drug_id,
                    target_node_type="Condition",
                    max_hops=2,
                    edge_filters={'label': 'CONTRAINDICATED_FOR'}
                )
                
                # Check if any path leads to this condition
                for path in paths:
                    if path.nodes:
                        last_node = path.nodes[-1]
                        node_name = last_node.get('name', '').lower()
                        if condition_lower in node_name or node_name in condition_lower:
                            is_contraindicated = True
                            break
            
            if not is_contraindicated:
                return None
            
            # Determine severity based on patient risk factors
            severity = self._determine_contraindication_severity(
                drug_id, condition, patient_context
            )
            
            return ContraindicationResult(
                drug_id=drug_id,
                drug_name=drug_name,
                condition_id=condition,
                condition_name=condition,
                severity=severity,
                reason=f"{drug_name} is contraindicated for patients with {condition}",
                confidence=0.8,
                alternative_recommendations=[]
            )
            
        except Exception as e:
            self.logger.error(f"Error detecting drug-condition contraindication: {e}")
            return None
    
    async def analyze_patient_medications(
        self,
        patient_context: PatientContext
    ) -> InteractionAnalysis:
        """
        Perform complete interaction analysis for patient's medications
        
        Args:
            patient_context: Patient context with medications and conditions
            
        Returns:
            Complete interaction analysis
        """
        try:
            self.logger.info(f"Analyzing medications for patient {patient_context.id}")
            
            # Extract drug IDs from patient medications
            drug_ids = []
            for med in patient_context.medications:
                drug_id = med.get('drug_id') or med.get('id')
                if drug_id:
                    drug_ids.append(drug_id)
            
            if not drug_ids:
                self.logger.warning("No medications found in patient context")
                return InteractionAnalysis(
                    patient_id=patient_context.id,
                    analyzed_drugs=[]
                )
            
            # Detect interactions
            interactions = await self.detect_drug_interactions(
                drug_ids=drug_ids,
                patient_context=patient_context,
                include_minor=False
            )
            
            # Detect contraindications
            contraindications = await self.detect_contraindications(
                drug_ids=drug_ids,
                patient_context=patient_context
            )
            
            # Generate risk summary
            risk_summary = self._generate_risk_summary(interactions, contraindications)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                interactions, contraindications, patient_context
            )
            
            return InteractionAnalysis(
                patient_id=patient_context.id,
                analyzed_drugs=drug_ids,
                interactions=interactions,
                contraindications=contraindications,
                risk_summary=risk_summary,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing patient medications: {e}")
            return InteractionAnalysis(
                patient_id=patient_context.id if patient_context else None,
                analyzed_drugs=[]
            )
    
    def _parse_severity(self, severity_str: Any) -> SeverityLevel:
        """Parse severity string to SeverityLevel enum"""
        if isinstance(severity_str, SeverityLevel):
            return severity_str
        
        severity_map = {
            'minor': SeverityLevel.MINOR,
            'moderate': SeverityLevel.MODERATE,
            'major': SeverityLevel.MAJOR,
            'contraindicated': SeverityLevel.CONTRAINDICATED,
            'critical': SeverityLevel.CONTRAINDICATED
        }
        
        severity_lower = str(severity_str).lower()
        return severity_map.get(severity_lower, SeverityLevel.MODERATE)
    
    def _severity_to_numeric(self, severity: SeverityLevel) -> int:
        """Convert severity to numeric value for sorting"""
        severity_values = {
            SeverityLevel.MINOR: 1,
            SeverityLevel.MODERATE: 2,
            SeverityLevel.MAJOR: 3,
            SeverityLevel.CONTRAINDICATED: 4
        }
        return severity_values.get(severity, 2)
    
    def _calculate_chain_severity(self, chain: GraphPath) -> SeverityLevel:
        """Calculate overall severity from interaction chain"""
        if not chain.edges:
            return SeverityLevel.MODERATE
        
        # Get maximum severity from chain
        max_severity = SeverityLevel.MINOR
        max_numeric = 0
        
        for edge in chain.edges:
            severity_str = edge.get('severity', 'moderate')
            severity = self._parse_severity(severity_str)
            numeric = self._severity_to_numeric(severity)
            
            if numeric > max_numeric:
                max_numeric = numeric
                max_severity = severity
        
        return max_severity
    
    def _adjust_confidence_for_patient(
        self,
        base_confidence: float,
        severity: SeverityLevel,
        patient_context: PatientContext
    ) -> float:
        """Adjust confidence based on patient-specific factors"""
        adjusted = base_confidence
        
        # Increase confidence for high-risk patients
        demographics = patient_context.demographics
        age = demographics.get('age', 0)
        
        if age > 65 or age < 18:
            adjusted *= 1.1
        
        # Increase confidence if patient has risk factors
        if len(patient_context.risk_factors) > 3:
            adjusted *= 1.05
        
        # Increase confidence for severe interactions
        if severity in [SeverityLevel.MAJOR, SeverityLevel.CONTRAINDICATED]:
            adjusted *= 1.1
        
        return min(adjusted, 1.0)
    
    def _determine_contraindication_severity(
        self,
        drug_id: str,
        condition: str,
        patient_context: PatientContext
    ) -> SeverityLevel:
        """Determine severity of contraindication"""
        # Default to major for contraindications
        severity = SeverityLevel.MAJOR
        
        # Increase to contraindicated for high-risk conditions
        high_risk_conditions = [
            'heart failure', 'kidney failure', 'liver failure',
            'severe allergy', 'pregnancy'
        ]
        
        condition_lower = condition.lower()
        if any(risk in condition_lower for risk in high_risk_conditions):
            severity = SeverityLevel.CONTRAINDICATED
        
        return severity
    
    def _generate_risk_summary(
        self,
        interactions: List[InteractionResult],
        contraindications: List[ContraindicationResult]
    ) -> Dict[str, Any]:
        """Generate risk summary from interactions and contraindications"""
        summary = {
            'total_interactions': len(interactions),
            'total_contraindications': len(contraindications),
            'severity_breakdown': {
                'minor': 0,
                'moderate': 0,
                'major': 0,
                'contraindicated': 0
            },
            'highest_risk': None,
            'requires_immediate_attention': False
        }
        
        # Count by severity
        for interaction in interactions:
            severity_key = interaction.severity.value
            summary['severity_breakdown'][severity_key] += 1
        
        for contraindication in contraindications:
            severity_key = contraindication.severity.value
            summary['severity_breakdown'][severity_key] += 1
        
        # Determine highest risk
        if summary['severity_breakdown']['contraindicated'] > 0:
            summary['highest_risk'] = 'contraindicated'
            summary['requires_immediate_attention'] = True
        elif summary['severity_breakdown']['major'] > 0:
            summary['highest_risk'] = 'major'
            summary['requires_immediate_attention'] = True
        elif summary['severity_breakdown']['moderate'] > 0:
            summary['highest_risk'] = 'moderate'
        else:
            summary['highest_risk'] = 'minor'
        
        return summary
    
    def _generate_recommendations(
        self,
        interactions: List[InteractionResult],
        contraindications: List[ContraindicationResult],
        patient_context: PatientContext
    ) -> List[str]:
        """Generate recommendations based on detected issues"""
        recommendations = []
        
        # Critical recommendations for contraindications
        if contraindications:
            critical_contras = [
                c for c in contraindications
                if c.severity == SeverityLevel.CONTRAINDICATED
            ]
            
            if critical_contras:
                recommendations.append(
                    "URGENT: Contraindicated medications detected. "
                    "Consult healthcare provider immediately."
                )
                for contra in critical_contras:
                    recommendations.append(
                        f"  - {contra.drug_name} is contraindicated for {contra.condition_name}"
                    )
        
        # Recommendations for major interactions
        major_interactions = [
            i for i in interactions
            if i.severity in [SeverityLevel.MAJOR, SeverityLevel.CONTRAINDICATED]
        ]
        
        if major_interactions:
            recommendations.append(
                "Major drug interactions detected. Consult healthcare provider."
            )
            for interaction in major_interactions[:3]:  # Top 3
                rec = f"  - {interaction.drug_a_name} and {interaction.drug_b_name}"
                if interaction.management:
                    rec += f": {interaction.management}"
                recommendations.append(rec)
        
        # General monitoring recommendations
        if interactions or contraindications:
            recommendations.append(
                "Monitor for adverse effects and report any concerns to your healthcare provider."
            )
        
        # Age-specific recommendations
        age = patient_context.demographics.get('age', 0)
        if age > 65:
            recommendations.append(
                "As a senior patient, you may be more sensitive to drug interactions. "
                "Regular monitoring is recommended."
            )
        elif age < 18:
            recommendations.append(
                "Pediatric patients require special attention to drug interactions. "
                "Ensure all medications are age-appropriate."
            )
        
        return recommendations


# Global interaction detector instance
interaction_detector = None


def initialize_interaction_detector(reasoning_engine: GraphReasoningEngine):
    """Initialize global interaction detector instance"""
    global interaction_detector
    interaction_detector = InteractionDetector(reasoning_engine)
    return interaction_detector
