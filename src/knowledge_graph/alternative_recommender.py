"""
Alternative medication recommendation service
Provides evidence-based alternative medication suggestions
"""
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .models import DrugEntity, SeverityLevel, PatientContext
from .reasoning_engine import GraphPath, GraphReasoningEngine
from .interaction_detector import InteractionResult, ContraindicationResult

logger = logging.getLogger(__name__)


@dataclass
class AlternativeMedication:
    """Alternative medication recommendation"""
    drug_id: str
    drug_name: str
    generic_name: Optional[str] = None
    similarity_score: float = 0.0
    safety_score: float = 0.0
    efficacy_score: float = 0.0
    overall_score: float = 0.0
    reasons: List[str] = field(default_factory=list)
    advantages: List[str] = field(default_factory=list)
    considerations: List[str] = field(default_factory=list)
    evidence_sources: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class ManagementStrategy:
    """Management strategy for drug interaction"""
    strategy_type: str  # dose_adjustment, timing_separation, monitoring, alternative
    description: str
    specific_actions: List[str] = field(default_factory=list)
    monitoring_requirements: List[str] = field(default_factory=list)
    evidence_level: Optional[str] = None
    confidence: float = 0.0


@dataclass
class AlternativeRecommendation:
    """Complete alternative recommendation"""
    original_drug_id: str
    original_drug_name: str
    reason_for_alternative: str
    alternatives: List[AlternativeMedication] = field(default_factory=list)
    management_strategies: List[ManagementStrategy] = field(default_factory=list)
    patient_specific_notes: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)


