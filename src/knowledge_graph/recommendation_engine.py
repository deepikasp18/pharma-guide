"""
Alternative medication recommendation engine for PharmaGuide
"""
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from src.knowledge_graph.database import KnowledgeGraphDatabase
from src.knowledge_graph.models import DrugEntity, InteractionEntity, SeverityLevel

logger = logging.getLogger(__name__)


class RecommendationStrategy(str, Enum):
    """Strategy for generating recommendations"""
    THERAPEUTIC_EQUIVALENT = "therapeutic_equivalent"
    SAME_CLASS_ALTERNATIVE = "same_class_alternative"
    DIFFERENT_CLASS_ALTERNATIVE = "different_class_alternative"
    DOSAGE_ADJUSTMENT = "dosage_adjustment"
    TIMING_ADJUSTMENT = "timing_adjustment"


@dataclass
class AlternativeMedication:
    """Alternative medication recommendation"""
    drug_id: str
    drug_name: str
    generic_name: str
    reason: str
    strategy: RecommendationStrategy
    confidence: float
    evidence_sources: List[str]
    considerations: List[str]
    contraindications: List[str]


@dataclass
class ManagementStrategy:
    """Management strategy for drug interactions"""
    strategy_type: str
    description: str
    implementation_steps: List[str]
    monitoring_requirements: List[str]
    confidence: float
    evidence_level: str


@dataclass
class RecommendationResult:
    """Complete recommendation result"""
    original_drug_id: str
    original_drug_name: str
    interaction_context: Optional[Dict[str, Any]]
    alternatives: List[AlternativeMedication]
    management_strategies: List[ManagementStrategy]
    overall_confidence: float
    requires_provider_consultation: bool


