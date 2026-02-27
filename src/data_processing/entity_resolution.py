"""
Entity resolution service for matching entities across datasets
"""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import difflib
from collections import defaultdict

from src.knowledge_graph.models import EntityMapping

logger = logging.getLogger(__name__)

class MatchingMethod(str, Enum):
    """Entity matching methods"""
    EXACT = "exact"
    FUZZY = "fuzzy"
    PHONETIC = "phonetic"
    SEMANTIC = "semantic"
    COMPOSITE = "composite"

class EntityType(str, Enum):
    """Entity types for resolution"""
    DRUG = "drug"
    SIDE_EFFECT = "side_effect"
    CONDITION = "condition"
    INTERACTION = "interaction"

@dataclass
class MatchCandidate:
    """Candidate match for entity resolution"""
    source_id: str
    target_id: str
    source_name: str
    target_name: str
    confidence: float
    method: MatchingMethod
    evidence: Dict[str, Any]

@dataclass
class ResolutionResult:
    """Result of entity resolution"""
    canonical_id: str
    matched_entities: List[Dict[str, Any]]
    confidence: float
    method: MatchingMethod
    conflicts: List[str]

class DrugNameNormalizer:
    """Normalizes drug names for better matching"""
    
    def __init__(self):
        # Common drug name variations and abbreviations
        self.abbreviations = {
            'hcl': 'hydrochloride',
            'hct': 'hydrochlorothiazide',
            'er': 'extended release',
            'xl': 'extended release',
            'sr': 'sustained release',
            'cr': 'controlled release',
            'ir': 'immediate release',
            'od': 'once daily',
            'bid': 'twice daily',
            'tid': 'three times daily'
        }
        
        # Common prefixes/suffixes to remove for matching
        self.noise_patterns = [
            r'\b(tablet|capsule|injection|solution|cream|gel|ointment)\b',
            r'\b\d+\s*units?/ml\b',  # Units per ml (must come before general pattern)
            r'\b\d+\s*(mg|mcg|g|ml|units?)\b',  # Dosage information
            r'\([^)]*\)',  # Parenthetical information
            r'\b(brand|generic)\b'
        ]
    
    def normalize(self, drug_name: str) -> str:
        """Normalize drug name for matching"""
        if not drug_name:
            return ""
        
        # Convert to lowercase
        normalized = drug_name.lower().strip()
        
        # Expand abbreviations
        for abbrev, full_form in self.abbreviations.items():
            normalized = re.sub(rf'\b{abbrev}\b', full_form, normalized)
        
        # Remove noise patterns
        for pattern in self.noise_patterns:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        # Clean up whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Remove special characters except hyphens and spaces
        normalized = re.sub(r'[^\w\s\-]', '', normalized)
        
        return normalized
    
    def extract_active_ingredient(self, drug_name: str) -> str:
        """Extract likely active ingredient from drug name"""
        # Split on common separators BEFORE normalization to preserve structure
        parts = re.split(r'[/+&,]', drug_name)
        if parts:
            # Normalize just the first part (active ingredient)
            return self.normalize(parts[0].strip())
        
        return self.normalize(drug_name)

class SideEffectNormalizer:
    """Normalizes side effect names for better matching"""
    
    def __init__(self):
        # Common side effect synonyms
        self.synonyms = {
            'nausea': ['feeling sick', 'queasiness', 'stomach upset'],
            'headache': ['head pain', 'cephalgia', 'migraine'],
            'dizziness': ['vertigo', 'lightheadedness', 'giddiness'],
            'fatigue': ['tiredness', 'exhaustion', 'weakness'],
            'diarrhea': ['loose stools', 'bowel problems'],
            'constipation': ['difficulty passing stools', 'hard stools'],
            'rash': ['skin irritation', 'dermatitis', 'skin reaction']
        }
        
        # Build reverse mapping
        self.synonym_map = {}
        for canonical, variants in self.synonyms.items():
            self.synonym_map[canonical] = canonical
            for variant in variants:
                self.synonym_map[variant] = canonical
    
    def normalize(self, side_effect_name: str) -> str:
        """Normalize side effect name for matching"""
        if not side_effect_name:
            return ""
        
        # Convert to lowercase and clean
        normalized = side_effect_name.lower().strip()
        
        # Remove common prefixes
        normalized = re.sub(r'^(acute|chronic|severe|mild|moderate)\s+', '', normalized)
        
        # Check for synonyms
        if normalized in self.synonym_map:
            normalized = self.synonym_map[normalized]
        
        # Clean up
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized

