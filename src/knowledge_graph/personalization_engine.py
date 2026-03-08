"""
Personalization engine for PharmaGuide
Implements risk-based ranking, physiological factor analysis, and dosing adjustments
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.knowledge_graph.database import KnowledgeGraphDatabase
from src.knowledge_graph.models import PatientContext, SeverityLevel

logger = logging.getLogger(__name__)


class RiskCategory(str, Enum):
    """Risk categories for personalized assessments"""
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class DosingAdjustmentType(str, Enum):
    """Types of dosing adjustments"""
    REDUCE_DOSE = "reduce_dose"
    INCREASE_DOSE = "increase_dose"
    ADJUST_FREQUENCY = "adjust_frequency"
    MONITOR_LEVELS = "monitor_levels"
    NO_ADJUSTMENT = "no_adjustment"


@dataclass
class PersonalizedRiskScore:
    """Personalized risk score for a medication"""
    drug_id: str
    drug_name: str
    base_risk: float
    age_adjusted_risk: float
    comorbidity_adjusted_risk: float
    polypharmacy_adjusted_risk: float
    genetic_adjusted_risk: float
    final_risk_score: float
    risk_category: RiskCategory
    risk_factors: List[str]
    evidence_sources: List[str]
    confidence: float


@dataclass
class PhysiologicalFactors:
    """Physiological factors affecting drug response"""
    age_factor: float
    weight_factor: float
    renal_function_factor: float
    hepatic_function_factor: float
    metabolizer_status: Optional[str]
    absorption_rate: float
    distribution_volume: float
    elimination_rate: float


@dataclass
class DosingRecommendation:
    """Dosing adjustment recommendation"""
    drug_id: str
    drug_name: str
    standard_dose: str
    recommended_dose: str
    adjustment_type: DosingAdjustmentType
    adjustment_percentage: float
    rationale: str
    physiological_basis: List[str]
    monitoring_requirements: List[str]
    confidence: float


@dataclass
class RankedMedication:
    """Medication ranked by personalized risk"""
    drug_id: str
    drug_name: str
    rank: int
    risk_score: PersonalizedRiskScore
    dosing_recommendation: Optional[DosingRecommendation]
    side_effects: List[Dict[str, Any]]
    interactions: List[Dict[str, Any]]
    overall_suitability: float


class PersonalizationEngine:
    """
    Personalization engine for medication recommendations
    Implements risk-based ranking, physiological analysis, and dosing adjustments
    """
    
    def __init__(self, database: KnowledgeGraphDatabase):
        self.database = database
        self.logger = logging.getLogger(__name__)
        
        # Real-world evidence weights from FAERS data
        self.faers_weight = 0.4
        self.clinical_trial_weight = 0.6
        
        # Age-based risk multipliers
        self.age_risk_multipliers = {
            'pediatric': 1.3,  # < 18
            'adult': 1.0,      # 18-64
            'elderly': 1.5     # >= 65
        }

    async def rank_medications_by_risk(
        self,
        drug_ids: List[str],
        patient_context: PatientContext,
        indication: Optional[str] = None
    ) -> List[RankedMedication]:
        """
        Rank medications based on personalized risk using real-world evidence
        
        Args:
            drug_ids: List of drug identifiers to rank
            patient_context: Patient context for personalization
            indication: Optional indication for filtering
        
        Returns:
            List of ranked medications with risk scores
        """
        try:
            self.logger.info(f"Ranking {len(drug_ids)} medications for patient {patient_context.id}")
            
            ranked_medications = []
            
            for drug_id in drug_ids:
                # Calculate personalized risk score
                risk_score = await self.calculate_personalized_risk(
                    drug_id, patient_context
                )
                
                # Get dosing recommendation
                dosing_rec = await self.generate_dosing_recommendation(
                    drug_id, patient_context
                )
                
                # Get side effects and interactions
                side_effects = await self._get_personalized_side_effects(
                    drug_id, patient_context
                )
                interactions = await self._get_drug_interactions(
                    drug_id, patient_context
                )
                
                # Calculate overall suitability
                suitability = self._calculate_suitability(
                    risk_score, dosing_rec, side_effects, interactions
                )
                
                ranked_medications.append(RankedMedication(
                    drug_id=drug_id,
                    drug_name=risk_score.drug_name,
                    rank=0,  # Will be set after sorting
                    risk_score=risk_score,
                    dosing_recommendation=dosing_rec,
                    side_effects=side_effects,
                    interactions=interactions,
                    overall_suitability=suitability
                ))
            
            # Sort by suitability (higher is better)
            ranked_medications.sort(key=lambda x: x.overall_suitability, reverse=True)
            
            # Assign ranks
            for i, med in enumerate(ranked_medications):
                med.rank = i + 1
            
            self.logger.info(f"Ranked {len(ranked_medications)} medications")
            return ranked_medications
        
        except Exception as e:
            self.logger.error(f"Error ranking medications: {e}")
            raise

    async def calculate_personalized_risk(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> PersonalizedRiskScore:
        """
        Calculate personalized risk score using real-world evidence from FAERS
        
        Args:
            drug_id: Drug identifier
            patient_context: Patient context
        
        Returns:
            Personalized risk score
        """
        try:
            self.logger.info(f"Calculating personalized risk for drug {drug_id}")
            
            # Get drug information
            drug_info = await self.database.find_drug_by_name(drug_id)
            if not drug_info:
                raise ValueError(f"Drug not found: {drug_id}")
            
            drug_name = drug_info.get('name', drug_id)
            
            # Calculate base risk from FAERS and clinical data
            base_risk = await self._calculate_base_risk_from_faers(drug_id)
            
            # Apply age adjustment
            age_adjusted = self._apply_age_adjustment(base_risk, patient_context)
            
            # Apply comorbidity adjustment
            comorbidity_adjusted = await self._apply_comorbidity_adjustment(
                age_adjusted, drug_id, patient_context
            )
            
            # Apply polypharmacy adjustment
            polypharmacy_adjusted = self._apply_polypharmacy_adjustment(
                comorbidity_adjusted, patient_context
            )
            
            # Apply genetic factors adjustment
            genetic_adjusted = self._apply_genetic_adjustment(
                polypharmacy_adjusted, drug_id, patient_context
            )
            
            # Determine risk category
            risk_category = self._categorize_risk(genetic_adjusted)
            
            # Extract risk factors
            risk_factors = self._extract_risk_factors(
                patient_context, drug_id, genetic_adjusted
            )
            
            # Determine evidence sources
            evidence_sources = ['FAERS', 'OnSIDES', 'SIDER']
            
            # Calculate confidence
            confidence = self._calculate_risk_confidence(
                base_risk, patient_context
            )
            
            return PersonalizedRiskScore(
                drug_id=drug_id,
                drug_name=drug_name,
                base_risk=base_risk,
                age_adjusted_risk=age_adjusted,
                comorbidity_adjusted_risk=comorbidity_adjusted,
                polypharmacy_adjusted_risk=polypharmacy_adjusted,
                genetic_adjusted_risk=genetic_adjusted,
                final_risk_score=genetic_adjusted,
                risk_category=risk_category,
                risk_factors=risk_factors,
                evidence_sources=evidence_sources,
                confidence=confidence
            )
        
        except Exception as e:
            self.logger.error(f"Error calculating personalized risk: {e}")
            raise

    async def analyze_physiological_factors(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> PhysiologicalFactors:
        """
        Analyze physiological factors affecting drug response
        
        Args:
            drug_id: Drug identifier
            patient_context: Patient context
        
        Returns:
            Physiological factors analysis
        """
        try:
            self.logger.info(f"Analyzing physiological factors for drug {drug_id}")
            
            demographics = patient_context.demographics
            age = demographics.get('age', 40)
            weight = demographics.get('weight', 70)  # kg
            
            # Age factor (affects metabolism and clearance)
            age_factor = self._calculate_age_factor(age)
            
            # Weight factor (affects distribution volume)
            weight_factor = self._calculate_weight_factor(weight)
            
            # Renal function factor (from conditions or estimated)
            renal_factor = self._estimate_renal_function(patient_context)
            
            # Hepatic function factor (from conditions or estimated)
            hepatic_factor = self._estimate_hepatic_function(patient_context)
            
            # Metabolizer status from genetic factors
            metabolizer_status = self._determine_metabolizer_status(
                drug_id, patient_context
            )
            
            # Pharmacokinetic parameters
            absorption_rate = self._estimate_absorption_rate(
                age_factor, patient_context
            )
            distribution_volume = self._estimate_distribution_volume(
                weight_factor, age_factor
            )
            elimination_rate = self._estimate_elimination_rate(
                renal_factor, hepatic_factor, age_factor
            )
            
            return PhysiologicalFactors(
                age_factor=age_factor,
                weight_factor=weight_factor,
                renal_function_factor=renal_factor,
                hepatic_function_factor=hepatic_factor,
                metabolizer_status=metabolizer_status,
                absorption_rate=absorption_rate,
                distribution_volume=distribution_volume,
                elimination_rate=elimination_rate
            )
        
        except Exception as e:
            self.logger.error(f"Error analyzing physiological factors: {e}")
            raise

    async def generate_dosing_recommendation(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> DosingRecommendation:
        """
        Generate dosing adjustment recommendations based on physiological factors
        
        Args:
            drug_id: Drug identifier
            patient_context: Patient context
        
        Returns:
            Dosing recommendation
        """
        try:
            self.logger.info(f"Generating dosing recommendation for drug {drug_id}")
            
            # Get drug information
            drug_info = await self.database.find_drug_by_name(drug_id)
            if not drug_info:
                raise ValueError(f"Drug not found: {drug_id}")
            
            drug_name = drug_info.get('name', drug_id)
            
            # Analyze physiological factors
            phys_factors = await self.analyze_physiological_factors(
                drug_id, patient_context
            )
            
            # Get standard dosing
            standard_dose = self._get_standard_dose(drug_info)
            
            # Calculate adjustment based on physiological factors
            adjustment_percentage, adjustment_type = self._calculate_dose_adjustment(
                phys_factors, patient_context
            )
            
            # Calculate recommended dose
            recommended_dose = self._apply_dose_adjustment(
                standard_dose, adjustment_percentage, adjustment_type
            )
            
            # Generate rationale
            rationale = self._generate_dosing_rationale(
                phys_factors, adjustment_percentage, patient_context
            )
            
            # Identify physiological basis
            physiological_basis = self._identify_physiological_basis(
                phys_factors, adjustment_type
            )
            
            # Determine monitoring requirements
            monitoring_requirements = self._determine_monitoring_requirements(
                adjustment_type, phys_factors, patient_context
            )
            
            # Calculate confidence
            confidence = self._calculate_dosing_confidence(
                phys_factors, patient_context
            )
            
            return DosingRecommendation(
                drug_id=drug_id,
                drug_name=drug_name,
                standard_dose=standard_dose,
                recommended_dose=recommended_dose,
                adjustment_type=adjustment_type,
                adjustment_percentage=adjustment_percentage,
                rationale=rationale,
                physiological_basis=physiological_basis,
                monitoring_requirements=monitoring_requirements,
                confidence=confidence
            )
        
        except Exception as e:
            self.logger.error(f"Error generating dosing recommendation: {e}")
            raise

    # Helper methods for risk calculation
    
    async def _calculate_base_risk_from_faers(self, drug_id: str) -> float:
        """Calculate base risk from FAERS real-world evidence"""
        try:
            # Query FAERS data from knowledge graph
            # In real implementation, this would query adverse event reports
            
            # For now, return a baseline risk
            # This would be calculated from:
            # - Number of adverse event reports
            # - Severity of reported events
            # - Reporting rate compared to prescription volume
            
            base_risk = 0.3  # Placeholder
            self.logger.debug(f"Base risk from FAERS: {base_risk}")
            return base_risk
        
        except Exception as e:
            self.logger.error(f"Error calculating base risk from FAERS: {e}")
            return 0.5  # Default moderate risk
    
    def _apply_age_adjustment(
        self,
        base_risk: float,
        patient_context: PatientContext
    ) -> float:
        """Apply age-based risk adjustment"""
        age = patient_context.demographics.get('age', 40)
        
        if age < 18:
            multiplier = self.age_risk_multipliers['pediatric']
        elif age >= 65:
            multiplier = self.age_risk_multipliers['elderly']
        else:
            multiplier = self.age_risk_multipliers['adult']
        
        adjusted_risk = min(base_risk * multiplier, 1.0)
        self.logger.debug(f"Age-adjusted risk: {adjusted_risk} (multiplier: {multiplier})")
        return adjusted_risk
    
    async def _apply_comorbidity_adjustment(
        self,
        current_risk: float,
        drug_id: str,
        patient_context: PatientContext
    ) -> float:
        """Apply comorbidity-based risk adjustment"""
        if not patient_context.conditions:
            return current_risk
        
        # High-risk conditions that increase adverse event risk
        high_risk_conditions = [
            'kidney_disease', 'renal_failure', 'liver_disease', 'cirrhosis',
            'heart_failure', 'diabetes', 'hypertension'
        ]
        
        # Count matching conditions
        risk_condition_count = sum(
            1 for condition in patient_context.conditions
            if any(hrc in condition.lower() for hrc in high_risk_conditions)
        )
        
        # Each high-risk condition adds 10% to risk
        adjustment = min(risk_condition_count * 0.1, 0.4)
        adjusted_risk = min(current_risk + adjustment, 1.0)
        
        self.logger.debug(
            f"Comorbidity-adjusted risk: {adjusted_risk} "
            f"({risk_condition_count} high-risk conditions)"
        )
        return adjusted_risk

    def _apply_polypharmacy_adjustment(
        self,
        current_risk: float,
        patient_context: PatientContext
    ) -> float:
        """Apply polypharmacy-based risk adjustment"""
        med_count = len(patient_context.medications)
        
        if med_count <= 3:
            return current_risk
        
        # Polypharmacy risk increases with medication count
        # Each medication beyond 3 adds 5% risk
        adjustment = min((med_count - 3) * 0.05, 0.3)
        adjusted_risk = min(current_risk + adjustment, 1.0)
        
        self.logger.debug(
            f"Polypharmacy-adjusted risk: {adjusted_risk} "
            f"({med_count} medications)"
        )
        return adjusted_risk
    
    def _apply_genetic_adjustment(
        self,
        current_risk: float,
        drug_id: str,
        patient_context: PatientContext
    ) -> float:
        """Apply genetic factor-based risk adjustment"""
        if not patient_context.genetic_factors:
            return current_risk
        
        # Check for poor metabolizer status
        # Poor metabolizers have higher risk of adverse events
        genetic_risk_increase = 0.0
        
        for gene, variant in patient_context.genetic_factors.items():
            if 'poor' in str(variant).lower():
                genetic_risk_increase += 0.15
            elif 'intermediate' in str(variant).lower():
                genetic_risk_increase += 0.08
        
        adjusted_risk = min(current_risk + genetic_risk_increase, 1.0)
        
        self.logger.debug(
            f"Genetic-adjusted risk: {adjusted_risk} "
            f"(genetic factors: {len(patient_context.genetic_factors)})"
        )
        return adjusted_risk
    
    def _categorize_risk(self, risk_score: float) -> RiskCategory:
        """Categorize risk score into risk category"""
        if risk_score < 0.2:
            return RiskCategory.VERY_LOW
        elif risk_score < 0.4:
            return RiskCategory.LOW
        elif risk_score < 0.6:
            return RiskCategory.MODERATE
        elif risk_score < 0.8:
            return RiskCategory.HIGH
        else:
            return RiskCategory.VERY_HIGH
    
    def _extract_risk_factors(
        self,
        patient_context: PatientContext,
        drug_id: str,
        final_risk: float
    ) -> List[str]:
        """Extract specific risk factors contributing to risk score"""
        risk_factors = []
        
        age = patient_context.demographics.get('age', 40)
        if age < 18:
            risk_factors.append("Pediatric patient (increased sensitivity)")
        elif age >= 65:
            risk_factors.append("Elderly patient (reduced clearance)")
        
        if len(patient_context.medications) > 5:
            risk_factors.append(f"Polypharmacy ({len(patient_context.medications)} medications)")
        
        if patient_context.conditions:
            risk_factors.append(f"Comorbidities ({len(patient_context.conditions)} conditions)")
        
        if patient_context.genetic_factors:
            risk_factors.append("Pharmacogenomic factors present")
        
        return risk_factors

    def _calculate_risk_confidence(
        self,
        base_risk: float,
        patient_context: PatientContext
    ) -> float:
        """Calculate confidence in risk assessment"""
        confidence = 0.7  # Base confidence
        
        # Increase confidence if we have genetic data
        if patient_context.genetic_factors:
            confidence += 0.1
        
        # Increase confidence if we have detailed demographics
        if all(k in patient_context.demographics for k in ['age', 'weight', 'gender']):
            confidence += 0.1
        
        # Decrease confidence if patient has many unknown factors
        if not patient_context.conditions:
            confidence -= 0.1
        
        return min(max(confidence, 0.0), 1.0)
    
    # Helper methods for physiological analysis
    
    def _calculate_age_factor(self, age: int) -> float:
        """Calculate age factor for drug metabolism"""
        if age < 18:
            # Pediatric: developing metabolism
            return 0.7 + (age / 18) * 0.3
        elif age < 65:
            # Adult: normal metabolism
            return 1.0
        else:
            # Elderly: declining metabolism
            decline_rate = (age - 65) * 0.01
            return max(1.0 - decline_rate, 0.5)
    
    def _calculate_weight_factor(self, weight: float) -> float:
        """Calculate weight factor for drug distribution"""
        # Normalized to 70kg reference
        reference_weight = 70.0
        return weight / reference_weight
    
    def _estimate_renal_function(self, patient_context: PatientContext) -> float:
        """Estimate renal function factor"""
        # Check for kidney disease
        has_kidney_disease = any(
            'kidney' in condition.lower() or 'renal' in condition.lower()
            for condition in patient_context.conditions
        )
        
        if has_kidney_disease:
            return 0.5  # Reduced renal function
        
        # Age-based estimation (Cockcroft-Gault approximation)
        age = patient_context.demographics.get('age', 40)
        if age >= 65:
            return max(1.0 - (age - 65) * 0.015, 0.4)
        
        return 1.0  # Normal renal function
    
    def _estimate_hepatic_function(self, patient_context: PatientContext) -> float:
        """Estimate hepatic function factor"""
        # Check for liver disease
        has_liver_disease = any(
            'liver' in condition.lower() or 'hepatic' in condition.lower() or 'cirrhosis' in condition.lower()
            for condition in patient_context.conditions
        )
        
        if has_liver_disease:
            return 0.4  # Significantly reduced hepatic function
        
        return 1.0  # Normal hepatic function

    def _determine_metabolizer_status(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> Optional[str]:
        """Determine metabolizer status from genetic factors"""
        if not patient_context.genetic_factors:
            return None
        
        # Check common CYP450 genes
        cyp_genes = ['CYP2D6', 'CYP2C19', 'CYP2C9', 'CYP3A4']
        
        for gene in cyp_genes:
            if gene in patient_context.genetic_factors:
                variant = patient_context.genetic_factors[gene]
                if 'poor' in str(variant).lower():
                    return 'poor_metabolizer'
                elif 'intermediate' in str(variant).lower():
                    return 'intermediate_metabolizer'
                elif 'rapid' in str(variant).lower() or 'ultra' in str(variant).lower():
                    return 'rapid_metabolizer'
        
        return 'normal_metabolizer'
    
    def _estimate_absorption_rate(
        self,
        age_factor: float,
        patient_context: PatientContext
    ) -> float:
        """Estimate drug absorption rate"""
        # Base absorption rate
        absorption = 1.0
        
        # Age affects absorption
        absorption *= age_factor
        
        # GI conditions affect absorption
        has_gi_condition = any(
            'gastro' in condition.lower() or 'intestinal' in condition.lower()
            for condition in patient_context.conditions
        )
        
        if has_gi_condition:
            absorption *= 0.8
        
        return max(absorption, 0.3)
    
    def _estimate_distribution_volume(
        self,
        weight_factor: float,
        age_factor: float
    ) -> float:
        """Estimate volume of distribution"""
        # Distribution volume affected by weight and age
        # Elderly have reduced lean body mass
        return weight_factor * age_factor
    
    def _estimate_elimination_rate(
        self,
        renal_factor: float,
        hepatic_factor: float,
        age_factor: float
    ) -> float:
        """Estimate drug elimination rate"""
        # Elimination depends on renal and hepatic function
        # Use the lower of the two as limiting factor
        limiting_factor = min(renal_factor, hepatic_factor)
        
        # Age also affects elimination
        return limiting_factor * age_factor

    # Helper methods for dosing recommendations
    
    def _get_standard_dose(self, drug_info: Dict[str, Any]) -> str:
        """Get standard dosing from drug information"""
        # In real implementation, would extract from drug_info
        return "Standard adult dose"
    
    def _calculate_dose_adjustment(
        self,
        phys_factors: PhysiologicalFactors,
        patient_context: PatientContext
    ) -> Tuple[float, DosingAdjustmentType]:
        """Calculate dose adjustment based on physiological factors"""
        adjustment_percentage = 0.0
        adjustment_type = DosingAdjustmentType.NO_ADJUSTMENT
        
        # Renal impairment requires dose reduction
        if phys_factors.renal_function_factor < 0.7:
            reduction = (1.0 - phys_factors.renal_function_factor) * 50
            adjustment_percentage = -reduction
            adjustment_type = DosingAdjustmentType.REDUCE_DOSE
        
        # Hepatic impairment requires dose reduction
        elif phys_factors.hepatic_function_factor < 0.7:
            reduction = (1.0 - phys_factors.hepatic_function_factor) * 40
            adjustment_percentage = -reduction
            adjustment_type = DosingAdjustmentType.REDUCE_DOSE
        
        # Poor metabolizers need dose reduction
        elif phys_factors.metabolizer_status == 'poor_metabolizer':
            adjustment_percentage = -30.0
            adjustment_type = DosingAdjustmentType.REDUCE_DOSE
        
        # Rapid metabolizers may need dose increase
        elif phys_factors.metabolizer_status == 'rapid_metabolizer':
            adjustment_percentage = 20.0
            adjustment_type = DosingAdjustmentType.INCREASE_DOSE
        
        # Elderly with reduced elimination
        elif phys_factors.age_factor < 0.8 and phys_factors.elimination_rate < 0.8:
            adjustment_percentage = -25.0
            adjustment_type = DosingAdjustmentType.REDUCE_DOSE
        
        # Weight-based adjustments for extreme weights
        elif phys_factors.weight_factor < 0.7:
            adjustment_percentage = -20.0
            adjustment_type = DosingAdjustmentType.REDUCE_DOSE
        elif phys_factors.weight_factor > 1.5:
            adjustment_percentage = 30.0
            adjustment_type = DosingAdjustmentType.INCREASE_DOSE
        
        # If significant factors present, recommend monitoring
        if abs(adjustment_percentage) > 0:
            if adjustment_type == DosingAdjustmentType.NO_ADJUSTMENT:
                adjustment_type = DosingAdjustmentType.MONITOR_LEVELS
        
        return adjustment_percentage, adjustment_type
    
    def _apply_dose_adjustment(
        self,
        standard_dose: str,
        adjustment_percentage: float,
        adjustment_type: DosingAdjustmentType
    ) -> str:
        """Apply dose adjustment to standard dose"""
        if adjustment_type == DosingAdjustmentType.NO_ADJUSTMENT:
            return standard_dose
        
        if adjustment_percentage < 0:
            return f"{standard_dose} (reduce by {abs(adjustment_percentage):.0f}%)"
        elif adjustment_percentage > 0:
            return f"{standard_dose} (increase by {adjustment_percentage:.0f}%)"
        else:
            return f"{standard_dose} (monitor levels)"

    def _generate_dosing_rationale(
        self,
        phys_factors: PhysiologicalFactors,
        adjustment_percentage: float,
        patient_context: PatientContext
    ) -> str:
        """Generate rationale for dosing recommendation"""
        rationale_parts = []
        
        if phys_factors.renal_function_factor < 0.7:
            rationale_parts.append("reduced renal function")
        
        if phys_factors.hepatic_function_factor < 0.7:
            rationale_parts.append("impaired hepatic function")
        
        if phys_factors.metabolizer_status == 'poor_metabolizer':
            rationale_parts.append("poor metabolizer status")
        elif phys_factors.metabolizer_status == 'rapid_metabolizer':
            rationale_parts.append("rapid metabolizer status")
        
        if phys_factors.age_factor < 0.8:
            age = patient_context.demographics.get('age', 0)
            if age >= 65:
                rationale_parts.append("elderly patient with reduced clearance")
            else:
                rationale_parts.append("pediatric patient")
        
        if phys_factors.weight_factor < 0.7:
            rationale_parts.append("low body weight")
        elif phys_factors.weight_factor > 1.5:
            rationale_parts.append("high body weight")
        
        if not rationale_parts:
            return "Standard dosing appropriate based on patient factors"
        
        return f"Dose adjustment recommended due to: {', '.join(rationale_parts)}"
    
    def _identify_physiological_basis(
        self,
        phys_factors: PhysiologicalFactors,
        adjustment_type: DosingAdjustmentType
    ) -> List[str]:
        """Identify physiological basis for dosing adjustment"""
        basis = []
        
        if phys_factors.renal_function_factor < 0.7:
            basis.append("Reduced renal clearance affects drug elimination")
        
        if phys_factors.hepatic_function_factor < 0.7:
            basis.append("Impaired hepatic metabolism reduces drug clearance")
        
        if phys_factors.metabolizer_status in ['poor_metabolizer', 'rapid_metabolizer']:
            basis.append(f"Genetic variation affects drug metabolism rate")
        
        if phys_factors.age_factor < 0.8:
            basis.append("Age-related changes in pharmacokinetics")
        
        if phys_factors.elimination_rate < 0.7:
            basis.append("Reduced elimination rate increases drug exposure")
        
        if phys_factors.distribution_volume != 1.0:
            basis.append("Altered volume of distribution affects drug concentration")
        
        return basis if basis else ["Standard pharmacokinetic parameters"]

    def _determine_monitoring_requirements(
        self,
        adjustment_type: DosingAdjustmentType,
        phys_factors: PhysiologicalFactors,
        patient_context: PatientContext
    ) -> List[str]:
        """Determine monitoring requirements for dosing adjustment"""
        monitoring = []
        
        if adjustment_type == DosingAdjustmentType.REDUCE_DOSE:
            monitoring.append("Monitor for therapeutic effectiveness")
            monitoring.append("Assess for signs of under-treatment")
        
        if adjustment_type == DosingAdjustmentType.INCREASE_DOSE:
            monitoring.append("Monitor for adverse effects")
            monitoring.append("Watch for signs of toxicity")
        
        if phys_factors.renal_function_factor < 0.7:
            monitoring.append("Monitor renal function (serum creatinine, eGFR)")
            monitoring.append("Consider therapeutic drug monitoring if available")
        
        if phys_factors.hepatic_function_factor < 0.7:
            monitoring.append("Monitor liver function tests (ALT, AST, bilirubin)")
        
        if phys_factors.metabolizer_status in ['poor_metabolizer', 'rapid_metabolizer']:
            monitoring.append("Consider therapeutic drug level monitoring")
        
        if len(patient_context.medications) > 5:
            monitoring.append("Monitor for drug interactions")
        
        if not monitoring:
            monitoring.append("Standard monitoring per prescribing information")
        
        return monitoring
    
    def _calculate_dosing_confidence(
        self,
        phys_factors: PhysiologicalFactors,
        patient_context: PatientContext
    ) -> float:
        """Calculate confidence in dosing recommendation"""
        confidence = 0.7  # Base confidence
        
        # Higher confidence with genetic data
        if phys_factors.metabolizer_status:
            confidence += 0.15
        
        # Higher confidence with complete demographics
        if all(k in patient_context.demographics for k in ['age', 'weight', 'gender']):
            confidence += 0.1
        
        # Lower confidence with multiple comorbidities (more complex)
        if len(patient_context.conditions) > 3:
            confidence -= 0.1
        
        return min(max(confidence, 0.0), 1.0)
    
    # Helper methods for ranking
    
    async def _get_personalized_side_effects(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> List[Dict[str, Any]]:
        """Get personalized side effects for a drug"""
        # In real implementation, would query knowledge graph
        # and filter/rank by patient factors
        return []
    
    async def _get_drug_interactions(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> List[Dict[str, Any]]:
        """Get drug interactions for current medications"""
        # In real implementation, would query knowledge graph
        # for interactions with patient's current medications
        return []
    
    def _calculate_suitability(
        self,
        risk_score: PersonalizedRiskScore,
        dosing_rec: DosingRecommendation,
        side_effects: List[Dict[str, Any]],
        interactions: List[Dict[str, Any]]
    ) -> float:
        """Calculate overall suitability score"""
        # Start with inverse of risk (lower risk = higher suitability)
        suitability = 1.0 - risk_score.final_risk_score
        
        # Adjust for dosing complexity
        if dosing_rec.adjustment_type != DosingAdjustmentType.NO_ADJUSTMENT:
            suitability *= 0.9
        
        # Adjust for interactions
        if interactions:
            suitability *= (1.0 - len(interactions) * 0.1)
        
        # Weight by confidence
        suitability *= risk_score.confidence
        
        return max(min(suitability, 1.0), 0.0)


# Factory function
async def create_personalization_engine(
    database: KnowledgeGraphDatabase
) -> PersonalizationEngine:
    """Create personalization engine"""
    return PersonalizationEngine(database)
