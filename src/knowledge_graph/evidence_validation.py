"""
Evidence validation service for PharmaGuide
Implements data quality validation and confidence scoring
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from src.knowledge_graph.models import DatasetMetadata, EvidenceProvenance

logger = logging.getLogger(__name__)


class DataQualityLevel(str, Enum):
    """Data quality levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    INSUFFICIENT = "insufficient"


class AuthorityLevel(str, Enum):
    """Source authority levels"""
    HIGH = "high"  # FDA, clinical trials
    MEDIUM = "medium"  # Curated databases
    LOW = "low"  # Observational data


@dataclass
class ValidationResult:
    """Data validation result"""
    is_valid: bool
    quality_level: DataQualityLevel
    quality_score: float  # 0.0 to 1.0
    issues: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


@dataclass
class ConfidenceScore:
    """Confidence score for evidence"""
    overall_confidence: float  # 0.0 to 1.0
    authority_score: float
    evidence_strength_score: float
    recency_score: float
    consistency_score: float
    contributing_factors: Dict[str, float]
    explanation: str


@dataclass
class CrossValidationResult:
    """Cross-validation result across datasets"""
    entity_id: str
    datasets_checked: List[str]
    consistent: bool
    consistency_score: float
    conflicts: List[Dict[str, Any]]
    consensus_value: Any
    confidence: float


