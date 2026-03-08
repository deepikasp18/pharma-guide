"""
Side effect retrieval service for PharmaGuide
Implements comprehensive side effect queries from clinical and real-world data
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.knowledge_graph.database import KnowledgeGraphDatabase
from src.knowledge_graph.models import (
    DrugEntity, SideEffectEntity, PatientContext,
    FrequencyCategory, SeverityLevel
)

logger = logging.getLogger(__name__)


class DataSourceType(str, Enum):
    """Type of data source for side effects"""
    CLINICAL_TRIAL = "clinical_trial"
    REAL_WORLD = "real_world"
    POST_MARKET = "post_market"
    SPONTANEOUS_REPORT = "spontaneous_report"


@dataclass
class SideEffectResult:
    """Side effect query result"""
    side_effect_id: str
    side_effect_name: str
    frequency: float  # 0.0 to 1.0
    frequency_category: FrequencyCategory
    severity: Optional[SeverityLevel]
    confidence: float
    data_sources: List[str]
    source_types: List[DataSourceType]
    patient_count: Optional[int]
    demographic_correlation: Optional[Dict[str, Any]]
    system_organ_class: Optional[str]
    description: Optional[str]


@dataclass
class DemographicCorrelation:
    """Demographic correlation for adverse events"""
    demographic_factor: str  # age, gender, weight, etc.
    factor_value: Any
    correlation_strength: float  # 0.0 to 1.0
    relative_risk: float
    patient_count: int
    confidence: float


class SideEffectRetrievalService:
    """
    Service for retrieving comprehensive side effect information
    Integrates clinical trial data and real-world evidence
    """
    
    def __init__(self, database: KnowledgeGraphDatabase):
        self.database = database
        self.logger = logging.getLogger(__name__)
        
        # Dataset authority weights
        self.dataset_weights = {
            'SIDER': 0.9,  # High quality clinical trial data
            'OnSIDES': 0.95,  # Modern comprehensive dataset
            'FAERS': 0.7,  # Real-world but variable quality
            'DrugBank': 0.85,  # Curated database
            'FDA': 1.0  # Highest authority
        }
    
    async def get_side_effects_for_drug(
        self,
        drug_id: str,
        include_frequency: bool = True,
        include_demographics: bool = False,
        patient_context: Optional[PatientContext] = None,
        min_confidence: float = 0.5
    ) -> List[SideEffectResult]:
        """
        Retrieve comprehensive side effects for a drug
        
        Args:
            drug_id: Drug identifier
            include_frequency: Include frequency data from SIDER
            include_demographics: Include demographic correlations
            patient_context: Optional patient context for personalization
            min_confidence: Minimum confidence threshold
        
        Returns:
            List of side effect results with comprehensive information
        """
        try:
            self.logger.info(f"Retrieving side effects for drug {drug_id}")
            
            # Query knowledge graph for side effects
            side_effects = await self._query_side_effects(drug_id)
            
            # Enrich with frequency data from SIDER
            if include_frequency:
                side_effects = await self._enrich_with_frequency_data(
                    drug_id, side_effects
                )
            
            # Add demographic correlations if requested
            if include_demographics:
                side_effects = await self._add_demographic_correlations(
                    drug_id, side_effects, patient_context
                )
            
            # Filter by confidence threshold
            side_effects = [
                se for se in side_effects
                if se.confidence >= min_confidence
            ]
            
            # Sort by severity and frequency
            side_effects = self._sort_by_relevance(side_effects, patient_context)
            
            self.logger.info(f"Found {len(side_effects)} side effects")
            return side_effects
        
        except Exception as e:
            self.logger.error(f"Error retrieving side effects: {e}")
            raise
    
    async def _query_side_effects(
        self,
        drug_id: str
    ) -> List[SideEffectResult]:
        """Query knowledge graph for side effects"""
        try:
            g = self.database.connection.g
            
            # Traverse from drug to side effects via CAUSES edges
            # Get both the side effect nodes and edge properties
            results = []
            
            # In a real implementation, this would be a proper Gremlin query
            # For now, we'll use the database's find_side_effects_for_drug method
            side_effect_nodes = await self.database.find_side_effects_for_drug(drug_id)
            
            for node in side_effect_nodes:
                # Extract side effect information
                side_effect_id = node.get('id', '')
                side_effect_name = node.get('name', 'Unknown')
                
                # Get edge properties (frequency, confidence, etc.)
                edge_props = await self._get_causes_edge_properties(
                    drug_id, side_effect_id
                )
                
                # Determine data sources
                data_sources = edge_props.get('evidence_sources', [])
                source_types = self._classify_data_sources(data_sources)
                
                # Create result
                result = SideEffectResult(
                    side_effect_id=side_effect_id,
                    side_effect_name=side_effect_name,
                    frequency=edge_props.get('frequency', 0.0),
                    frequency_category=self._categorize_frequency(
                        edge_props.get('frequency', 0.0)
                    ),
                    severity=self._parse_severity(node.get('severity')),
                    confidence=edge_props.get('confidence', 0.5),
                    data_sources=data_sources,
                    source_types=source_types,
                    patient_count=edge_props.get('patient_count'),
                    demographic_correlation=None,
                    system_organ_class=node.get('system_organ_class'),
                    description=node.get('description')
                )
                
                results.append(result)
            
            return results
        
        except Exception as e:
            self.logger.error(f"Error querying side effects: {e}")
            return []
    
    async def _get_causes_edge_properties(
        self,
        drug_id: str,
        side_effect_id: str
    ) -> Dict[str, Any]:
        """Get properties of CAUSES edge between drug and side effect"""
        try:
            g = self.database.connection.g
            
            # Query for edge properties
            edges = (g.V().has('id', drug_id)
                    .outE('CAUSES')
                    .where(g.V().has('id', side_effect_id))
                    .toList())
            
            if edges:
                edge = edges[0]
                return {
                    'frequency': float(edge.get('frequency', 0.0)),
                    'confidence': float(edge.get('confidence', 0.5)),
                    'evidence_sources': edge.get('evidence_sources', '').split(','),
                    'patient_count': edge.get('patient_count'),
                    'statistical_significance': edge.get('statistical_significance'),
                    'temporal_relationship': edge.get('temporal_relationship')
                }
            
            return {}
        
        except Exception as e:
            self.logger.error(f"Error getting edge properties: {e}")
            return {}
    
    async def _enrich_with_frequency_data(
        self,
        drug_id: str,
        side_effects: List[SideEffectResult]
    ) -> List[SideEffectResult]:
        """Enrich side effects with frequency data from SIDER dataset"""
        try:
            # Query SIDER-specific frequency data
            sider_frequencies = await self._query_sider_frequencies(drug_id)
            
            # Merge with existing results
            for se in side_effects:
                if se.side_effect_id in sider_frequencies:
                    sider_data = sider_frequencies[se.side_effect_id]
                    
                    # Update frequency if SIDER has more precise data
                    if 'SIDER' in sider_data.get('sources', []):
                        se.frequency = sider_data.get('frequency', se.frequency)
                        se.frequency_category = self._categorize_frequency(se.frequency)
                    
                    # Add SIDER to data sources if not already present
                    if 'SIDER' not in se.data_sources:
                        se.data_sources.append('SIDER')
                        se.source_types.append(DataSourceType.CLINICAL_TRIAL)
            
            return side_effects
        
        except Exception as e:
            self.logger.error(f"Error enriching with frequency data: {e}")
            return side_effects
    
    async def _query_sider_frequencies(
        self,
        drug_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """Query SIDER dataset for frequency information"""
        try:
            # In a real implementation, this would query SIDER-specific nodes/edges
            # For now, return empty dict as placeholder
            self.logger.info(f"Querying SIDER frequencies for drug {drug_id}")
            return {}
        
        except Exception as e:
            self.logger.error(f"Error querying SIDER frequencies: {e}")
            return {}
    
    async def _add_demographic_correlations(
        self,
        drug_id: str,
        side_effects: List[SideEffectResult],
        patient_context: Optional[PatientContext]
    ) -> List[SideEffectResult]:
        """Add demographic-based adverse event correlations"""
        try:
            self.logger.info("Adding demographic correlations")
            
            # Query FAERS data for demographic correlations
            for se in side_effects:
                correlations = await self._query_demographic_correlations(
                    drug_id,
                    se.side_effect_id,
                    patient_context
                )
                
                if correlations:
                    se.demographic_correlation = {
                        'correlations': correlations,
                        'patient_match': self._calculate_patient_match(
                            correlations, patient_context
                        ) if patient_context else None
                    }
            
            return side_effects
        
        except Exception as e:
            self.logger.error(f"Error adding demographic correlations: {e}")
            return side_effects
    
    async def _query_demographic_correlations(
        self,
        drug_id: str,
        side_effect_id: str,
        patient_context: Optional[PatientContext]
    ) -> List[DemographicCorrelation]:
        """Query demographic correlations from FAERS data"""
        try:
            correlations = []
            
            # Query knowledge graph for demographic relationships
            # This would traverse from drug-side effect to demographic nodes
            g = self.database.connection.g
            
            # Example: Find age-related correlations
            # In real implementation, this would query actual demographic nodes
            
            # Placeholder correlations based on common patterns
            if patient_context:
                age = patient_context.demographics.get('age', 0)
                gender = patient_context.demographics.get('gender', '')
                
                # Age correlation
                if age > 65:
                    correlations.append(DemographicCorrelation(
                        demographic_factor='age',
                        factor_value='elderly',
                        correlation_strength=0.7,
                        relative_risk=1.5,
                        patient_count=1000,
                        confidence=0.8
                    ))
                
                # Gender correlation (example)
                if gender:
                    correlations.append(DemographicCorrelation(
                        demographic_factor='gender',
                        factor_value=gender,
                        correlation_strength=0.6,
                        relative_risk=1.2,
                        patient_count=500,
                        confidence=0.7
                    ))
            
            return correlations
        
        except Exception as e:
            self.logger.error(f"Error querying demographic correlations: {e}")
            return []
    
    def _calculate_patient_match(
        self,
        correlations: List[DemographicCorrelation],
        patient_context: PatientContext
    ) -> float:
        """Calculate how well patient matches demographic correlations"""
        if not correlations:
            return 0.0
        
        total_match = 0.0
        total_weight = 0.0
        
        for corr in correlations:
            # Check if patient matches this demographic factor
            patient_value = patient_context.demographics.get(corr.demographic_factor)
            
            if patient_value == corr.factor_value:
                # Patient matches this correlation
                weight = corr.correlation_strength
                total_match += weight
                total_weight += weight
            else:
                total_weight += corr.correlation_strength
        
        return total_match / total_weight if total_weight > 0 else 0.0
    
    def _classify_data_sources(
        self,
        data_sources: List[str]
    ) -> List[DataSourceType]:
        """Classify data sources by type"""
        source_types = []
        
        for source in data_sources:
            source_upper = source.upper()
            
            if 'SIDER' in source_upper or 'CLINICAL' in source_upper:
                source_types.append(DataSourceType.CLINICAL_TRIAL)
            elif 'FAERS' in source_upper or 'ADVERSE' in source_upper:
                source_types.append(DataSourceType.REAL_WORLD)
                source_types.append(DataSourceType.SPONTANEOUS_REPORT)
            elif 'ONSIDES' in source_upper:
                source_types.append(DataSourceType.CLINICAL_TRIAL)
            elif 'FDA' in source_upper:
                source_types.append(DataSourceType.POST_MARKET)
            else:
                source_types.append(DataSourceType.REAL_WORLD)
        
        return list(set(source_types))  # Remove duplicates
    
    def _categorize_frequency(self, frequency: float) -> FrequencyCategory:
        """Categorize numeric frequency into standard categories"""
        if frequency >= 0.1:
            return FrequencyCategory.VERY_COMMON
        elif frequency >= 0.01:
            return FrequencyCategory.COMMON
        elif frequency >= 0.001:
            return FrequencyCategory.UNCOMMON
        elif frequency >= 0.0001:
            return FrequencyCategory.RARE
        elif frequency > 0:
            return FrequencyCategory.VERY_RARE
        else:
            return FrequencyCategory.UNKNOWN
    
    def _parse_severity(self, severity_str: Optional[str]) -> Optional[SeverityLevel]:
        """Parse severity string to SeverityLevel enum"""
        if not severity_str:
            return None
        
        severity_str = severity_str.lower()
        
        if severity_str in ['minor', 'mild']:
            return SeverityLevel.MINOR
        elif severity_str in ['moderate', 'medium']:
            return SeverityLevel.MODERATE
        elif severity_str in ['major', 'severe']:
            return SeverityLevel.MAJOR
        elif severity_str in ['contraindicated', 'critical']:
            return SeverityLevel.CONTRAINDICATED
        
        return None
    
    def _sort_by_relevance(
        self,
        side_effects: List[SideEffectResult],
        patient_context: Optional[PatientContext]
    ) -> List[SideEffectResult]:
        """Sort side effects by relevance (severity, frequency, patient match)"""
        
        def relevance_score(se: SideEffectResult) -> float:
            score = 0.0
            
            # Severity weight (highest priority)
            if se.severity == SeverityLevel.CONTRAINDICATED:
                score += 100.0
            elif se.severity == SeverityLevel.MAJOR:
                score += 75.0
            elif se.severity == SeverityLevel.MODERATE:
                score += 50.0
            elif se.severity == SeverityLevel.MINOR:
                score += 25.0
            
            # Frequency weight
            score += se.frequency * 20.0
            
            # Confidence weight
            score += se.confidence * 10.0
            
            # Patient match weight (if available)
            if patient_context and se.demographic_correlation:
                patient_match = se.demographic_correlation.get('patient_match', 0.0)
                score += patient_match * 30.0
            
            # Data source quality weight
            for source in se.data_sources:
                score += self.dataset_weights.get(source, 0.5) * 5.0
            
            return score
        
        return sorted(side_effects, key=relevance_score, reverse=True)
    
    async def get_real_world_evidence(
        self,
        drug_id: str,
        side_effect_id: Optional[str] = None,
        min_patient_count: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get real-world evidence from FAERS dataset
        
        Args:
            drug_id: Drug identifier
            side_effect_id: Optional specific side effect
            min_patient_count: Minimum number of patient reports
        
        Returns:
            List of real-world evidence records
        """
        try:
            self.logger.info(f"Retrieving real-world evidence for drug {drug_id}")
            
            # Query FAERS data from knowledge graph
            evidence = await self._query_faers_data(
                drug_id, side_effect_id, min_patient_count
            )
            
            return evidence
        
        except Exception as e:
            self.logger.error(f"Error retrieving real-world evidence: {e}")
            return []
    
    async def _query_faers_data(
        self,
        drug_id: str,
        side_effect_id: Optional[str],
        min_patient_count: int
    ) -> List[Dict[str, Any]]:
        """Query FAERS dataset from knowledge graph"""
        try:
            # In real implementation, this would query FAERS-specific nodes
            # For now, return placeholder
            self.logger.info("Querying FAERS data")
            return []
        
        except Exception as e:
            self.logger.error(f"Error querying FAERS data: {e}")
            return []
    
    async def compare_clinical_vs_realworld(
        self,
        drug_id: str,
        side_effect_id: str
    ) -> Dict[str, Any]:
        """
        Compare clinical trial data vs real-world evidence for a side effect
        
        Args:
            drug_id: Drug identifier
            side_effect_id: Side effect identifier
        
        Returns:
            Comparison data with clinical and real-world statistics
        """
        try:
            self.logger.info(
                f"Comparing clinical vs real-world data for "
                f"drug {drug_id}, side effect {side_effect_id}"
            )
            
            # Get clinical trial data (SIDER, OnSIDES)
            clinical_data = await self._get_clinical_trial_data(
                drug_id, side_effect_id
            )
            
            # Get real-world data (FAERS)
            realworld_data = await self._get_realworld_data(
                drug_id, side_effect_id
            )
            
            # Calculate comparison metrics
            comparison = {
                'drug_id': drug_id,
                'side_effect_id': side_effect_id,
                'clinical': clinical_data,
                'real_world': realworld_data,
                'frequency_ratio': self._calculate_frequency_ratio(
                    clinical_data, realworld_data
                ),
                'reporting_difference': self._calculate_reporting_difference(
                    clinical_data, realworld_data
                ),
                'confidence': min(
                    clinical_data.get('confidence', 0.5),
                    realworld_data.get('confidence', 0.5)
                )
            }
            
            return comparison
        
        except Exception as e:
            self.logger.error(f"Error comparing clinical vs real-world data: {e}")
            return {}
    
    async def _get_clinical_trial_data(
        self,
        drug_id: str,
        side_effect_id: str
    ) -> Dict[str, Any]:
        """Get clinical trial data for drug-side effect pair"""
        # Placeholder implementation
        return {
            'frequency': 0.05,
            'patient_count': 1000,
            'confidence': 0.9,
            'sources': ['SIDER', 'OnSIDES']
        }
    
    async def _get_realworld_data(
        self,
        drug_id: str,
        side_effect_id: str
    ) -> Dict[str, Any]:
        """Get real-world data for drug-side effect pair"""
        # Placeholder implementation
        return {
            'frequency': 0.08,
            'patient_count': 5000,
            'confidence': 0.7,
            'sources': ['FAERS']
        }
    
    def _calculate_frequency_ratio(
        self,
        clinical_data: Dict[str, Any],
        realworld_data: Dict[str, Any]
    ) -> float:
        """Calculate ratio of real-world to clinical trial frequency"""
        clinical_freq = clinical_data.get('frequency', 0.0)
        realworld_freq = realworld_data.get('frequency', 0.0)
        
        if clinical_freq == 0:
            return 0.0
        
        return realworld_freq / clinical_freq
    
    def _calculate_reporting_difference(
        self,
        clinical_data: Dict[str, Any],
        realworld_data: Dict[str, Any]
    ) -> str:
        """Calculate qualitative reporting difference"""
        ratio = self._calculate_frequency_ratio(clinical_data, realworld_data)
        
        if ratio > 1.5:
            return "significantly_higher_in_realworld"
        elif ratio > 1.1:
            return "moderately_higher_in_realworld"
        elif ratio > 0.9:
            return "similar"
        elif ratio > 0.5:
            return "moderately_lower_in_realworld"
        else:
            return "significantly_lower_in_realworld"


# Factory function
async def create_side_effect_service(
    database: KnowledgeGraphDatabase
) -> SideEffectRetrievalService:
    """Create side effect retrieval service"""
    return SideEffectRetrievalService(database)
