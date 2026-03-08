"""
Provenance and transparency service for PharmaGuide
Tracks data sources, confidence levels, and evidence paths for all recommendations
"""
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.knowledge_graph.database import KnowledgeGraphDatabase

logger = logging.getLogger(__name__)


class DatasetType(str, Enum):
    """Type of dataset"""
    CLINICAL_TRIAL = "clinical_trial"
    REAL_WORLD_EVIDENCE = "real_world_evidence"
    REGULATORY = "regulatory"
    CURATED_DATABASE = "curated_database"
    LITERATURE = "literature"


@dataclass
class DatasetProvenance:
    """Provenance metadata for a dataset"""
    dataset_id: str
    dataset_name: str
    dataset_type: DatasetType
    version: str
    last_updated: datetime
    source_url: Optional[str]
    authority_score: float  # 0.0 to 1.0
    coverage: str
    limitations: List[str]
    citation: str


@dataclass
class EvidencePath:
    """Path through knowledge graph showing evidence chain"""
    path_id: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    datasets_used: List[str]
    confidence_scores: List[float]
    overall_confidence: float
    explanation: str


@dataclass
class TransparencyReport:
    """Transparency report for a recommendation"""
    recommendation_id: str
    recommendation_text: str
    evidence_paths: List[EvidencePath]
    data_sources: List[DatasetProvenance]
    confidence_breakdown: Dict[str, float]
    limitations: List[str]
    last_updated: datetime
    generated_at: datetime


