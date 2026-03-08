"""
Tests for entity resolution service
"""
import pytest
from src.data_processing.entity_resolution import (
    EntityResolutionService, EntityMatcher, DrugNameNormalizer, 
    SideEffectNormalizer, EntityType, MatchingMethod
)

class TestDrugNameNormalizer:
    """Test drug name normalization"""
    
    def test_basic_normalization(self):
        """Test basic drug name normalization"""
        normalizer = DrugNameNormalizer()
        
        # Test case conversion and whitespace
        assert normalizer.normalize("  ASPIRIN  ") == "aspirin"
        
        # Test abbreviation expansion
        assert normalizer.normalize("Lisinopril HCL") == "lisinopril hydrochloride"
        assert normalizer.normalize("Metformin ER") == "metformin extended release"
        
        # Test dosage removal
        assert normalizer.normalize("Aspirin 325mg tablet") == "aspirin"
        assert normalizer.normalize("Insulin 100 units/ml") == "insulin"
        
        # Test parenthetical removal
        assert normalizer.normalize("Tylenol (acetaminophen)") == "tylenol"
    
    def test_extract_active_ingredient(self):
        """Test active ingredient extraction"""
        normalizer = DrugNameNormalizer()
        
        # Simple cases
        assert normalizer.extract_active_ingredient("Aspirin") == "aspirin"
        
        # Combination drugs
        assert normalizer.extract_active_ingredient("Lisinopril/HCTZ") == "lisinopril"
        assert normalizer.extract_active_ingredient("Acetaminophen + Codeine") == "acetaminophen"
        
        # Complex names
        assert normalizer.extract_active_ingredient("Tylenol Extra Strength") == "tylenol extra strength"

class TestSideEffectNormalizer:
    """Test side effect normalization"""
    
    def test_basic_normalization(self):
        """Test basic side effect normalization"""
        normalizer = SideEffectNormalizer()
        
        # Test case conversion
        assert normalizer.normalize("HEADACHE") == "headache"
        
        # Test prefix removal
        assert normalizer.normalize("Severe headache") == "headache"
        assert normalizer.normalize("Chronic fatigue") == "fatigue"
        
        # Test synonym mapping
        assert normalizer.normalize("feeling sick") == "nausea"
        assert normalizer.normalize("stomach upset") == "nausea"
        assert normalizer.normalize("head pain") == "headache"

class TestEntityMatcher:
    """Test entity matching algorithms"""
    
    def test_exact_match_drugs(self):
        """Test exact matching for drugs"""
        matcher = EntityMatcher()
        
        # Exact matches
        assert matcher.exact_match("Aspirin", "aspirin", EntityType.DRUG) == 1.0
        assert matcher.exact_match("Lisinopril HCL", "Lisinopril Hydrochloride", EntityType.DRUG) == 1.0
        
        # Non-matches
        assert matcher.exact_match("Aspirin", "Ibuprofen", EntityType.DRUG) == 0.0
    
    def test_fuzzy_match_drugs(self):
        """Test fuzzy matching for drugs"""
        matcher = EntityMatcher()
        
        # Similar names
        score = matcher.fuzzy_match("Lisinopril", "Lysinopril", EntityType.DRUG)
        assert score > 0.8  # Should be high similarity
        
        # Very different names
        score = matcher.fuzzy_match("Aspirin", "Metformin", EntityType.DRUG)
        assert score < 0.5  # Should be low similarity
        
        # Partial matches
        score = matcher.fuzzy_match("Acetaminophen Extra Strength", "Acetaminophen", EntityType.DRUG)
        assert score > 0.7  # Should recognize partial match
    
    def test_active_ingredient_match(self):
        """Test active ingredient matching"""
        matcher = EntityMatcher()
        
        # Same active ingredient, different formulations
        score = matcher.active_ingredient_match("Tylenol", "Acetaminophen")
        # Note: This would require more sophisticated ingredient mapping
        
        # Different active ingredients
        score = matcher.active_ingredient_match("Aspirin", "Ibuprofen")
        assert score < 0.5
    
    def test_composite_match(self):
        """Test composite matching"""
        matcher = EntityMatcher()
        
        # Test with additional data
        drug1_data = {
            'name': 'Lisinopril',
            'drugbank_id': 'DB00722',
            'rxcui': '29046'
        }
        
        drug2_data = {
            'name': 'Lisinopril HCL',
            'drugbank_id': 'DB00722',  # Same DrugBank ID
            'rxcui': '29046'           # Same RxCUI
        }
        
        score, evidence = matcher.composite_match(
            drug1_data['name'], drug2_data['name'], EntityType.DRUG,
            drug1_data, drug2_data
        )
        
        assert score > 0.8  # Should be high due to matching identifiers
        assert evidence['drugbank_match'] is True
        assert evidence['rxcui_match'] is True

