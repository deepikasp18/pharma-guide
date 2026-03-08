"""
ETL Pipeline for medical dataset ingestion
"""
import asyncio
import logging
import pandas as pd
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

from src.knowledge_graph.models import DatasetMetadata, DrugEntity, SideEffectEntity

logger = logging.getLogger(__name__)

class DatasetType(str, Enum):
    """Supported dataset types"""
    ONSIDES = "onsides"
    SIDER = "sider"
    FAERS = "faers"
    DRUGBANK = "drugbank"
    DDINTER = "ddinter"
    DRUGS_FDA = "drugs_fda"

@dataclass
class IngestionResult:
    """Result of dataset ingestion"""
    dataset_name: str
    records_processed: int
    records_successful: int
    records_failed: int
    errors: List[str]
    processing_time: float
    metadata: Optional[DatasetMetadata] = None

class DatasetIngestionError(Exception):
    """Dataset ingestion error"""
    pass

class BaseDatasetProcessor(ABC):
    """Base class for dataset processors"""
    
    def __init__(self, dataset_type: DatasetType):
        self.dataset_type = dataset_type
        self.logger = logging.getLogger(f"{__name__}.{dataset_type}")
    
    @abstractmethod
    async def extract(self, source_path: str) -> pd.DataFrame:
        """Extract data from source"""
        pass
    
    @abstractmethod
    async def transform(self, data: pd.DataFrame) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Transform data into knowledge graph entities"""
        pass
    
    @abstractmethod
    async def validate(self, entities: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Validate transformed entities"""
        pass
    
    async def process(self, source_path: str) -> IngestionResult:
        """Process dataset from source to validated entities"""
        start_time = datetime.utcnow()
        errors = []
        
        try:
            # Extract
            self.logger.info(f"Extracting data from {source_path}")
            raw_data = await self.extract(source_path)
            
            # Transform
            self.logger.info(f"Transforming {len(raw_data)} records")
            entities, transform_errors = await self.transform(raw_data)
            errors.extend(transform_errors)
            
            # Validate
            self.logger.info(f"Validating {len(entities)} entities")
            validated_entities, validation_errors = await self.validate(entities)
            errors.extend(validation_errors)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            result = IngestionResult(
                dataset_name=self.dataset_type.value,
                records_processed=len(raw_data),
                records_successful=len(validated_entities),
                records_failed=len(raw_data) - len(validated_entities),
                errors=errors,
                processing_time=processing_time
            )
            
            self.logger.info(f"Processing complete: {result.records_successful}/{result.records_processed} successful")
            return result
            
        except Exception as e:
            self.logger.error(f"Processing failed: {e}")
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            return IngestionResult(
                dataset_name=self.dataset_type.value,
                records_processed=0,
                records_successful=0,
                records_failed=0,
                errors=[str(e)],
                processing_time=processing_time
            )

