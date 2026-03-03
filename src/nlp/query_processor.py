"""
Natural language processing components for medical query understanding
"""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import spacy
from spacy.matcher import Matcher

logger = logging.getLogger(__name__)

class QueryIntent(str, Enum):
    """Types of medical query intents"""
    SIDE_EFFECTS = "side_effects"
    DRUG_INTERACTIONS = "drug_interactions"
    DOSING = "dosing"
    CONTRAINDICATIONS = "contraindications"
    GENERAL_INFO = "general_info"
    ALTERNATIVES = "alternatives"
    EFFECTIVENESS = "effectiveness"
    UNKNOWN = "unknown"

class EntityType(str, Enum):
    """Types of medical entities"""
    DRUG = "drug"
    CONDITION = "condition"
    SYMPTOM = "symptom"
    DOSAGE = "dosage"
    AGE = "age"
    GENDER = "gender"
    WEIGHT = "weight"

@dataclass
class ExtractedEntity:
    """Extracted medical entity"""
    text: str
    entity_type: EntityType
    confidence: float
    start_pos: int
    end_pos: int
    normalized_form: Optional[str] = None

@dataclass
class QueryAnalysis:
    """Result of query analysis"""
    original_query: str
    intent: QueryIntent
    intent_confidence: float
    entities: List[ExtractedEntity]
    query_confidence: float
    normalized_query: str
    context_hints: Dict[str, Any]
    needs_clarification: bool = False
    clarification_request: Optional[str] = None
    ambiguous_terms: List[str] = None
    
    def __post_init__(self):
        if self.ambiguous_terms is None:
            self.ambiguous_terms = []

