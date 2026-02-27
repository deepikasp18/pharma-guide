"""
Tests for ETL pipeline
"""
import pytest
import pandas as pd
import tempfile
import os
from unittest.mock import AsyncMock, patch

from src.data_processing.etl_pipeline import (
    ETLPipeline, OnSIDESProcessor, SIDERProcessor, FAERSProcessor,
    DatasetType, IngestionResult, DatasetIngestionError
)
from src.data_processing.data_quality import DataQualityValidator, QualityCheckType
from src.data_processing.metadata_manager import MetadataManager

class TestOnSIDESProcessor:
    """Test OnSIDES dataset processor"""
    
    @pytest.mark.asyncio
    async def test_extract_valid_csv(self):
        """Test extracting valid OnSIDES CSV"""
        processor = OnSIDESProcessor()
        
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("drug_concept_name,condition_concept_name,prr,case_count\n")
            f.write("Aspirin,Headache,1.5,100\n")
            f.write("Lisinopril,Cough,2.1,50\n")
            temp_file = f.name
        
        try:
            data = await processor.extract(temp_file)
            assert len(data) == 2
            assert 'drug_concept_name' in data.columns
            assert 'condition_concept_name' in data.columns
            assert data.iloc[0]['drug_concept_name'] == 'Aspirin'
        finally:
            os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_transform_valid_data(self):
        """Test transforming OnSIDES data"""
        processor = OnSIDESProcessor()
        
        data = pd.DataFrame({
            'drug_concept_name': ['Aspirin', 'Lisinopril'],
            'condition_concept_name': ['Headache', 'Cough'],
            'prr': [1.5, 2.1],
            'case_count': [100, 50]
        })
        
        entities, errors = await processor.transform(data)
        
        assert len(entities) == 2
        assert len(errors) == 0
        
        entity = entities[0]
        assert entity['type'] == 'causes_relationship'
        assert entity['drug_name'] == 'Aspirin'
        assert entity['side_effect_name'] == 'Headache'
        assert entity['frequency'] == 1.5
        assert 'OnSIDES' in entity['evidence_sources']
    
    @pytest.mark.asyncio
    async def test_validate_entities(self):
        """Test validating OnSIDES entities"""
        processor = OnSIDESProcessor()
        
        entities = [
            {
                'drug_name': 'Aspirin',
                'side_effect_name': 'Headache',
                'frequency': 1.5,
                'confidence': 0.8
            },
            {
                'drug_name': '',  # Invalid: empty drug name
                'side_effect_name': 'Nausea',
                'frequency': 0.5,
                'confidence': 0.7
            },
            {
                'drug_name': 'Ibuprofen',
                'side_effect_name': 'Stomach upset',
                'frequency': -0.1,  # Invalid: negative frequency
                'confidence': 0.9
            }
        ]
        
        validated, errors = await processor.validate(entities)
        
        assert len(validated) == 1  # Only first entity is valid
        assert len(errors) == 2
        assert validated[0]['drug_name'] == 'Aspirin'

class TestSIDERProcessor:
    """Test SIDER dataset processor"""
    
    @pytest.mark.asyncio
    async def test_transform_sider_data(self):
        """Test transforming SIDER data"""
        processor = SIDERProcessor()
        
        data = pd.DataFrame({
            'drug_name': ['Aspirin', 'Ibuprofen'],
            'side_effect': ['Gastric irritation', 'Headache'],
            'frequency': [0.15, 0.08],
            'meddra_code': ['10017853', '10019211']
        })
        
        entities, errors = await processor.transform(data)
        
        assert len(entities) == 2
        assert len(errors) == 0
        
        entity = entities[0]
        assert entity['type'] == 'causes_relationship'
        assert entity['drug_name'] == 'Aspirin'
        assert entity['side_effect_name'] == 'Gastric irritation'
        assert entity['confidence'] == 0.8  # SIDER default confidence
        assert entity['meddra_code'] == '10017853'

class TestFAERSProcessor:
    """Test FAERS dataset processor"""
    
    @pytest.mark.asyncio
    async def test_transform_faers_data(self):
        """Test transforming FAERS data"""
        processor = FAERSProcessor()
        
        data = pd.DataFrame({
            'drug_name': ['Warfarin', 'Metformin'],
            'adverse_event': ['Bleeding', 'Nausea'],
            'frequency': [0.05, 0.12],
            'case_count': [25, 60],
            'age': [65, 45],
            'gender': ['M', 'F'],
            'weight': [75, 68]
        })
        
        entities, errors = await processor.transform(data)
        
        assert len(entities) == 2
        assert len(errors) == 0
        
        entity = entities[0]
        assert entity['type'] == 'causes_relationship'
        assert entity['drug_name'] == 'Warfarin'
        assert entity['side_effect_name'] == 'Bleeding'
        assert entity['confidence'] == 0.6  # FAERS default confidence
        assert entity['patient_demographics']['age'] == 65
        assert entity['patient_demographics']['gender'] == 'M'

