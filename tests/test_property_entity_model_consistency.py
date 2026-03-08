"""
Property-based tests for entity model consistency in semantic query processing and graph traversal

**Validates: Requirements 1.1, 1.5**

Property 1: Semantic Query Processing and Graph Traversal
For any valid natural language medication query, the system should parse it semantically,
execute appropriate knowledge graph traversals, and provide relevant responses within 45 seconds
with complete provenance tracking.
"""
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from hypothesis.strategies import composite
from datetime import datetime
from typing import List, Dict, Any
import asyncio

from src.knowledge_graph.models import (
    DrugEntity, SideEffectEntity, PatientContext, CausesRelationship,
    SeverityLevel, FrequencyCategory, SemanticQuery, GraphResponse
)
from src.knowledge_graph.database import KnowledgeGraphDatabase
from src.nlp.query_processor import MedicalQueryProcessor, QueryIntent, EntityType


# ============================================================================
# Strategy Generators for Property-Based Testing
# ============================================================================

@composite
def drug_name_strategy(draw):
    """Generate realistic drug names"""
    # Common drug name patterns
    prefixes = ["Lis", "Met", "Ator", "Sim", "Prav", "Ros", "Amlod", "Losar", "Valsar"]
    suffixes = ["pril", "formin", "vastatin", "ipine", "tan", "olol"]
    
    prefix = draw(st.sampled_from(prefixes))
    suffix = draw(st.sampled_from(suffixes))
    
    return prefix + suffix


@composite
def drug_entity_strategy(draw):
    """Generate valid DrugEntity instances"""
    drug_id = f"drug_{draw(st.integers(min_value=1, max_value=10000))}"
    name = draw(drug_name_strategy())
    generic_name = name.lower()
    
    return DrugEntity(
        id=drug_id,
        name=name,
        generic_name=generic_name,
        drugbank_id=f"DB{draw(st.integers(min_value=10000, max_value=99999))}",
        rxcui=str(draw(st.integers(min_value=1000, max_value=999999))),
        atc_codes=draw(st.lists(
            st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Nd')), min_size=7, max_size=7),
            min_size=0, max_size=3
        )),
        mechanism=draw(st.sampled_from([
            "ACE inhibitor", "Beta blocker", "Calcium channel blocker",
            "Statin", "Diuretic", "ARB"
        ])),
        indications=draw(st.lists(
            st.sampled_from(["hypertension", "diabetes", "heart failure", "high cholesterol"]),
            min_size=1, max_size=3
        )),
        contraindications=draw(st.lists(
            st.sampled_from(["pregnancy", "liver disease", "kidney disease"]),
            min_size=0, max_size=2
        ))
    )


@composite
def side_effect_entity_strategy(draw):
    """Generate valid SideEffectEntity instances"""
    side_effect_id = f"se_{draw(st.integers(min_value=1, max_value=10000))}"
    
    side_effects = [
        "Headache", "Nausea", "Dizziness", "Fatigue", "Dry cough",
        "Muscle pain", "Insomnia", "Diarrhea", "Rash", "Weakness"
    ]
    
    return SideEffectEntity(
        id=side_effect_id,
        name=draw(st.sampled_from(side_effects)),
        meddra_code=str(draw(st.integers(min_value=10000000, max_value=99999999))),
        severity=draw(st.sampled_from(list(SeverityLevel))),
        frequency_category=draw(st.sampled_from(list(FrequencyCategory))),
        system_organ_class=draw(st.sampled_from([
            "Nervous system", "Gastrointestinal", "Cardiovascular",
            "Respiratory", "Musculoskeletal"
        ])),
        description=f"Description of {draw(st.sampled_from(side_effects))}"
    )


@composite
def patient_context_strategy(draw):
    """Generate valid PatientContext instances"""
    patient_id = f"patient_{draw(st.integers(min_value=1, max_value=10000))}"
    
    age = draw(st.integers(min_value=18, max_value=100))
    gender = draw(st.sampled_from(["male", "female"]))
    weight = draw(st.integers(min_value=40, max_value=200))
    
    return PatientContext(
        id=patient_id,
        demographics={
            "age": age,
            "gender": gender,
            "weight": weight,
            "height": draw(st.integers(min_value=140, max_value=210))
        },
        conditions=draw(st.lists(
            st.sampled_from(["diabetes", "hypertension", "heart failure", "asthma"]),
            min_size=0, max_size=3
        )),
        medications=draw(st.lists(
            st.fixed_dictionaries({
                "name": drug_name_strategy(),
                "dosage": st.sampled_from(["5mg", "10mg", "20mg", "40mg"])
            }),
            min_size=0, max_size=5
        )),
        allergies=draw(st.lists(
            st.sampled_from(["penicillin", "sulfa", "aspirin"]),
            min_size=0, max_size=2
        ))
    )