class MedicalEntityExtractor:
    """Extracts medical entities from text"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Load spaCy model (fallback to basic model if medical model not available)
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            self.logger.warning("spaCy model not found, using basic processing")
            self.nlp = None
        
        # Initialize matcher for medical patterns
        if self.nlp:
            self.matcher = Matcher(self.nlp.vocab)
            self._setup_medical_patterns()
        
        # Drug name patterns
        self.drug_patterns = [
            r'\b[A-Z][a-z]+(?:pril|olol|mycin|cillin|statin|zole|pine|ide|ine|ate|al)\b',  # Common drug suffixes
            r'\b(?:aspirin|ibuprofen|acetaminophen|tylenol|advil|motrin|aleve|lisinopril|metformin|atorvastatin|lipitor|warfarin|plavix)\b',  # Common drugs
        ]
        
        # Condition patterns
        self.condition_patterns = [
            r'\b(?:diabetes|hypertension|depression|anxiety|arthritis|asthma|copd)\b',
            r'\b(?:high blood pressure|heart disease|kidney disease|liver disease)\b',
            r'\b(?:migraine|headache|back pain|chest pain)\b'
        ]
        
        # Symptom patterns
        self.symptom_patterns = [
            r'\b(?:nausea|vomiting|dizziness|fatigue|weakness|drowsiness)\b',
            r'\b(?:headache|stomach ache|muscle pain|joint pain)\b',
            r'\b(?:rash|itching|swelling|shortness of breath)\b'
        ]
    
    def _setup_medical_patterns(self):
        """Setup spaCy matcher patterns for medical entities"""
        if not self.nlp or not self.matcher:
            return
        
        # Drug patterns
        drug_patterns = [
            [{"LOWER": {"REGEX": r"[a-z]+pril"}}, {"LOWER": {"IN": ["hcl", "hct"]}, "OP": "?"}],
            [{"LOWER": {"REGEX": r"[a-z]+olol"}}, {"LOWER": {"IN": ["xl", "er"]}, "OP": "?"}],
            [{"LOWER": {"IN": ["aspirin", "ibuprofen", "acetaminophen", "tylenol"]}}],
        ]
        
        # Add patterns to matcher
        self.matcher.add("DRUG", drug_patterns)
        
        # Condition patterns
        condition_patterns = [
            [{"LOWER": "diabetes"}],
            [{"LOWER": "high"}, {"LOWER": "blood"}, {"LOWER": "pressure"}],
            [{"LOWER": "heart"}, {"LOWER": "disease"}],
        ]
        
        self.matcher.add("CONDITION", condition_patterns)
    
    def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract medical entities from text"""
        entities = []
        
        # Use spaCy if available
        if self.nlp:
            entities.extend(self._extract_with_spacy(text))
        
        # Use regex patterns as fallback/supplement
        entities.extend(self._extract_with_regex(text))
        
        # Remove duplicates and merge overlapping entities
        entities = self._merge_overlapping_entities(entities)
        
        return entities
    
    def _extract_with_spacy(self, text: str) -> List[ExtractedEntity]:
        """Extract entities using spaCy"""
        entities = []
        
        try:
            doc = self.nlp(text)
            
            # Extract named entities
            for ent in doc.ents:
                if ent.label_ in ["PERSON", "ORG"]:  # Skip non-medical entities
                    continue
                
                entity_type = self._map_spacy_label_to_entity_type(ent.label_)
                if entity_type:
                    entities.append(ExtractedEntity(
                        text=ent.text,
                        entity_type=entity_type,
                        confidence=0.8,  # Default confidence for spaCy entities
                        start_pos=ent.start_char,
                        end_pos=ent.end_char,
                        normalized_form=ent.text.lower()
                    ))
            
            # Extract using matcher patterns
            matches = self.matcher(doc)
            for match_id, start, end in matches:
                span = doc[start:end]
                label = self.nlp.vocab.strings[match_id]
                
                entity_type = self._map_matcher_label_to_entity_type(label)
                if entity_type:
                    entities.append(ExtractedEntity(
                        text=span.text,
                        entity_type=entity_type,
                        confidence=0.9,  # Higher confidence for pattern matches
                        start_pos=span.start_char,
                        end_pos=span.end_char,
                        normalized_form=span.text.lower()
                    ))
        
        except Exception as e:
            self.logger.error(f"Error in spaCy entity extraction: {e}")
        
        return entities
    
    def _extract_with_regex(self, text: str) -> List[ExtractedEntity]:
        """Extract entities using regex patterns"""
        entities = []
        text_lower = text.lower()
        
        # Extract drugs
        for pattern in self.drug_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append(ExtractedEntity(
                    text=match.group(),
                    entity_type=EntityType.DRUG,
                    confidence=0.7,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    normalized_form=match.group().lower()
                ))
        
        # Extract conditions
        for pattern in self.condition_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append(ExtractedEntity(
                    text=match.group(),
                    entity_type=EntityType.CONDITION,
                    confidence=0.8,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    normalized_form=match.group().lower()
                ))
        
        # Extract symptoms
        for pattern in self.symptom_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append(ExtractedEntity(
                    text=match.group(),
                    entity_type=EntityType.SYMPTOM,
                    confidence=0.7,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    normalized_form=match.group().lower()
                ))
        
        # Extract demographic information
        entities.extend(self._extract_demographics(text))
        
        return entities
    
    def _extract_demographics(self, text: str) -> List[ExtractedEntity]:
        """Extract demographic information"""
        entities = []
        
        # Age patterns
        age_patterns = [
            r'\b(\d{1,3})\s*(?:years?\s*old|yo|y\.o\.)\b',
            r'\bage\s*(\d{1,3})\b',
            r'\b(\d{1,3})\s*year\s*old\b'
        ]
        
        for pattern in age_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                age = int(match.group(1))
                if 0 <= age <= 150:  # Reasonable age range
                    entities.append(ExtractedEntity(
                        text=match.group(),
                        entity_type=EntityType.AGE,
                        confidence=0.9,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        normalized_form=str(age)
                    ))
        
        # Gender patterns
        gender_patterns = [
            r'\b(male|female|man|woman|boy|girl)\b'
        ]
        
        for pattern in gender_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                gender = match.group(1).lower()
                normalized_gender = self._normalize_gender(gender)
                entities.append(ExtractedEntity(
                    text=match.group(),
                    entity_type=EntityType.GENDER,
                    confidence=0.8,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    normalized_form=normalized_gender
                ))
        
        # Weight patterns
        weight_patterns = [
            r'\b(\d{1,3}(?:\.\d+)?)\s*(?:lbs?|pounds?)\b',
            r'\b(\d{1,3}(?:\.\d+)?)\s*kg\b'
        ]
        
        for pattern in weight_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append(ExtractedEntity(
                    text=match.group(),
                    entity_type=EntityType.WEIGHT,
                    confidence=0.8,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    normalized_form=match.group(1)
                ))
        
        return entities
    
    def _normalize_gender(self, gender: str) -> str:
        """Normalize gender terms"""
        gender = gender.lower()
        if gender in ['male', 'man', 'boy']:
            return 'male'
        elif gender in ['female', 'woman', 'girl']:
            return 'female'
        return gender
    
    def _map_spacy_label_to_entity_type(self, label: str) -> Optional[EntityType]:
        """Map spaCy entity labels to our entity types"""
        mapping = {
            'CARDINAL': EntityType.DOSAGE,  # Numbers might be dosages
            'QUANTITY': EntityType.DOSAGE,
        }
        return mapping.get(label)
    
    def _map_matcher_label_to_entity_type(self, label: str) -> Optional[EntityType]:
        """Map matcher labels to entity types"""
        mapping = {
            'DRUG': EntityType.DRUG,
            'CONDITION': EntityType.CONDITION,
        }
        return mapping.get(label)
    
    def _merge_overlapping_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """Merge overlapping entities, keeping the one with higher confidence"""
        if not entities:
            return entities
        
        # Sort by start position
        entities.sort(key=lambda x: x.start_pos)
        
        merged = []
        current = entities[0]
        
        for next_entity in entities[1:]:
            # Check for overlap
            if next_entity.start_pos < current.end_pos:
                # Overlapping entities - keep the one with higher confidence
                if next_entity.confidence > current.confidence:
                    current = next_entity
                # If same confidence, keep the longer one
                elif (next_entity.confidence == current.confidence and 
                      (next_entity.end_pos - next_entity.start_pos) > (current.end_pos - current.start_pos)):
                    current = next_entity
            else:
                # No overlap - add current and move to next
                merged.append(current)
                current = next_entity
        
        merged.append(current)
        return merged

