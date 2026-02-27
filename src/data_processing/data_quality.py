"""
Data quality validation and assurance utilities
"""
import logging
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re

logger = logging.getLogger(__name__)

class QualityCheckType(str, Enum):
    """Types of quality checks"""
    COMPLETENESS = "completeness"
    VALIDITY = "validity"
    CONSISTENCY = "consistency"
    ACCURACY = "accuracy"
    UNIQUENESS = "uniqueness"

class QualityLevel(str, Enum):
    """Quality levels"""
    EXCELLENT = "excellent"  # 95-100%
    GOOD = "good"           # 85-94%
    FAIR = "fair"           # 70-84%
    POOR = "poor"           # <70%

@dataclass
class QualityCheckResult:
    """Result of a quality check"""
    check_type: QualityCheckType
    field_name: str
    passed: bool
    score: float  # 0.0 to 1.0
    total_records: int
    failed_records: int
    error_details: List[str]
    recommendations: List[str]

@dataclass
class DataQualityReport:
    """Comprehensive data quality report"""
    dataset_name: str
    total_records: int
    overall_score: float
    quality_level: QualityLevel
    check_results: List[QualityCheckResult]
    summary: Dict[str, Any]
    timestamp: str

class DataQualityValidator:
    """Data quality validation utilities"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_completeness(self, data: pd.DataFrame, required_fields: List[str]) -> List[QualityCheckResult]:
        """Check data completeness"""
        results = []
        
        for field in required_fields:
            if field not in data.columns:
                result = QualityCheckResult(
                    check_type=QualityCheckType.COMPLETENESS,
                    field_name=field,
                    passed=False,
                    score=0.0,
                    total_records=len(data),
                    failed_records=len(data),
                    error_details=[f"Field '{field}' is missing from dataset"],
                    recommendations=[f"Add required field '{field}' to dataset"]
                )
                results.append(result)
                continue
            
            # Check for null/empty values
            null_count = data[field].isnull().sum()
            empty_count = (data[field] == '').sum() if data[field].dtype == 'object' else 0
            failed_records = null_count + empty_count
            
            score = 1.0 - (failed_records / len(data))
            passed = score >= 0.95  # 95% completeness threshold
            
            error_details = []
            recommendations = []
            
            if null_count > 0:
                error_details.append(f"{null_count} null values found")
                recommendations.append("Remove or impute null values")
            
            if empty_count > 0:
                error_details.append(f"{empty_count} empty string values found")
                recommendations.append("Remove or populate empty string values")
            
            result = QualityCheckResult(
                check_type=QualityCheckType.COMPLETENESS,
                field_name=field,
                passed=passed,
                score=score,
                total_records=len(data),
                failed_records=failed_records,
                error_details=error_details,
                recommendations=recommendations
            )
            results.append(result)
        
        return results
    
    def validate_drug_names(self, data: pd.DataFrame, drug_field: str) -> QualityCheckResult:
        """Validate drug name format and content"""
        error_details = []
        failed_records = 0
        
        if drug_field not in data.columns:
            return QualityCheckResult(
                check_type=QualityCheckType.VALIDITY,
                field_name=drug_field,
                passed=False,
                score=0.0,
                total_records=len(data),
                failed_records=len(data),
                error_details=[f"Field '{drug_field}' not found"],
                recommendations=[f"Add field '{drug_field}' to dataset"]
            )
        
        for idx, drug_name in enumerate(data[drug_field]):
            if pd.isna(drug_name):
                continue
            
            drug_str = str(drug_name).strip()
            
            # Check for minimum length
            if len(drug_str) < 2:
                error_details.append(f"Row {idx}: Drug name too short: '{drug_str}'")
                failed_records += 1
                continue
            
            # Check for maximum length
            if len(drug_str) > 200:
                error_details.append(f"Row {idx}: Drug name too long: '{drug_str[:50]}...'")
                failed_records += 1
                continue
            
            # Check for invalid characters (basic validation)
            if re.search(r'[<>{}[\]\\|`~]', drug_str):
                error_details.append(f"Row {idx}: Invalid characters in drug name: '{drug_str}'")
                failed_records += 1
                continue
        
        score = 1.0 - (failed_records / len(data))
        passed = score >= 0.90
        
        recommendations = []
        if failed_records > 0:
            recommendations.extend([
                "Review and clean drug name formatting",
                "Standardize drug name conventions",
                "Remove or fix invalid drug names"
            ])
        
        return QualityCheckResult(
            check_type=QualityCheckType.VALIDITY,
            field_name=drug_field,
            passed=passed,
            score=score,
            total_records=len(data),
            failed_records=failed_records,
            error_details=error_details[:10],  # Limit error details
            recommendations=recommendations
        )
    
    def validate_numeric_ranges(self, data: pd.DataFrame, field: str, 
                               min_val: Optional[float] = None, 
                               max_val: Optional[float] = None) -> QualityCheckResult:
        """Validate numeric field ranges"""
        error_details = []
        failed_records = 0
        
        if field not in data.columns:
            return QualityCheckResult(
                check_type=QualityCheckType.VALIDITY,
                field_name=field,
                passed=False,
                score=0.0,
                total_records=len(data),
                failed_records=len(data),
                error_details=[f"Field '{field}' not found"],
                recommendations=[f"Add field '{field}' to dataset"]
            )
        
        for idx, value in enumerate(data[field]):
            if pd.isna(value):
                continue
            
            try:
                num_val = float(value)
                
                if min_val is not None and num_val < min_val:
                    error_details.append(f"Row {idx}: Value {num_val} below minimum {min_val}")
                    failed_records += 1
                    continue
                
                if max_val is not None and num_val > max_val:
                    error_details.append(f"Row {idx}: Value {num_val} above maximum {max_val}")
                    failed_records += 1
                    continue
                    
            except (ValueError, TypeError):
                error_details.append(f"Row {idx}: Invalid numeric value: '{value}'")
                failed_records += 1
                continue
        
        score = 1.0 - (failed_records / len(data))
        passed = score >= 0.95
        
        recommendations = []
        if failed_records > 0:
            recommendations.extend([
                f"Review values outside expected range [{min_val}, {max_val}]",
                "Validate data source and collection methods",
                "Consider outlier detection and handling"
            ])
        
        return QualityCheckResult(
            check_type=QualityCheckType.VALIDITY,
            field_name=field,
            passed=passed,
            score=score,
            total_records=len(data),
            failed_records=failed_records,
            error_details=error_details[:10],
            recommendations=recommendations
        )
    
    def validate_duplicates(self, data: pd.DataFrame, key_fields: List[str]) -> QualityCheckResult:
        """Check for duplicate records"""
        if not all(field in data.columns for field in key_fields):
            missing = [field for field in key_fields if field not in data.columns]
            return QualityCheckResult(
                check_type=QualityCheckType.UNIQUENESS,
                field_name=','.join(key_fields),
                passed=False,
                score=0.0,
                total_records=len(data),
                failed_records=len(data),
                error_details=[f"Missing key fields: {missing}"],
                recommendations=["Add missing key fields to dataset"]
            )
        
        # Check for duplicates based on key fields
        duplicates = data.duplicated(subset=key_fields, keep=False)
        duplicate_count = duplicates.sum()
        
        score = 1.0 - (duplicate_count / len(data))
        passed = score >= 0.98  # Allow up to 2% duplicates
        
        error_details = []
        recommendations = []
        
        if duplicate_count > 0:
            error_details.append(f"{duplicate_count} duplicate records found")
            recommendations.extend([
                "Remove duplicate records",
                "Investigate data source for duplicate generation",
                "Implement deduplication logic in ETL pipeline"
            ])
        
        return QualityCheckResult(
            check_type=QualityCheckType.UNIQUENESS,
            field_name=','.join(key_fields),
            passed=passed,
            score=score,
            total_records=len(data),
            failed_records=duplicate_count,
            error_details=error_details,
            recommendations=recommendations
        )
    
    def validate_consistency(self, data: pd.DataFrame, field_mappings: Dict[str, List[str]]) -> List[QualityCheckResult]:
        """Check data consistency across related fields"""
        results = []
        
        for primary_field, related_fields in field_mappings.items():
            if primary_field not in data.columns:
                continue
            
            # Check if related fields exist
            missing_fields = [f for f in related_fields if f not in data.columns]
            if missing_fields:
                result = QualityCheckResult(
                    check_type=QualityCheckType.CONSISTENCY,
                    field_name=f"{primary_field}->{'|'.join(related_fields)}",
                    passed=False,
                    score=0.0,
                    total_records=len(data),
                    failed_records=len(data),
                    error_details=[f"Missing related fields: {missing_fields}"],
                    recommendations=["Add missing related fields"]
                )
                results.append(result)
                continue
            
            # Check consistency (example: drug names should be consistent across records)
            inconsistencies = 0
            error_details = []
            
            # Group by primary field and check if related fields are consistent
            grouped = data.groupby(primary_field)
            for name, group in grouped:
                for related_field in related_fields:
                    unique_values = group[related_field].dropna().unique()
                    if len(unique_values) > 1:
                        inconsistencies += len(group) - 1  # All but one are inconsistent
                        error_details.append(f"Inconsistent {related_field} for {primary_field}='{name}': {unique_values}")
            
            score = 1.0 - (inconsistencies / len(data))
            passed = score >= 0.95
            
            recommendations = []
            if inconsistencies > 0:
                recommendations.extend([
                    "Standardize related field values",
                    "Implement data normalization rules",
                    "Review data source consistency"
                ])
            
            result = QualityCheckResult(
                check_type=QualityCheckType.CONSISTENCY,
                field_name=f"{primary_field}->{'|'.join(related_fields)}",
                passed=passed,
                score=score,
                total_records=len(data),
                failed_records=inconsistencies,
                error_details=error_details[:5],
                recommendations=recommendations
            )
            results.append(result)
        
        return results
    
    def generate_quality_report(self, dataset_name: str, data: pd.DataFrame, 
                              validation_config: Dict[str, Any]) -> DataQualityReport:
        """Generate comprehensive data quality report"""
        all_results = []
        
        # Completeness checks
        if 'required_fields' in validation_config:
            completeness_results = self.validate_completeness(data, validation_config['required_fields'])
            all_results.extend(completeness_results)
        
        # Drug name validation
        if 'drug_field' in validation_config:
            drug_result = self.validate_drug_names(data, validation_config['drug_field'])
            all_results.append(drug_result)
        
        # Numeric range validation
        if 'numeric_fields' in validation_config:
            for field_config in validation_config['numeric_fields']:
                numeric_result = self.validate_numeric_ranges(
                    data, 
                    field_config['field'],
                    field_config.get('min_val'),
                    field_config.get('max_val')
                )
                all_results.append(numeric_result)
        
        # Duplicate validation
        if 'key_fields' in validation_config:
            duplicate_result = self.validate_duplicates(data, validation_config['key_fields'])
            all_results.append(duplicate_result)
        
        # Consistency validation
        if 'field_mappings' in validation_config:
            consistency_results = self.validate_consistency(data, validation_config['field_mappings'])
            all_results.extend(consistency_results)
        
        # Calculate overall score
        if all_results:
            overall_score = sum(result.score for result in all_results) / len(all_results)
        else:
            overall_score = 0.0
        
        # Determine quality level
        if overall_score >= 0.95:
            quality_level = QualityLevel.EXCELLENT
        elif overall_score >= 0.85:
            quality_level = QualityLevel.GOOD
        elif overall_score >= 0.70:
            quality_level = QualityLevel.FAIR
        else:
            quality_level = QualityLevel.POOR
        
        # Generate summary
        summary = {
            'total_checks': len(all_results),
            'passed_checks': sum(1 for r in all_results if r.passed),
            'failed_checks': sum(1 for r in all_results if not r.passed),
            'average_score': overall_score,
            'quality_level': quality_level.value,
            'total_failed_records': sum(r.failed_records for r in all_results),
            'recommendations_count': sum(len(r.recommendations) for r in all_results)
        }
        
        return DataQualityReport(
            dataset_name=dataset_name,
            total_records=len(data),
            overall_score=overall_score,
            quality_level=quality_level,
            check_results=all_results,
            summary=summary,
            timestamp=pd.Timestamp.now().isoformat()
        )

# Global data quality validator instance
data_quality_validator = DataQualityValidator()