class TestETLPipeline:
    """Test main ETL pipeline"""
    
    @pytest.mark.asyncio
    async def test_ingest_dataset_success(self):
        """Test successful dataset ingestion"""
        pipeline = ETLPipeline()
        
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("drug_concept_name,condition_concept_name,prr,case_count\n")
            f.write("Aspirin,Headache,1.5,100\n")
            temp_file = f.name
        
        try:
            result = await pipeline.ingest_dataset(DatasetType.ONSIDES, temp_file)
            
            assert isinstance(result, IngestionResult)
            assert result.dataset_name == DatasetType.ONSIDES.value
            assert result.records_processed == 1
            assert result.records_successful == 1
            assert result.records_failed == 0
            assert result.metadata is not None
            assert result.metadata.name == DatasetType.ONSIDES.value
        finally:
            os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_ingest_unsupported_dataset(self):
        """Test ingesting unsupported dataset type"""
        pipeline = ETLPipeline()
        
        # Use a string that's not in the supported processors
        with pytest.raises(DatasetIngestionError):
            await pipeline.ingest_dataset("unknown_dataset", "dummy_path")
    
    def test_get_supported_datasets(self):
        """Test getting supported dataset types"""
        pipeline = ETLPipeline()
        supported = pipeline.get_supported_datasets()
        
        assert DatasetType.ONSIDES in supported
        assert DatasetType.SIDER in supported
        assert DatasetType.FAERS in supported

class TestDataQualityValidator:
    """Test data quality validation"""
    
    def test_validate_completeness(self):
        """Test completeness validation"""
        validator = DataQualityValidator()
        
        data = pd.DataFrame({
            'drug_name': ['Aspirin', '', 'Ibuprofen'],  # One empty
            'side_effect': ['Headache', 'Nausea', None],  # One null
            'frequency': [0.1, 0.2, 0.3]
        })
        
        results = validator.validate_completeness(data, ['drug_name', 'side_effect', 'frequency'])
        
        assert len(results) == 3
        
        # Check drug_name result
        drug_result = next(r for r in results if r.field_name == 'drug_name')
        assert drug_result.failed_records == 1  # One empty string
        assert drug_result.score < 1.0
        
        # Check side_effect result
        se_result = next(r for r in results if r.field_name == 'side_effect')
        assert se_result.failed_records == 1  # One null
        
        # Check frequency result (should be complete)
        freq_result = next(r for r in results if r.field_name == 'frequency')
        assert freq_result.failed_records == 0
        assert freq_result.score == 1.0
    
    def test_validate_drug_names(self):
        """Test drug name validation"""
        validator = DataQualityValidator()
        
        data = pd.DataFrame({
            'drug_name': [
                'Aspirin',           # Valid
                'A',                 # Too short
                'X' * 250,          # Too long
                'Drug<script>',      # Invalid characters
                'Lisinopril'         # Valid
            ]
        })
        
        result = validator.validate_drug_names(data, 'drug_name')
        
        assert result.field_name == 'drug_name'
        assert result.failed_records == 3  # Three invalid names
        assert result.score == 0.4  # 2/5 valid
        assert not result.passed
    
    def test_validate_numeric_ranges(self):
        """Test numeric range validation"""
        validator = DataQualityValidator()
        
        data = pd.DataFrame({
            'frequency': [0.1, 0.5, -0.1, 1.5, 0.8]  # Two out of range [0, 1]
        })
        
        result = validator.validate_numeric_ranges(data, 'frequency', min_val=0.0, max_val=1.0)
        
        assert result.field_name == 'frequency'
        assert result.failed_records == 2  # -0.1 and 1.5 are out of range
        assert result.score == 0.6  # 3/5 valid
    
    def test_validate_duplicates(self):
        """Test duplicate validation"""
        validator = DataQualityValidator()
        
        data = pd.DataFrame({
            'drug_name': ['Aspirin', 'Aspirin', 'Ibuprofen', 'Aspirin'],
            'side_effect': ['Headache', 'Headache', 'Nausea', 'Headache']
        })
        
        result = validator.validate_duplicates(data, ['drug_name', 'side_effect'])
        
        assert result.field_name == 'drug_name,side_effect'
        assert result.failed_records == 3  # Three duplicate records (Aspirin-Headache appears 3 times)
        assert result.score == 0.25  # 1/4 unique

class TestMetadataManager:
    """Test metadata management"""
    
    def test_save_and_load_metadata(self):
        """Test saving and loading metadata"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = MetadataManager(temp_dir)
            
            from src.knowledge_graph.models import DatasetMetadata
            metadata = DatasetMetadata(
                name="test_dataset",
                version="1.0",
                last_updated=pd.Timestamp.now(),
                record_count=1000,
                entity_types=["drug", "side_effect"],
                relationship_types=["CAUSES"],
                quality_score=0.95,
                authority_level="high",
                description="Test dataset"
            )
            
            # Save metadata
            manager.save_metadata(metadata)
            
            # Load metadata
            loaded = manager.load_metadata("test_dataset")
            
            assert loaded is not None
            assert loaded.name == "test_dataset"
            assert loaded.version == "1.0"
            assert loaded.record_count == 1000
            assert loaded.quality_score == 0.95
    
    def test_list_datasets(self):
        """Test listing datasets"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = MetadataManager(temp_dir)
            
            # Create some test metadata files
            from src.knowledge_graph.models import DatasetMetadata
            
            for name in ["dataset1", "dataset2", "dataset3"]:
                metadata = DatasetMetadata(
                    name=name,
                    version="1.0",
                    last_updated=pd.Timestamp.now(),
                    record_count=100,
                    entity_types=["drug"],
                    relationship_types=["CAUSES"],
                    quality_score=0.8,
                    authority_level="medium"
                )
                manager.save_metadata(metadata)
            
            datasets = manager.list_datasets()
            assert len(datasets) == 3
            assert "dataset1" in datasets
            assert "dataset2" in datasets
            assert "dataset3" in datasets