class OnSIDESProcessor(BaseDatasetProcessor):
    """OnSIDES dataset processor"""
    
    def __init__(self):
        super().__init__(DatasetType.ONSIDES)
    
    async def extract(self, source_path: str) -> pd.DataFrame:
        """Extract OnSIDES data"""
        try:
            # OnSIDES is typically a CSV file with drug-ADE pairs
            data = pd.read_csv(source_path)
            self.logger.info(f"Extracted {len(data)} records from OnSIDES")
            return data
        except Exception as e:
            raise DatasetIngestionError(f"Failed to extract OnSIDES data: {e}")
    
    async def transform(self, data: pd.DataFrame) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Transform OnSIDES data to knowledge graph entities"""
        entities = []
        errors = []
        
        try:
            # Expected columns: drug_concept_name, condition_concept_name, prr, prr_95_percent_lower_bound, etc.
            required_columns = ['drug_concept_name', 'condition_concept_name', 'prr']
            
            if not all(col in data.columns for col in required_columns):
                missing = [col for col in required_columns if col not in data.columns]
                raise DatasetIngestionError(f"Missing required columns: {missing}")
            
            for idx, row in data.iterrows():
                try:
                    # Create drug-side effect relationship
                    entity = {
                        'type': 'causes_relationship',
                        'drug_name': str(row['drug_concept_name']).strip(),
                        'side_effect_name': str(row['condition_concept_name']).strip(),
                        'frequency': float(row.get('prr', 0.0)),
                        'confidence': float(row.get('prr_95_percent_lower_bound', 0.0)),
                        'evidence_sources': ['OnSIDES'],
                        'patient_count': int(row.get('case_count', 0)) if 'case_count' in row else None,
                        'statistical_significance': float(row.get('p_value', 1.0)) if 'p_value' in row else None,
                        'source_dataset': 'OnSIDES'
                    }
                    entities.append(entity)
                    
                except Exception as e:
                    errors.append(f"Row {idx}: {str(e)}")
                    continue
            
            self.logger.info(f"Transformed {len(entities)} OnSIDES entities")
            return entities, errors
            
        except Exception as e:
            raise DatasetIngestionError(f"Failed to transform OnSIDES data: {e}")
    
    async def validate(self, entities: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Validate OnSIDES entities"""
        validated = []
        errors = []
        
        for i, entity in enumerate(entities):
            try:
                # Validate required fields
                if not entity.get('drug_name') or not entity.get('side_effect_name'):
                    errors.append(f"Entity {i}: Missing drug or side effect name")
                    continue
                
                # Validate frequency range
                frequency = entity.get('frequency', 0.0)
                if frequency < 0:
                    errors.append(f"Entity {i}: Invalid frequency {frequency}")
                    continue
                
                # Validate confidence range
                confidence = entity.get('confidence', 0.0)
                if confidence < 0 or confidence > 1:
                    entity['confidence'] = max(0.0, min(1.0, confidence))
                
                validated.append(entity)
                
            except Exception as e:
                errors.append(f"Entity {i}: Validation error - {str(e)}")
                continue
        
        return validated, errors

class SIDERProcessor(BaseDatasetProcessor):
    """SIDER dataset processor"""
    
    def __init__(self):
        super().__init__(DatasetType.SIDER)
    
    async def extract(self, source_path: str) -> pd.DataFrame:
        """Extract SIDER data"""
        try:
            # SIDER typically comes as multiple files, we'll assume a consolidated CSV
            data = pd.read_csv(source_path)
            self.logger.info(f"Extracted {len(data)} records from SIDER")
            return data
        except Exception as e:
            raise DatasetIngestionError(f"Failed to extract SIDER data: {e}")
    
    async def transform(self, data: pd.DataFrame) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Transform SIDER data to knowledge graph entities"""
        entities = []
        errors = []
        
        try:
            # Expected columns: drug_name, side_effect, frequency, meddra_code
            for idx, row in data.iterrows():
                try:
                    entity = {
                        'type': 'causes_relationship',
                        'drug_name': str(row['drug_name']).strip(),
                        'side_effect_name': str(row['side_effect']).strip(),
                        'frequency': float(row.get('frequency', 0.0)),
                        'confidence': 0.8,  # SIDER has high confidence as it's from labels
                        'evidence_sources': ['SIDER'],
                        'meddra_code': str(row.get('meddra_code', '')),
                        'source_dataset': 'SIDER'
                    }
                    entities.append(entity)
                    
                except Exception as e:
                    errors.append(f"Row {idx}: {str(e)}")
                    continue
            
            return entities, errors
            
        except Exception as e:
            raise DatasetIngestionError(f"Failed to transform SIDER data: {e}")
    
    async def validate(self, entities: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Validate SIDER entities"""
        validated = []
        errors = []
        
        for i, entity in enumerate(entities):
            try:
                # Basic validation similar to OnSIDES
                if not entity.get('drug_name') or not entity.get('side_effect_name'):
                    errors.append(f"Entity {i}: Missing drug or side effect name")
                    continue
                
                # Validate MedDRA code format if present
                meddra_code = entity.get('meddra_code', '')
                if meddra_code and not meddra_code.isdigit():
                    errors.append(f"Entity {i}: Invalid MedDRA code format")
                    continue
                
                validated.append(entity)
                
            except Exception as e:
                errors.append(f"Entity {i}: Validation error - {str(e)}")
                continue
        
        return validated, errors