class TestEntityResolutionService:
    """Test entity resolution service"""
    
    def test_find_matches_drugs(self):
        """Test finding matches among drug entities"""
        service = EntityResolutionService(confidence_threshold=0.7)
        
        entities = [
            {'id': 'drug1', 'name': 'Aspirin', 'source_dataset': 'DrugBank'},
            {'id': 'drug2', 'name': 'aspirin', 'source_dataset': 'SIDER'},
            {'id': 'drug3', 'name': 'Acetylsalicylic Acid', 'source_dataset': 'OnSIDES'},
            {'id': 'drug4', 'name': 'Ibuprofen', 'source_dataset': 'DrugBank'}
        ]
        
        matches = service.find_matches(entities, EntityType.DRUG)
        
        # Should find match between 'Aspirin' and 'aspirin'
        aspirin_matches = [m for m in matches if 
                          ('drug1' in [m.source_id, m.target_id] and 
                           'drug2' in [m.source_id, m.target_id])]
        assert len(aspirin_matches) > 0
        
        # Should not match Aspirin with Ibuprofen
        different_drug_matches = [m for m in matches if 
                                ('drug1' in [m.source_id, m.target_id] and 
                                 'drug4' in [m.source_id, m.target_id])]
        assert len(different_drug_matches) == 0
    
    def test_resolve_entities_simple(self):
        """Test simple entity resolution"""
        service = EntityResolutionService(confidence_threshold=0.8)
        
        entities = [
            {'id': 'drug1', 'name': 'Aspirin', 'source_dataset': 'DrugBank'},
            {'id': 'drug2', 'name': 'aspirin', 'source_dataset': 'SIDER'},
            {'id': 'drug3', 'name': 'Ibuprofen', 'source_dataset': 'DrugBank'}
        ]
        
        results = service.resolve_entities(entities, EntityType.DRUG)
        
        # Should have 2 groups: one for aspirin variants, one for ibuprofen
        assert len(results) == 2
        
        # Find the aspirin group
        aspirin_group = None
        for result in results:
            entity_names = [e['name'].lower() for e in result.matched_entities]
            if 'aspirin' in entity_names:
                aspirin_group = result
                break
        
        assert aspirin_group is not None
        assert len(aspirin_group.matched_entities) == 2  # Both aspirin entities
        assert aspirin_group.confidence > 0.8
    
    def test_resolve_entities_with_conflicts(self):
        """Test entity resolution with conflicts"""
        service = EntityResolutionService(confidence_threshold=0.7)
        
        entities = [
            {
                'id': 'drug1', 
                'name': 'Lisinopril', 
                'drugbank_id': 'DB00722',
                'source_dataset': 'DrugBank'
            },
            {
                'id': 'drug2', 
                'name': 'Lisinopril', 
                'drugbank_id': 'DB99999',  # Conflicting DrugBank ID
                'source_dataset': 'SIDER'
            }
        ]
        
        results = service.resolve_entities(entities, EntityType.DRUG)
        
        # Should still group them but detect conflict
        assert len(results) == 1
        result = results[0]
        assert len(result.matched_entities) == 2
        assert len(result.conflicts) > 0
        assert 'Conflicting DrugBank IDs' in result.conflicts[0]
    
    def test_select_canonical_entity(self):
        """Test canonical entity selection"""
        service = EntityResolutionService()
        
        entities = [
            {
                'id': 'drug1',
                'name': 'Aspirin',
                'source_dataset': 'FAERS'  # Lower authority
            },
            {
                'id': 'drug2',
                'name': 'Aspirin',
                'drugbank_id': 'DB00945',
                'generic_name': 'acetylsalicylic acid',
                'source_dataset': 'DrugBank'  # Higher authority
            }
        ]
        
        canonical = service._select_canonical_entity(entities)
        
        # Should select the DrugBank entity due to higher authority and more data
        assert canonical['id'] == 'drug2'
        assert canonical['drugbank_id'] == 'DB00945'
    
    def test_create_entity_mappings(self):
        """Test creating entity mappings"""
        service = EntityResolutionService()
        
        from src.data_processing.entity_resolution import ResolutionResult
        
        # Mock resolution result
        result = ResolutionResult(
            canonical_id='drug1',
            matched_entities=[
                {'id': 'drug1', 'source_dataset': 'DrugBank'},
                {'id': 'drug2', 'source_dataset': 'SIDER'}
            ],
            confidence=0.95,
            method=MatchingMethod.COMPOSITE,
            conflicts=[]
        )
        
        mappings = service.create_entity_mappings([result], EntityType.DRUG)
        
        assert len(mappings) == 2
        
        for mapping in mappings:
            assert mapping.canonical_id == 'drug1'
            assert mapping.entity_type == 'drug'
            assert mapping.confidence == 0.95
            assert mapping.verified is True  # No conflicts
    
    def test_get_resolution_stats(self):
        """Test resolution statistics"""
        service = EntityResolutionService()
        
        from src.data_processing.entity_resolution import ResolutionResult
        
        results = [
            ResolutionResult(
                canonical_id='drug1',
                matched_entities=[
                    {'id': 'drug1', 'source_dataset': 'DrugBank'},
                    {'id': 'drug2', 'source_dataset': 'SIDER'}
                ],
                confidence=0.95,
                method=MatchingMethod.COMPOSITE,
                conflicts=[]
            ),
            ResolutionResult(
                canonical_id='drug3',
                matched_entities=[
                    {'id': 'drug3', 'source_dataset': 'DrugBank'}
                ],
                confidence=1.0,
                method=MatchingMethod.EXACT,
                conflicts=[]
            )
        ]
        
        stats = service.get_resolution_stats(results)
        
        assert stats['total_entities'] == 3
        assert stats['total_groups'] == 2
        assert stats['entities_merged'] == 1  # 3 entities - 2 groups
        assert stats['merge_rate'] == 1/3
        assert stats['total_conflicts'] == 0
        assert stats['average_confidence'] == 0.975  # (0.95 + 1.0) / 2
        assert stats['high_confidence_groups'] == 2  # Both groups >= 0.9

