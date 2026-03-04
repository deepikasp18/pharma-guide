"""
Unit tests for query translation service
"""
import pytest
from src.nlp.query_processor import (
    QueryIntent, EntityType, ExtractedEntity, QueryAnalysis
)
from src.nlp.query_translator import (
    QueryTranslator, QueryOptimizer, GremlinQuery, QueryProvenance
)


class TestQueryOptimizer:
    """Test query optimization functionality"""
    
    def test_optimizer_adds_limit_to_unlimited_queries(self):
        """Test that optimizer adds limit to queries without one"""
        optimizer = QueryOptimizer()
        
        query = GremlinQuery(
            query_string="g.V().hasLabel('Drug').toList()",
            parameters={},
            explanation="Test query",
            optimization_hints=[],
            estimated_complexity="low"
        )
        
        optimized = optimizer.optimize_query(query)
        
        assert ".limit(" in optimized.query_string
        assert "Added result limit" in " ".join(optimized.optimization_hints)
    
    def test_optimizer_adds_dedup_to_traversals(self):
        """Test that optimizer adds deduplication to edge traversals"""
        optimizer = QueryOptimizer()
        
        query = GremlinQuery(
            query_string="g.V().hasLabel('Drug').outE('CAUSES').inV().toList()",
            parameters={},
            explanation="Test query",
            optimization_hints=[],
            estimated_complexity="low"
        )
        
        optimized = optimizer.optimize_query(query)
        
        assert ".dedup()" in optimized.query_string
        assert "deduplication" in " ".join(optimized.optimization_hints).lower()
    
    def test_optimizer_detects_high_complexity(self):
        """Test that optimizer detects high complexity queries"""
        optimizer = QueryOptimizer()
        
        # Multi-hop traversal query
        query = GremlinQuery(
            query_string="g.V().outE('A').inV().outE('B').inV().outE('C').inV().toList()",
            parameters={},
            explanation="Test query",
            optimization_hints=[],
            estimated_complexity="low"
        )
        
        optimized = optimizer.optimize_query(query)
        
        assert optimized.estimated_complexity == "high"
        assert any("multi-hop" in hint.lower() for hint in optimized.optimization_hints)
    
    def test_estimate_query_cost(self):
        """Test query cost estimation"""
        optimizer = QueryOptimizer()
        
        query = GremlinQuery(
            query_string="g.V().hasLabel('Drug').has('name', 'Aspirin').outE('CAUSES').inV().limit(10).toList()",
            parameters={},
            explanation="Test query",
            optimization_hints=[],
            estimated_complexity="low"
        )
        
        cost = optimizer.estimate_query_cost(query)
        
        assert "cost_score" in cost
        assert "complexity" in cost
        assert "factors" in cost
        assert cost["factors"]["has_limit"] is True
    
    def test_cost_recommendations_for_expensive_query(self):
        """Test that cost recommendations are provided for expensive queries"""
        optimizer = QueryOptimizer()
        
        # Expensive query without limit
        query = GremlinQuery(
            query_string="g.V().outE('A').inV().outE('B').inV().outE('C').inV().toList()",
            parameters={},
            explanation="Test query",
            optimization_hints=[],
            estimated_complexity="low"
        )
        
        cost = optimizer.estimate_query_cost(query)
        
        assert len(cost["recommendations"]) > 0
        assert any("limit" in rec.lower() for rec in cost["recommendations"])