class AlternativeMedicationEngine:
    """Engine for generating alternative medication recommendations"""
    
    def __init__(self, database: KnowledgeGraphDatabase):
        self.database = database
        self.logger = logging.getLogger(__name__)
    
    async def find_alternatives(
        self,
        drug_id: str,
        patient_context: Optional[Dict[str, Any]] = None,
        interaction_context: Optional[Dict[str, Any]] = None
    ) -> RecommendationResult:
        """Find alternative medications for a given drug"""
        try:
            # Get drug information
            drug_info = await self._get_drug_info(drug_id)
            if not drug_info:
                raise ValueError(f"Drug not found: {drug_id}")
            
            # Find therapeutic alternatives
            alternatives = []
            
            # Strategy 1: Therapeutic equivalents (same active ingredient, different formulation)
            therapeutic_equivalents = await self._find_therapeutic_equivalents(
                drug_info, patient_context
            )
            alternatives.extend(therapeutic_equivalents)
            
            # Strategy 2: Same class alternatives (same therapeutic class, different drug)
            same_class_alternatives = await self._find_same_class_alternatives(
                drug_info, patient_context, interaction_context
            )
            alternatives.extend(same_class_alternatives)
            
            # Strategy 3: Different class alternatives (different mechanism, same indication)
            different_class_alternatives = await self._find_different_class_alternatives(
                drug_info, patient_context, interaction_context
            )
            alternatives.extend(different_class_alternatives)
            
            # Generate management strategies
            management_strategies = await self._generate_management_strategies(
                drug_info, interaction_context
            )
            
            # Calculate overall confidence
            overall_confidence = self._calculate_overall_confidence(
                alternatives, management_strategies
            )
            
            # Determine if provider consultation is required
            requires_consultation = self._requires_provider_consultation(
                drug_info, interaction_context, alternatives
            )
            
            return RecommendationResult(
                original_drug_id=drug_id,
                original_drug_name=drug_info.get('name', ''),
                interaction_context=interaction_context,
                alternatives=alternatives,
                management_strategies=management_strategies,
                overall_confidence=overall_confidence,
                requires_provider_consultation=requires_consultation
            )
        
        except Exception as e:
            self.logger.error(f"Error finding alternatives for drug {drug_id}: {e}")
            raise
    
    async def _get_drug_info(self, drug_id: str) -> Optional[Dict[str, Any]]:
        """Get drug information from knowledge graph"""
        try:
            # Query knowledge graph for drug information
            result = await self.database.find_drug_by_name(drug_id)
            return result
        except Exception as e:
            self.logger.error(f"Error getting drug info: {e}")
            return None
    
    async def _find_therapeutic_equivalents(
        self,
        drug_info: Dict[str, Any],
        patient_context: Optional[Dict[str, Any]]
    ) -> List[AlternativeMedication]:
        """Find therapeutic equivalents (same active ingredient)"""
        alternatives = []
        
        try:
            generic_name = drug_info.get('generic_name', '')
            if not generic_name:
                return alternatives
            
            # In a real implementation, this would query the knowledge graph
            # for drugs with the same generic name but different formulations
            
            # For now, return empty list as this requires actual graph data
            self.logger.info(f"Finding therapeutic equivalents for {generic_name}")
            
        except Exception as e:
            self.logger.error(f"Error finding therapeutic equivalents: {e}")
        
        return alternatives
    
    async def _find_same_class_alternatives(
        self,
        drug_info: Dict[str, Any],
        patient_context: Optional[Dict[str, Any]],
        interaction_context: Optional[Dict[str, Any]]
    ) -> List[AlternativeMedication]:
        """Find alternatives in the same therapeutic class"""
        alternatives = []
        
        try:
            atc_codes = drug_info.get('atc_codes', [])
            if not atc_codes:
                return alternatives
            
            # Extract therapeutic class from ATC code (first 4 characters)
            therapeutic_classes = [code[:4] for code in atc_codes if len(code) >= 4]
            
            # In a real implementation, query knowledge graph for drugs
            # in the same therapeutic class
            self.logger.info(f"Finding same class alternatives for classes: {therapeutic_classes}")
            
        except Exception as e:
            self.logger.error(f"Error finding same class alternatives: {e}")
        
        return alternatives
    
    async def _find_different_class_alternatives(
        self,
        drug_info: Dict[str, Any],
        patient_context: Optional[Dict[str, Any]],
        interaction_context: Optional[Dict[str, Any]]
    ) -> List[AlternativeMedication]:
        """Find alternatives in different therapeutic classes"""
        alternatives = []
        
        try:
            indications = drug_info.get('indications', [])
            if not indications:
                return alternatives
            
            # In a real implementation, query knowledge graph for drugs
            # with the same indications but different mechanisms
            self.logger.info(f"Finding different class alternatives for indications: {indications}")
            
        except Exception as e:
            self.logger.error(f"Error finding different class alternatives: {e}")
        
        return alternatives
    
    async def _generate_management_strategies(
        self,
        drug_info: Dict[str, Any],
        interaction_context: Optional[Dict[str, Any]]
    ) -> List[ManagementStrategy]:
        """Generate management strategies for drug interactions"""
        strategies = []
        
        if not interaction_context:
            return strategies
        
        try:
            severity = interaction_context.get('severity', '')
            mechanism = interaction_context.get('mechanism', '')
            
            # Strategy 1: Dosage adjustment
            if severity in ['minor', 'moderate']:
                strategies.append(ManagementStrategy(
                    strategy_type="dosage_adjustment",
                    description="Adjust dosage to minimize interaction risk",
                    implementation_steps=[
                        "Reduce dose of one or both medications",
                        "Monitor for therapeutic effect",
                        "Adjust based on patient response"
                    ],
                    monitoring_requirements=[
                        "Monitor drug levels if available",
                        "Watch for signs of toxicity or reduced efficacy",
                        "Regular follow-up appointments"
                    ],
                    confidence=0.7,
                    evidence_level="moderate"
                ))
            
            # Strategy 2: Timing adjustment
            if 'absorption' in mechanism.lower() or 'bioavailability' in mechanism.lower():
                strategies.append(ManagementStrategy(
                    strategy_type="timing_adjustment",
                    description="Separate administration times to reduce interaction",
                    implementation_steps=[
                        "Administer medications at different times of day",
                        "Maintain consistent spacing (e.g., 2-4 hours apart)",
                        "Take with or without food as appropriate"
                    ],
                    monitoring_requirements=[
                        "Ensure patient adherence to timing schedule",
                        "Monitor for therapeutic effectiveness",
                        "Adjust timing if needed"
                    ],
                    confidence=0.8,
                    evidence_level="high"
                ))
            
            # Strategy 3: Enhanced monitoring
            if severity in ['moderate', 'major']:
                strategies.append(ManagementStrategy(
                    strategy_type="enhanced_monitoring",
                    description="Continue both medications with increased monitoring",
                    implementation_steps=[
                        "Establish baseline measurements",
                        "Schedule regular monitoring appointments",
                        "Educate patient on warning signs"
                    ],
                    monitoring_requirements=[
                        "Regular lab tests as appropriate",
                        "Frequent clinical assessments",
                        "Patient self-monitoring and reporting"
                    ],
                    confidence=0.6,
                    evidence_level="moderate"
                ))
        
        except Exception as e:
            self.logger.error(f"Error generating management strategies: {e}")
        
        return strategies
    
    def _calculate_overall_confidence(
        self,
        alternatives: List[AlternativeMedication],
        strategies: List[ManagementStrategy]
    ) -> float:
        """Calculate overall confidence in recommendations"""
        if not alternatives and not strategies:
            return 0.0
        
        # Average confidence from alternatives
        alt_confidence = (
            sum(alt.confidence for alt in alternatives) / len(alternatives)
            if alternatives else 0.0
        )
        
        # Average confidence from strategies
        strat_confidence = (
            sum(strat.confidence for strat in strategies) / len(strategies)
            if strategies else 0.0
        )
        
        # Weight alternatives higher than strategies
        if alternatives and strategies:
            return (alt_confidence * 0.7) + (strat_confidence * 0.3)
        elif alternatives:
            return alt_confidence
        else:
            return strat_confidence
    
    def _requires_provider_consultation(
        self,
        drug_info: Dict[str, Any],
        interaction_context: Optional[Dict[str, Any]],
        alternatives: List[AlternativeMedication]
    ) -> bool:
        """Determine if provider consultation is required"""
        # Always require consultation for major interactions
        if interaction_context:
            severity = interaction_context.get('severity', '')
            if severity in ['major', 'contraindicated']:
                return True
        
        # Require consultation if no alternatives found
        if not alternatives:
            return True
        
        # Require consultation if drug has narrow therapeutic index
        # (would be determined from drug properties in real implementation)
        
        # Require consultation if patient has multiple conditions
        # (would check patient context in real implementation)
        
        return False