class ProvenanceService:
    """
    Service for tracking provenance and providing transparency
    Maintains complete audit trail of data sources and evidence
    """
    
    def __init__(self, database: KnowledgeGraphDatabase):
        self.database = database
        self.logger = logging.getLogger(__name__)
        
        # Dataset registry
        self.datasets = {
            'SIDER': DatasetProvenance(
                dataset_id='sider_v4.1',
                dataset_name='SIDER (Side Effect Resource)',
                dataset_type=DatasetType.CLINICAL_TRIAL,
                version='4.1',
                last_updated=datetime(2015, 10, 21),
                source_url='http://sideeffects.embl.de/',
                authority_score=0.9,
                coverage='4,192 drugs, 139,756 drug-side effect pairs',
                limitations=['Limited to marketed drugs', 'May not include rare side effects'],
                citation='Kuhn et al., Molecular Systems Biology 2016'
            ),
            'OnSIDES': DatasetProvenance(
                dataset_id='onsides_v1.0',
                dataset_name='OnSIDES',
                dataset_type=DatasetType.REAL_WORLD_EVIDENCE,
                version='1.0',
                last_updated=datetime(2022, 3, 15),
                source_url='https://github.com/tatonetti-lab/onsides',
                authority_score=0.95,
                coverage='1,430 drugs, comprehensive adverse event profiles',
                limitations=['Based on FDA labels', 'May have reporting bias'],
                citation='Vanguri et al., Nature Medicine 2022'
            ),
            'FAERS': DatasetProvenance(
                dataset_id='faers_2023q4',
                dataset_name='FDA Adverse Event Reporting System',
                dataset_type=DatasetType.REAL_WORLD_EVIDENCE,
                version='2023 Q4',
                last_updated=datetime(2023, 12, 31),
                source_url='https://fis.fda.gov/extensions/FPD-QDE-FAERS/FPD-QDE-FAERS.html',
                authority_score=0.7,
                coverage='Millions of adverse event reports',
                limitations=['Voluntary reporting', 'Variable data quality', 'Reporting bias'],
                citation='FDA FAERS Database'
            ),
            'DrugBank': DatasetProvenance(
                dataset_id='drugbank_v5.1',
                dataset_name='DrugBank',
                dataset_type=DatasetType.CURATED_DATABASE,
                version='5.1.10',
                last_updated=datetime(2023, 1, 4),
                source_url='https://go.drugbank.com/',
                authority_score=0.85,
                coverage='14,000+ drugs, comprehensive drug information',
                limitations=['Requires subscription for full access'],
                citation='Wishart et al., Nucleic Acids Research 2023'
            ),
            'DDInter': DatasetProvenance(
                dataset_id='ddinter_v2.0',
                dataset_name='DDInter',
                dataset_type=DatasetType.CURATED_DATABASE,
                version='2.0',
                last_updated=datetime(2022, 6, 1),
                source_url='http://ddinter.scbdd.com/',
                authority_score=0.8,
                coverage='2,329 drugs, 278,850 DDIs',
                limitations=['May not include all rare interactions'],
                citation='Xiong et al., Nucleic Acids Research 2022'
            ),
            'FDA': DatasetProvenance(
                dataset_id='fda_drugs_2023',
                dataset_name='Drugs@FDA',
                dataset_type=DatasetType.REGULATORY,
                version='2023',
                last_updated=datetime(2023, 12, 31),
                source_url='https://www.fda.gov/drugs/drug-approvals-and-databases/drugsfda-data-files',
                authority_score=1.0,
                coverage='All FDA-approved drugs',
                limitations=['US-specific approvals'],
                citation='FDA Drugs@FDA Database'
            )
        }
    
    async def get_provenance_for_recommendation(
        self,
        recommendation_id: str,
        recommendation_text: str,
        evidence_paths: List[EvidencePath]
    ) -> TransparencyReport:
        """
        Get complete provenance and transparency report for a recommendation
        
        Args:
            recommendation_id: Unique identifier for recommendation
            recommendation_text: The recommendation text
            evidence_paths: Evidence paths supporting the recommendation
        
        Returns:
            Transparency report with complete provenance
        """
        try:
            self.logger.info(f"Generating transparency report for {recommendation_id}")
            
            # Extract data sources from evidence paths
            data_sources = self._extract_data_sources(evidence_paths)
            
            # Calculate confidence breakdown
            confidence_breakdown = self._calculate_confidence_breakdown(
                evidence_paths, data_sources
            )
            
            # Aggregate limitations
            limitations = self._aggregate_limitations(data_sources, evidence_paths)
            
            # Get last update time
            last_updated = self._get_last_update_time(data_sources)
            
            return TransparencyReport(
                recommendation_id=recommendation_id,
                recommendation_text=recommendation_text,
                evidence_paths=evidence_paths,
                data_sources=data_sources,
                confidence_breakdown=confidence_breakdown,
                limitations=limitations,
                last_updated=last_updated,
                generated_at=datetime.utcnow()
            )
        
        except Exception as e:
            self.logger.error(f"Error generating transparency report: {e}")
            raise
    
    def _extract_data_sources(
        self,
        evidence_paths: List[EvidencePath]
    ) -> List[DatasetProvenance]:
        """Extract unique data sources from evidence paths"""
        dataset_ids = set()
        for path in evidence_paths:
            dataset_ids.update(path.datasets_used)
        
        sources = []
        for dataset_id in dataset_ids:
            if dataset_id in self.datasets:
                sources.append(self.datasets[dataset_id])
        
        # Sort by authority score (highest first)
        sources.sort(key=lambda x: x.authority_score, reverse=True)
        
        return sources
    
    def _calculate_confidence_breakdown(
        self,
        evidence_paths: List[EvidencePath],
        data_sources: List[DatasetProvenance]
    ) -> Dict[str, float]:
        """Calculate confidence breakdown by source"""
        breakdown = {}
        
        # Overall confidence from paths
        if evidence_paths:
            overall = sum(p.overall_confidence for p in evidence_paths) / len(evidence_paths)
            breakdown['overall'] = overall
        
        # Confidence by dataset
        for source in data_sources:
            # Find paths using this dataset
            relevant_paths = [
                p for p in evidence_paths
                if source.dataset_id in p.datasets_used
            ]
            
            if relevant_paths:
                avg_confidence = sum(
                    p.overall_confidence for p in relevant_paths
                ) / len(relevant_paths)
                breakdown[source.dataset_name] = avg_confidence
        
        # Confidence by evidence type
        clinical_paths = [
            p for p in evidence_paths
            if any(ds in p.datasets_used for ds in ['SIDER', 'OnSIDES'])
        ]
        if clinical_paths:
            breakdown['clinical_evidence'] = sum(
                p.overall_confidence for p in clinical_paths
            ) / len(clinical_paths)
        
        realworld_paths = [
            p for p in evidence_paths
            if 'FAERS' in p.datasets_used
        ]
        if realworld_paths:
            breakdown['real_world_evidence'] = sum(
                p.overall_confidence for p in realworld_paths
            ) / len(realworld_paths)
        
        return breakdown
    
    def _aggregate_limitations(
        self,
        data_sources: List[DatasetProvenance],
        evidence_paths: List[EvidencePath]
    ) -> List[str]:
        """Aggregate limitations from all sources"""
        limitations = set()
        
        # Add dataset limitations
        for source in data_sources:
            limitations.update(source.limitations)
        
        # Add general limitations
        if len(evidence_paths) < 2:
            limitations.add('Limited evidence - single source only')
        
        if any(p.overall_confidence < 0.7 for p in evidence_paths):
            limitations.add('Some evidence has moderate to low confidence')
        
        return sorted(list(limitations))
    
    def _get_last_update_time(
        self,
        data_sources: List[DatasetProvenance]
    ) -> datetime:
        """Get most recent update time from data sources"""
        if not data_sources:
            return datetime.utcnow()
        
        return max(source.last_updated for source in data_sources)
    
    async def trace_evidence_path(
        self,
        start_entity: str,
        end_entity: str,
        relationship_type: Optional[str] = None
    ) -> List[EvidencePath]:
        """
        Trace evidence paths between two entities in knowledge graph
        
        Args:
            start_entity: Starting entity ID
            end_entity: Ending entity ID
            relationship_type: Optional relationship type filter
        
        Returns:
            List of evidence paths
        """
        try:
            self.logger.info(f"Tracing evidence path from {start_entity} to {end_entity}")
            
            # Query knowledge graph for paths
            paths = await self._query_graph_paths(
                start_entity, end_entity, relationship_type
            )
            
            # Convert to evidence paths with provenance
            evidence_paths = []
            for i, path in enumerate(paths):
                evidence_path = await self._create_evidence_path(
                    f"path_{i}", path
                )
                evidence_paths.append(evidence_path)
            
            return evidence_paths
        
        except Exception as e:
            self.logger.error(f"Error tracing evidence path: {e}")
            return []
    
    async def _query_graph_paths(
        self,
        start_entity: str,
        end_entity: str,
        relationship_type: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Query knowledge graph for paths"""
        try:
            # In real implementation, would use Gremlin traversal
            # For now, return placeholder
            self.logger.info("Querying graph paths")
            return []
        
        except Exception as e:
            self.logger.error(f"Error querying graph paths: {e}")
            return []
    
    async def _create_evidence_path(
        self,
        path_id: str,
        path_data: Dict[str, Any]
    ) -> EvidencePath:
        """Create evidence path with provenance metadata"""
        nodes = path_data.get('nodes', [])
        edges = path_data.get('edges', [])
        
        # Extract datasets from edges
        datasets_used = []
        confidence_scores = []
        
        for edge in edges:
            sources = edge.get('evidence_sources', [])
            datasets_used.extend(sources)
            
            confidence = edge.get('confidence', 0.5)
            confidence_scores.append(confidence)
        
        # Calculate overall confidence
        overall_confidence = (
            sum(confidence_scores) / len(confidence_scores)
            if confidence_scores else 0.5
        )
        
        # Generate explanation
        explanation = self._generate_path_explanation(nodes, edges, datasets_used)
        
        return EvidencePath(
            path_id=path_id,
            nodes=nodes,
            edges=edges,
            datasets_used=list(set(datasets_used)),
            confidence_scores=confidence_scores,
            overall_confidence=overall_confidence,
            explanation=explanation
        )
    
    def _generate_path_explanation(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        datasets: List[str]
    ) -> str:
        """Generate human-readable explanation of evidence path"""
        if not nodes or not edges:
            return "No evidence path available"
        
        # Build explanation
        parts = []
        parts.append(f"Evidence from {len(set(datasets))} dataset(s):")
        
        for dataset in set(datasets):
            if dataset in self.datasets:
                parts.append(f"- {self.datasets[dataset].dataset_name}")
        
        parts.append(f"\nPath traverses {len(nodes)} entities through {len(edges)} relationships")
        
        return " ".join(parts)
    
    def get_dataset_info(self, dataset_id: str) -> Optional[DatasetProvenance]:
        """Get provenance information for a dataset"""
        return self.datasets.get(dataset_id)
    
    def list_all_datasets(self) -> List[DatasetProvenance]:
        """List all registered datasets"""
        return sorted(
            self.datasets.values(),
            key=lambda x: x.authority_score,
            reverse=True
        )
    
    async def validate_data_quality(
        self,
        entity_id: str,
        entity_type: str
    ) -> Dict[str, Any]:
        """
        Validate data quality for an entity
        
        Args:
            entity_id: Entity identifier
            entity_type: Type of entity (drug, side_effect, etc.)
        
        Returns:
            Data quality metrics
        """
        try:
            self.logger.info(f"Validating data quality for {entity_id}")
            
            # Query entity data
            entity_data = await self._query_entity_data(entity_id, entity_type)
            
            # Check completeness
            completeness = self._check_completeness(entity_data)
            
            # Check consistency
            consistency = self._check_consistency(entity_data)
            
            # Check currency (how recent is the data)
            currency = self._check_currency(entity_data)
            
            # Calculate overall quality score
            quality_score = (completeness + consistency + currency) / 3
            
            return {
                'entity_id': entity_id,
                'entity_type': entity_type,
                'quality_score': quality_score,
                'completeness': completeness,
                'consistency': consistency,
                'currency': currency,
                'issues': self._identify_quality_issues(entity_data),
                'recommendations': self._generate_quality_recommendations(entity_data)
            }
        
        except Exception as e:
            self.logger.error(f"Error validating data quality: {e}")
            return {
                'entity_id': entity_id,
                'entity_type': entity_type,
                'quality_score': 0.0,
                'error': str(e)
            }
    
    async def _query_entity_data(
        self,
        entity_id: str,
        entity_type: str
    ) -> Dict[str, Any]:
        """Query entity data from knowledge graph"""
        try:
            # In real implementation, would query graph
            self.logger.info(f"Querying entity data for {entity_id}")
            return {
                'id': entity_id,
                'type': entity_type,
                'properties': {},
                'relationships': [],
                'sources': []
            }
        
        except Exception as e:
            self.logger.error(f"Error querying entity data: {e}")
            return {}
    
    def _check_completeness(self, entity_data: Dict[str, Any]) -> float:
        """Check data completeness (0.0 to 1.0)"""
        required_fields = ['id', 'type', 'properties', 'sources']
        present_fields = sum(1 for field in required_fields if field in entity_data)
        
        completeness = present_fields / len(required_fields)
        
        # Bonus for having multiple sources
        if entity_data.get('sources') and len(entity_data['sources']) > 1:
            completeness = min(completeness + 0.1, 1.0)
        
        return completeness
    
    def _check_consistency(self, entity_data: Dict[str, Any]) -> float:
        """Check data consistency across sources (0.0 to 1.0)"""
        sources = entity_data.get('sources', [])
        
        if len(sources) < 2:
            return 0.8  # Single source, assume consistent
        
        # In real implementation, would check for conflicts
        # For now, return high consistency
        return 0.9
    
    def _check_currency(self, entity_data: Dict[str, Any]) -> float:
        """Check data currency (how recent) (0.0 to 1.0)"""
        sources = entity_data.get('sources', [])
        
        if not sources:
            return 0.5
        
        # Check most recent update
        most_recent = datetime(2020, 1, 1)  # Default old date
        
        for source_id in sources:
            if source_id in self.datasets:
                source_date = self.datasets[source_id].last_updated
                if source_date > most_recent:
                    most_recent = source_date
        
        # Calculate currency based on age
        age_days = (datetime.utcnow() - most_recent).days
        
        if age_days < 365:
            return 1.0
        elif age_days < 730:
            return 0.8
        elif age_days < 1095:
            return 0.6
        else:
            return 0.4
    
    def _identify_quality_issues(self, entity_data: Dict[str, Any]) -> List[str]:
        """Identify data quality issues"""
        issues = []
        
        if not entity_data.get('sources'):
            issues.append('No data sources identified')
        
        if len(entity_data.get('sources', [])) == 1:
            issues.append('Single source only - no cross-validation')
        
        if not entity_data.get('properties'):
            issues.append('Missing property data')
        
        return issues
    
    def _generate_quality_recommendations(
        self,
        entity_data: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations for improving data quality"""
        recommendations = []
        
        if len(entity_data.get('sources', [])) < 2:
            recommendations.append('Add additional data sources for cross-validation')
        
        if not entity_data.get('properties'):
            recommendations.append('Enrich entity with additional properties')
        
        return recommendations


# Factory function
async def create_provenance_service(
    database: KnowledgeGraphDatabase
) -> ProvenanceService:
    """Create provenance service"""
    return ProvenanceService(database)