class EvidenceValidationService:
    """
    Service for validating data quality and scoring evidence confidence
    Implements validation before knowledge graph integration
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Authority weights for different data sources
        self.authority_weights = {
            'FDA': 1.0,
            'Drugs@FDA': 1.0,
            'OnSIDES': 0.95,
            'SIDER': 0.9,
            'DrugBank': 0.85,
            'DDInter': 0.85,
            'FAERS': 0.7,
            'Clinical_Trial': 0.9,
            'Observational': 0.6
        }
        
        # Minimum thresholds
        self.min_quality_score = 0.5
        self.min_confidence_score = 0.4
    
    def validate_data_quality(
        self,
        data: Dict[str, Any],
        dataset_name: str,
        required_fields: Optional[List[str]] = None
    ) -> ValidationResult:
        """
        Validate data quality before knowledge graph integration
        
        Args:
            data: Data to validate
            dataset_name: Name of source dataset
            required_fields: Optional list of required fields
        
        Returns:
            Validation result with quality assessment
        """
        try:
            self.logger.info(f"Validating data quality for {dataset_name}")
            
            issues = []
            warnings = []
            
            # Check required fields
            if required_fields:
                missing_fields = [f for f in required_fields if f not in data]
                if missing_fields:
                    issues.append(f"Missing required fields: {', '.join(missing_fields)}")
            
            # Check data completeness
            completeness_score = self._check_completeness(data)
            if completeness_score < 0.5:
                issues.append(f"Low data completeness: {completeness_score:.2f}")
            elif completeness_score < 0.7:
                warnings.append(f"Moderate data completeness: {completeness_score:.2f}")
            
            # Check data consistency
            consistency_issues = self._check_consistency(data)
            issues.extend(consistency_issues)
            
            # Check data validity
            validity_issues = self._check_validity(data)
            issues.extend(validity_issues)
            
            # Check data recency
            recency_score = self._check_recency(data)
            if recency_score < 0.3:
                warnings.append("Data may be outdated")
            
            # Calculate overall quality score
            quality_score = self._calculate_quality_score(
                completeness_score,
                len(consistency_issues),
                len(validity_issues),
                recency_score
            )
            
            # Determine quality level
            quality_level = self._determine_quality_level(quality_score)
            
            # Determine if valid
            is_valid = len(issues) == 0 and quality_score >= self.min_quality_score
            
            result = ValidationResult(
                is_valid=is_valid,
                quality_level=quality_level,
                quality_score=quality_score,
                issues=issues,
                warnings=warnings,
                metadata={
                    'dataset': dataset_name,
                    'completeness': completeness_score,
                    'recency': recency_score,
                    'validated_at': datetime.utcnow().isoformat()
                }
            )
            
            self.logger.info(
                f"Validation complete: valid={is_valid}, "
                f"quality={quality_level.value}, score={quality_score:.2f}"
            )
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error validating data quality: {e}")
            return ValidationResult(
                is_valid=False,
                quality_level=DataQualityLevel.INSUFFICIENT,
                quality_score=0.0,
                issues=[f"Validation error: {str(e)}"],
                warnings=[],
                metadata={}
            )
    
    def _check_completeness(self, data: Dict[str, Any]) -> float:
        """Check data completeness"""
        if not data:
            return 0.0
        
        # Count non-null, non-empty values
        total_fields = len(data)
        complete_fields = sum(
            1 for v in data.values()
            if v is not None and v != '' and v != []
        )
        
        return complete_fields / total_fields if total_fields > 0 else 0.0
    
    def _check_consistency(self, data: Dict[str, Any]) -> List[str]:
        """Check data consistency"""
        issues = []
        
        # Check numeric ranges
        if 'frequency' in data:
            freq = data['frequency']
            if isinstance(freq, (int, float)) and (freq < 0 or freq > 1):
                issues.append(f"Frequency out of range: {freq}")
        
        if 'confidence' in data:
            conf = data['confidence']
            if isinstance(conf, (int, float)) and (conf < 0 or conf > 1):
                issues.append(f"Confidence out of range: {conf}")
        
        # Check date consistency
        if 'start_date' in data and 'end_date' in data:
            try:
                start = datetime.fromisoformat(str(data['start_date']))
                end = datetime.fromisoformat(str(data['end_date']))
                if end < start:
                    issues.append("End date before start date")
            except (ValueError, TypeError):
                pass
        
        return issues
    
    def _check_validity(self, data: Dict[str, Any]) -> List[str]:
        """Check data validity"""
        issues = []
        
        # Check for negative patient counts
        if 'patient_count' in data:
            count = data['patient_count']
            if isinstance(count, (int, float)) and count < 0:
                issues.append(f"Negative patient count: {count}")
        
        # Check for invalid severity levels
        if 'severity' in data:
            valid_severities = ['minor', 'moderate', 'major', 'contraindicated', 'critical']
            severity = str(data['severity']).lower()
            if severity not in valid_severities:
                issues.append(f"Invalid severity level: {severity}")
        
        return issues
    
    def _check_recency(self, data: Dict[str, Any]) -> float:
        """Check data recency"""
        # Look for date fields
        date_fields = ['last_updated', 'publication_date', 'created_at', 'updated_at']
        
        for field in date_fields:
            if field in data:
                try:
                    date = datetime.fromisoformat(str(data[field]))
                    age_days = (datetime.utcnow() - date).days
                    
                    # Score based on age
                    if age_days < 365:
                        return 1.0
                    elif age_days < 730:
                        return 0.8
                    elif age_days < 1825:  # 5 years
                        return 0.6
                    else:
                        return 0.3
                except (ValueError, TypeError):
                    continue
        
        # No date found, assume moderate recency
        return 0.5
    
    def _calculate_quality_score(
        self,
        completeness: float,
        consistency_issues: int,
        validity_issues: int,
        recency: float
    ) -> float:
        """Calculate overall quality score"""
        # Base score from completeness
        score = completeness * 0.4
        
        # Penalty for issues
        issue_penalty = min((consistency_issues + validity_issues) * 0.1, 0.3)
        score -= issue_penalty
        
        # Recency contribution
        score += recency * 0.2
        
        # Ensure in valid range
        return max(0.0, min(1.0, score))
    
    def _determine_quality_level(self, score: float) -> DataQualityLevel:
        """Determine quality level from score"""
        if score >= 0.9:
            return DataQualityLevel.EXCELLENT
        elif score >= 0.7:
            return DataQualityLevel.GOOD
        elif score >= 0.5:
            return DataQualityLevel.FAIR
        elif score >= 0.3:
            return DataQualityLevel.POOR
        else:
            return DataQualityLevel.INSUFFICIENT
    
    def calculate_confidence_score(
        self,
        source_dataset: str,
        evidence_strength: float,
        publication_date: Optional[datetime] = None,
        patient_count: Optional[int] = None,
        cross_validation_score: Optional[float] = None
    ) -> ConfidenceScore:
        """
        Calculate confidence score based on source authority and evidence strength
        
        Args:
            source_dataset: Name of source dataset
            evidence_strength: Strength of evidence (0.0 to 1.0)
            publication_date: Optional publication date
            patient_count: Optional number of patients in evidence
            cross_validation_score: Optional cross-validation score
        
        Returns:
            Confidence score with breakdown
        """
        try:
            self.logger.info(f"Calculating confidence score for {source_dataset}")
            
            # Authority score
            authority_score = self._get_authority_score(source_dataset)
            
            # Evidence strength score (already provided)
            evidence_strength_score = max(0.0, min(1.0, evidence_strength))
            
            # Recency score
            recency_score = self._calculate_recency_score(publication_date)
            
            # Sample size score
            sample_size_score = self._calculate_sample_size_score(patient_count)
            
            # Cross-validation score
            consistency_score = cross_validation_score if cross_validation_score is not None else 0.5
            
            # Calculate weighted overall confidence
            weights = {
                'authority': 0.3,
                'evidence_strength': 0.3,
                'recency': 0.15,
                'sample_size': 0.15,
                'consistency': 0.1
            }
            
            overall_confidence = (
                authority_score * weights['authority'] +
                evidence_strength_score * weights['evidence_strength'] +
                recency_score * weights['recency'] +
                sample_size_score * weights['sample_size'] +
                consistency_score * weights['consistency']
            )
            
            # Generate explanation
            explanation = self._generate_confidence_explanation(
                authority_score, evidence_strength_score, recency_score,
                sample_size_score, consistency_score
            )
            
            score = ConfidenceScore(
                overall_confidence=overall_confidence,
                authority_score=authority_score,
                evidence_strength_score=evidence_strength_score,
                recency_score=recency_score,
                consistency_score=consistency_score,
                contributing_factors={
                    'authority': authority_score * weights['authority'],
                    'evidence_strength': evidence_strength_score * weights['evidence_strength'],
                    'recency': recency_score * weights['recency'],
                    'sample_size': sample_size_score * weights['sample_size'],
                    'consistency': consistency_score * weights['consistency']
                },
                explanation=explanation
            )
            
            self.logger.info(f"Confidence score: {overall_confidence:.2f}")
            return score
        
        except Exception as e:
            self.logger.error(f"Error calculating confidence score: {e}")
            return ConfidenceScore(
                overall_confidence=0.0,
                authority_score=0.0,
                evidence_strength_score=0.0,
                recency_score=0.0,
                consistency_score=0.0,
                contributing_factors={},
                explanation=f"Error calculating confidence: {str(e)}"
            )
    
    def _get_authority_score(self, dataset_name: str) -> float:
        """Get authority score for dataset"""
        # Check exact match
        if dataset_name in self.authority_weights:
            return self.authority_weights[dataset_name]
        
        # Check partial matches
        dataset_upper = dataset_name.upper()
        for key, weight in self.authority_weights.items():
            if key.upper() in dataset_upper:
                return weight
        
        # Default to medium authority
        return 0.6
    
    def _calculate_recency_score(self, publication_date: Optional[datetime]) -> float:
        """Calculate recency score"""
        if publication_date is None:
            return 0.5  # Unknown, assume moderate
        
        age_days = (datetime.utcnow() - publication_date).days
        
        if age_days < 365:
            return 1.0
        elif age_days < 730:
            return 0.9
        elif age_days < 1825:  # 5 years
            return 0.7
        elif age_days < 3650:  # 10 years
            return 0.5
        else:
            return 0.3
    
    def _calculate_sample_size_score(self, patient_count: Optional[int]) -> float:
        """Calculate score based on sample size"""
        if patient_count is None:
            return 0.5  # Unknown, assume moderate
        
        if patient_count >= 10000:
            return 1.0
        elif patient_count >= 1000:
            return 0.9
        elif patient_count >= 100:
            return 0.7
        elif patient_count >= 10:
            return 0.5
        else:
            return 0.3
    
    def _generate_confidence_explanation(
        self,
        authority: float,
        evidence: float,
        recency: float,
        sample_size: float,
        consistency: float
    ) -> str:
        """Generate human-readable confidence explanation"""
        parts = []
        
        if authority >= 0.9:
            parts.append("high-authority source")
        elif authority >= 0.7:
            parts.append("reputable source")
        else:
            parts.append("moderate-authority source")
        
        if evidence >= 0.8:
            parts.append("strong evidence")
        elif evidence >= 0.6:
            parts.append("moderate evidence")
        else:
            parts.append("limited evidence")
        
        if recency >= 0.8:
            parts.append("recent data")
        elif recency < 0.5:
            parts.append("older data")
        
        if sample_size >= 0.8:
            parts.append("large sample size")
        elif sample_size < 0.5:
            parts.append("limited sample size")
        
        return f"Based on {', '.join(parts)}"
    
    def cross_validate(
        self,
        entity_id: str,
        entity_type: str,
        datasets: List[Dict[str, Any]]
    ) -> CrossValidationResult:
        """
        Cross-validate entity across multiple datasets
        
        Args:
            entity_id: Entity identifier
            entity_type: Type of entity (drug, side_effect, etc.)
            datasets: List of dataset records for this entity
        
        Returns:
            Cross-validation result
        """
        try:
            self.logger.info(
                f"Cross-validating {entity_type} {entity_id} "
                f"across {len(datasets)} datasets"
            )
            
            if len(datasets) < 2:
                return CrossValidationResult(
                    entity_id=entity_id,
                    datasets_checked=[d.get('source', 'unknown') for d in datasets],
                    consistent=True,
                    consistency_score=1.0,
                    conflicts=[],
                    consensus_value=datasets[0] if datasets else None,
                    confidence=0.5
                )
            
            # Check for conflicts
            conflicts = self._identify_conflicts(datasets, entity_type)
            
            # Calculate consistency score
            consistency_score = self._calculate_consistency_score(datasets, conflicts)
            
            # Determine consensus value
            consensus_value = self._determine_consensus(datasets, conflicts)
            
            # Calculate overall confidence
            confidence = self._calculate_cross_validation_confidence(
                len(datasets), consistency_score
            )
            
            result = CrossValidationResult(
                entity_id=entity_id,
                datasets_checked=[d.get('source', 'unknown') for d in datasets],
                consistent=len(conflicts) == 0,
                consistency_score=consistency_score,
                conflicts=conflicts,
                consensus_value=consensus_value,
                confidence=confidence
            )
            
            self.logger.info(
                f"Cross-validation complete: consistent={result.consistent}, "
                f"score={consistency_score:.2f}"
            )
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error in cross-validation: {e}")
            return CrossValidationResult(
                entity_id=entity_id,
                datasets_checked=[],
                consistent=False,
                consistency_score=0.0,
                conflicts=[{'error': str(e)}],
                consensus_value=None,
                confidence=0.0
            )
    
    def _identify_conflicts(
        self,
        datasets: List[Dict[str, Any]],
        entity_type: str
    ) -> List[Dict[str, Any]]:
        """Identify conflicts between datasets"""
        conflicts = []
        
        # Compare key fields across datasets
        key_fields = self._get_key_fields(entity_type)
        
        for field in key_fields:
            values = {}
            for dataset in datasets:
                if field in dataset:
                    source = dataset.get('source', 'unknown')
                    value = dataset[field]
                    if value not in values:
                        values[value] = []
                    values[value].append(source)
            
            # Check for conflicts (multiple different values)
            if len(values) > 1:
                conflicts.append({
                    'field': field,
                    'values': values,
                    'conflict_type': 'value_mismatch'
                })
        
        return conflicts
    
    def _get_key_fields(self, entity_type: str) -> List[str]:
        """Get key fields to compare for entity type"""
        common_fields = ['name', 'description']
        
        type_specific = {
            'drug': ['generic_name', 'mechanism', 'indications'],
            'side_effect': ['severity', 'frequency', 'system_organ_class'],
            'interaction': ['severity', 'mechanism', 'clinical_effect']
        }
        
        return common_fields + type_specific.get(entity_type, [])
    
    def _calculate_consistency_score(
        self,
        datasets: List[Dict[str, Any]],
        conflicts: List[Dict[str, Any]]
    ) -> float:
        """Calculate consistency score"""
        if not datasets:
            return 0.0
        
        # Base score
        score = 1.0
        
        # Penalty for each conflict
        conflict_penalty = len(conflicts) * 0.15
        score -= conflict_penalty
        
        # Bonus for multiple agreeing sources
        if len(datasets) >= 3 and len(conflicts) == 0:
            score = min(1.0, score + 0.1)
        
        return max(0.0, score)
    
    def _determine_consensus(
        self,
        datasets: List[Dict[str, Any]],
        conflicts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Determine consensus value from datasets"""
        if not datasets:
            return {}
        
        # Start with first dataset
        consensus = datasets[0].copy()
        
        # For conflicting fields, use value from highest authority source
        for conflict in conflicts:
            field = conflict['field']
            values = conflict['values']
            
            # Find highest authority source
            best_source = None
            best_authority = 0.0
            
            for value, sources in values.items():
                for source in sources:
                    authority = self._get_authority_score(source)
                    if authority > best_authority:
                        best_authority = authority
                        best_source = source
                        consensus[field] = value
        
        return consensus
    
    def _calculate_cross_validation_confidence(
        self,
        num_datasets: int,
        consistency_score: float
    ) -> float:
        """Calculate confidence from cross-validation"""
        # Base confidence from consistency
        confidence = consistency_score * 0.7
        
        # Bonus for multiple sources
        if num_datasets >= 3:
            confidence += 0.2
        elif num_datasets >= 2:
            confidence += 0.1
        
        return min(1.0, confidence)


# Factory function
def create_evidence_validation_service() -> EvidenceValidationService:
    """Create evidence validation service"""
    return EvidenceValidationService()