class IntentClassifier:
    """Classifies the intent of medical queries"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Intent keywords and patterns
        self.intent_patterns = {
            QueryIntent.SIDE_EFFECTS: [
                r'\b(?:side effects?|adverse effects?|reactions?)\b',
                r'\bwhat.*(?:happen|expect|feel)\b',
                r'\b(?:symptoms?|problems?)\b.*\bcaused?\b',
                r'\b(?:safe|safety)\b'
            ],
            QueryIntent.DRUG_INTERACTIONS: [
                r'\b(?:interact|interaction|combine|together)\b',
                r'\bcan.*(?:take|use).*(?:with|and)\b',
                r'\b(?:mix|mixing)\b',
                r'\b(?:contraindication|contraindicated)\b'
            ],
            QueryIntent.DOSING: [
                r'\b(?:dose|dosage|dosing|amount)\b',
                r'\bhow much\b',
                r'\bhow often\b',
                r'\b(?:mg|mcg|ml|tablet|pill|capsule)\b'
            ],
            QueryIntent.CONTRAINDICATIONS: [
                r'\b(?:contraindication|contraindicated|avoid)\b',
                r'\bshould.*not\b',
                r'\b(?:dangerous|harmful)\b.*\bif\b',
                r'\bcan.*(?:take|use).*(?:if|when|with)\b'
            ],
            QueryIntent.ALTERNATIVES: [
                r'\b(?:alternative|substitute|replacement|instead)\b',
                r'\bother.*(?:drug|medication|option)\b',
                r'\bwhat else\b',
                r'\bdifferent.*(?:drug|medication)\b'
            ],
            QueryIntent.EFFECTIVENESS: [
                r'\b(?:effective|effectiveness|work|working)\b',
                r'\bhow well\b',
                r'\b(?:help|helps|benefit)\b',
                r'\b(?:better|best)\b.*\bfor\b'
            ]
        }
    
    def classify_intent(self, query: str) -> Tuple[QueryIntent, float]:
        """Classify the intent of a query"""
        query_lower = query.lower()
        intent_scores = {}
        
        # Score each intent based on pattern matches
        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, query_lower))
                score += matches
            
            if score > 0:
                # Normalize score by query length
                intent_scores[intent] = score / len(query.split())
        
        if not intent_scores:
            return QueryIntent.GENERAL_INFO, 0.5
        
        # Return intent with highest score
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        confidence = min(best_intent[1] * 2, 1.0)  # Scale confidence
        
        return best_intent[0], confidence

class MedicalQueryProcessor:
    """Main query processor that combines entity extraction and intent classification"""
    
    def __init__(self):
        self.entity_extractor = MedicalEntityExtractor()
        self.intent_classifier = IntentClassifier()
        self.logger = logging.getLogger(__name__)
    
    def process_query(self, query: str) -> QueryAnalysis:
        """Process a medical query and return analysis"""
        try:
            # Normalize query
            normalized_query = self._normalize_query(query)
            
            # Extract entities
            entities = self.entity_extractor.extract_entities(query)
            
            # Classify intent
            intent, intent_confidence = self.intent_classifier.classify_intent(query)
            
            # Calculate overall query confidence
            entity_confidence = sum(e.confidence for e in entities) / len(entities) if entities else 0.5
            query_confidence = (intent_confidence + entity_confidence) / 2
            
            # Extract context hints
            context_hints = self._extract_context_hints(query, entities)
            
            # Check if clarification is needed
            needs_clarification, clarification_request, ambiguous_terms = self._check_clarification_needed(
                query, entities, intent_confidence, entity_confidence
            )
            
            return QueryAnalysis(
                original_query=query,
                intent=intent,
                intent_confidence=intent_confidence,
                entities=entities,
                query_confidence=query_confidence,
                normalized_query=normalized_query,
                context_hints=context_hints,
                needs_clarification=needs_clarification,
                clarification_request=clarification_request,
                ambiguous_terms=ambiguous_terms
            )
        
        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            return QueryAnalysis(
                original_query=query,
                intent=QueryIntent.UNKNOWN,
                intent_confidence=0.0,
                entities=[],
                query_confidence=0.0,
                normalized_query=query,
                context_hints={},
                needs_clarification=True,
                clarification_request="I'm having trouble understanding your query. Could you please rephrase it?",
                ambiguous_terms=[]
            )
    
    def _check_clarification_needed(
        self, 
        query: str, 
        entities: List[ExtractedEntity],
        intent_confidence: float,
        entity_confidence: float
    ) -> Tuple[bool, Optional[str], List[str]]:
        """
        Check if the query needs clarification based on ambiguity detection
        
        Returns:
            Tuple of (needs_clarification, clarification_request, ambiguous_terms)
        """
        ambiguous_terms = []
        clarification_parts = []
        
        # Filter out common words that were incorrectly identified as drugs
        common_words = {'what', 'side', 'effects', 'safe', 'can', 'take', 'use', 'tell', 'about', 'is', 'are', 'the', 'of', 'for', 'with', 'and', 'or', 'medicine', 'medication', 'drug', 'pill', 'tablet'}
        drug_entities = [e for e in entities if e.entity_type == EntityType.DRUG and e.text.lower() not in common_words]
        
        # Check 1: Low intent confidence indicates unclear query purpose
        # But only if there are no clear drug entities - if we have drugs, the query might still be clear
        if intent_confidence < 0.3 and len(drug_entities) == 0:
            clarification_parts.append("I'm not sure what type of information you're looking for")
            ambiguous_terms.append("query_intent")
        
        # Check 2: No drug entities extracted from a query that seems to be about medications
        medication_keywords = ['medication', 'medicine', 'drug', 'pill', 'tablet', 'side effect', 'interaction', 'dose', 'dosage']
        has_medication_keyword = any(keyword in query.lower() for keyword in medication_keywords)
        
        # Also check for vague help-seeking queries
        vague_help_patterns = ['help me understand', 'can you help', 'tell me more', 'explain', 'what should i know']
        is_vague_help = any(pattern in query.lower() for pattern in vague_help_patterns)
        
        if (has_medication_keyword or is_vague_help) and len(drug_entities) == 0:
            if "missing_drug_name" not in ambiguous_terms:  # Avoid duplication
                clarification_parts.append("Which specific medication are you asking about?")
                ambiguous_terms.append("missing_drug_name")
        
        # Check 3: Low confidence entities (ambiguous entity recognition)
        low_confidence_entities = [e for e in entities if e.confidence < 0.5]
        if low_confidence_entities:
            entity_texts = [e.text for e in low_confidence_entities]
            clarification_parts.append(f"I'm uncertain about: {', '.join(entity_texts)}")
            ambiguous_terms.extend(entity_texts)
        
        # Check 4: Vague pronouns or references
        vague_patterns = [
            r'\b(?:it|this|that|these|those|them)\b',
            r'\b(?:something|anything|everything)\b'
        ]
        for pattern in vague_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                clarification_parts.append(f"Could you be more specific about what '{matches[0]}' refers to?")
                ambiguous_terms.extend(matches)
                break
        
        # Check 5: Very short queries (likely incomplete) - but only if no clear entities
        words = query.split()
        if len(words) <= 2 and len(drug_entities) == 0:
            # Single word queries or very short queries without context
            if len(words) == 1 or (len(words) == 2 and words[1] in ['?', '.']):
                clarification_parts.append("Could you provide more details about what you'd like to know?")
                ambiguous_terms.append("incomplete_query")
        
        # Check 6: Generic drug references without specific names
        generic_drug_patterns = [
            r'\bmy\s+(?:medication|medicine|drug|pill)\b'
        ]
        has_generic_ref = any(re.search(p, query, re.IGNORECASE) for p in generic_drug_patterns)
        
        if has_generic_ref and len(drug_entities) == 0:
            if "missing_drug_name" not in ambiguous_terms:  # Avoid duplication
                clarification_parts.append("Which specific medication are you asking about?")
                ambiguous_terms.append("generic_drug_reference")
        
        # Check 7: Queries with multiple drugs but unclear intent about interactions
        if len(drug_entities) >= 2:
            # Check if it's clearly an interaction query
            interaction_keywords = ['interact', 'interaction', 'together', 'combine', 'mix', 'taking', 'take both']
            has_interaction_keyword = any(keyword in query.lower() for keyword in interaction_keywords)
            
            # Check if it's a vague query with multiple drugs
            vague_query_patterns = ['tell me about', 'what about', 'info on', 'information on']
            is_vague_query = any(pattern in query.lower() for pattern in vague_query_patterns)
            
            # Check if it's a simple list without context
            is_simple_list = len(query.split()) <= len(drug_entities) + 2  # e.g., "Drug1 and Drug2"
            
            if not has_interaction_keyword and (is_simple_list or is_vague_query):
                drug_names = [e.text for e in drug_entities]
                clarification_parts.append(
                    f"You mentioned {', '.join(drug_names)}. Are you asking about interactions or something else?"
                )
                ambiguous_terms.append("multiple_drugs_unclear")
        
        # Determine if clarification is needed
        needs_clarification = len(clarification_parts) > 0
        
        # Build clarification request
        clarification_request = None
        if needs_clarification:
            if len(clarification_parts) == 1:
                clarification_request = clarification_parts[0] + ". Could you please clarify?"
            else:
                clarification_request = (
                    "I need some clarification:\n" + 
                    "\n".join(f"- {part}" for part in clarification_parts)
                )
        
        return needs_clarification, clarification_request, ambiguous_terms
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query text"""
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', query.strip())
        
        # Expand common abbreviations
        abbreviations = {
            r'\bw/\b': 'with',
            r'\bw/o\b': 'without',
            r'\bmg\b': 'milligrams',
            r'\bmcg\b': 'micrograms',
            r'\bml\b': 'milliliters',
        }
        
        for abbrev, expansion in abbreviations.items():
            normalized = re.sub(abbrev, expansion, normalized, flags=re.IGNORECASE)
        
        return normalized
    
    def _extract_context_hints(self, query: str, entities: List[ExtractedEntity]) -> Dict[str, Any]:
        """Extract additional context hints from query"""
        hints = {}
        
        # Check for urgency indicators
        urgency_patterns = [
            r'\b(?:urgent|emergency|immediately|asap|right away)\b',
            r'\b(?:severe|serious|bad|terrible)\b'
        ]
        
        for pattern in urgency_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                hints['urgency'] = 'high'
                break
        else:
            hints['urgency'] = 'normal'
        
        # Check for time references
        time_patterns = [
            r'\b(?:today|now|currently|right now)\b',
            r'\b(?:tomorrow|next week|soon)\b',
            r'\b(?:before|after|during)\b'
        ]
        
        for pattern in time_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                hints['time_sensitive'] = True
                break
        else:
            hints['time_sensitive'] = False
        
        # Extract patient context from entities
        patient_context = {}
        for entity in entities:
            if entity.entity_type == EntityType.AGE:
                patient_context['age'] = entity.normalized_form
            elif entity.entity_type == EntityType.GENDER:
                patient_context['gender'] = entity.normalized_form
            elif entity.entity_type == EntityType.WEIGHT:
                patient_context['weight'] = entity.normalized_form
        
        if patient_context:
            hints['patient_context'] = patient_context
        
        return hints

# Global query processor instance
medical_query_processor = MedicalQueryProcessor()