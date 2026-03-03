"""
Personalization engine for PharmaGuide
Implements risk-based ranking, physiological factor analysis, and dosing adjustments
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .models import PatientContext, SeverityLevel
from .database import KnowledgeGraphDatabase
from .reasoning_engine import GraphReasoningEngine, RiskAssessment

logger = logging.getLogger(__name__)


class RiskCategory(str, Enum):
    """Risk categories for personalized assessments"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class DosingAdjustmentReason(str, Enum):
    """Reasons for dosing adjustments"""
    AGE = "age"
    WEIGHT = "weight"
    RENAL_IMPAIRMENT = "renal_impairment"
    HEPATIC_IMPAIRMENT = "hepatic_impairment"
    DRUG_INTERACTION = "drug_interaction"
    GENETIC_FACTOR = "genetic_factor"


@dataclass
class RankedResult:
    """Ranked result with personalized risk score"""
    entity_id: str
    entity_type: str
    entity_name: str
    base_risk_score: float
    personalized_risk_score: float
    risk_category: RiskCategory
    contributing_factors: List[str] = field(default_factory=list)
    evidence_sources: List[str] = field(default_factory=list)
    confidence: float = 0.0
    real_world_evidence_count: int = 0


@dataclass
class PhysiologicalFactor:
    """Physiological factor affecting drug response"""
    factor_name: str
    factor_value: Any
    impact_on_response: str  # increased, decreased, no_change
    impact_magnitude: float  # 0.0 to 1.0
    explanation: str
    evidence_sources: List[str] = field(default_factory=list)


@dataclass
class DosingAdjustment:
    """Dosing adjustment recommendation"""
    drug_id: str
    drug_name: str
    standard_dose: str
    adjusted_dose: str
    adjustment_factor: float
    explanation: str
    reasons: List[DosingAdjustmentReason] = field(default_factory=list)
    confidence: float = 0.0
    monitoring_recommendations: List[str] = field(default_factory=list)