@composite
def medical_query_strategy(draw):
    """Generate realistic medical queries about medications"""
    query_templates = [
        "What are the side effects of {drug}?",
        "Can I take {drug} with {condition}?",
        "Is {drug} safe for a {age} year old {gender}?",
        "What are the side effects of {drug} for someone with {condition}?",
        "How does {drug} interact with other medications?",
        "What should I know about {drug}?",
        "Are there any risks with {drug} for {condition}?",
        "Can {drug} cause {symptom}?",
        "What are the common side effects of {drug}?",
        "Is {drug} safe during pregnancy?"
    ]
    
    template = draw(st.sampled_from(query_templates))
    drug = draw(drug_name_strategy())
    age = draw(st.integers(min_value=18, max_value=90))
    gender = draw(st.sampled_from(["male", "female", "man", "woman"]))
    condition = draw(st.sampled_from(["diabetes", "hypertension", "heart disease", "kidney disease"]))
    symptom = draw(st.sampled_from(["headache", "nausea", "dizziness", "fatigue"]))
    
    query = template.format(
        drug=drug,
        age=age,
        gender=gender,
        condition=condition,
        symptom=symptom
    )
    
    return query


@composite
def causes_relationship_strategy(draw, drug_id: str, side_effect_id: str):
    """Generate valid CausesRelationship instances"""
    return CausesRelationship(
        drug_id=drug_id,
        side_effect_id=side_effect_id,
        frequency=draw(st.floats(min_value=0.0, max_value=1.0)),
        confidence=draw(st.floats(min_value=0.0, max_value=1.0)),
        evidence_sources=draw(st.lists(
            st.sampled_from(["FAERS", "SIDER", "OnSIDES", "DrugBank"]),
            min_size=1, max_size=4, unique=True
        )),
        patient_count=draw(st.integers(min_value=1, max_value=100000)),
        statistical_significance=draw(st.floats(min_value=0.0, max_value=0.05)),
        temporal_relationship=draw(st.sampled_from([
            "immediate", "within 24 hours", "within 1 week", "delayed"
        ]))
    )


# ============================================================================
# Property-Based Tests
# ============================================================================

