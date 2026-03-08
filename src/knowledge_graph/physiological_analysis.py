"""
Physiological factor analysis service for PharmaGuide
Maps patient characteristics to drug responses through pharmacogenomic and pharmacokinetic analysis
"""
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from src.knowledge_graph.database import KnowledgeGraphDatabase
from src.knowledge_graph.models import PatientContext

logger = logging.getLogger(__name__)


class MetabolizerType(str, Enum):
    """CYP450 metabolizer phenotype"""
    POOR = "poor"
    INTERMEDIATE = "intermediate"
    NORMAL = "normal"
    RAPID = "rapid"
    ULTRA_RAPID = "ultra_rapid"


class ADMEPhase(str, Enum):
    """ADME (Absorption, Distribution, Metabolism, Excretion) phases"""
    ABSORPTION = "absorption"
    DISTRIBUTION = "distribution"
    METABOLISM = "metabolism"
    EXCRETION = "excretion"


@dataclass
class PharmacogenomicFactor:
    """Pharmacogenomic factor affecting drug response"""
    gene: str
    variant: str
    metabolizer_type: MetabolizerType
    affected_drugs: List[str]
    clinical_significance: str
    dosing_recommendation: Optional[str]
    confidence: float


@dataclass
class ADMEPattern:
    """ADME pattern explanation for drug"""
    phase: ADMEPhase
    description: str
    affected_by: List[str]  # Patient factors affecting this phase
    impact_on_efficacy: str
    impact_on_safety: str
    recommendations: List[str]


@dataclass
class PhysiologicalResponse:
    """Patient-specific physiological response to drug"""
    drug_id: str
    patient_id: str
    pharmacogenomic_factors: List[PharmacogenomicFactor]
    adme_patterns: List[ADMEPattern]
    predicted_efficacy: float  # 0.0 to 1.0
    predicted_safety: float  # 0.0 to 1.0
    dosing_adjustments: List[str]
    monitoring_recommendations: List[str]
    confidence: float