class PersonalizationEngine:
    """
    Personalization engine for risk-based ranking and physiological analysis
    
    Implements:
    - Risk-based ranking using real-world evidence
    - Physiological factor analysis for drug response
    - Dosing adjustment recommendations
    """
    
    def __init__(
        self,
        database: KnowledgeGraphDatabase,
        reasoning_engine: GraphReasoningEngine
    ):
        """
        Initialize personalization engine
        
        Args:
            database: Knowledge graph database connection
            reasoning_engine: Graph reasoning engine
        """
        self.db = database
        self.reasoning_engine = reasoning_engine
        self.logger = logging.getLogger(__name__)
        
        # Real-world evidence dataset weights
        self.rwe_weights = {
            'FAERS': 0.8,  # High weight for real-world adverse events
            'OnSIDES': 0.9,  # High weight for modern side effects data
            'SIDER': 0.7,  # Clinical trial data
            'DrugBank': 0.85,  # Authoritative drug information
            'DDInter': 0.8  # Drug interaction data
        }
    
    async def rank_by_personalized_risk(
        self,
        results: List[Dict[str, Any]],
        patient_context: PatientContext,
        include_rwe: bool = True
    ) -> List[RankedResult]:
        """
        Rank results by personalized risk using real-world evidence
        
        Args:
            results: List of results to rank (side effects, interactions, etc.)
            patient_context: Patient context for personalization
            include_rwe: Whether to include real-world evidence in ranking
            
        Returns:
            List of ranked results with personalized risk scores
        """
        try:
            self.logger.info(
                f"Ranking {len(results)} results for patient {patient_context.id}"
            )
            
            ranked_results = []
            
            for result in results:
                entity_id = result.get('id', '')
                entity_type = result.get('type', result.get('label', ''))
                entity_name = result.get('name', '')
                
                # Calculate base risk score
                base_risk = result.get('risk_score', result.get('frequency', 0.5))
                
                # Calculate personalized risk
                personalized_risk, factors = await self._calculate_personalized_risk(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    base_risk=base_risk,
                    patient_context=patient_context
                )
                
                # Get real-world evidence if requested
                rwe_count = 0
                evidence_sources = result.get('evidence_sources', [])
                
                if include_rwe:
                    rwe_data = await self._get_real_world_evidence(
                        entity_id=entity_id,
                        patient_context=patient_context
                    )
                    rwe_count = rwe_data.get('patient_count', 0)
                    evidence_sources.extend(rwe_data.get('sources', []))
                    
                    # Adjust risk based on RWE
                    rwe_adjustment = self._calculate_rwe_adjustment(rwe_data)
                    personalized_risk *= rwe_adjustment
                
                # Determine risk category
                risk_category = self._determine_risk_category(personalized_risk)
                
                # Calculate confidence
                confidence = result.get('confidence', 0.8)
                if include_rwe and rwe_count > 0:
                    # Increase confidence with more real-world evidence
                    confidence = min(confidence * (1 + (rwe_count / 10000)), 1.0)
                
                ranked_result = RankedResult(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    entity_name=entity_name,
                    base_risk_score=base_risk,
                    personalized_risk_score=personalized_risk,
                    risk_category=risk_category,
                    contributing_factors=factors,
                    evidence_sources=list(set(evidence_sources)),
                    confidence=confidence,
                    real_world_evidence_count=rwe_count
                )
                
                ranked_results.append(ranked_result)
            
            # Sort by personalized risk score (highest first)
            ranked_results.sort(
                key=lambda r: r.personalized_risk_score,
                reverse=True
            )
            
            self.logger.info(
                f"Ranked {len(ranked_results)} results, "
                f"top risk: {ranked_results[0].personalized_risk_score:.3f}"
                if ranked_results else "no results"
            )
            
            return ranked_results
            
        except Exception as e:
            self.logger.error(f"Error ranking by personalized risk: {e}")
            return []
    
    async def analyze_physiological_factors(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> List[PhysiologicalFactor]:
        """
        Analyze physiological factors affecting drug response
        
        Args:
            drug_id: Drug to analyze
            patient_context: Patient context
            
        Returns:
            List of physiological factors affecting drug response
        """
        try:
            self.logger.info(
                f"Analyzing physiological factors for drug {drug_id} "
                f"and patient {patient_context.id}"
            )
            
            factors = []
            
            # Analyze age factors
            age_factors = await self._analyze_age_factors(drug_id, patient_context)
            factors.extend(age_factors)
            
            # Analyze weight factors
            weight_factors = await self._analyze_weight_factors(drug_id, patient_context)
            factors.extend(weight_factors)
            
            # Analyze renal function
            renal_factors = await self._analyze_renal_factors(drug_id, patient_context)
            factors.extend(renal_factors)
            
            # Analyze hepatic function
            hepatic_factors = await self._analyze_hepatic_factors(drug_id, patient_context)
            factors.extend(hepatic_factors)
            
            # Analyze genetic factors
            genetic_factors = await self._analyze_genetic_factors(drug_id, patient_context)
            factors.extend(genetic_factors)
            
            # Analyze gender-specific factors
            gender_factors = await self._analyze_gender_factors(drug_id, patient_context)
            factors.extend(gender_factors)
            
            self.logger.info(
                f"Identified {len(factors)} physiological factors"
            )
            
            return factors
            
        except Exception as e:
            self.logger.error(f"Error analyzing physiological factors: {e}")
            return []
    
    async def generate_dosing_adjustments(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> Optional[DosingAdjustment]:
        """
        Generate dosing adjustment recommendations
        
        Args:
            drug_id: Drug to generate adjustments for
            patient_context: Patient context
            
        Returns:
            Dosing adjustment recommendation if needed
        """
        try:
            self.logger.info(
                f"Generating dosing adjustments for drug {drug_id} "
                f"and patient {patient_context.id}"
            )
            
            # Get drug information
            drug_info = await self._get_drug_info(drug_id)
            if not drug_info:
                return None
            
            drug_name = drug_info.get('name', 'Unknown')
            standard_dose = drug_info.get('standard_dose', 'Not specified')
            
            # Calculate adjustment factors
            adjustment_factor = 1.0
            reasons = []
            explanations = []
            monitoring_recs = []
            
            # Age-based adjustments
            age_adjustment, age_reason = self._calculate_age_adjustment(
                patient_context, drug_info
            )
            if age_adjustment != 1.0:
                adjustment_factor *= age_adjustment
                reasons.append(age_reason)
                explanations.append(
                    f"Age-based adjustment: {age_adjustment:.2f}x"
                )
            
            # Weight-based adjustments
            weight_adjustment, weight_reason = self._calculate_weight_adjustment(
                patient_context, drug_info
            )
            if weight_adjustment != 1.0:
                adjustment_factor *= weight_adjustment
                reasons.append(weight_reason)
                explanations.append(
                    f"Weight-based adjustment: {weight_adjustment:.2f}x"
                )
            
            # Renal function adjustments
            renal_adjustment, renal_reason = await self._calculate_renal_adjustment(
                drug_id, patient_context
            )
            if renal_adjustment != 1.0:
                adjustment_factor *= renal_adjustment
                reasons.append(renal_reason)
                explanations.append(
                    f"Renal function adjustment: {renal_adjustment:.2f}x"
                )
                monitoring_recs.append("Monitor renal function regularly")
            
            # Hepatic function adjustments
            hepatic_adjustment, hepatic_reason = await self._calculate_hepatic_adjustment(
                drug_id, patient_context
            )
            if hepatic_adjustment != 1.0:
                adjustment_factor *= hepatic_adjustment
                reasons.append(hepatic_reason)
                explanations.append(
                    f"Hepatic function adjustment: {hepatic_adjustment:.2f}x"
                )
                monitoring_recs.append("Monitor liver function regularly")
            
            # Drug interaction adjustments
            interaction_adjustment, interaction_reason = await self._calculate_interaction_adjustment(
                drug_id, patient_context
            )
            if interaction_adjustment != 1.0:
                adjustment_factor *= interaction_adjustment
                reasons.append(interaction_reason)
                explanations.append(
                    f"Drug interaction adjustment: {interaction_adjustment:.2f}x"
                )
                monitoring_recs.append("Monitor for drug interactions")
            
            # Genetic factor adjustments
            genetic_adjustment, genetic_reason = await self._calculate_genetic_adjustment(
                drug_id, patient_context
            )
            if genetic_adjustment != 1.0:
                adjustment_factor *= genetic_adjustment
                reasons.append(genetic_reason)
                explanations.append(
                    f"Genetic factor adjustment: {genetic_adjustment:.2f}x"
                )
            
            # Only create adjustment if factor is significantly different from 1.0
            if abs(adjustment_factor - 1.0) < 0.1:
                self.logger.info("No significant dosing adjustment needed")
                return None
            
            # Generate adjusted dose description
            adjusted_dose = self._generate_adjusted_dose_description(
                standard_dose, adjustment_factor
            )
            
            # Combine explanations
            full_explanation = "; ".join(explanations)
            
            # Calculate confidence based on number of factors
            confidence = min(0.7 + (len(reasons) * 0.05), 0.95)
            
            adjustment = DosingAdjustment(
                drug_id=drug_id,
                drug_name=drug_name,
                standard_dose=standard_dose,
                adjusted_dose=adjusted_dose,
                adjustment_factor=adjustment_factor,
                reasons=reasons,
                explanation=full_explanation,
                confidence=confidence,
                monitoring_recommendations=monitoring_recs
            )
            
            self.logger.info(
                f"Generated dosing adjustment: {adjustment_factor:.2f}x "
                f"for {len(reasons)} reasons"
            )
            
            return adjustment
            
        except Exception as e:
            self.logger.error(f"Error generating dosing adjustments: {e}")
            return None
    
    async def _calculate_personalized_risk(
        self,
        entity_id: str,
        entity_type: str,
        base_risk: float,
        patient_context: PatientContext
    ) -> Tuple[float, List[str]]:
        """Calculate personalized risk score"""
        personalized_risk = base_risk
        factors = []
        
        demographics = patient_context.demographics
        
        # Age adjustments
        age = demographics.get('age', 0)
        if age > 65:
            personalized_risk *= 1.25
            factors.append("Advanced age (>65)")
        elif age < 18:
            personalized_risk *= 1.2
            factors.append("Pediatric patient")
        elif age < 2:
            personalized_risk *= 1.3
            factors.append("Infant")
        
        # Gender adjustments for certain conditions
        gender = demographics.get('gender', '').lower()
        if gender == 'female' and entity_type == 'SideEffect':
            # Some side effects more common in females
            personalized_risk *= 1.05
            factors.append("Gender-specific risk factor")
        
        # Weight adjustments
        weight = demographics.get('weight', 0)
        if weight > 0:
            if weight < 50:  # kg
                personalized_risk *= 1.15
                factors.append("Low body weight")
            elif weight > 120:  # kg
                personalized_risk *= 1.1
                factors.append("High body weight")
        
        # Condition-based adjustments
        high_risk_conditions = {
            'diabetes': 1.15,
            'heart_disease': 1.2,
            'kidney_disease': 1.25,
            'liver_disease': 1.25,
            'hypertension': 1.1
        }
        
        for condition in patient_context.conditions:
            condition_lower = condition.lower()
            for risk_condition, multiplier in high_risk_conditions.items():
                if risk_condition in condition_lower:
                    personalized_risk *= multiplier
                    factors.append(f"Pre-existing condition: {condition}")
                    break
        
        # Polypharmacy risk
        med_count = len(patient_context.medications)
        if med_count > 5:
            personalized_risk *= 1.15
            factors.append(f"Polypharmacy ({med_count} medications)")
        elif med_count > 10:
            personalized_risk *= 1.25
            factors.append(f"High polypharmacy ({med_count} medications)")
        
        # Risk factors
        for risk_factor in patient_context.risk_factors:
            personalized_risk *= 1.05
            factors.append(f"Risk factor: {risk_factor}")
        
        # Allergy history
        if patient_context.allergies:
            personalized_risk *= 1.1
            factors.append(f"Drug allergy history ({len(patient_context.allergies)} allergies)")
        
        # Cap at 1.0
        personalized_risk = min(personalized_risk, 1.0)
        
        return personalized_risk, factors
    
    async def _get_real_world_evidence(
        self,
        entity_id: str,
        patient_context: PatientContext
    ) -> Dict[str, Any]:
        """Get real-world evidence for entity"""
        try:
            g = self.db.connection.g
            
            # Query for real-world evidence relationships
            evidence_results = g.V().has('id', entity_id).inE('REPORTED_IN').valueMap(True).toList()
            
            patient_count = 0
            sources = []
            demographic_matches = 0
            
            for evidence in evidence_results:
                source = evidence.get('source_dataset', '')
                sources.append(source)
                
                # Count patients
                count = evidence.get('patient_count', 0)
                if isinstance(count, (int, float)):
                    patient_count += int(count)
                
                # Check demographic matching
                evidence_age = evidence.get('age_range', '')
                evidence_gender = evidence.get('gender', '')
                
                patient_age = patient_context.demographics.get('age', 0)
                patient_gender = patient_context.demographics.get('gender', '').lower()
                
                # Simple demographic matching
                if evidence_age and patient_age:
                    # Parse age range (e.g., "60-70")
                    if '-' in str(evidence_age):
                        try:
                            min_age, max_age = map(int, str(evidence_age).split('-'))
                            if min_age <= patient_age <= max_age:
                                demographic_matches += 1
                        except ValueError:
                            pass
                
                if evidence_gender and patient_gender:
                    if str(evidence_gender).lower() == patient_gender:
                        demographic_matches += 1
            
            return {
                'patient_count': patient_count,
                'sources': list(set(sources)),
                'demographic_matches': demographic_matches
            }
            
        except Exception as e:
            self.logger.error(f"Error getting real-world evidence: {e}")
            return {'patient_count': 0, 'sources': [], 'demographic_matches': 0}
    
    def _calculate_rwe_adjustment(self, rwe_data: Dict[str, Any]) -> float:
        """Calculate risk adjustment based on real-world evidence"""
        patient_count = rwe_data.get('patient_count', 0)
        demographic_matches = rwe_data.get('demographic_matches', 0)
        sources = rwe_data.get('sources', [])
        
        adjustment = 1.0
        
        # Increase risk if many patients reported this
        if patient_count > 1000:
            adjustment *= 1.1
        elif patient_count > 10000:
            adjustment *= 1.15
        elif patient_count > 100000:
            adjustment *= 1.2
        
        # Increase risk if demographics match
        if demographic_matches > 0:
            adjustment *= (1.0 + (demographic_matches * 0.05))
        
        # Weight by source authority
        source_weight = 1.0
        for source in sources:
            source_weight = max(source_weight, self.rwe_weights.get(source, 0.5))
        
        adjustment *= source_weight
        
        return adjustment
    
    def _determine_risk_category(self, risk_score: float) -> RiskCategory:
        """Determine risk category from score"""
        if risk_score < 0.25:
            return RiskCategory.LOW
        elif risk_score < 0.5:
            return RiskCategory.MODERATE
        elif risk_score < 0.75:
            return RiskCategory.HIGH
        else:
            return RiskCategory.CRITICAL

    
    async def _analyze_age_factors(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> List[PhysiologicalFactor]:
        """Analyze age-related factors"""
        factors = []
        age = patient_context.demographics.get('age', 0)
        
        if age == 0:
            return factors
        
        try:
            # Query knowledge graph for age-related drug response
            g = self.db.connection.g
            age_relationships = g.V().has('id', drug_id).outE('AGE_RESPONSE').valueMap(True).toList()
            
            for rel in age_relationships:
                age_range = rel.get('age_range', '')
                impact = rel.get('impact', 'no_change')
                magnitude = rel.get('magnitude', 0.5)
                
                # Check if patient age falls in this range
                if self._age_in_range(age, age_range):
                    factor = PhysiologicalFactor(
                        factor_name="Age",
                        factor_value=age,
                        impact_on_response=impact,
                        impact_magnitude=magnitude,
                        explanation=f"Patient age {age} affects drug metabolism and clearance",
                        evidence_sources=rel.get('sources', [])
                    )
                    factors.append(factor)
            
            # Add general age-based factors if no specific data
            if not factors:
                if age > 65:
                    factors.append(PhysiologicalFactor(
                        factor_name="Advanced Age",
                        factor_value=age,
                        impact_on_response="decreased",
                        impact_magnitude=0.7,
                        explanation="Elderly patients may have reduced drug clearance and increased sensitivity",
                        evidence_sources=["Clinical Guidelines"]
                    ))
                elif age < 18:
                    factors.append(PhysiologicalFactor(
                        factor_name="Pediatric Age",
                        factor_value=age,
                        impact_on_response="increased",
                        impact_magnitude=0.6,
                        explanation="Pediatric patients may have different pharmacokinetics",
                        evidence_sources=["Clinical Guidelines"]
                    ))
        
        except Exception as e:
            self.logger.error(f"Error analyzing age factors: {e}")
        
        return factors
    
    async def _analyze_weight_factors(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> List[PhysiologicalFactor]:
        """Analyze weight-related factors"""
        factors = []
        weight = patient_context.demographics.get('weight', 0)
        
        if weight == 0:
            return factors
        
        try:
            # Query for weight-based dosing information
            g = self.db.connection.g
            weight_relationships = g.V().has('id', drug_id).outE('WEIGHT_RESPONSE').valueMap(True).toList()
            
            for rel in weight_relationships:
                weight_range = rel.get('weight_range', '')
                impact = rel.get('impact', 'no_change')
                magnitude = rel.get('magnitude', 0.5)
                
                if self._weight_in_range(weight, weight_range):
                    factor = PhysiologicalFactor(
                        factor_name="Body Weight",
                        factor_value=weight,
                        impact_on_response=impact,
                        impact_magnitude=magnitude,
                        explanation=f"Patient weight {weight}kg affects drug distribution and dosing",
                        evidence_sources=rel.get('sources', [])
                    )
                    factors.append(factor)
            
            # Add general weight-based factors
            if not factors:
                if weight < 50:
                    factors.append(PhysiologicalFactor(
                        factor_name="Low Body Weight",
                        factor_value=weight,
                        impact_on_response="increased",
                        impact_magnitude=0.6,
                        explanation="Low body weight may require dose reduction",
                        evidence_sources=["Clinical Guidelines"]
                    ))
                elif weight > 120:
                    factors.append(PhysiologicalFactor(
                        factor_name="High Body Weight",
                        factor_value=weight,
                        impact_on_response="decreased",
                        impact_magnitude=0.5,
                        explanation="High body weight may require dose adjustment",
                        evidence_sources=["Clinical Guidelines"]
                    ))
        
        except Exception as e:
            self.logger.error(f"Error analyzing weight factors: {e}")
        
        return factors
    
    async def _analyze_renal_factors(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> List[PhysiologicalFactor]:
        """Analyze renal function factors"""
        factors = []
        
        # Check for kidney disease in conditions
        has_kidney_disease = any(
            'kidney' in condition.lower() or 'renal' in condition.lower()
            for condition in patient_context.conditions
        )
        
        if not has_kidney_disease:
            return factors
        
        try:
            # Query for renal clearance information
            g = self.db.connection.g
            renal_relationships = g.V().has('id', drug_id).outE('RENAL_CLEARANCE').valueMap(True).toList()
            
            for rel in renal_relationships:
                clearance_pct = rel.get('renal_clearance_percentage', 0)
                
                if clearance_pct > 50:  # Drug primarily cleared by kidneys
                    factor = PhysiologicalFactor(
                        factor_name="Renal Impairment",
                        factor_value="Present",
                        impact_on_response="decreased",
                        impact_magnitude=0.8,
                        explanation=f"Drug is {clearance_pct}% renally cleared; impairment may reduce clearance",
                        evidence_sources=rel.get('sources', [])
                    )
                    factors.append(factor)
        
        except Exception as e:
            self.logger.error(f"Error analyzing renal factors: {e}")
        
        return factors
    
    async def _analyze_hepatic_factors(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> List[PhysiologicalFactor]:
        """Analyze hepatic function factors"""
        factors = []
        
        # Check for liver disease in conditions
        has_liver_disease = any(
            'liver' in condition.lower() or 'hepatic' in condition.lower()
            for condition in patient_context.conditions
        )
        
        if not has_liver_disease:
            return factors
        
        try:
            # Query for hepatic metabolism information
            g = self.db.connection.g
            hepatic_relationships = g.V().has('id', drug_id).outE('HEPATIC_METABOLISM').valueMap(True).toList()
            
            for rel in hepatic_relationships:
                metabolism_pct = rel.get('hepatic_metabolism_percentage', 0)
                
                if metabolism_pct > 50:  # Drug primarily metabolized by liver
                    factor = PhysiologicalFactor(
                        factor_name="Hepatic Impairment",
                        factor_value="Present",
                        impact_on_response="decreased",
                        impact_magnitude=0.8,
                        explanation=f"Drug is {metabolism_pct}% hepatically metabolized; impairment may reduce metabolism",
                        evidence_sources=rel.get('sources', [])
                    )
                    factors.append(factor)
        
        except Exception as e:
            self.logger.error(f"Error analyzing hepatic factors: {e}")
        
        return factors
    
    async def _analyze_genetic_factors(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> List[PhysiologicalFactor]:
        """Analyze genetic factors"""
        factors = []
        
        if not patient_context.genetic_factors:
            return factors
        
        try:
            # Query for pharmacogenomic relationships
            g = self.db.connection.g
            genetic_relationships = g.V().has('id', drug_id).outE('PHARMACOGENOMIC').valueMap(True).toList()
            
            for rel in genetic_relationships:
                gene = rel.get('gene', '')
                variant = rel.get('variant', '')
                impact = rel.get('impact', 'no_change')
                magnitude = rel.get('magnitude', 0.5)
                
                # Check if patient has this genetic variant
                patient_variant = patient_context.genetic_factors.get(gene, '')
                
                if patient_variant == variant:
                    factor = PhysiologicalFactor(
                        factor_name=f"Genetic Variant: {gene}",
                        factor_value=variant,
                        impact_on_response=impact,
                        impact_magnitude=magnitude,
                        explanation=f"Patient has {gene} {variant} variant affecting drug metabolism",
                        evidence_sources=rel.get('sources', [])
                    )
                    factors.append(factor)
        
        except Exception as e:
            self.logger.error(f"Error analyzing genetic factors: {e}")
        
        return factors
    
    async def _analyze_gender_factors(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> List[PhysiologicalFactor]:
        """Analyze gender-specific factors"""
        factors = []
        gender = patient_context.demographics.get('gender', '').lower()
        
        if not gender:
            return factors
        
        try:
            # Query for gender-specific drug response
            g = self.db.connection.g
            gender_relationships = g.V().has('id', drug_id).outE('GENDER_RESPONSE').valueMap(True).toList()
            
            for rel in gender_relationships:
                rel_gender = rel.get('gender', '').lower()
                impact = rel.get('impact', 'no_change')
                magnitude = rel.get('magnitude', 0.5)
                
                if rel_gender == gender:
                    factor = PhysiologicalFactor(
                        factor_name="Gender",
                        factor_value=gender,
                        impact_on_response=impact,
                        impact_magnitude=magnitude,
                        explanation=f"Gender-specific drug response patterns identified",
                        evidence_sources=rel.get('sources', [])
                    )
                    factors.append(factor)
        
        except Exception as e:
            self.logger.error(f"Error analyzing gender factors: {e}")
        
        return factors
    
    async def _get_drug_info(self, drug_id: str) -> Optional[Dict[str, Any]]:
        """Get drug information from knowledge graph"""
        try:
            g = self.db.connection.g
            result = g.V().has('id', drug_id).valueMap(True).toList()
            
            if result:
                return result[0]
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting drug info: {e}")
            return None
    
    def _calculate_age_adjustment(
        self,
        patient_context: PatientContext,
        drug_info: Dict[str, Any]
    ) -> Tuple[float, Optional[DosingAdjustmentReason]]:
        """Calculate age-based dosing adjustment"""
        age = patient_context.demographics.get('age', 0)
        
        if age == 0:
            return 1.0, None
        
        # Elderly patients (>65)
        if age > 65:
            if age > 80:
                return 0.7, DosingAdjustmentReason.AGE
            return 0.8, DosingAdjustmentReason.AGE
        
        # Pediatric patients
        elif age < 18:
            if age < 2:
                return 0.5, DosingAdjustmentReason.AGE
            elif age < 12:
                return 0.6, DosingAdjustmentReason.AGE
            return 0.75, DosingAdjustmentReason.AGE
        
        return 1.0, None
    
    def _calculate_weight_adjustment(
        self,
        patient_context: PatientContext,
        drug_info: Dict[str, Any]
    ) -> Tuple[float, Optional[DosingAdjustmentReason]]:
        """Calculate weight-based dosing adjustment"""
        weight = patient_context.demographics.get('weight', 0)
        
        if weight == 0:
            return 1.0, None
        
        # Low body weight
        if weight < 50:
            return 0.75, DosingAdjustmentReason.WEIGHT
        
        # High body weight (may need increase for some drugs)
        elif weight > 120:
            # Check if drug is weight-based
            weight_based = drug_info.get('weight_based_dosing', False)
            if weight_based:
                return 1.2, DosingAdjustmentReason.WEIGHT
        
        return 1.0, None
    
    async def _calculate_renal_adjustment(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> Tuple[float, Optional[DosingAdjustmentReason]]:
        """Calculate renal function-based dosing adjustment"""
        has_kidney_disease = any(
            'kidney' in condition.lower() or 'renal' in condition.lower()
            for condition in patient_context.conditions
        )
        
        if not has_kidney_disease:
            return 1.0, None
        
        try:
            # Check if drug is renally cleared
            g = self.db.connection.g
            renal_relationships = g.V().has('id', drug_id).outE('RENAL_CLEARANCE').valueMap(True).toList()
            
            for rel in renal_relationships:
                clearance_pct = rel.get('renal_clearance_percentage', 0)
                
                if clearance_pct > 70:
                    return 0.5, DosingAdjustmentReason.RENAL_IMPAIRMENT
                elif clearance_pct > 50:
                    return 0.7, DosingAdjustmentReason.RENAL_IMPAIRMENT
                elif clearance_pct > 30:
                    return 0.85, DosingAdjustmentReason.RENAL_IMPAIRMENT
        
        except Exception as e:
            self.logger.error(f"Error calculating renal adjustment: {e}")
        
        return 1.0, None
    
    async def _calculate_hepatic_adjustment(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> Tuple[float, Optional[DosingAdjustmentReason]]:
        """Calculate hepatic function-based dosing adjustment"""
        has_liver_disease = any(
            'liver' in condition.lower() or 'hepatic' in condition.lower()
            for condition in patient_context.conditions
        )
        
        if not has_liver_disease:
            return 1.0, None
        
        try:
            # Check if drug is hepatically metabolized
            g = self.db.connection.g
            hepatic_relationships = g.V().has('id', drug_id).outE('HEPATIC_METABOLISM').valueMap(True).toList()
            
            for rel in hepatic_relationships:
                metabolism_pct = rel.get('hepatic_metabolism_percentage', 0)
                
                if metabolism_pct > 70:
                    return 0.5, DosingAdjustmentReason.HEPATIC_IMPAIRMENT
                elif metabolism_pct > 50:
                    return 0.7, DosingAdjustmentReason.HEPATIC_IMPAIRMENT
                elif metabolism_pct > 30:
                    return 0.85, DosingAdjustmentReason.HEPATIC_IMPAIRMENT
        
        except Exception as e:
            self.logger.error(f"Error calculating hepatic adjustment: {e}")
        
        return 1.0, None
    
    async def _calculate_interaction_adjustment(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> Tuple[float, Optional[DosingAdjustmentReason]]:
        """Calculate drug interaction-based dosing adjustment"""
        if not patient_context.medications:
            return 1.0, None
        
        try:
            # Check for interactions with current medications
            medication_ids = [
                med.get('id', '') for med in patient_context.medications
                if med.get('id')
            ]
            
            if not medication_ids:
                return 1.0, None
            
            # Query for interactions
            g = self.db.connection.g
            
            for med_id in medication_ids:
                interactions = g.V().has('id', drug_id).outE('INTERACTS_WITH').where(
                    g.inV().has('id', med_id)
                ).valueMap(True).toList()
                
                for interaction in interactions:
                    severity = interaction.get('severity', '')
                    mechanism = interaction.get('mechanism', '')
                    
                    # Check if interaction affects drug levels
                    if 'increase' in mechanism.lower() or 'inhibit' in mechanism.lower():
                        if severity == 'major':
                            return 0.6, DosingAdjustmentReason.DRUG_INTERACTION
                        elif severity == 'moderate':
                            return 0.8, DosingAdjustmentReason.DRUG_INTERACTION
                    elif 'decrease' in mechanism.lower() or 'induce' in mechanism.lower():
                        if severity == 'major':
                            return 1.4, DosingAdjustmentReason.DRUG_INTERACTION
                        elif severity == 'moderate':
                            return 1.2, DosingAdjustmentReason.DRUG_INTERACTION
        
        except Exception as e:
            self.logger.error(f"Error calculating interaction adjustment: {e}")
        
        return 1.0, None
    
    async def _calculate_genetic_adjustment(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> Tuple[float, Optional[DosingAdjustmentReason]]:
        """Calculate genetic factor-based dosing adjustment"""
        if not patient_context.genetic_factors:
            return 1.0, None
        
        try:
            # Query for pharmacogenomic relationships
            g = self.db.connection.g
            genetic_relationships = g.V().has('id', drug_id).outE('PHARMACOGENOMIC').valueMap(True).toList()
            
            for rel in genetic_relationships:
                gene = rel.get('gene', '')
                variant = rel.get('variant', '')
                dosing_impact = rel.get('dosing_impact', 1.0)
                
                # Check if patient has this genetic variant
                patient_variant = patient_context.genetic_factors.get(gene, '')
                
                if patient_variant == variant and dosing_impact != 1.0:
                    return dosing_impact, DosingAdjustmentReason.GENETIC_FACTOR
        
        except Exception as e:
            self.logger.error(f"Error calculating genetic adjustment: {e}")
        
        return 1.0, None
    
    def _generate_adjusted_dose_description(
        self,
        standard_dose: str,
        adjustment_factor: float
    ) -> str:
        """Generate adjusted dose description"""
        if adjustment_factor < 1.0:
            percentage = int((1.0 - adjustment_factor) * 100)
            return f"{standard_dose} reduced by {percentage}%"
        elif adjustment_factor > 1.0:
            percentage = int((adjustment_factor - 1.0) * 100)
            return f"{standard_dose} increased by {percentage}%"
        else:
            return standard_dose
    
    def _age_in_range(self, age: int, age_range: str) -> bool:
        """Check if age falls in range"""
        if not age_range or not age:
            return False
        
        try:
            if '-' in age_range:
                min_age, max_age = map(int, age_range.split('-'))
                return min_age <= age <= max_age
            else:
                return age == int(age_range)
        except (ValueError, TypeError):
            return False
    
    def _weight_in_range(self, weight: float, weight_range: str) -> bool:
        """Check if weight falls in range"""
        if not weight_range or not weight:
            return False
        
        try:
            if '-' in weight_range:
                min_weight, max_weight = map(float, weight_range.split('-'))
                return min_weight <= weight <= max_weight
            else:
                return weight == float(weight_range)
        except (ValueError, TypeError):
            return False


# Global personalization engine instance
personalization_engine = None


def initialize_personalization_engine(
    database_connection,
    reasoning_engine_instance
):
    """Initialize global personalization engine instance"""
    global personalization_engine
    personalization_engine = PersonalizationEngine(
        database_connection,
        reasoning_engine_instance
    )
    return personalization_engine