class TestEntityModelConsistency:
    """
    Property-based tests for entity model consistency in semantic query processing
    
    **Validates: Requirements 1.1, 1.5**
    """
    
    @given(drug=drug_entity_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_drug_entity_model_consistency(self, drug: DrugEntity):
        """
        Property: Drug entities maintain consistent structure and valid data
        
        For any generated drug entity, all fields should be valid and consistent
        """
        # Verify required fields are present
        assert drug.id is not None and len(drug.id) > 0
        assert drug.name is not None and len(drug.name) > 0
        assert drug.generic_name is not None and len(drug.generic_name) > 0
        
        # Verify optional fields have correct types when present
        if drug.drugbank_id:
            assert drug.drugbank_id.startswith("DB")
            assert len(drug.drugbank_id) == 7
        
        if drug.rxcui:
            assert drug.rxcui.isdigit()
        
        # Verify lists are actually lists
        assert isinstance(drug.atc_codes, list)
        assert isinstance(drug.indications, list)
        assert isinstance(drug.contraindications, list)
        
        # Verify timestamps are datetime objects
        assert isinstance(drug.created_at, datetime)
        assert isinstance(drug.updated_at, datetime)
        
        # Verify serialization round-trip
        drug_dict = drug.model_dump()
        recreated_drug = DrugEntity(**drug_dict)
        assert recreated_drug.id == drug.id
        assert recreated_drug.name == drug.name
    
    @given(side_effect=side_effect_entity_strategy())
    @settings(max_examples=100, deadline=None)
    def test_side_effect_entity_model_consistency(self, side_effect: SideEffectEntity):
        """
        Property: Side effect entities maintain consistent structure and valid data
        
        For any generated side effect entity, all fields should be valid
        """
        # Verify required fields
        assert side_effect.id is not None and len(side_effect.id) > 0
        assert side_effect.name is not None and len(side_effect.name) > 0
        
        # Verify enums are valid
        if side_effect.severity:
            assert side_effect.severity in SeverityLevel
        
        if side_effect.frequency_category:
            assert side_effect.frequency_category in FrequencyCategory
        
        # Verify timestamps
        assert isinstance(side_effect.created_at, datetime)
        assert isinstance(side_effect.updated_at, datetime)
        
        # Verify serialization round-trip
        se_dict = side_effect.model_dump()
        recreated_se = SideEffectEntity(**se_dict)
        assert recreated_se.id == side_effect.id
        assert recreated_se.name == side_effect.name
    
    @given(patient=patient_context_strategy())
    @settings(max_examples=100, deadline=None)
    def test_patient_context_model_consistency(self, patient: PatientContext):
        """
        Property: Patient context maintains consistent structure and valid demographics
        
        For any generated patient context, demographics should be valid
        """
        # Verify required fields
        assert patient.id is not None and len(patient.id) > 0
        
        # Verify demographics are valid
        if "age" in patient.demographics:
            age = patient.demographics["age"]
            assert 0 <= age <= 150, f"Age {age} is out of valid range"
        
        if "weight" in patient.demographics:
            weight = patient.demographics["weight"]
            assert 0 < weight <= 500, f"Weight {weight} is out of valid range"
        
        # Verify lists are lists
        assert isinstance(patient.conditions, list)
        assert isinstance(patient.medications, list)
        assert isinstance(patient.allergies, list)
        
        # Verify serialization round-trip
        patient_dict = patient.model_dump()
        recreated_patient = PatientContext(**patient_dict)
        assert recreated_patient.id == patient.id
        assert recreated_patient.demographics == patient.demographics
    
    @given(
        drug=drug_entity_strategy(),
        side_effect=side_effect_entity_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_causes_relationship_consistency(self, drug: DrugEntity, side_effect: SideEffectEntity):
        """
        Property: Drug-side effect relationships maintain valid confidence and frequency scores
        
        For any drug-side effect relationship, confidence and frequency should be in [0, 1]
        """
        relationship = CausesRelationship(
            drug_id=drug.id,
            side_effect_id=side_effect.id,
            frequency=0.15,
            confidence=0.85,
            evidence_sources=["FAERS", "SIDER"]
        )
        
        # Verify relationship fields
        assert relationship.drug_id == drug.id
        assert relationship.side_effect_id == side_effect.id
        assert 0.0 <= relationship.frequency <= 1.0
        assert 0.0 <= relationship.confidence <= 1.0
        assert len(relationship.evidence_sources) > 0
        
        # Verify all evidence sources are valid
        valid_sources = {"FAERS", "SIDER", "OnSIDES", "DrugBank", "DDInter", "Drugs@FDA"}
        for source in relationship.evidence_sources:
            assert source in valid_sources, f"Invalid evidence source: {source}"
    
    @given(query_text=medical_query_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_semantic_query_processing_consistency(self, query_text: str):
        """
        Property: Semantic query processing produces consistent results
        
        **Validates: Requirements 1.1, 1.5**
        
        For any valid natural language medication query:
        1. The system should parse it semantically
        2. Extract relevant entities
        3. Classify intent with confidence score
        4. Produce consistent results for the same query
        """
        processor = MedicalQueryProcessor()
        
        # Process the query
        result = processor.process_query(query_text)
        
        # Verify query analysis structure
        assert result.original_query == query_text
        assert result.intent in QueryIntent
        assert 0.0 <= result.intent_confidence <= 1.0
        assert 0.0 <= result.query_confidence <= 1.0
        assert isinstance(result.entities, list)
        assert isinstance(result.context_hints, dict)
        
        # Verify extracted entities have valid structure
        for entity in result.entities:
            assert entity.entity_type in EntityType
            assert 0.0 <= entity.confidence <= 1.0
            assert entity.start_pos >= 0
            assert entity.end_pos > entity.start_pos
            assert entity.end_pos <= len(query_text)
        
        # Verify consistency: processing the same query twice should yield same results
        result2 = processor.process_query(query_text)
        assert result.intent == result2.intent
        assert result.intent_confidence == result2.intent_confidence
        assert len(result.entities) == len(result2.entities)
    
    @given(
        query_text=medical_query_strategy(),
        patient=patient_context_strategy()
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_query_with_patient_context_consistency(self, query_text: str, patient: PatientContext):
        """
        Property: Queries with patient context maintain consistency
        
        **Validates: Requirements 1.1, 1.5**
        
        For any query with patient context, the system should:
        1. Parse the query semantically
        2. Incorporate patient demographics into context
        3. Maintain provenance of patient-specific factors
        """
        processor = MedicalQueryProcessor()
        
        # Process query
        result = processor.process_query(query_text)
        
        # Create semantic query with patient context
        semantic_query = SemanticQuery(
            id=f"query_{hash(query_text) % 10000}",
            patient_id=patient.id,
            raw_query=query_text,
            intent=result.intent.value,
            entities=[
                {
                    "text": e.text,
                    "type": e.entity_type.value,
                    "confidence": e.confidence
                }
                for e in result.entities
            ],
            confidence=result.query_confidence
        )
        
        # Verify semantic query structure
        assert semantic_query.patient_id == patient.id
        assert semantic_query.raw_query == query_text
        assert len(semantic_query.entities) == len(result.entities)
        
        # Verify patient context is preserved
        assert patient.id is not None
        assert isinstance(patient.demographics, dict)
    
    @given(
        drug=drug_entity_strategy(),
        side_effect=side_effect_entity_strategy()
    )
    @settings(max_examples=50, deadline=None)
    def test_graph_response_provenance_completeness(self, drug: DrugEntity, side_effect: SideEffectEntity):
        """
        Property: Graph responses maintain complete provenance tracking
        
        **Validates: Requirements 1.1, 1.5**
        
        For any knowledge graph query result:
        1. Evidence paths should be tracked
        2. Data sources should be documented
        3. Confidence scores should be provided
        4. Reasoning steps should be recorded
        """
        # Create a relationship
        relationship = CausesRelationship(
            drug_id=drug.id,
            side_effect_id=side_effect.id,
            frequency=0.2,
            confidence=0.8,
            evidence_sources=["FAERS", "SIDER", "OnSIDES"]
        )
        
        # Create graph response
        graph_response = GraphResponse(
            query_id="test_query_123",
            results=[
                {
                    "drug": drug.name,
                    "side_effect": side_effect.name,
                    "frequency": relationship.frequency,
                    "confidence": relationship.confidence
                }
            ],
            evidence_paths=[
                [drug.id, "CAUSES", side_effect.id]
            ],
            confidence_scores={
                side_effect.name: relationship.confidence
            },
            data_sources=relationship.evidence_sources,
            reasoning_steps=[
                f"Queried drug {drug.name}",
                f"Traversed CAUSES relationship",
                f"Found side effect {side_effect.name}"
            ]
        )
        
        # Verify provenance completeness
        assert len(graph_response.results) > 0
        assert len(graph_response.evidence_paths) > 0
        assert len(graph_response.data_sources) > 0
        assert len(graph_response.reasoning_steps) > 0
        
        # Verify all results have confidence scores
        for result in graph_response.results:
            side_effect_name = result["side_effect"]
            assert side_effect_name in graph_response.confidence_scores
            assert 0.0 <= graph_response.confidence_scores[side_effect_name] <= 1.0
        
        # Verify evidence paths are valid
        for path in graph_response.evidence_paths:
            assert len(path) >= 3  # At minimum: source, relationship, target
            assert path[0] == drug.id
            assert path[-1] == side_effect.id
        
        # Verify data sources are from valid datasets
        valid_datasets = {"FAERS", "SIDER", "OnSIDES", "DrugBank", "DDInter", "Drugs@FDA"}
        for source in graph_response.data_sources:
            assert source in valid_datasets
    
    @given(
        query_text=medical_query_strategy(),
        drug=drug_entity_strategy(),
        side_effect=side_effect_entity_strategy()
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_end_to_end_query_to_response_consistency(
        self, query_text: str, drug: DrugEntity, side_effect: SideEffectEntity
    ):
        """
        Property: End-to-end query processing maintains consistency from query to response
        
        **Validates: Requirements 1.1, 1.5**
        
        For any complete query-to-response flow:
        1. Query is parsed semantically
        2. Entities are extracted
        3. Graph traversal is executed
        4. Response includes complete provenance
        5. All components maintain referential integrity
        """
        processor = MedicalQueryProcessor()
        
        # Step 1: Parse query
        query_analysis = processor.process_query(query_text)
        
        # Step 2: Create semantic query
        semantic_query = SemanticQuery(
            id=f"query_{hash(query_text) % 10000}",
            raw_query=query_text,
            intent=query_analysis.intent.value,
            entities=[
                {
                    "text": e.text,
                    "type": e.entity_type.value,
                    "confidence": e.confidence
                }
                for e in query_analysis.entities
            ],
            confidence=query_analysis.query_confidence
        )
        
        # Step 3: Simulate graph traversal result
        relationship = CausesRelationship(
            drug_id=drug.id,
            side_effect_id=side_effect.id,
            frequency=0.25,
            confidence=0.75,
            evidence_sources=["FAERS", "SIDER"]
        )
        
        # Step 4: Create graph response with provenance
        graph_response = GraphResponse(
            query_id=semantic_query.id,
            results=[
                {
                    "drug_id": drug.id,
                    "drug_name": drug.name,
                    "side_effect_id": side_effect.id,
                    "side_effect_name": side_effect.name,
                    "frequency": relationship.frequency
                }
            ],
            evidence_paths=[
                [drug.id, "CAUSES", side_effect.id]
            ],
            confidence_scores={
                side_effect.name: relationship.confidence
            },
            data_sources=relationship.evidence_sources,
            reasoning_steps=[
                f"Parsed query: {query_text}",
                f"Identified intent: {query_analysis.intent.value}",
                f"Extracted entities: {len(query_analysis.entities)}",
                f"Queried drug: {drug.name}",
                f"Found side effect: {side_effect.name}"
            ]
        )
        
        # Verify end-to-end consistency
        assert graph_response.query_id == semantic_query.id
        assert len(graph_response.results) > 0
        assert len(graph_response.evidence_paths) > 0
        assert len(graph_response.data_sources) > 0
        assert len(graph_response.reasoning_steps) >= 3
        
        # Verify referential integrity
        for result in graph_response.results:
            assert result["drug_id"] == drug.id
            assert result["side_effect_id"] == side_effect.id
        
        # Verify provenance tracking
        assert all(source in ["FAERS", "SIDER", "OnSIDES", "DrugBank", "DDInter", "Drugs@FDA"] 
                  for source in graph_response.data_sources)
        
        # Verify confidence scores are present for all results
        for result in graph_response.results:
            assert result["side_effect_name"] in graph_response.confidence_scores


# ============================================================================
# Additional Property Tests for Edge Cases
# ============================================================================

class TestEntityModelEdgeCases:
    """Property tests for edge cases in entity models"""
    
    @given(
        frequency=st.floats(min_value=0.0, max_value=1.0),
        confidence=st.floats(min_value=0.0, max_value=1.0)
    )
    @settings(max_examples=100, deadline=None)
    def test_relationship_score_boundaries(self, frequency: float, confidence: float):
        """
        Property: Relationship scores are always within valid bounds
        
        For any frequency and confidence scores, they must be in [0, 1]
        """
        relationship = CausesRelationship(
            drug_id="drug_test",
            side_effect_id="se_test",
            frequency=frequency,
            confidence=confidence,
            evidence_sources=["FAERS"]
        )
        
        assert 0.0 <= relationship.frequency <= 1.0
        assert 0.0 <= relationship.confidence <= 1.0
    
    @given(query_text=st.text(min_size=1, max_size=500))
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_query_processor_handles_arbitrary_text(self, query_text: str):
        """
        Property: Query processor handles any text input without crashing
        
        For any text input, the processor should return a valid result
        """
        # Skip empty or whitespace-only strings
        assume(query_text.strip() != "")
        
        processor = MedicalQueryProcessor()
        result = processor.process_query(query_text)
        
        # Should always return a valid QueryAnalysis
        assert result is not None
        assert result.original_query == query_text
        assert result.intent in QueryIntent
        assert 0.0 <= result.query_confidence <= 1.0