class EntityMatcher:
    """Core entity matching algorithms"""
    
    def __init__(self):
        self.drug_normalizer = DrugNameNormalizer()
        self.side_effect_normalizer = SideEffectNormalizer()
    
    def exact_match(self, name1: str, name2: str, entity_type: EntityType) -> float:
        """Exact string matching with normalization"""
        if entity_type == EntityType.DRUG:
            norm1 = self.drug_normalizer.normalize(name1)
            norm2 = self.drug_normalizer.normalize(name2)
        elif entity_type == EntityType.SIDE_EFFECT:
            norm1 = self.side_effect_normalizer.normalize(name1)
            norm2 = self.side_effect_normalizer.normalize(name2)
        else:
            norm1 = name1.lower().strip()
            norm2 = name2.lower().strip()
        
        return 1.0 if norm1 == norm2 else 0.0
    
    def fuzzy_match(self, name1: str, name2: str, entity_type: EntityType) -> float:
        """Fuzzy string matching using sequence similarity"""
        if entity_type == EntityType.DRUG:
            norm1 = self.drug_normalizer.normalize(name1)
            norm2 = self.drug_normalizer.normalize(name2)
        elif entity_type == EntityType.SIDE_EFFECT:
            norm1 = self.side_effect_normalizer.normalize(name1)
            norm2 = self.side_effect_normalizer.normalize(name2)
        else:
            norm1 = name1.lower().strip()
            norm2 = name2.lower().strip()
        
        if not norm1 or not norm2:
            return 0.0
        
        # Use difflib for sequence matching
        similarity = difflib.SequenceMatcher(None, norm1, norm2).ratio()
        
        # Boost score for partial matches of longer strings
        if len(norm1) > 10 and len(norm2) > 10:
            if norm1 in norm2 or norm2 in norm1:
                similarity = max(similarity, 0.8)
        
        return similarity
    
    def active_ingredient_match(self, drug1: str, drug2: str) -> float:
        """Match drugs based on active ingredients"""
        ingredient1 = self.drug_normalizer.extract_active_ingredient(drug1)
        ingredient2 = self.drug_normalizer.extract_active_ingredient(drug2)
        
        if not ingredient1 or not ingredient2:
            return 0.0
        
        # Exact match on active ingredients
        if ingredient1 == ingredient2:
            return 0.95
        
        # Fuzzy match on active ingredients
        similarity = difflib.SequenceMatcher(None, ingredient1, ingredient2).ratio()
        return similarity * 0.9  # Slightly lower confidence for fuzzy ingredient match
    
    def composite_match(self, name1: str, name2: str, entity_type: EntityType, 
                       additional_data1: Dict[str, Any] = None,
                       additional_data2: Dict[str, Any] = None) -> Tuple[float, Dict[str, Any]]:
        """Composite matching using multiple methods"""
        evidence = {}
        scores = []
        
        # Exact match
        exact_score = self.exact_match(name1, name2, entity_type)
        evidence['exact_score'] = exact_score
        if exact_score > 0:
            scores.append(exact_score)
        
        # Fuzzy match
        fuzzy_score = self.fuzzy_match(name1, name2, entity_type)
        evidence['fuzzy_score'] = fuzzy_score
        scores.append(fuzzy_score)
        
        # Special handling for drugs
        if entity_type == EntityType.DRUG:
            ingredient_score = self.active_ingredient_match(name1, name2)
            evidence['ingredient_score'] = ingredient_score
            scores.append(ingredient_score)
            
            # Check additional identifiers if available
            if additional_data1 and additional_data2:
                # DrugBank ID matching
                if (additional_data1.get('drugbank_id') and 
                    additional_data2.get('drugbank_id') and
                    additional_data1['drugbank_id'] == additional_data2['drugbank_id']):
                    evidence['drugbank_match'] = True
                    scores.append(1.0)
                
                # RxCUI matching
                if (additional_data1.get('rxcui') and 
                    additional_data2.get('rxcui') and
                    additional_data1['rxcui'] == additional_data2['rxcui']):
                    evidence['rxcui_match'] = True
                    scores.append(1.0)
        
        # Calculate weighted average
        if scores:
            # Give higher weight to exact matches and identifier matches
            weights = []
            for i, score in enumerate(scores):
                if score == 1.0:  # Exact or identifier match
                    weights.append(2.0)
                else:
                    weights.append(1.0)
            
            weighted_score = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
        else:
            weighted_score = 0.0
        
        return weighted_score, evidence

