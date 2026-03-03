"""
Property-based tests for entity recognition and clarification

Feature: pharmaguide-health-companion, Property 3: Entity Recognition and Clarification
Validates: Requirements 1.3
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from src.nlp.query_processor import (
    MedicalQueryProcessor,
    QueryIntent,
    EntityType
)


# Strategies for generating test data
@st.composite
def ambiguous_query_strategy(draw):
    """Generate ambiguous queries that should trigger clarification"""
    
    ambiguous_patterns = [
        # Vague pronouns
        "What about it?",
        "Can I take this?",
        "Is that safe?",
        "Tell me about them",
        "What does it do?",
        
        # Generic drug references without specifics
        "What are the side effects of my medication?",
        "Can I take my medicine with food?",
        "Is my drug safe?",
        "Tell me about my pill",
        
        # Very short/incomplete queries
        "Side effects?",
        "Interactions",
        "Safe?",
        "Dosage",
        
        # Multiple drugs without clear intent
        "Lisinopril and aspirin",
        "Metformin ibuprofen",
        "Tell me about Lipitor and Plavix",
        
        # No entities in non-trivial query
        "What should I know about this situation?",
        "Is there anything I should be concerned about?",
        "Can you help me understand?",
    ]
    
    return draw(st.sampled_from(ambiguous_patterns))


@st.composite
def clear_query_strategy(draw):
    """Generate clear, unambiguous queries"""
    
    clear_patterns = [
        # Specific drug with clear intent
        "What are the side effects of Lisinopril?",
        "Can I take aspirin with ibuprofen?",
        "What is the recommended dosage for metformin?",
        "Is Lipitor contraindicated for people with diabetes?",
        "What are alternatives to atorvastatin?",
        
        # Queries with patient context
        "What are the side effects of Lisinopril for a 65-year-old with diabetes?",
        "Can a 45-year-old woman take ibuprofen while pregnant?",
        "Is metformin safe for someone with kidney disease?",
        
        # Specific interaction queries
        "Does warfarin interact with aspirin?",
        "Can I take Tylenol with my blood pressure medication?",
        "Are there interactions between metformin and lisinopril?",
    ]
    
    return draw(st.sampled_from(clear_patterns))


@st.composite
def mixed_clarity_query_strategy(draw):
    """Generate queries with varying levels of clarity"""
    return draw(st.one_of(
        ambiguous_query_strategy(),
        clear_query_strategy()
    ))


# Property-Based Tests

@settings(max_examples=50, deadline=None)
@given(query=ambiguous_query_strategy())
def test_ambiguous_queries_trigger_clarification(query):
    """
    Property 3: Entity Recognition and Clarification
    
    For any ambiguous or unclear patient query, the system should use entity 
    recognition to identify problematic terms and request specific clarification.
    
    Validates: Requirements 1.3
    """
    processor = MedicalQueryProcessor()
    result = processor.process_query(query)
    
    # Ambiguous queries should trigger clarification
    assert result.needs_clarification, (
        f"Ambiguous query '{query}' should trigger clarification but didn't. "
        f"Query confidence: {result.query_confidence}, "
        f"Intent confidence: {result.intent_confidence}"
    )
    
    # Clarification request should be provided
    assert result.clarification_request is not None, (
        f"Ambiguous query '{query}' needs clarification but no request was generated"
    )
    
    # Clarification request should be a non-empty string
    assert isinstance(result.clarification_request, str), (
        "Clarification request should be a string"
    )
    assert len(result.clarification_request) > 0, (
        "Clarification request should not be empty"
    )
    
    # Ambiguous terms should be identified
    assert isinstance(result.ambiguous_terms, list), (
        "Ambiguous terms should be a list"
    )
    assert len(result.ambiguous_terms) > 0, (
        f"Ambiguous query '{query}' should identify ambiguous terms"
    )


@settings(max_examples=50, deadline=None)
@given(query=clear_query_strategy())
def test_clear_queries_do_not_require_clarification(query):
    """
    Property 3: Entity Recognition and Clarification (Inverse)
    
    For any clear and specific patient query, the system should not request 
    clarification unnecessarily.
    
    Validates: Requirements 1.3
    """
    processor = MedicalQueryProcessor()
    result = processor.process_query(query)
    
    # Clear queries should not trigger clarification
    assert not result.needs_clarification, (
        f"Clear query '{query}' should not require clarification. "
        f"Query confidence: {result.query_confidence}, "
        f"Clarification request: {result.clarification_request}"
    )
    
    # If no clarification needed, request should be None
    assert result.clarification_request is None, (
        f"Clear query '{query}' should not have a clarification request"
    )


@settings(max_examples=50, deadline=None)
@given(query=st.text(min_size=1, max_size=200))
def test_all_queries_have_consistent_clarification_fields(query):
    """
    Property 3: Entity Recognition and Clarification (Consistency)
    
    For any query, the clarification fields should be consistent:
    - If needs_clarification is True, clarification_request should be non-None
    - If needs_clarification is False, clarification_request should be None
    - ambiguous_terms should always be a list
    
    Validates: Requirements 1.3
    """
    # Filter out empty or whitespace-only queries
    assume(query.strip())
    
    processor = MedicalQueryProcessor()
    result = processor.process_query(query)
    
    # Check consistency of clarification fields
    if result.needs_clarification:
        assert result.clarification_request is not None, (
            f"Query '{query}' needs clarification but has no clarification request"
        )
        assert isinstance(result.clarification_request, str), (
            "Clarification request must be a string"
        )
        assert len(result.clarification_request) > 0, (
            "Clarification request must not be empty"
        )
    else:
        assert result.clarification_request is None, (
            f"Query '{query}' doesn't need clarification but has a request: "
            f"{result.clarification_request}"
        )
    
    # Ambiguous terms should always be a list
    assert isinstance(result.ambiguous_terms, list), (
        "Ambiguous terms must always be a list"
    )


@settings(max_examples=50, deadline=None)
@given(query=ambiguous_query_strategy())
def test_clarification_identifies_specific_ambiguous_terms(query):
    """
    Property 3: Entity Recognition and Clarification (Specificity)
    
    For any ambiguous query, the system should identify specific ambiguous terms
    that caused the clarification request.
    
    Validates: Requirements 1.3
    """
    processor = MedicalQueryProcessor()
    result = processor.process_query(query)
    
    # Should identify ambiguous terms
    assert len(result.ambiguous_terms) > 0, (
        f"Ambiguous query '{query}' should identify specific ambiguous terms"
    )
    
    # Ambiguous terms should be strings
    for term in result.ambiguous_terms:
        assert isinstance(term, str), (
            f"Ambiguous term should be a string, got {type(term)}"
        )


@settings(max_examples=50, deadline=None)
@given(
    base_query=st.sampled_from([
        "What are the side effects of",
        "Can I take",
        "Is it safe to use",
        "Tell me about"
    ]),
    drug_name=st.sampled_from([
        "Lisinopril",
        "aspirin",
        "metformin",
        "ibuprofen",
        "atorvastatin"
    ])
)
def test_adding_specific_drug_reduces_ambiguity(base_query, drug_name):
    """
    Property 3: Entity Recognition and Clarification (Refinement)
    
    For any query, adding specific drug names should reduce ambiguity and
    decrease the likelihood of clarification being needed.
    
    Validates: Requirements 1.3
    """
    processor = MedicalQueryProcessor()
    
    # Incomplete query (more likely to need clarification)
    incomplete_query = base_query + "?"
    incomplete_result = processor.process_query(incomplete_query)
    
    # Complete query with drug name
    complete_query = base_query + " " + drug_name + "?"
    complete_result = processor.process_query(complete_query)
    
    # Complete query should have higher confidence or fewer ambiguous terms
    assert (
        complete_result.query_confidence >= incomplete_result.query_confidence or
        len(complete_result.ambiguous_terms) <= len(incomplete_result.ambiguous_terms)
    ), (
        f"Adding drug name '{drug_name}' to '{base_query}' should reduce ambiguity. "
        f"Incomplete confidence: {incomplete_result.query_confidence}, "
        f"Complete confidence: {complete_result.query_confidence}"
    )


@settings(max_examples=50, deadline=None)
@given(query=mixed_clarity_query_strategy())
def test_entity_recognition_always_returns_valid_entities(query):
    """
    Property 3: Entity Recognition and Clarification (Entity Validity)
    
    For any query, extracted entities should have valid types, confidence scores,
    and positions.
    
    Validates: Requirements 1.3
    """
    processor = MedicalQueryProcessor()
    result = processor.process_query(query)
    
    # Check each extracted entity
    for entity in result.entities:
        # Entity type should be valid
        assert isinstance(entity.entity_type, EntityType), (
            f"Entity type should be EntityType enum, got {type(entity.entity_type)}"
        )
        
        # Confidence should be between 0 and 1
        assert 0 <= entity.confidence <= 1, (
            f"Entity confidence should be between 0 and 1, got {entity.confidence}"
        )
        
        # Positions should be valid
        assert entity.start_pos >= 0, (
            f"Entity start position should be non-negative, got {entity.start_pos}"
        )
        assert entity.end_pos > entity.start_pos, (
            f"Entity end position should be greater than start position"
        )
        assert entity.end_pos <= len(query), (
            f"Entity end position should not exceed query length"
        )
        
        # Text should match the position in query
        extracted_text = query[entity.start_pos:entity.end_pos]
        assert entity.text.lower() == extracted_text.lower(), (
            f"Entity text '{entity.text}' doesn't match query substring '{extracted_text}'"
        )


@settings(max_examples=30, deadline=None)
@given(
    query=st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs', 'Po')),
        min_size=5,
        max_size=100
    )
)
def test_processor_handles_arbitrary_text_gracefully(query):
    """
    Property 3: Entity Recognition and Clarification (Robustness)
    
    For any arbitrary text input, the processor should handle it gracefully
    without crashing and return a valid QueryAnalysis object.
    
    Validates: Requirements 1.3
    """
    # Filter out empty or whitespace-only queries
    assume(query.strip())
    
    processor = MedicalQueryProcessor()
    
    # Should not raise an exception
    result = processor.process_query(query)
    
    # Should return a valid QueryAnalysis object
    assert result is not None, "Processor should return a result"
    assert hasattr(result, 'needs_clarification'), "Result should have needs_clarification field"
    assert hasattr(result, 'clarification_request'), "Result should have clarification_request field"
    assert hasattr(result, 'ambiguous_terms'), "Result should have ambiguous_terms field"
    assert hasattr(result, 'entities'), "Result should have entities field"
    assert hasattr(result, 'intent'), "Result should have intent field"
    
    # Fields should have correct types
    assert isinstance(result.needs_clarification, bool)
    assert result.clarification_request is None or isinstance(result.clarification_request, str)
    assert isinstance(result.ambiguous_terms, list)
    assert isinstance(result.entities, list)
    assert isinstance(result.intent, QueryIntent)
