"""
Dataset metadata tracking and versioning
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import asdict

from src.knowledge_graph.models import DatasetMetadata

logger = logging.getLogger(__name__)

class MetadataManager:
    """Manages dataset metadata and versioning"""
    
    def __init__(self, metadata_dir: str = "data/metadata"):
        self.metadata_dir = Path(metadata_dir)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def save_metadata(self, metadata: DatasetMetadata) -> None:
        """Save dataset metadata to file"""
        try:
            metadata_file = self.metadata_dir / f"{metadata.name}_metadata.json"
            
            # Convert to dictionary
            metadata_dict = {
                'name': metadata.name,
                'version': metadata.version,
                'last_updated': metadata.last_updated.isoformat(),
                'record_count': metadata.record_count,
                'entity_types': metadata.entity_types,
                'relationship_types': metadata.relationship_types,
                'quality_score': metadata.quality_score,
                'authority_level': metadata.authority_level,
                'license': metadata.license,
                'description': metadata.description
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata_dict, f, indent=2)
            
            self.logger.info(f"Saved metadata for {metadata.name} to {metadata_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save metadata for {metadata.name}: {e}")
            raise
    
    def load_metadata(self, dataset_name: str) -> Optional[DatasetMetadata]:
        """Load dataset metadata from file"""
        try:
            metadata_file = self.metadata_dir / f"{dataset_name}_metadata.json"
            
            if not metadata_file.exists():
                self.logger.warning(f"Metadata file not found for {dataset_name}")
                return None
            
            with open(metadata_file, 'r') as f:
                metadata_dict = json.load(f)
            
            # Convert back to DatasetMetadata
            metadata = DatasetMetadata(
                name=metadata_dict['name'],
                version=metadata_dict['version'],
                last_updated=datetime.fromisoformat(metadata_dict['last_updated']),
                record_count=metadata_dict['record_count'],
                entity_types=metadata_dict['entity_types'],
                relationship_types=metadata_dict['relationship_types'],
                quality_score=metadata_dict['quality_score'],
                authority_level=metadata_dict['authority_level'],
                license=metadata_dict.get('license'),
                description=metadata_dict.get('description')
            )
            
            self.logger.info(f"Loaded metadata for {dataset_name}")
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to load metadata for {dataset_name}: {e}")
            return None
    
    def list_datasets(self) -> List[str]:
        """List all datasets with metadata"""
        try:
            datasets = []
            for metadata_file in self.metadata_dir.glob("*_metadata.json"):
                dataset_name = metadata_file.stem.replace("_metadata", "")
                datasets.append(dataset_name)
            
            return sorted(datasets)
            
        except Exception as e:
            self.logger.error(f"Failed to list datasets: {e}")
            return []
    
    def get_dataset_info(self, dataset_name: str) -> Optional[Dict[str, Any]]:
        """Get basic dataset information"""
        metadata = self.load_metadata(dataset_name)
        if not metadata:
            return None
        
        return {
            'name': metadata.name,
            'version': metadata.version,
            'last_updated': metadata.last_updated.isoformat(),
            'record_count': metadata.record_count,
            'quality_score': metadata.quality_score,
            'authority_level': metadata.authority_level,
            'description': metadata.description
        }
    
    def update_metadata(self, dataset_name: str, updates: Dict[str, Any]) -> bool:
        """Update specific fields in dataset metadata"""
        try:
            metadata = self.load_metadata(dataset_name)
            if not metadata:
                self.logger.error(f"Cannot update metadata for non-existent dataset: {dataset_name}")
                return False
            
            # Update fields
            for field, value in updates.items():
                if hasattr(metadata, field):
                    setattr(metadata, field, value)
                else:
                    self.logger.warning(f"Unknown metadata field: {field}")
            
            # Update timestamp
            metadata.last_updated = datetime.utcnow()
            
            # Save updated metadata
            self.save_metadata(metadata)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update metadata for {dataset_name}: {e}")
            return False
    
    def delete_metadata(self, dataset_name: str) -> bool:
        """Delete dataset metadata"""
        try:
            metadata_file = self.metadata_dir / f"{dataset_name}_metadata.json"
            
            if metadata_file.exists():
                metadata_file.unlink()
                self.logger.info(f"Deleted metadata for {dataset_name}")
                return True
            else:
                self.logger.warning(f"Metadata file not found for {dataset_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to delete metadata for {dataset_name}: {e}")
            return False
    
    def create_version_snapshot(self, dataset_name: str) -> str:
        """Create a versioned snapshot of dataset metadata"""
        try:
            metadata = self.load_metadata(dataset_name)
            if not metadata:
                raise ValueError(f"Dataset {dataset_name} not found")
            
            # Create version identifier
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            version_id = f"{metadata.version}_{timestamp}"
            
            # Save versioned metadata
            version_file = self.metadata_dir / f"{dataset_name}_v{version_id}_metadata.json"
            
            metadata_dict = {
                'name': metadata.name,
                'version': version_id,
                'original_version': metadata.version,
                'snapshot_timestamp': timestamp,
                'last_updated': metadata.last_updated.isoformat(),
                'record_count': metadata.record_count,
                'entity_types': metadata.entity_types,
                'relationship_types': metadata.relationship_types,
                'quality_score': metadata.quality_score,
                'authority_level': metadata.authority_level,
                'license': metadata.license,
                'description': metadata.description
            }
            
            with open(version_file, 'w') as f:
                json.dump(metadata_dict, f, indent=2)
            
            self.logger.info(f"Created version snapshot {version_id} for {dataset_name}")
            return version_id
            
        except Exception as e:
            self.logger.error(f"Failed to create version snapshot for {dataset_name}: {e}")
            raise
    
    def list_versions(self, dataset_name: str) -> List[str]:
        """List all versions of a dataset"""
        try:
            versions = []
            pattern = f"{dataset_name}_v*_metadata.json"
            
            for version_file in self.metadata_dir.glob(pattern):
                # Extract version from filename
                filename = version_file.stem
                version_part = filename.replace(f"{dataset_name}_v", "").replace("_metadata", "")
                versions.append(version_part)
            
            return sorted(versions, reverse=True)  # Most recent first
            
        except Exception as e:
            self.logger.error(f"Failed to list versions for {dataset_name}: {e}")
            return []
    
    def compare_versions(self, dataset_name: str, version1: str, version2: str) -> Dict[str, Any]:
        """Compare two versions of a dataset"""
        try:
            # Load version metadata
            v1_file = self.metadata_dir / f"{dataset_name}_v{version1}_metadata.json"
            v2_file = self.metadata_dir / f"{dataset_name}_v{version2}_metadata.json"
            
            if not v1_file.exists() or not v2_file.exists():
                raise ValueError("One or both versions not found")
            
            with open(v1_file, 'r') as f:
                v1_data = json.load(f)
            
            with open(v2_file, 'r') as f:
                v2_data = json.load(f)
            
            # Compare key metrics
            comparison = {
                'dataset_name': dataset_name,
                'version1': version1,
                'version2': version2,
                'record_count_change': v2_data['record_count'] - v1_data['record_count'],
                'quality_score_change': v2_data['quality_score'] - v1_data['quality_score'],
                'entity_types_added': list(set(v2_data['entity_types']) - set(v1_data['entity_types'])),
                'entity_types_removed': list(set(v1_data['entity_types']) - set(v2_data['entity_types'])),
                'relationship_types_added': list(set(v2_data['relationship_types']) - set(v1_data['relationship_types'])),
                'relationship_types_removed': list(set(v1_data['relationship_types']) - set(v2_data['relationship_types'])),
                'authority_level_changed': v1_data['authority_level'] != v2_data['authority_level']
            }
            
            return comparison
            
        except Exception as e:
            self.logger.error(f"Failed to compare versions for {dataset_name}: {e}")
            raise
    
    def get_metadata_summary(self) -> Dict[str, Any]:
        """Get summary of all dataset metadata"""
        try:
            datasets = self.list_datasets()
            summary = {
                'total_datasets': len(datasets),
                'datasets': [],
                'total_records': 0,
                'average_quality_score': 0.0,
                'authority_levels': {'high': 0, 'medium': 0, 'low': 0}
            }
            
            quality_scores = []
            
            for dataset_name in datasets:
                info = self.get_dataset_info(dataset_name)
                if info:
                    summary['datasets'].append(info)
                    summary['total_records'] += info['record_count']
                    quality_scores.append(info['quality_score'])
                    
                    authority_level = info['authority_level']
                    if authority_level in summary['authority_levels']:
                        summary['authority_levels'][authority_level] += 1
            
            if quality_scores:
                summary['average_quality_score'] = sum(quality_scores) / len(quality_scores)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to generate metadata summary: {e}")
            return {'error': str(e)}

# Global metadata manager instance
metadata_manager = MetadataManager()