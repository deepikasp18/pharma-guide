"""
Tests for query translation service
"""
import pytest
from src.nlp.query_processor import (
    QueryAnalysis, QueryIntent, EntityType, ExtractedEntity
)
from src.nlp.query_translator import (
    QueryTranslator, QueryType, GraphQuery, QueryExplanation, ProvenanceInfo
)


@pytest.fixture
def query_translator():
    """Create query translator instance"""
    return QueryTranslator()


@pytest.fixture
def sample_side_effects_query():
    """Sample query analysis for side effects"""
    return QueryAnalysis(
        original_query="What are the side effects of Lisinopril?",
        intent=QueryIntent.SIDE_EFFECTS,
        intent_confidence=0.9,
        entities=[
            ExtractedEntity(
                text="Lisinopril",
                entity_type=EntityType.DRUG,
                confidence=0.95,
                start_pos=27,
                end_pos=37,
                normalized_form="lisinopril"
            )
        ],
        query_confidence=0.92,
        normalized_query="What are the side effects of Lisinopril?",
        context_hints={}
    )


@pytest.fixture
def sample_interaction_query():
    """Sample query analysis for drug interactions"""
    return QueryAnalysis(
        original_query="Can I take Lisinopril with Ibuprofen?",
        intent=QueryIntent.DRUG_INTERACTIONS,
        intent_confidence=0.85,
        entities=[
            ExtractedEntity(
                text="Lisinopril",
                entity_type=EntityType.DRUG,
                confidence=0.95,
                start_pos=11,
                end_pos=21,
                normalized_form="lisinopril"
            ),
            ExtractedEntity(
                text="Ibuprofen",
                entity_type=EntityType.DRUG,
                confidence=0.95,
                start_pos=27,
                end_pos=36,
                normalized_form="ibuprofen"
            )
        ],
        query_confidence=0.90,
        normalized_query="Can I take Lisinopril with Ibuprofen?",
        context_hints={}
    )


@pytest.fixture
def sample_patient_context():
    """Sample patient context"""
    return {
        'demographics': {
            'age': 65,
            'gender': 'male',
            'weight': 180
        },
        'conditions': ['diabetes', 'hypertension'],
        'medications': [
            {'name': 'metformin', 'dosage': '500mg'},
            {'name': 'lisinopril', 'dosage': '10mg'}
        ],
        'risk_factors': ['smoking', 'obesity']
    }