class EntityResolutionService:
    """Main entity resolution service"""
    
    def __init__(self, confidence_threshold: float = 0.8):
        self.matcher = EntityMatcher()
        self.confidence_threshold = confidence_threshold
        self.logger = logging.getLogger(__name__)
        
        # Cache for resolved entities
        self.resolution_cache: Dict[str, ResolutionResult] = {}
    
    def find_matches(self, entities: List[Dict[str, Any]], entity_type: EntityType) -> List[MatchCandidate]:
        """Find potential matches among a list of entities"""
        matches = []
        
        # Compare each entity with every other entity
        for i, entity1 in enumerate(entities):
            for j, entity2 in enumerate(entities[i+1:], i+1):
                name1 = entity1.get('name', '')
                name2 = entity2.get('name', '')
                
                if not name1 or not name2:
                    continue
                
                # Use composite matching
                confidence, evidence = self.matcher.composite_match(
                    name1, name2, entity_type, entity1, entity2
                )
                
                if confidence >= self.confidence_threshold:
                    match = MatchCandidate(
                        source_id=entity1.get('id', f"entity_{i}"),
                        target_id=entity2.get('id', f"entity_{j}"),
                        source_name=name1,
                        target_name=name2,
                        confidence=confidence,
                        method=MatchingMethod.COMPOSITE,
                        evidence=evidence
                    )
                    matches.append(match)
        
        return matches
    
    def resolve_entities(self, entities: List[Dict[str, Any]], entity_type: EntityType) -> List[ResolutionResult]:
        """Resolve entities into canonical groups"""
        if not entities:
            return []
        
        # Find all potential matches
        matches = self.find_matches(entities, entity_type)
        
        # Build entity groups using connected components
        entity_groups = self._build_entity_groups(entities, matches)
        
        # Create resolution results
        results = []
        for group_id, group_entities in entity_groups.items():
            # Select canonical entity (highest confidence or most complete data)
            canonical_entity = self._select_canonical_entity(group_entities)
            
            # Calculate overall confidence
            if len(group_entities) == 1:
                confidence = 1.0  # Single entity, perfect confidence
            else:
                # Average confidence of matches in this group
                group_matches = [m for m in matches 
                               if m.source_id in [e['id'] for e in group_entities] or
                                  m.target_id in [e['id'] for e in group_entities]]
                confidence = sum(m.confidence for m in group_matches) / len(group_matches) if group_matches else 0.8
            
            # Detect conflicts
            conflicts = self._detect_conflicts(group_entities)
            
            result = ResolutionResult(
                canonical_id=canonical_entity['id'],
                matched_entities=group_entities,
                confidence=confidence,
                method=MatchingMethod.COMPOSITE,
                conflicts=conflicts
            )
            results.append(result)
        
        return results
    
    def _build_entity_groups(self, entities: List[Dict[str, Any]], 
                           matches: List[MatchCandidate]) -> Dict[str, List[Dict[str, Any]]]:
        """Build connected components of matching entities"""
        # Create entity lookup
        entity_lookup = {e.get('id', f"entity_{i}"): e for i, e in enumerate(entities)}
        
        # Build adjacency list
        adjacency = defaultdict(set)
        for match in matches:
            adjacency[match.source_id].add(match.target_id)
            adjacency[match.target_id].add(match.source_id)
        
        # Find connected components using DFS
        visited = set()
        groups = {}
        group_id = 0
        
        for entity_id in entity_lookup:
            if entity_id not in visited:
                # Start new group
                group = []
                stack = [entity_id]
                
                while stack:
                    current_id = stack.pop()
                    if current_id not in visited:
                        visited.add(current_id)
                        group.append(entity_lookup[current_id])
                        
                        # Add connected entities
                        for neighbor_id in adjacency[current_id]:
                            if neighbor_id not in visited:
                                stack.append(neighbor_id)
                
                groups[f"group_{group_id}"] = group
                group_id += 1
        
        return groups
    
    def _select_canonical_entity(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the canonical entity from a group"""
        if len(entities) == 1:
            return entities[0]
        
        # Score entities based on completeness and data quality
        scored_entities = []
        
        for entity in entities:
            score = 0
            
            # Prefer entities with more complete data
            if entity.get('drugbank_id'):
                score += 10
            if entity.get('rxcui'):
                score += 8
            if entity.get('generic_name'):
                score += 5
            if entity.get('mechanism'):
                score += 3
            if entity.get('indications'):
                score += len(entity['indications'])
            
            # Prefer entities from authoritative sources
            source = entity.get('source_dataset', '').lower()
            if 'drugbank' in source:
                score += 20
            elif 'sider' in source:
                score += 15
            elif 'onsides' in source:
                score += 10
            
            # Prefer longer, more descriptive names (up to a point)
            name_length = len(entity.get('name', ''))
            if 5 <= name_length <= 50:
                score += min(name_length // 5, 10)
            
            scored_entities.append((score, entity))
        
        # Return entity with highest score
        scored_entities.sort(key=lambda x: x[0], reverse=True)
        return scored_entities[0][1]
    
    def _detect_conflicts(self, entities: List[Dict[str, Any]]) -> List[str]:
        """Detect conflicts within an entity group"""
        conflicts = []
        
        if len(entities) <= 1:
            return conflicts
        
        # Check for conflicting identifiers
        drugbank_ids = set()
        rxcuis = set()
        
        for entity in entities:
            if entity.get('drugbank_id'):
                drugbank_ids.add(entity['drugbank_id'])
            if entity.get('rxcui'):
                rxcuis.add(entity['rxcui'])
        
        if len(drugbank_ids) > 1:
            conflicts.append(f"Conflicting DrugBank IDs: {drugbank_ids}")
        
        if len(rxcuis) > 1:
            conflicts.append(f"Conflicting RxCUIs: {rxcuis}")
        
        # Check for very different names (might indicate false positive)
        names = [entity.get('name', '') for entity in entities]
        for i, name1 in enumerate(names):
            for name2 in names[i+1:]:
                similarity = difflib.SequenceMatcher(None, name1.lower(), name2.lower()).ratio()
                if similarity < 0.3:  # Very different names
                    conflicts.append(f"Very different names: '{name1}' vs '{name2}'")
        
        return conflicts
    
    def create_entity_mappings(self, resolution_results: List[ResolutionResult], 
                             entity_type: EntityType) -> List[EntityMapping]:
        """Create entity mappings from resolution results"""
        mappings = []
        
        for result in resolution_results:
            for entity in result.matched_entities:
                mapping = EntityMapping(
                    source_id=entity.get('id', ''),
                    canonical_id=result.canonical_id,
                    source_dataset=entity.get('source_dataset', 'unknown'),
                    entity_type=entity_type.value,
                    confidence=result.confidence,
                    mapping_method=result.method.value,
                    verified=len(result.conflicts) == 0  # No conflicts = auto-verified
                )
                mappings.append(mapping)
        
        return mappings
    
    def get_resolution_stats(self, resolution_results: List[ResolutionResult]) -> Dict[str, Any]:
        """Get statistics about entity resolution"""
        total_entities = sum(len(r.matched_entities) for r in resolution_results)
        total_groups = len(resolution_results)
        
        # Count conflicts
        total_conflicts = sum(len(r.conflicts) for r in resolution_results)
        
        # Average group size
        avg_group_size = total_entities / total_groups if total_groups > 0 else 0
        
        # Confidence distribution
        confidences = [r.confidence for r in resolution_results]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            'total_entities': total_entities,
            'total_groups': total_groups,
            'entities_merged': total_entities - total_groups,
            'merge_rate': (total_entities - total_groups) / total_entities if total_entities > 0 else 0,
            'average_group_size': avg_group_size,
            'total_conflicts': total_conflicts,
            'conflict_rate': total_conflicts / total_groups if total_groups > 0 else 0,
            'average_confidence': avg_confidence,
            'high_confidence_groups': sum(1 for r in resolution_results if r.confidence >= 0.9),
            'low_confidence_groups': sum(1 for r in resolution_results if r.confidence < 0.7)
        }

# Global entity resolution service instance
entity_resolution_service = EntityResolutionService()