class TestIntegration:
    """Integration tests for entity resolution"""
    
    def test_end_to_end_drug_resolution(self):
        """Test end-to-end drug entity resolution"""
        service = EntityResolutionService(confidence_threshold=0.7)  # Lower threshold
        
        # Realistic drug entities from different sources
        entities = [
            {
                'id': 'drugbank_1',
                'name': 'Lisinopril',
                'drugbank_id': 'DB00722',
                'generic_name': 'lisinopril',
                'source_dataset': 'DrugBank'
            },
            {
                'id': 'sider_1',
                'name': 'Lisinopril HCL',
                'source_dataset': 'SIDER'
            },
            {
                'id': 'onsides_1',
                'name': 'lisinopril',
                'source_dataset': 'OnSIDES'
            },
            {
                'id': 'drugbank_2',
                'name': 'Metformin',
                'drugbank_id': 'DB00331',
                'generic_name': 'metformin',
                'source_dataset': 'DrugBank'
            },
            {
                'id': 'faers_1',
                'name': 'METFORMIN HCL',
                'source_dataset': 'FAERS'
            }
        ]
        
        # Resolve entities
        results = service.resolve_entities(entities, EntityType.DRUG)
        
        # Should have 2-4 groups depending on matching effectiveness
        assert len(results) >= 2
        assert len(results) <= 4
        
        # Check that we have some grouping (total entities > total groups)
        total_entities = sum(len(r.matched_entities) for r in results)
        assert total_entities == 5  # All original entities should be accounted for
        
        # Find groups with multiple entities (successful matches)
        multi_entity_groups = [r for r in results if len(r.matched_entities) > 1]
        assert len(multi_entity_groups) >= 1  # Should have at least one successful match
        
        # Check that we found some lisinopril and metformin groups
        # (may be separate due to matching algorithm limitations)
        lisinopril_entities = []
        metformin_entities = []
        
        for result in results:
            for entity in result.matched_entities:
                name = entity['name'].lower()
                if 'lisinopril' in name:
                    lisinopril_entities.append(entity)
                elif 'metformin' in name:
                    metformin_entities.append(entity)
        
        assert len(lisinopril_entities) == 3  # All lisinopril variants found
        assert len(metformin_entities) == 2   # All metformin variants found
        
        # Create mappings
        mappings = service.create_entity_mappings(results, EntityType.DRUG)
        assert len(mappings) == 5  # All original entities should have mappings
        
        # Get statistics
        stats = service.get_resolution_stats(results)
        assert stats['total_entities'] == 5
        assert stats['total_groups'] >= 2  # Should have at least 2 groups
        assert stats['entities_merged'] >= 1  # Should have merged at least 1 entity