class TestQueryTranslator:
    """Test query translator functionality"""
    
    def test_translate_side_effects_query(self, query_translator, sample_side_effects_query):
        """Test translation of side effects query"""
        graph_query, explanation = query_translator.translate_query(sample_side_effects_query)
        
        # Verify graph query structure
        assert isinstance(graph_query, GraphQuery)
        assert graph_query.query_type == QueryType.RELATIONSHIP_TRAVERSAL
        assert "hasLabel('Drug')" in graph_query.gremlin_query
        assert "outE('CAUSES')" in graph_query.gremlin_query
        assert "lisinopril" in graph_query.gremlin_query.lower()
        
        # Verify parameters
        assert "drug_name" in graph_query.parameters
        assert graph_query.parameters["drug_name"] == "lisinopril"
        
        # Verify optimization hints
        assert len(graph_query.optimization_hints) > 0
        assert graph_query.estimated_complexity > 0
        
        # Verify explanation
        assert isinstance(explanation, QueryExplanation)
        assert explanation.intent == QueryIntent.SIDE_EFFECTS
        assert len(explanation.translation_steps) > 0
        assert len(explanation.extracted_entities) == 1
        assert explanation.confidence > 0
    
    def test_translate_interaction_query(self, query_translator, sample_interaction_query):
        """Test translation of drug interaction query"""
        graph_query, explanation = query_translator.translate_query(sample_interaction_query)
        
        # Verify graph query structure
        assert isinstance(graph_query, GraphQuery)
        assert graph_query.query_type == QueryType.RELATIONSHIP_TRAVERSAL
        assert "INTERACTS_WITH" in graph_query.gremlin_query
        assert "lisinopril" in graph_query.gremlin_query.lower()
        assert "ibuprofen" in graph_query.gremlin_query.lower()
        
        # Verify parameters
        assert "drug_a" in graph_query.parameters
        assert "drug_b" in graph_query.parameters
        
        # Verify explanation
        assert explanation.intent == QueryIntent.DRUG_INTERACTIONS
        assert len(explanation.extracted_entities) == 2
    
    def test_translate_with_patient_context(
        self, query_translator, sample_side_effects_query, sample_patient_context
    ):
        """Test translation with patient context"""
        graph_query, explanation = query_translator.translate_query(
            sample_side_effects_query,
            patient_context=sample_patient_context
        )
        
        # Verify patient context affects query
        assert isinstance(graph_query, GraphQuery)
        # Should have confidence threshold adjusted for patient risk factors
        assert "confidence" in graph_query.gremlin_query
    
    def test_query_optimization(self, query_translator, sample_side_effects_query):
        """Test query optimization"""
        graph_query, _ = query_translator.translate_query(sample_side_effects_query)
        
        # Verify optimization hints are present
        assert len(graph_query.optimization_hints) > 0
        
        # Verify complexity estimation
        assert 1 <= graph_query.estimated_complexity <= 10
    
    def test_cypher_query_generation(self, query_translator, sample_side_effects_query):
        """Test Cypher query generation for future compatibility"""
        graph_query, _ = query_translator.translate_query(sample_side_effects_query)
        
        # Verify Cypher query is generated
        assert graph_query.cypher_query is not None
        assert "MATCH" in graph_query.cypher_query
        assert "RETURN" in graph_query.cypher_query
    
    def test_provenance_creation(self, query_translator):
        """Test provenance information creation"""
        graph_query = GraphQuery(
            query_type=QueryType.RELATIONSHIP_TRAVERSAL,
            gremlin_query="g.V().hasLabel('Drug').outE('CAUSES').inV()",
            cypher_query=None,
            parameters={"drug_name": "lisinopril"},
            optimization_hints=["index_lookup"],
            estimated_complexity=3
        )
        
        provenance = query_translator.create_provenance_info(
            query_id="test-123",
            graph_query=graph_query,
            data_sources=["OnSIDES", "SIDER"],
            confidence_scores={"result1": 0.9, "result2": 0.8}
        )
        
        # Verify provenance structure
        assert isinstance(provenance, ProvenanceInfo)
        assert provenance.query_id == "test-123"
        assert len(provenance.data_sources) == 2
        assert len(provenance.traversal_path) > 0
        assert len(provenance.confidence_scores) == 2
        assert len(provenance.reasoning_steps) > 0
    
    def test_fallback_query(self, query_translator):
        """Test fallback query when translation fails"""
        # Create query with no entities
        empty_query = QueryAnalysis(
            original_query="Tell me about medications",
            intent=QueryIntent.GENERAL_INFO,
            intent_confidence=0.5,
            entities=[],
            query_confidence=0.4,
            normalized_query="Tell me about medications",
            context_hints={}
        )
        
        graph_query, explanation = query_translator.translate_query(empty_query)
        
        # Verify fallback query is generated
        assert isinstance(graph_query, GraphQuery)
        assert graph_query.query_type == QueryType.SIMPLE_LOOKUP
        assert explanation.confidence < 0.5
    
    def test_dosing_query_translation(self, query_translator):
        """Test dosing query translation"""
        dosing_query = QueryAnalysis(
            original_query="What is the dosage for Lisinopril?",
            intent=QueryIntent.DOSING,
            intent_confidence=0.88,
            entities=[
                ExtractedEntity(
                    text="Lisinopril",
                    entity_type=EntityType.DRUG,
                    confidence=0.95,
                    start_pos=24,
                    end_pos=34,
                    normalized_form="lisinopril"
                )
            ],
            query_confidence=0.91,
            normalized_query="What is the dosage for Lisinopril?",
            context_hints={}
        )
        
        graph_query, explanation = query_translator.translate_query(dosing_query)
        
        # Verify dosing query structure
        assert graph_query.query_type == QueryType.SIMPLE_LOOKUP
        assert "dosage_forms" in graph_query.gremlin_query
        assert explanation.intent == QueryIntent.DOSING
    
    def test_contraindications_query_translation(self, query_translator):
        """Test contraindications query translation"""
        contraindication_query = QueryAnalysis(
            original_query="Can I take Lisinopril if I have diabetes?",
            intent=QueryIntent.CONTRAINDICATIONS,
            intent_confidence=0.82,
            entities=[
                ExtractedEntity(
                    text="Lisinopril",
                    entity_type=EntityType.DRUG,
                    confidence=0.95,
                    start_pos=11,
                    end_pos=21,
                    normalized_form="lisinopril"
                ),
                ExtractedEntity(
                    text="diabetes",
                    entity_type=EntityType.CONDITION,
                    confidence=0.90,
                    start_pos=33,
                    end_pos=41,
                    normalized_form="diabetes"
                )
            ],
            query_confidence=0.86,
            normalized_query="Can I take Lisinopril if I have diabetes?",
            context_hints={}
        )
        
        graph_query, explanation = query_translator.translate_query(contraindication_query)
        
        # Verify contraindication query structure
        assert graph_query.query_type == QueryType.RELATIONSHIP_TRAVERSAL
        assert "CONTRAINDICATED_WITH" in graph_query.gremlin_query or "contraindications" in graph_query.gremlin_query
        assert explanation.intent == QueryIntent.CONTRAINDICATIONS
    
    def test_alternatives_query_translation(self, query_translator):
        """Test alternatives query translation"""
        alternatives_query = QueryAnalysis(
            original_query="What are alternatives to Lisinopril?",
            intent=QueryIntent.ALTERNATIVES,
            intent_confidence=0.87,
            entities=[
                ExtractedEntity(
                    text="Lisinopril",
                    entity_type=EntityType.DRUG,
                    confidence=0.95,
                    start_pos=25,
                    end_pos=35,
                    normalized_form="lisinopril"
                )
            ],
            query_confidence=0.91,
            normalized_query="What are alternatives to Lisinopril?",
            context_hints={}
        )
        
        graph_query, explanation = query_translator.translate_query(alternatives_query)
        
        # Verify alternatives query structure
        assert graph_query.query_type == QueryType.MULTI_HOP
        assert "union" in graph_query.gremlin_query.lower()
        assert explanation.intent == QueryIntent.ALTERNATIVES
    
    def test_multi_drug_interaction_with_patient_meds(
        self, query_translator, sample_patient_context
    ):
        """Test interaction query with patient's current medications"""
        single_drug_query = QueryAnalysis(
            original_query="Can I take Aspirin with my current medications?",
            intent=QueryIntent.DRUG_INTERACTIONS,
            intent_confidence=0.85,
            entities=[
                ExtractedEntity(
                    text="Aspirin",
                    entity_type=EntityType.DRUG,
                    confidence=0.95,
                    start_pos=11,
                    end_pos=18,
                    normalized_form="aspirin"
                )
            ],
            query_confidence=0.88,
            normalized_query="Can I take Aspirin with my current medications?",
            context_hints={}
        )
        
        graph_query, explanation = query_translator.translate_query(
            single_drug_query,
            patient_context=sample_patient_context
        )
        
        # Verify multi-drug interaction query
        assert graph_query.query_type == QueryType.MULTI_HOP
        assert "new_drug" in graph_query.parameters
        assert "existing_drugs" in graph_query.parameters
    
    def test_explanation_completeness(self, query_translator, sample_side_effects_query):
        """Test that explanation contains all required information"""
        _, explanation = query_translator.translate_query(sample_side_effects_query)
        
        # Verify all explanation fields are populated
        assert explanation.original_query
        assert explanation.intent
        assert len(explanation.extracted_entities) > 0
        assert len(explanation.translation_steps) > 0
        assert explanation.graph_traversal_description
        assert len(explanation.expected_result_types) > 0
        assert 0 <= explanation.confidence <= 1
    
    def test_traversal_path_extraction(self, query_translator):
        """Test extraction of traversal path from query"""
        graph_query = GraphQuery(
            query_type=QueryType.RELATIONSHIP_TRAVERSAL,
            gremlin_query="g.V().hasLabel('Drug').outE('CAUSES').inV()",
            cypher_query=None,
            parameters={},
            optimization_hints=[],
            estimated_complexity=3
        )
        
        path = query_translator._extract_traversal_path(graph_query)
        
        # Verify path extraction
        assert len(path) > 0
        assert "Drug" in path
        assert "CAUSES" in path
        assert "SideEffect" in path
    
    def test_confidence_threshold_calculation(self, query_translator):
        """Test confidence threshold calculation based on patient risk"""
        # Low risk patient
        low_risk_context = {
            'risk_factors': ['none']
        }
        threshold_low = query_translator._calculate_confidence_threshold(low_risk_context)
        
        # High risk patient
        high_risk_context = {
            'risk_factors': ['smoking', 'obesity', 'diabetes', 'hypertension', 'heart_disease']
        }
        threshold_high = query_translator._calculate_confidence_threshold(high_risk_context)
        
        # High risk should have higher threshold
        assert threshold_high > threshold_low
        assert 0.7 <= threshold_low <= 1.0
        assert 0.7 <= threshold_high <= 1.0