class InteractionManagementService:
    """Service for managing drug interactions"""
    
    def __init__(self, database: KnowledgeGraphDatabase):
        self.database = database
        self.alternative_engine = AlternativeMedicationEngine(database)
        self.logger = logging.getLogger(__name__)
    
    async def get_interaction_recommendations(
        self,
        drug_a_id: str,
        drug_b_id: str,
        patient_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, RecommendationResult]:
        """Get recommendations for managing a drug interaction"""
        try:
            # Get interaction information
            interaction = await self._get_interaction_info(drug_a_id, drug_b_id)
            
            if not interaction:
                self.logger.warning(f"No interaction found between {drug_a_id} and {drug_b_id}")
                return {}
            
            # Prepare interaction context
            interaction_context = {
                'severity': interaction.get('severity', ''),
                'mechanism': interaction.get('mechanism', ''),
                'clinical_effect': interaction.get('clinical_effect', ''),
                'interacting_drug_id': drug_b_id
            }
            
            # Get recommendations for drug A
            recommendations_a = await self.alternative_engine.find_alternatives(
                drug_a_id, patient_context, interaction_context
            )
            
            # Get recommendations for drug B
            interaction_context['interacting_drug_id'] = drug_a_id
            recommendations_b = await self.alternative_engine.find_alternatives(
                drug_b_id, patient_context, interaction_context
            )
            
            return {
                'drug_a_recommendations': recommendations_a,
                'drug_b_recommendations': recommendations_b,
                'interaction_severity': interaction.get('severity', ''),
                'interaction_mechanism': interaction.get('mechanism', '')
            }
        
        except Exception as e:
            self.logger.error(f"Error getting interaction recommendations: {e}")
            raise
    
    async def _get_interaction_info(
        self,
        drug_a_id: str,
        drug_b_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get interaction information from knowledge graph"""
        try:
            # In a real implementation, query the knowledge graph
            # for interaction information between the two drugs
            self.logger.info(f"Getting interaction info for {drug_a_id} and {drug_b_id}")
            
            # Return mock data for now
            return {
                'severity': 'moderate',
                'mechanism': 'CYP450 enzyme interaction',
                'clinical_effect': 'Increased drug levels'
            }
        
        except Exception as e:
            self.logger.error(f"Error getting interaction info: {e}")
            return None


# Factory function
async def create_recommendation_engine(database: KnowledgeGraphDatabase) -> AlternativeMedicationEngine:
    """Create alternative medication engine"""
    return AlternativeMedicationEngine(database)


async def create_interaction_management_service(
    database: KnowledgeGraphDatabase
) -> InteractionManagementService:
    """Create interaction management service"""
    return InteractionManagementService(database)