class AlternativeRecommender:
    """
    Alternative medication recommendation engine
    Suggests alternative medications and management strategies
    """
    
    def __init__(self, reasoning_engine: GraphReasoningEngine):
        """
        Initialize alternative recommender
        
        Args:
            reasoning_engine: Graph reasoning engine instance
        """
        self.reasoning_engine = reasoning_engine
        self.db = reasoning_engine.db
        self.logger = logging.getLogger(__name__)
        self.min_similarity = 0.6
        self.min_safety_score = 0.7
    
    async def recommend_alternatives_for_interaction(
        self,
        interaction: InteractionResult,
        patient_context: Optional[PatientContext] = None
    ) -> AlternativeRecommendation:
        """
        Recommend alternatives for a drug involved in an interaction
        
        Args:
            interaction: Detected drug interaction
            patient_context: Optional patient context
            
        Returns:
            Alternative recommendation with suggested medications
        """
        try:
            self.logger.info(
                f"Finding alternatives for interaction between "
                f"{interaction.drug_a_name} and {interaction.drug_b_name}"
            )
            
            # Determine which drug to replace (typically the one with more alternatives)
            drug_to_replace_id = interaction.drug_a_id
            drug_to_replace_name = interaction.drug_a_name
            other_drug_id = interaction.drug_b_id
            
            # Find alternatives for the drug
            alternatives = await self._find_alternative_drugs(
                drug_id=drug_to_replace_id,
                exclude_drug_ids=[other_drug_id],
                patient_context=patient_context
            )
            
            # Generate management strategies
            management_strategies = await self._generate_management_strategies(
                interaction, patient_context
            )
            
            # Generate patient-specific notes
            patient_notes = self._generate_patient_notes(
                interaction, alternatives, patient_context
            )
            
            return AlternativeRecommendation(
                original_drug_id=drug_to_replace_id,
                original_drug_name=drug_to_replace_name,
                reason_for_alternative=f"Interaction with {interaction.drug_b_name} ({interaction.severity.value})",
                alternatives=alternatives,
                management_strategies=management_strategies,
                patient_specific_notes=patient_notes
            )
            
        except Exception as e:
            self.logger.error(f"Error recommending alternatives for interaction: {e}")
            return AlternativeRecommendation(
                original_drug_id=interaction.drug_a_id,
                original_drug_name=interaction.drug_a_name,
                reason_for_alternative="Error generating recommendations"
            )
    
    async def recommend_alternatives_for_contraindication(
        self,
        contraindication: ContraindicationResult,
        patient_context: PatientContext
    ) -> AlternativeRecommendation:
        """
        Recommend alternatives for a contraindicated drug
        
        Args:
            contraindication: Detected contraindication
            patient_context: Patient context
            
        Returns:
            Alternative recommendation
        """
        try:
            self.logger.info(
                f"Finding alternatives for contraindicated drug {contraindication.drug_name}"
            )
            
            # Find alternatives that don't have the same contraindication
            alternatives = await self._find_alternative_drugs(
                drug_id=contraindication.drug_id,
                exclude_drug_ids=[],
                patient_context=patient_context,
                avoid_contraindication=contraindication.condition_name
            )
            
            # Generate management strategies (may include non-pharmacological options)
            management_strategies = await self._generate_contraindication_management(
                contraindication, patient_context
            )
            
            # Generate patient-specific notes
            patient_notes = [
                f"Avoid {contraindication.drug_name} due to {contraindication.condition_name}",
                "Consult healthcare provider before making any medication changes"
            ]
            
            return AlternativeRecommendation(
                original_drug_id=contraindication.drug_id,
                original_drug_name=contraindication.drug_name,
                reason_for_alternative=f"Contraindicated for {contraindication.condition_name}",
                alternatives=alternatives,
                management_strategies=management_strategies,
                patient_specific_notes=patient_notes
            )
            
        except Exception as e:
            self.logger.error(f"Error recommending alternatives for contraindication: {e}")
            return AlternativeRecommendation(
                original_drug_id=contraindication.drug_id,
                original_drug_name=contraindication.drug_name,
                reason_for_alternative="Error generating recommendations"
            )
    
    async def _find_alternative_drugs(
        self,
        drug_id: str,
        exclude_drug_ids: List[str],
        patient_context: Optional[PatientContext] = None,
        avoid_contraindication: Optional[str] = None
    ) -> List[AlternativeMedication]:
        """Find alternative drugs with similar therapeutic effects"""
        try:
            g = self.db.connection.g
            
            # Get original drug info
            drug_result = g.V().has('id', drug_id).valueMap(True).toList()
            if not drug_result:
                return []
            
            original_drug = drug_result[0]
            
            # Find drugs with similar indications
            indications_str = original_drug.get('indications', '')
            if isinstance(indications_str, str):
                indications = [i.strip() for i in indications_str.split(',') if i.strip()]
            elif isinstance(indications_str, list):
                indications = indications_str
            else:
                indications = []
            
            # Find drugs that treat the same conditions
            similar_drugs = await self._find_drugs_by_indications(indications)
            
            # Filter out excluded drugs and original drug
            exclude_set = set(exclude_drug_ids + [drug_id])
            similar_drugs = [d for d in similar_drugs if d.get('id') not in exclude_set]
            
            # Filter out contraindicated drugs if specified
            if avoid_contraindication and patient_context:
                similar_drugs = await self._filter_contraindicated_drugs(
                    similar_drugs, avoid_contraindication
                )
            
            # Score and rank alternatives
            alternatives = []
            for drug in similar_drugs[:10]:  # Limit to top 10
                alternative = await self._score_alternative(
                    original_drug, drug, patient_context
                )
                
                if alternative and alternative.overall_score >= 0.5:
                    alternatives.append(alternative)
            
            # Sort by overall score
            alternatives.sort(key=lambda x: x.overall_score, reverse=True)
            
            return alternatives[:5]  # Return top 5
            
        except Exception as e:
            self.logger.error(f"Error finding alternative drugs: {e}")
            return []
    
    async def _find_drugs_by_indications(
        self,
        indications: List[str]
    ) -> List[Dict[str, Any]]:
        """Find drugs that treat the same conditions"""
        try:
            g = self.db.connection.g
            
            # Query drugs with matching indications
            # This is a simplified approach - in production, would use more sophisticated matching
            all_drugs = g.V().hasLabel('Drug').valueMap(True).toList()
            
            matching_drugs = []
            for drug in all_drugs:
                drug_indications_str = drug.get('indications', '')
                if isinstance(drug_indications_str, str):
                    drug_indications = [i.strip().lower() for i in drug_indications_str.split(',')]
                elif isinstance(drug_indications_str, list):
                    drug_indications = [str(i).lower() for i in drug_indications_str]
                else:
                    continue
                
                # Check for overlap in indications
                indications_lower = [i.lower() for i in indications]
                overlap = any(
                    any(ind in drug_ind or drug_ind in ind for drug_ind in drug_indications)
                    for ind in indications_lower
                )
                
                if overlap:
                    matching_drugs.append(drug)
            
            return matching_drugs
            
        except Exception as e:
            self.logger.error(f"Error finding drugs by indications: {e}")
            return []
    
    async def _filter_contraindicated_drugs(
        self,
        drugs: List[Dict[str, Any]],
        condition: str
    ) -> List[Dict[str, Any]]:
        """Filter out drugs contraindicated for a condition"""
        filtered = []
        condition_lower = condition.lower()
        
        for drug in drugs:
            contraindications_str = drug.get('contraindications', '')
            if isinstance(contraindications_str, str):
                contraindications = [c.strip().lower() for c in contraindications_str.split(',') if c.strip()]
            elif isinstance(contraindications_str, list):
                contraindications = [str(c).lower() for c in contraindications_str if c]
            else:
                contraindications = []
            
            # Check if condition is in contraindications
            is_contraindicated = any(
                condition_lower in contra or contra in condition_lower
                for contra in contraindications
            )
            
            if not is_contraindicated:
                filtered.append(drug)
        
        return filtered
    
    async def _score_alternative(
        self,
        original_drug: Dict[str, Any],
        alternative_drug: Dict[str, Any],
        patient_context: Optional[PatientContext] = None
    ) -> Optional[AlternativeMedication]:
        """Score an alternative drug"""
        try:
            # Calculate similarity score
            similarity_score = self._calculate_drug_similarity(
                original_drug, alternative_drug
            )
            
            if similarity_score < self.min_similarity:
                return None
            
            # Calculate safety score
            safety_score = await self._calculate_safety_score(
                alternative_drug, patient_context
            )
            
            if safety_score < self.min_safety_score:
                return None
            
            # Efficacy score (simplified - would use clinical data in production)
            efficacy_score = 0.8  # Default assumption
            
            # Calculate overall score
            overall_score = (
                similarity_score * 0.3 +
                safety_score * 0.5 +
                efficacy_score * 0.2
            )
            
            # Generate reasons and advantages
            reasons = self._generate_alternative_reasons(
                original_drug, alternative_drug, similarity_score
            )
            
            advantages = self._generate_alternative_advantages(
                alternative_drug, safety_score
            )
            
            considerations = self._generate_alternative_considerations(
                alternative_drug, patient_context
            )
            
            return AlternativeMedication(
                drug_id=alternative_drug.get('id', ''),
                drug_name=alternative_drug.get('name', ''),
                generic_name=alternative_drug.get('generic_name'),
                similarity_score=similarity_score,
                safety_score=safety_score,
                efficacy_score=efficacy_score,
                overall_score=overall_score,
                reasons=reasons,
                advantages=advantages,
                considerations=considerations,
                evidence_sources=['DrugBank', 'Clinical Guidelines'],
                confidence=overall_score
            )
            
        except Exception as e:
            self.logger.error(f"Error scoring alternative: {e}")
            return None
    
    def _calculate_drug_similarity(
        self,
        drug1: Dict[str, Any],
        drug2: Dict[str, Any]
    ) -> float:
        """Calculate similarity between two drugs"""
        similarity = 0.0
        factors = 0
        
        # Compare indications
        ind1_str = drug1.get('indications', '')
        ind2_str = drug2.get('indications', '')
        
        if ind1_str and ind2_str:
            ind1 = set(str(ind1_str).lower().split(','))
            ind2 = set(str(ind2_str).lower().split(','))
            
            if ind1 and ind2:
                overlap = len(ind1 & ind2)
                union = len(ind1 | ind2)
                if union > 0:
                    similarity += overlap / union
                    factors += 1
        
        # Compare ATC codes (therapeutic classification)
        atc1 = drug1.get('atc_codes', [])
        atc2 = drug2.get('atc_codes', [])
        
        if atc1 and atc2:
            if isinstance(atc1, str):
                atc1 = [atc1]
            if isinstance(atc2, str):
                atc2 = [atc2]
            
            atc1_set = set(atc1)
            atc2_set = set(atc2)
            
            if atc1_set and atc2_set:
                overlap = len(atc1_set & atc2_set)
                if overlap > 0:
                    similarity += 1.0
                else:
                    # Check if they share the same first character (same anatomical group)
                    if any(a1[0] == a2[0] for a1 in atc1_set for a2 in atc2_set if a1 and a2):
                        similarity += 0.5
                factors += 1
        
        # Compare mechanism of action
        mech1 = str(drug1.get('mechanism', '')).lower()
        mech2 = str(drug2.get('mechanism', '')).lower()
        
        if mech1 and mech2:
            # Simple keyword overlap
            words1 = set(mech1.split())
            words2 = set(mech2.split())
            if words1 and words2:
                overlap = len(words1 & words2)
                union = len(words1 | words2)
                if union > 0:
                    similarity += overlap / union
                    factors += 1
        
        return similarity / factors if factors > 0 else 0.0
    
    async def _calculate_safety_score(
        self,
        drug: Dict[str, Any],
        patient_context: Optional[PatientContext] = None
    ) -> float:
        """Calculate safety score for a drug"""
        safety_score = 1.0
        
        # Check for contraindications with patient conditions
        if patient_context and patient_context.conditions:
            contraindications_str = drug.get('contraindications', '')
            if isinstance(contraindications_str, str):
                contraindications = [c.strip().lower() for c in contraindications_str.split(',') if c.strip()]
            elif isinstance(contraindications_str, list):
                contraindications = [str(c).lower() for c in contraindications_str if c]
            else:
                contraindications = []
            
            for condition in patient_context.conditions:
                condition_lower = condition.lower()
                if any(condition_lower in contra or contra in condition_lower for contra in contraindications):
                    safety_score -= 0.3
        
        # Check for interactions with current medications
        if patient_context and patient_context.medications:
            # Simplified - would check actual interactions in production
            if len(patient_context.medications) > 5:
                safety_score -= 0.1  # Polypharmacy risk
        
        # Age-based adjustments
        if patient_context:
            age = patient_context.demographics.get('age', 0)
            if age > 65 or age < 18:
                # Some drugs are safer for specific age groups
                # This would be drug-specific in production
                pass
        
        return max(safety_score, 0.0)
    
    def _generate_alternative_reasons(
        self,
        original_drug: Dict[str, Any],
        alternative_drug: Dict[str, Any],
        similarity_score: float
    ) -> List[str]:
        """Generate reasons for recommending this alternative"""
        reasons = []
        
        if similarity_score > 0.8:
            reasons.append("Very similar therapeutic profile")
        elif similarity_score > 0.6:
            reasons.append("Similar therapeutic effects")
        
        # Check for same drug class
        atc1 = original_drug.get('atc_codes', [])
        atc2 = alternative_drug.get('atc_codes', [])
        
        if atc1 and atc2:
            if isinstance(atc1, str):
                atc1 = [atc1]
            if isinstance(atc2, str):
                atc2 = [atc2]
            
            if any(a1 == a2 for a1 in atc1 for a2 in atc2):
                reasons.append("Same drug class")
            elif any(a1[0] == a2[0] for a1 in atc1 for a2 in atc2 if a1 and a2):
                reasons.append("Same therapeutic category")
        
        return reasons
    
    def _generate_alternative_advantages(
        self,
        drug: Dict[str, Any],
        safety_score: float
    ) -> List[str]:
        """Generate advantages of this alternative"""
        advantages = []
        
        if safety_score > 0.9:
            advantages.append("Excellent safety profile")
        elif safety_score > 0.8:
            advantages.append("Good safety profile")
        
        # Check dosage forms
        dosage_forms = drug.get('dosage_forms', [])
        if dosage_forms:
            if isinstance(dosage_forms, str):
                dosage_forms = [dosage_forms]
            if len(dosage_forms) > 2:
                advantages.append("Multiple dosage forms available")
        
        return advantages
    
    def _generate_alternative_considerations(
        self,
        drug: Dict[str, Any],
        patient_context: Optional[PatientContext] = None
    ) -> List[str]:
        """Generate considerations for this alternative"""
        considerations = []
        
        # Generic name consideration
        generic_name = drug.get('generic_name')
        if generic_name:
            considerations.append(f"Generic name: {generic_name}")
        
        # Dosage forms
        dosage_forms = drug.get('dosage_forms', [])
        if dosage_forms:
            if isinstance(dosage_forms, str):
                dosage_forms = [dosage_forms]
            considerations.append(f"Available as: {', '.join(dosage_forms)}")
        
        # Patient-specific considerations
        if patient_context:
            age = patient_context.demographics.get('age', 0)
            if age > 65:
                considerations.append("Dosage adjustment may be needed for elderly patients")
            elif age < 18:
                considerations.append("Pediatric dosing required")
        
        return considerations
    
    async def _generate_management_strategies(
        self,
        interaction: InteractionResult,
        patient_context: Optional[PatientContext] = None
    ) -> List[ManagementStrategy]:
        """Generate management strategies for an interaction"""
        strategies = []
        
        # Use management info from interaction if available
        if interaction.management:
            strategies.append(ManagementStrategy(
                strategy_type="management",
                description=interaction.management,
                specific_actions=[interaction.management],
                confidence=interaction.confidence
            ))
        
        # Severity-based strategies
        if interaction.severity == SeverityLevel.CONTRAINDICATED:
            strategies.append(ManagementStrategy(
                strategy_type="alternative",
                description="Avoid combination - use alternative medication",
                specific_actions=[
                    "Discontinue one of the medications",
                    "Consult healthcare provider for alternative"
                ],
                confidence=0.9
            ))
        
        elif interaction.severity == SeverityLevel.MAJOR:
            strategies.append(ManagementStrategy(
                strategy_type="monitoring",
                description="Close monitoring required if combination is necessary",
                specific_actions=[
                    "Monitor for adverse effects",
                    "Consider dose adjustment",
                    "Regular follow-up with healthcare provider"
                ],
                monitoring_requirements=[
                    "Monitor relevant lab values",
                    "Watch for signs of adverse effects"
                ],
                confidence=0.8
            ))
            
            strategies.append(ManagementStrategy(
                strategy_type="timing_separation",
                description="Separate administration times if possible",
                specific_actions=[
                    "Take medications at different times of day",
                    "Maintain at least 2-4 hours between doses"
                ],
                confidence=0.7
            ))
        
        elif interaction.severity == SeverityLevel.MODERATE:
            strategies.append(ManagementStrategy(
                strategy_type="monitoring",
                description="Monitor for potential interaction effects",
                specific_actions=[
                    "Be aware of potential interaction",
                    "Report any unusual symptoms"
                ],
                confidence=0.7
            ))
        
        return strategies
    
    async def _generate_contraindication_management(
        self,
        contraindication: ContraindicationResult,
        patient_context: PatientContext
    ) -> List[ManagementStrategy]:
        """Generate management strategies for a contraindication"""
        strategies = []
        
        # Primary strategy: avoid the medication
        strategies.append(ManagementStrategy(
            strategy_type="alternative",
            description=f"Avoid {contraindication.drug_name} due to {contraindication.condition_name}",
            specific_actions=[
                f"Do not use {contraindication.drug_name}",
                "Consult healthcare provider for alternative medications",
                "Discuss treatment options that are safe for your condition"
            ],
            confidence=0.95
        ))
        
        # If severity is not absolute contraindication, may have monitoring option
        if contraindication.severity == SeverityLevel.MAJOR:
            strategies.append(ManagementStrategy(
                strategy_type="monitoring",
                description="If no alternatives available, intensive monitoring required",
                specific_actions=[
                    "Use only under close medical supervision",
                    "Frequent monitoring of condition and drug effects",
                    "Immediate reporting of any adverse effects"
                ],
                monitoring_requirements=[
                    "Regular medical check-ups",
                    "Laboratory monitoring as appropriate",
                    "Close symptom monitoring"
                ],
                evidence_level="Expert opinion",
                confidence=0.6
            ))
        
        return strategies
    
    def _generate_patient_notes(
        self,
        interaction: InteractionResult,
        alternatives: List[AlternativeMedication],
        patient_context: Optional[PatientContext] = None
    ) -> List[str]:
        """Generate patient-specific notes"""
        notes = []
        
        # Severity-based notes
        if interaction.severity in [SeverityLevel.MAJOR, SeverityLevel.CONTRAINDICATED]:
            notes.append(
                "This is a significant interaction. Do not make changes without "
                "consulting your healthcare provider."
            )
        
        # Alternative availability
        if alternatives:
            notes.append(
                f"Found {len(alternatives)} potential alternative(s). "
                "Discuss these options with your healthcare provider."
            )
        else:
            notes.append(
                "Limited alternatives available. Focus on management strategies "
                "and close monitoring."
            )
        
        # Patient-specific notes
        if patient_context:
            age = patient_context.demographics.get('age', 0)
            if age > 65:
                notes.append(
                    "As a senior patient, you may be more sensitive to medication changes. "
                    "Work closely with your healthcare provider."
                )
            
            if len(patient_context.medications) > 5:
                notes.append(
                    "With multiple medications, any changes should be carefully coordinated "
                    "to avoid new interactions."
                )
        
        return notes


# Global alternative recommender instance
alternative_recommender = None


def initialize_alternative_recommender(reasoning_engine: GraphReasoningEngine):
    """Initialize global alternative recommender instance"""
    global alternative_recommender
    alternative_recommender = AlternativeRecommender(reasoning_engine)
    return alternative_recommender