class FAERSProcessor(BaseDatasetProcessor):
    """FAERS dataset processor"""
    
    def __init__(self):
        super().__init__(DatasetType.FAERS)
    
    async def extract(self, source_path: str) -> pd.DataFrame:
        """Extract FAERS data"""
        try:
            # FAERS data is typically in multiple files, we'll assume processed CSV
            data = pd.read_csv(source_path)
            self.logger.info(f"Extracted {len(data)} records from FAERS")
            return data
        except Exception as e:
            raise DatasetIngestionError(f"Failed to extract FAERS data: {e}")
    
    async def transform(self, data: pd.DataFrame) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Transform FAERS data to knowledge graph entities"""
        entities = []
        errors = []
        
        try:
            for idx, row in data.iterrows():
                try:
                    entity = {
                        'type': 'causes_relationship',
                        'drug_name': str(row['drug_name']).strip(),
                        'side_effect_name': str(row['adverse_event']).strip(),
                        'frequency': float(row.get('frequency', 0.0)),
                        'confidence': 0.6,  # FAERS has lower confidence due to reporting bias
                        'evidence_sources': ['FAERS'],
                        'patient_count': int(row.get('case_count', 0)) if 'case_count' in row else None,
                        'patient_demographics': {
                            'age': row.get('age'),
                            'gender': row.get('gender'),
                            'weight': row.get('weight')
                        },
                        'source_dataset': 'FAERS'
                    }
                    entities.append(entity)
                    
                except Exception as e:
                    errors.append(f"Row {idx}: {str(e)}")
                    continue
            
            return entities, errors
            
        except Exception as e:
            raise DatasetIngestionError(f"Failed to transform FAERS data: {e}")
    
    async def validate(self, entities: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Validate FAERS entities"""
        validated = []
        errors = []
        
        for i, entity in enumerate(entities):
            try:
                if not entity.get('drug_name') or not entity.get('side_effect_name'):
                    errors.append(f"Entity {i}: Missing drug or side effect name")
                    continue
                
                # Validate patient demographics if present
                demographics = entity.get('patient_demographics', {})
                if demographics.get('age') and (demographics['age'] < 0 or demographics['age'] > 150):
                    errors.append(f"Entity {i}: Invalid age")
                    continue
                
                validated.append(entity)
                
            except Exception as e:
                errors.append(f"Entity {i}: Validation error - {str(e)}")
                continue
        
        return validated, errors

class ETLPipeline:
    """Main ETL pipeline coordinator"""
    
    def __init__(self):
        self.processors = {
            DatasetType.ONSIDES: OnSIDESProcessor(),
            DatasetType.SIDER: SIDERProcessor(),
            DatasetType.FAERS: FAERSProcessor(),
            # Add other processors as needed
        }
        self.logger = logging.getLogger(__name__)
    
    async def ingest_dataset(self, dataset_type: Union[DatasetType, str], source_path: str) -> IngestionResult:
        """Ingest a single dataset"""
        if dataset_type not in self.processors:
            raise DatasetIngestionError(f"Unsupported dataset type: {dataset_type}")
        
        processor = self.processors[dataset_type]
        self.logger.info(f"Starting ingestion of {dataset_type.value} from {source_path}")
        
        result = await processor.process(source_path)
        
        # Create metadata
        result.metadata = DatasetMetadata(
            name=dataset_type.value,
            version="1.0",
            last_updated=datetime.utcnow(),
            record_count=result.records_successful,
            entity_types=["drug", "side_effect", "causes_relationship"],
            relationship_types=["CAUSES"],
            quality_score=result.records_successful / max(result.records_processed, 1),
            authority_level="high" if dataset_type in [DatasetType.SIDER, DatasetType.DRUGBANK] else "medium",
            description=f"Processed {dataset_type.value} dataset"
        )
        
        return result
    
    async def ingest_multiple_datasets(self, dataset_configs: List[Tuple[DatasetType, str]]) -> List[IngestionResult]:
        """Ingest multiple datasets concurrently"""
        tasks = []
        
        for dataset_type, source_path in dataset_configs:
            task = asyncio.create_task(self.ingest_dataset(dataset_type, source_path))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                dataset_type, source_path = dataset_configs[i]
                error_result = IngestionResult(
                    dataset_name=dataset_type.value,
                    records_processed=0,
                    records_successful=0,
                    records_failed=0,
                    errors=[str(result)],
                    processing_time=0.0
                )
                final_results.append(error_result)
            else:
                final_results.append(result)
        
        return final_results
    
    def get_supported_datasets(self) -> List[DatasetType]:
        """Get list of supported dataset types"""
        return list(self.processors.keys())

# Global ETL pipeline instance
etl_pipeline = ETLPipeline()