class PhysiologicalAnalysisService:
    """
    Service for analyzing physiological factors affecting drug response
    Integrates pharmacogenomic and pharmacokinetic data
    """
    
    def __init__(self, database: KnowledgeGraphDatabase):
        self.database = database
        self.logger = logging.getLogger(__name__)
        
        # CYP450 enzyme to drug mappings (simplified)
        self.cyp450_substrates = {
            'CYP2D6': ['codeine', 'tramadol', 'metoprolol', 'fluoxetine'],
            'CYP2C19': ['clopidogrel', 'omeprazole', 'escitalopram'],
            'CYP2C9': ['warfarin', 'phenytoin', 'losartan'],
            'CYP3A4': ['atorvastatin', 'simvastatin', 'amlodipine', 'midazolam']
        }
    
    async def analyze_physiological_response(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> PhysiologicalResponse:
        """
        Analyze patient-specific physiological response to drug
        
        Args:
            drug_id: Drug identifier
            patient_context: Patient context with demographics and genetic factors
        
        Returns:
            Physiological response analysis
        """
        try:
            self.logger.info(f"Analyzing physiological response for drug {drug_id}")
            
            # Analyze pharmacogenomic factors
            pg_factors = await self._analyze_pharmacogenomic_factors(
                drug_id, patient_context
            )
            
            # Analyze ADME patterns
            adme_patterns = await self._analyze_adme_patterns(
                drug_id, patient_context
            )
            
            # Predict efficacy and safety
            efficacy = self._predict_efficacy(pg_factors, adme_patterns, patient_context)
            safety = self._predict_safety(pg_factors, adme_patterns, patient_context)
            
            # Generate dosing adjustments
            dosing_adjustments = self._generate_dosing_adjustments(
                pg_factors, adme_patterns, patient_context
            )
            
            # Generate monitoring recommendations
            monitoring = self._generate_monitoring_recommendations(
                pg_factors, adme_patterns, patient_context
            )
            
            # Calculate overall confidence
            confidence = self._calculate_confidence(pg_factors, adme_patterns)
            
            return PhysiologicalResponse(
                drug_id=drug_id,
                patient_id=patient_context.id,
                pharmacogenomic_factors=pg_factors,
                adme_patterns=adme_patterns,
                predicted_efficacy=efficacy,
                predicted_safety=safety,
                dosing_adjustments=dosing_adjustments,
                monitoring_recommendations=monitoring,
                confidence=confidence
            )
        
        except Exception as e:
            self.logger.error(f"Error analyzing physiological response: {e}")
            raise
    
    async def _analyze_pharmacogenomic_factors(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> List[PharmacogenomicFactor]:
        """Analyze pharmacogenomic factors from patient genetic data"""
        factors = []
        
        try:
            genetic_factors = patient_context.genetic_factors
            
            # Check CYP450 enzyme variants
            for gene, substrates in self.cyp450_substrates.items():
                if gene in genetic_factors:
                    variant = genetic_factors[gene]
                    metabolizer_type = self._determine_metabolizer_type(gene, variant)
                    
                    # Check if drug is affected by this enzyme
                    drug_name = drug_id.replace('drug_', '')
                    if drug_name in substrates:
                        factor = PharmacogenomicFactor(
                            gene=gene,
                            variant=variant,
                            metabolizer_type=metabolizer_type,
                            affected_drugs=[drug_id],
                            clinical_significance=self._get_clinical_significance(
                                gene, metabolizer_type, drug_name
                            ),
                            dosing_recommendation=self._get_dosing_recommendation(
                                gene, metabolizer_type, drug_name
                            ),
                            confidence=0.85
                        )
                        factors.append(factor)
            
            # Query knowledge graph for additional pharmacogenomic relationships
            kg_factors = await self._query_pharmacogenomic_relationships(
                drug_id, patient_context
            )
            factors.extend(kg_factors)
            
            return factors
        
        except Exception as e:
            self.logger.error(f"Error analyzing pharmacogenomic factors: {e}")
            return []
    
    def _determine_metabolizer_type(self, gene: str, variant: str) -> MetabolizerType:
        """Determine metabolizer phenotype from genotype"""
        # Simplified mapping - in reality would use star allele nomenclature
        variant_lower = variant.lower()
        
        if 'poor' in variant_lower or '*4/*4' in variant or '*5/*5' in variant:
            return MetabolizerType.POOR
        elif 'intermediate' in variant_lower or '*1/*4' in variant:
            return MetabolizerType.INTERMEDIATE
        elif 'rapid' in variant_lower or '*1/*2' in variant:
            return MetabolizerType.RAPID
        elif 'ultra' in variant_lower or '*2/*2' in variant:
            return MetabolizerType.ULTRA_RAPID
        else:
            return MetabolizerType.NORMAL
    
    def _get_clinical_significance(
        self,
        gene: str,
        metabolizer_type: MetabolizerType,
        drug_name: str
    ) -> str:
        """Get clinical significance of pharmacogenomic factor"""
        if metabolizer_type == MetabolizerType.POOR:
            if gene == 'CYP2D6' and drug_name in ['codeine', 'tramadol']:
                return "Reduced analgesic efficacy - consider alternative"
            elif gene == 'CYP2C19' and drug_name == 'clopidogrel':
                return "Reduced antiplatelet effect - consider alternative"
            else:
                return "Increased drug exposure - risk of adverse effects"
        
        elif metabolizer_type == MetabolizerType.ULTRA_RAPID:
            if gene == 'CYP2D6' and drug_name in ['codeine', 'tramadol']:
                return "Increased risk of toxicity - avoid use"
            else:
                return "Reduced drug exposure - may need higher dose"
        
        elif metabolizer_type == MetabolizerType.INTERMEDIATE:
            return "Moderately altered drug metabolism - monitor closely"
        
        return "Normal drug metabolism expected"
    
    def _get_dosing_recommendation(
        self,
        gene: str,
        metabolizer_type: MetabolizerType,
        drug_name: str
    ) -> Optional[str]:
        """Get dosing recommendation based on pharmacogenomics"""
        if metabolizer_type == MetabolizerType.POOR:
            if drug_name == 'warfarin':
                return "Start with 50% of standard dose, titrate carefully"
            else:
                return "Consider 25-50% dose reduction"
        
        elif metabolizer_type == MetabolizerType.ULTRA_RAPID:
            if drug_name in ['codeine', 'tramadol']:
                return "Avoid use - select alternative analgesic"
            else:
                return "May require 50-100% dose increase"
        
        elif metabolizer_type == MetabolizerType.INTERMEDIATE:
            return "Monitor response, adjust dose as needed"
        
        return None
    
    async def _query_pharmacogenomic_relationships(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> List[PharmacogenomicFactor]:
        """Query knowledge graph for pharmacogenomic relationships"""
        try:
            # In real implementation, would query graph for drug-gene relationships
            self.logger.info("Querying pharmacogenomic relationships")
            return []
        
        except Exception as e:
            self.logger.error(f"Error querying pharmacogenomic relationships: {e}")
            return []
    
    async def _analyze_adme_patterns(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> List[ADMEPattern]:
        """Analyze ADME patterns for drug given patient characteristics"""
        patterns = []
        
        try:
            # Absorption analysis
            absorption = self._analyze_absorption(drug_id, patient_context)
            if absorption:
                patterns.append(absorption)
            
            # Distribution analysis
            distribution = self._analyze_distribution(drug_id, patient_context)
            if distribution:
                patterns.append(distribution)
            
            # Metabolism analysis
            metabolism = self._analyze_metabolism(drug_id, patient_context)
            if metabolism:
                patterns.append(metabolism)
            
            # Excretion analysis
            excretion = self._analyze_excretion(drug_id, patient_context)
            if excretion:
                patterns.append(excretion)
            
            return patterns
        
        except Exception as e:
            self.logger.error(f"Error analyzing ADME patterns: {e}")
            return []
    
    def _analyze_absorption(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> Optional[ADMEPattern]:
        """Analyze drug absorption factors"""
        affected_by = []
        recommendations = []
        
        # Age affects absorption
        age = patient_context.demographics.get('age', 0)
        if age > 65:
            affected_by.append('Advanced age - reduced gastric motility')
            recommendations.append('Monitor for delayed onset of action')
        
        # GI conditions affect absorption
        if 'inflammatory_bowel_disease' in patient_context.conditions:
            affected_by.append('Inflammatory bowel disease')
            recommendations.append('Consider parenteral administration if available')
        
        if not affected_by:
            return None
        
        return ADMEPattern(
            phase=ADMEPhase.ABSORPTION,
            description='Drug absorption may be altered by patient factors',
            affected_by=affected_by,
            impact_on_efficacy='Potentially reduced or delayed',
            impact_on_safety='Generally minimal',
            recommendations=recommendations
        )
    
    def _analyze_distribution(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> Optional[ADMEPattern]:
        """Analyze drug distribution factors"""
        affected_by = []
        recommendations = []
        
        # Body composition affects distribution
        weight = patient_context.demographics.get('weight', 70)
        if weight < 50:
            affected_by.append('Low body weight')
            recommendations.append('Consider weight-based dosing')
        elif weight > 100:
            affected_by.append('High body weight')
            recommendations.append('May require dose adjustment for lipophilic drugs')
        
        # Protein binding affected by conditions
        if 'liver_disease' in patient_context.conditions:
            affected_by.append('Liver disease - reduced protein synthesis')
            recommendations.append('Monitor for increased free drug concentration')
        
        if not affected_by:
            return None
        
        return ADMEPattern(
            phase=ADMEPhase.DISTRIBUTION,
            description='Drug distribution affected by patient characteristics',
            affected_by=affected_by,
            impact_on_efficacy='Variable',
            impact_on_safety='Increased risk with altered protein binding',
            recommendations=recommendations
        )
    
    def _analyze_metabolism(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> Optional[ADMEPattern]:
        """Analyze drug metabolism factors"""
        affected_by = []
        recommendations = []
        
        # Liver function affects metabolism
        if 'liver_disease' in patient_context.conditions:
            affected_by.append('Hepatic impairment')
            recommendations.append('Reduce dose by 25-50% for hepatically cleared drugs')
            recommendations.append('Monitor liver function tests')
        
        # Age affects metabolism
        age = patient_context.demographics.get('age', 0)
        if age > 65:
            affected_by.append('Advanced age - reduced hepatic metabolism')
            recommendations.append('Start with lower doses, titrate slowly')
        
        # Genetic factors
        if patient_context.genetic_factors:
            affected_by.append('Genetic variants affecting drug metabolism')
            recommendations.append('Consider pharmacogenomic-guided dosing')
        
        if not affected_by:
            return None
        
        return ADMEPattern(
            phase=ADMEPhase.METABOLISM,
            description='Drug metabolism influenced by patient factors',
            affected_by=affected_by,
            impact_on_efficacy='Potentially reduced with impaired metabolism',
            impact_on_safety='Increased risk of accumulation and toxicity',
            recommendations=recommendations
        )
    
    def _analyze_excretion(
        self,
        drug_id: str,
        patient_context: PatientContext
    ) -> Optional[ADMEPattern]:
        """Analyze drug excretion factors"""
        affected_by = []
        recommendations = []
        
        # Renal function affects excretion
        if 'kidney_disease' in patient_context.conditions:
            affected_by.append('Renal impairment')
            recommendations.append('Adjust dose based on creatinine clearance')
            recommendations.append('Monitor renal function regularly')
        
        # Age affects renal function
        age = patient_context.demographics.get('age', 0)
        if age > 65:
            affected_by.append('Age-related decline in renal function')
            recommendations.append('Calculate creatinine clearance, adjust dose accordingly')
        
        if not affected_by:
            return None
        
        return ADMEPattern(
            phase=ADMEPhase.EXCRETION,
            description='Drug excretion affected by patient factors',
            affected_by=affected_by,
            impact_on_efficacy='Potentially increased with impaired excretion',
            impact_on_safety='Significant risk of drug accumulation',
            recommendations=recommendations
        )
    
    def _predict_efficacy(
        self,
        pg_factors: List[PharmacogenomicFactor],
        adme_patterns: List[ADMEPattern],
        patient_context: PatientContext
    ) -> float:
        """Predict drug efficacy based on physiological factors"""
        base_efficacy = 0.7  # Baseline efficacy
        
        # Adjust for pharmacogenomic factors
        for factor in pg_factors:
            if factor.metabolizer_type == MetabolizerType.POOR:
                if 'Reduced' in factor.clinical_significance:
                    base_efficacy *= 0.6  # Reduced efficacy
                else:
                    base_efficacy *= 1.1  # Increased exposure may improve efficacy
            elif factor.metabolizer_type == MetabolizerType.ULTRA_RAPID:
                base_efficacy *= 0.7  # Reduced exposure
        
        # Adjust for ADME patterns
        for pattern in adme_patterns:
            if 'reduced' in pattern.impact_on_efficacy.lower():
                base_efficacy *= 0.9
        
        return min(max(base_efficacy, 0.0), 1.0)
    
    def _predict_safety(
        self,
        pg_factors: List[PharmacogenomicFactor],
        adme_patterns: List[ADMEPattern],
        patient_context: PatientContext
    ) -> float:
        """Predict drug safety based on physiological factors"""
        base_safety = 0.8  # Baseline safety
        
        # Adjust for pharmacogenomic factors
        for factor in pg_factors:
            if factor.metabolizer_type == MetabolizerType.POOR:
                base_safety *= 0.8  # Increased risk of adverse effects
            elif factor.metabolizer_type == MetabolizerType.ULTRA_RAPID:
                if 'toxicity' in factor.clinical_significance.lower():
                    base_safety *= 0.5  # High risk
        
        # Adjust for ADME patterns
        for pattern in adme_patterns:
            if 'increased risk' in pattern.impact_on_safety.lower():
                base_safety *= 0.85
            elif 'significant risk' in pattern.impact_on_safety.lower():
                base_safety *= 0.7
        
        # Adjust for age
        age = patient_context.demographics.get('age', 0)
        if age > 75:
            base_safety *= 0.9
        
        return min(max(base_safety, 0.0), 1.0)
    
    def _generate_dosing_adjustments(
        self,
        pg_factors: List[PharmacogenomicFactor],
        adme_patterns: List[ADMEPattern],
        patient_context: PatientContext
    ) -> List[str]:
        """Generate dosing adjustment recommendations"""
        adjustments = []
        
        # From pharmacogenomic factors
        for factor in pg_factors:
            if factor.dosing_recommendation:
                adjustments.append(factor.dosing_recommendation)
        
        # From ADME patterns
        for pattern in adme_patterns:
            for rec in pattern.recommendations:
                if 'dose' in rec.lower() or 'dosing' in rec.lower():
                    adjustments.append(rec)
        
        # Remove duplicates
        return list(set(adjustments))
    
    def _generate_monitoring_recommendations(
        self,
        pg_factors: List[PharmacogenomicFactor],
        adme_patterns: List[ADMEPattern],
        patient_context: PatientContext
    ) -> List[str]:
        """Generate monitoring recommendations"""
        monitoring = []
        
        # From pharmacogenomic factors
        for factor in pg_factors:
            if 'monitor' in factor.clinical_significance.lower():
                monitoring.append(f"Monitor for {factor.gene}-related effects")
        
        # From ADME patterns
        for pattern in adme_patterns:
            for rec in pattern.recommendations:
                if 'monitor' in rec.lower():
                    monitoring.append(rec)
        
        # General monitoring based on conditions
        if 'kidney_disease' in patient_context.conditions:
            monitoring.append('Monitor renal function (creatinine, eGFR)')
        
        if 'liver_disease' in patient_context.conditions:
            monitoring.append('Monitor liver function tests (AST, ALT, bilirubin)')
        
        # Remove duplicates
        return list(set(monitoring))
    
    def _calculate_confidence(
        self,
        pg_factors: List[PharmacogenomicFactor],
        adme_patterns: List[ADMEPattern]
    ) -> float:
        """Calculate overall confidence in analysis"""
        if not pg_factors and not adme_patterns:
            return 0.5  # Low confidence with no data
        
        # Average confidence from pharmacogenomic factors
        pg_confidence = 0.7
        if pg_factors:
            pg_confidence = sum(f.confidence for f in pg_factors) / len(pg_factors)
        
        # ADME patterns have moderate confidence
        adme_confidence = 0.75 if adme_patterns else 0.5
        
        # Weighted average
        total_confidence = (pg_confidence * 0.6 + adme_confidence * 0.4)
        
        return min(max(total_confidence, 0.0), 1.0)


# Factory function
async def create_physiological_analysis_service(
    database: KnowledgeGraphDatabase
) -> PhysiologicalAnalysisService:
    """Create physiological analysis service"""
    return PhysiologicalAnalysisService(database)