class TestQueryOptimization:
    """Test query optimization strategies"""
    
    def test_early_limit_optimization(self, query_translator):
        """Test that multi-hop queries get early limits"""
        alternatives_query = QueryAnalysis(
            original_query="What are alternatives to Lisinopril?",
            intent=QueryIntent.ALTERNATIVES,
            intent_confidence=0.87,
            entities=[
                ExtractedEntity(
                    text="Lisinopril",
                    entity_type=EntityType.DRUG,
                    confidence=0.95,
                    start_pos=25,
                    end_pos=35,
                    normalized_form="lisinopril"
                )
            ],
            query_confidence=0.91,
            normalized_query="What are alternatives to Lisinopril?",
            context_hints={}
        )
        
        graph_query, _ = query_translator.translate_query(alternatives_query)
        
        # Multi-hop queries should have limits
        assert graph_query.query_type == QueryType.MULTI_HOP
        assert ".limit(" in graph_query.gremlin_query
    
    def test_cache_candidate_identification(self, query_translator, sample_side_effects_query):
        """Test identification of queries suitable for caching"""
        # High confidence query should be cache candidate
        sample_side_effects_query.query_confidence = 0.95
        
        graph_query, _ = query_translator.translate_query(sample_side_effects_query)
        
        # Should be marked as cache candidate
        assert "cache_candidate" in graph_query.optimization_hints


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_entity_list(self, query_translator):
        """Test handling of query with no entities"""
        empty_query = QueryAnalysis(
            original_query="Tell me about drugs",
            intent=QueryIntent.GENERAL_INFO,
            intent_confidence=0.5,
            entities=[],
            query_confidence=0.4,
            normalized_query="Tell me about drugs",
            context_hints={}
        )
        
        graph_query, explanation = query_translator.translate_query(empty_query)
        
        # Should return fallback query
        assert isinstance(graph_query, GraphQuery)
        assert isinstance(explanation, QueryExplanation)
    
    def test_unknown_intent(self, query_translator):
        """Test handling of unknown intent"""
        unknown_query = QueryAnalysis(
            original_query="Random question",
            intent=QueryIntent.UNKNOWN,
            intent_confidence=0.3,
            entities=[],
            query_confidence=0.2,
            normalized_query="Random question",
            context_hints={}
        )
        
        graph_query, explanation = query_translator.translate_query(unknown_query)
        
        # Should handle gracefully
        assert isinstance(graph_query, GraphQuery)
        assert isinstance(explanation, QueryExplanation)
    
    def test_single_drug_interaction_query(self, query_translator):
        """Test interaction query with only one drug (should use fallback)"""
        single_drug_query = QueryAnalysis(
            original_query="What interactions does Lisinopril have?",
            intent=QueryIntent.DRUG_INTERACTIONS,
            intent_confidence=0.80,
            entities=[
                ExtractedEntity(
                    text="Lisinopril",
                    entity_type=EntityType.DRUG,
                    confidence=0.95,
                    start_pos=22,
                    end_pos=32,
                    normalized_form="lisinopril"
                )
            ],
            query_confidence=0.87,
            normalized_query="What interactions does Lisinopril have?",
            context_hints={}
        )
        
        # Without patient context, should use fallback
        graph_query, explanation = query_translator.translate_query(single_drug_query)
        
        # Should handle gracefully
        assert isinstance(graph_query, GraphQuery)