class TestQueryTranslator:
    """Test query translation functionality"""
    
    def test_translate_side_effects_query(self):
        """Test translation of side effects query"""
        translator = QueryTranslator()
        
        # Create mock query analysis
        analysis = QueryAnalysis(
            original_query="What are the side effects of Lisinopril?",
            intent=QueryIntent.SIDE_EFFECTS,
            intent_confidence=0.9,
            entities=[
                ExtractedEntity(
                    text="Lisinopril",
                    entity_type=EntityType.DRUG,
                    confidence=0.95,
                    start_pos=28,
                    end_pos=38,
                    normalized_form="lisinopril"
                )
            ],
            query_confidence=0.92,
            normalized_query="What are the side effects of Lisinopril?",
            context_hints={}
        )
        
        query, provenance = translator.translate_query(analysis)
        
        assert "Drug" in query.query_string
        assert "lisinopril" in query.query_string
        assert "CAUSES" in query.query_string
        assert query.parameters.get('drug_name') == 'lisinopril'
        assert provenance.query_id is not None
        assert "OnSIDES" in provenance.data_sources or "SIDER" in provenance.data_sources
    
    def test_translate_side_effects_with_patient_context(self):
        """Test side effects query with patient context"""
        translator = QueryTranslator()
        
        analysis = QueryAnalysis(
            original_query="What are the side effects of Lisinopril for a 65-year-old?",
            intent=QueryIntent.SIDE_EFFECTS,
            intent_confidence=0.9,
            entities=[
                ExtractedEntity(
                    text="Lisinopril",
                    entity_type=EntityType.DRUG,
                    confidence=0.95,
                    start_pos=28,
                    end_pos=38,
                    normalized_form="lisinopril"
                ),
                ExtractedEntity(
                    text="65",
                    entity_type=EntityType.AGE,
                    confidence=0.9,
                    start_pos=45,
                    end_pos=47,
                    normalized_form="65"
                )
            ],
            query_confidence=0.92,
            normalized_query="What are the side effects of Lisinopril for a 65-year-old?",
            context_hints={'patient_context': {'age': '65'}}
        )
        
        patient_context = {
            'demographics': {'age': 65},
            'risk_factors': ['hypertension']
        }
        
        query, provenance = translator.translate_query(analysis, patient_context)
        
        assert "confidence" in query.query_string
        assert "P.gte(0.7)" in query.query_string  # Higher confidence threshold for risk factors
        assert query.parameters.get('patient_age') == 65
    
    def test_translate_drug_interactions_query(self):
        """Test translation of drug interactions query"""
        translator = QueryTranslator()
        
        analysis = QueryAnalysis(
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
        
        query, provenance = translator.translate_query(analysis)
        
        assert "INTERACTS_WITH" in query.query_string
        assert "lisinopril" in query.query_string
        assert "ibuprofen" in query.query_string
        assert query.parameters.get('drug_a') == 'lisinopril'
        assert query.parameters.get('drug_b') == 'ibuprofen'
        assert "DDInter" in provenance.data_sources or "DrugBank" in provenance.data_sources
    
    def test_translate_interactions_with_patient_medications(self):
        """Test interactions query using patient's current medications"""
        translator = QueryTranslator()
        
        analysis = QueryAnalysis(
            original_query="Can I take Aspirin?",
            intent=QueryIntent.DRUG_INTERACTIONS,
            intent_confidence=0.8,
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
            query_confidence=0.87,
            normalized_query="Can I take Aspirin?",
            context_hints={}
        )
        
        patient_context = {
            'medications': [
                {'name': 'Lisinopril', 'dosage': '10mg'},
                {'name': 'Metformin', 'dosage': '500mg'}
            ]
        }
        
        query, provenance = translator.translate_query(analysis, patient_context)
        
        assert "INTERACTS_WITH" in query.query_string
        assert "aspirin" in query.query_string
        assert query.parameters.get('patient_medications') is not None
    
    def test_translate_dosing_query(self):
        """Test translation of dosing query"""
        translator = QueryTranslator()
        
        analysis = QueryAnalysis(
            original_query="What is the dosage for Metformin?",
            intent=QueryIntent.DOSING,
            intent_confidence=0.9,
            entities=[
                ExtractedEntity(
                    text="Metformin",
                    entity_type=EntityType.DRUG,
                    confidence=0.95,
                    start_pos=23,
                    end_pos=32,
                    normalized_form="metformin"
                )
            ],
            query_confidence=0.92,
            normalized_query="What is the dosage for Metformin?",
            context_hints={}
        )
        
        query, provenance = translator.translate_query(analysis)
        
        assert "Drug" in query.query_string
        assert "metformin" in query.query_string
        assert query.parameters.get('drug_name') == 'metformin'
    
    def test_translate_contraindications_query(self):
        """Test translation of contraindications query"""
        translator = QueryTranslator()
        
        analysis = QueryAnalysis(
            original_query="Can I take Aspirin if I have asthma?",
            intent=QueryIntent.CONTRAINDICATIONS,
            intent_confidence=0.85,
            entities=[
                ExtractedEntity(
                    text="Aspirin",
                    entity_type=EntityType.DRUG,
                    confidence=0.95,
                    start_pos=11,
                    end_pos=18,
                    normalized_form="aspirin"
                ),
                ExtractedEntity(
                    text="asthma",
                    entity_type=EntityType.CONDITION,
                    confidence=0.9,
                    start_pos=29,
                    end_pos=35,
                    normalized_form="asthma"
                )
            ],
            query_confidence=0.87,
            normalized_query="Can I take Aspirin if I have asthma?",
            context_hints={}
        )
        
        query, provenance = translator.translate_query(analysis)
        
        assert "CONTRAINDICATED_WITH" in query.query_string
        assert "aspirin" in query.query_string
        assert "asthma" in query.query_string
        assert query.parameters.get('condition') == 'asthma'
    
    def test_translate_alternatives_query(self):
        """Test translation of alternatives query"""
        translator = QueryTranslator()
        
        analysis = QueryAnalysis(
            original_query="What are alternatives to Ibuprofen?",
            intent=QueryIntent.ALTERNATIVES,
            intent_confidence=0.9,
            entities=[
                ExtractedEntity(
                    text="Ibuprofen",
                    entity_type=EntityType.DRUG,
                    confidence=0.95,
                    start_pos=25,
                    end_pos=34,
                    normalized_form="ibuprofen"
                )
            ],
            query_confidence=0.92,
            normalized_query="What are alternatives to Ibuprofen?",
            context_hints={}
        )
        
        query, provenance = translator.translate_query(analysis)
        
        assert "TREATS" in query.query_string
        assert "ibuprofen" in query.query_string
        assert ".dedup()" in query.query_string
        assert query.estimated_complexity == "high"  # Multi-hop traversal
    
    def test_translate_effectiveness_query(self):
        """Test translation of effectiveness query"""
        translator = QueryTranslator()
        
        analysis = QueryAnalysis(
            original_query="How effective is Metformin for diabetes?",
            intent=QueryIntent.EFFECTIVENESS,
            intent_confidence=0.85,
            entities=[
                ExtractedEntity(
                    text="Metformin",
                    entity_type=EntityType.DRUG,
                    confidence=0.95,
                    start_pos=17,
                    end_pos=26,
                    normalized_form="metformin"
                ),
                ExtractedEntity(
                    text="diabetes",
                    entity_type=EntityType.CONDITION,
                    confidence=0.9,
                    start_pos=31,
                    end_pos=39,
                    normalized_form="diabetes"
                )
            ],
            query_confidence=0.87,
            normalized_query="How effective is Metformin for diabetes?",
            context_hints={}
        )
        
        query, provenance = translator.translate_query(analysis)
        
        assert "TREATS" in query.query_string
        assert "metformin" in query.query_string
        assert "diabetes" in query.query_string
        assert "efficacy" in query.query_string
    
    def test_translate_general_info_query(self):
        """Test translation of general information query"""
        translator = QueryTranslator()
        
        analysis = QueryAnalysis(
            original_query="Tell me about Aspirin",
            intent=QueryIntent.GENERAL_INFO,
            intent_confidence=0.8,
            entities=[
                ExtractedEntity(
                    text="Aspirin",
                    entity_type=EntityType.DRUG,
                    confidence=0.95,
                    start_pos=14,
                    end_pos=21,
                    normalized_form="aspirin"
                )
            ],
            query_confidence=0.87,
            normalized_query="Tell me about Aspirin",
            context_hints={}
        )
        
        query, provenance = translator.translate_query(analysis)
        
        assert "Drug" in query.query_string
        assert "aspirin" in query.query_string
        assert query.estimated_complexity == "low"
    
    def test_translate_query_without_entities(self):
        """Test handling of query without entities"""
        translator = QueryTranslator()
        
        analysis = QueryAnalysis(
            original_query="What are side effects?",
            intent=QueryIntent.SIDE_EFFECTS,
            intent_confidence=0.7,
            entities=[],
            query_confidence=0.5,
            normalized_query="What are side effects?",
            context_hints={}
        )
        
        query, provenance = translator.translate_query(analysis)
        
        # Should return empty query
        assert ".limit(0)" in query.query_string
        assert "no drugs specified" in query.explanation.lower()
    
    def test_explain_query(self):
        """Test query explanation generation"""
        translator = QueryTranslator()
        
        analysis = QueryAnalysis(
            original_query="What are the side effects of Aspirin?",
            intent=QueryIntent.SIDE_EFFECTS,
            intent_confidence=0.9,
            entities=[
                ExtractedEntity(
                    text="Aspirin",
                    entity_type=EntityType.DRUG,
                    confidence=0.95,
                    start_pos=28,
                    end_pos=35,
                    normalized_form="aspirin"
                )
            ],
            query_confidence=0.92,
            normalized_query="What are the side effects of Aspirin?",
            context_hints={}
        )
        
        query, provenance = translator.translate_query(analysis)
        explanation = translator.explain_query(query, provenance)
        
        assert "query_id" in explanation
        assert "original_question" in explanation
        assert "intent" in explanation
        assert "entities_found" in explanation
        assert "graph_query_explanation" in explanation
        assert "optimization_applied" in explanation
        assert "complexity" in explanation
        assert "data_sources" in explanation
        assert "reasoning_steps" in explanation
        assert "estimated_cost" in explanation
    
    def test_provenance_tracking(self):
        """Test that provenance is properly tracked"""
        translator = QueryTranslator()
        
        analysis = QueryAnalysis(
            original_query="Can Lisinopril interact with Ibuprofen?",
            intent=QueryIntent.DRUG_INTERACTIONS,
            intent_confidence=0.85,
            entities=[
                ExtractedEntity(
                    text="Lisinopril",
                    entity_type=EntityType.DRUG,
                    confidence=0.95,
                    start_pos=4,
                    end_pos=14,
                    normalized_form="lisinopril"
                ),
                ExtractedEntity(
                    text="Ibuprofen",
                    entity_type=EntityType.DRUG,
                    confidence=0.95,
                    start_pos=29,
                    end_pos=38,
                    normalized_form="ibuprofen"
                )
            ],
            query_confidence=0.90,
            normalized_query="Can Lisinopril interact with Ibuprofen?",
            context_hints={}
        )
        
        query, provenance = translator.translate_query(analysis)
        
        assert provenance.query_id is not None
        assert provenance.original_query == analysis.original_query
        assert provenance.intent == str(QueryIntent.DRUG_INTERACTIONS)
        assert len(provenance.entities) == 2
        assert provenance.gremlin_query == query.query_string
        assert len(provenance.reasoning_steps) > 0
        assert len(provenance.data_sources) > 0
        assert "DDInter" in provenance.data_sources or "DrugBank" in provenance.data_sources


class TestQueryTranslatorEdgeCases:
    """Test edge cases and error handling"""
    
    def test_unknown_intent(self):
        """Test handling of unknown intent"""
        translator = QueryTranslator()
        
        analysis = QueryAnalysis(
            original_query="Random query",
            intent=QueryIntent.UNKNOWN,
            intent_confidence=0.3,
            entities=[],
            query_confidence=0.3,
            normalized_query="Random query",
            context_hints={}
        )
        
        query, provenance = translator.translate_query(analysis)
        
        # Should fall back to general info query
        assert query.query_string is not None
        assert provenance.query_id is not None
    
    def test_multiple_drugs_in_side_effects_query(self):
        """Test that only first drug is used for side effects query"""
        translator = QueryTranslator()
        
        analysis = QueryAnalysis(
            original_query="What are the side effects of Aspirin and Ibuprofen?",
            intent=QueryIntent.SIDE_EFFECTS,
            intent_confidence=0.8,
            entities=[
                ExtractedEntity(
                    text="Aspirin",
                    entity_type=EntityType.DRUG,
                    confidence=0.95,
                    start_pos=33,
                    end_pos=40,
                    normalized_form="aspirin"
                ),
                ExtractedEntity(
                    text="Ibuprofen",
                    entity_type=EntityType.DRUG,
                    confidence=0.95,
                    start_pos=45,
                    end_pos=54,
                    normalized_form="ibuprofen"
                )
            ],
            query_confidence=0.87,
            normalized_query="What are the side effects of Aspirin and Ibuprofen?",
            context_hints={}
        )
        
        query, provenance = translator.translate_query(analysis)
        
        # Should use first drug
        assert "aspirin" in query.query_string
        assert query.parameters.get('drug_name') == 'aspirin'
