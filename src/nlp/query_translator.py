"""
Query translation service for converting natural language to Gremlin graph queries
"""
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from .query_processor import QueryIntent, EntityType, QueryAnalysis
from src.knowledge_graph.models import SemanticQuery

logger = logging.getLogger(__name__)


@dataclass
class GremlinQuery:
    """Gremlin query with metadata"""
    query_string: str
    parameters: Dict[str, Any]
    explanation: str
    optimization_hints: List[str]
    estimated_complexity: str  # "low", "medium", "high"


@dataclass
class QueryProvenance:
    """Query provenance tracking"""
    query_id: str
    original_query: str
    intent: str
    entities: List[Dict[str, Any]]
    gremlin_query: str
    reasoning_steps: List[str]
    data_sources: List[str]


class QueryOptimizer:
    """Optimizes Gremlin queries for efficient graph traversal"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def optimize_query(self, query: GremlinQuery) -> GremlinQuery:
        """Optimize a Gremlin query for better performance"""
        optimizations = []
        optimized_query = query.query_string
        
        # Add index hints for property lookups
        if ".has(" in optimized_query and ".hasLabel(" in optimized_query:
            optimizations.append("Using label and property filters for efficient vertex lookup")
        
        # Suggest limiting results early
        if ".limit(" not in optimized_query and ".toList()" in optimized_query:
            # Add a reasonable default limit if none specified
            optimized_query = optimized_query.replace(".toList()", ".limit(100).toList()")
            optimizations.append("Added result limit to prevent excessive data retrieval")
        
        # Optimize multi-hop traversals
        if optimized_query.count(".outE(") > 2 or optimized_query.count(".inE(") > 2:
            optimizations.append("Multi-hop traversal detected - consider using path optimization")
            query.estimated_complexity = "high"
        
        # Add deduplication for complex queries
        if ".outE(" in optimized_query and ".inV(" in optimized_query:
            if ".dedup()" not in optimized_query:
                # Add dedup before final collection
                optimized_query = optimized_query.replace(".toList()", ".dedup().toList()")
                optimizations.append("Added deduplication to remove duplicate results")
        
        return GremlinQuery(
            query_string=optimized_query,
            parameters=query.parameters,
            explanation=query.explanation,
            optimization_hints=query.optimization_hints + optimizations,
            estimated_complexity=query.estimated_complexity
        )
    
    def estimate_query_cost(self, query: GremlinQuery) -> Dict[str, Any]:
        """Estimate the computational cost of a query"""
        cost_factors = {
            "vertex_scans": query.query_string.count(".V()"),
            "edge_traversals": query.query_string.count(".outE(") + query.query_string.count(".inE("),
            "property_filters": query.query_string.count(".has("),
            "aggregations": query.query_string.count(".count()") + query.query_string.count(".sum()"),
            "has_limit": ".limit(" in query.query_string
        }
        
        # Calculate estimated cost score
        cost_score = (
            cost_factors["vertex_scans"] * 10 +
            cost_factors["edge_traversals"] * 5 +
            cost_factors["property_filters"] * 2 +
            cost_factors["aggregations"] * 3
        )
        
        # Reduce cost if query has limit
        if cost_factors["has_limit"]:
            cost_score = cost_score * 0.5
        
        return {
            "cost_score": cost_score,
            "complexity": "low" if cost_score < 20 else "medium" if cost_score < 50 else "high",
            "factors": cost_factors,
            "recommendations": self._get_cost_recommendations(cost_factors, cost_score)
        }
    
    def _get_cost_recommendations(self, factors: Dict[str, Any], cost_score: float) -> List[str]:
        """Get recommendations for reducing query cost"""
        recommendations = []
        
        if factors["vertex_scans"] > 1:
            recommendations.append("Consider using more specific vertex filters to reduce full scans")
        
        if factors["edge_traversals"] > 3:
            recommendations.append("Multi-hop traversal detected - consider caching intermediate results")
        
        if not factors["has_limit"] and cost_score > 20:
            recommendations.append("Add .limit() to prevent retrieving excessive results")
        
        if factors["aggregations"] > 2:
            recommendations.append("Multiple aggregations detected - consider breaking into separate queries")
        
        return recommendations


class QueryTranslator:
    """Translates natural language queries to Gremlin graph queries"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.optimizer = QueryOptimizer()
        
        # Intent to query template mapping
        self.query_templates = {
            QueryIntent.SIDE_EFFECTS: self._build_side_effects_query,
            QueryIntent.DRUG_INTERACTIONS: self._build_interactions_query,
            QueryIntent.DOSING: self._build_dosing_query,
            QueryIntent.CONTRAINDICATIONS: self._build_contraindications_query,
            QueryIntent.ALTERNATIVES: self._build_alternatives_query,
            QueryIntent.EFFECTIVENESS: self._build_effectiveness_query,
            QueryIntent.GENERAL_INFO: self._build_general_info_query
        }
    
    def translate_query(self, analysis: QueryAnalysis, 
                       patient_context: Optional[Dict[str, Any]] = None) -> Tuple[GremlinQuery, QueryProvenance]:
        """
        Translate a natural language query to Gremlin
        
        Args:
            analysis: Query analysis from NLP processor
            patient_context: Optional patient context for personalization
            
        Returns:
            Tuple of (GremlinQuery, QueryProvenance)
        """
        try:
            # Get the appropriate query builder for this intent
            query_builder = self.query_templates.get(
                analysis.intent,
                self._build_general_info_query
            )
            
            # Build the base query
            gremlin_query = query_builder(analysis, patient_context)
            
            # Optimize the query
            optimized_query = self.optimizer.optimize_query(gremlin_query)
            
            # Create provenance record
            provenance = self._create_provenance(analysis, optimized_query)
            
            self.logger.info(f"Translated query: {analysis.intent} -> {len(optimized_query.query_string)} chars")
            
            return optimized_query, provenance
            
        except Exception as e:
            self.logger.error(f"Error translating query: {e}")
            # Return a safe fallback query
            fallback_query = GremlinQuery(
                query_string="g.V().limit(0).toList()",
                parameters={},
                explanation="Query translation failed - returning empty result",
                optimization_hints=[],
                estimated_complexity="low"
            )
            provenance = QueryProvenance(
                query_id=str(uuid.uuid4()),
                original_query=analysis.original_query,
                intent=str(analysis.intent),
                entities=[],
                gremlin_query=fallback_query.query_string,
                reasoning_steps=[f"Error: {str(e)}"],
                data_sources=[]
            )
            return fallback_query, provenance
    
    def _build_side_effects_query(self, analysis: QueryAnalysis, 
                                  patient_context: Optional[Dict[str, Any]] = None) -> GremlinQuery:
        """Build query for side effects intent"""
        reasoning_steps = ["Building side effects query"]
        parameters = {}
        
        # Extract drug entities
        drugs = [e for e in analysis.entities if e.entity_type == EntityType.DRUG]
        
        if not drugs:
            reasoning_steps.append("No drug entities found - returning empty query")
            return GremlinQuery(
                query_string="g.V().limit(0).toList()",
                parameters={},
                explanation="No drugs specified in query",
                optimization_hints=[],
                estimated_complexity="low"
            )
        
        drug_name = drugs[0].normalized_form or drugs[0].text
        parameters['drug_name'] = drug_name
        reasoning_steps.append(f"Searching for side effects of drug: {drug_name}")
        
        # Base query: find drug and traverse to side effects
        query_parts = [
            "g.V()",
            ".hasLabel('Drug')",
            f".has('name', '{drug_name}')",
            ".outE('CAUSES')"
        ]
        
        # Add patient context filters if available
        if patient_context:
            reasoning_steps.append("Applying patient context filters")
            
            # Filter by confidence threshold based on patient risk factors
            if patient_context.get('risk_factors'):
                query_parts.append(".has('confidence', P.gte(0.7))")
                reasoning_steps.append("Filtering for high-confidence side effects due to patient risk factors")
            else:
                query_parts.append(".has('confidence', P.gte(0.5))")
            
            # Consider patient age for side effect relevance
            if 'age' in patient_context.get('demographics', {}):
                age = patient_context['demographics']['age']
                parameters['patient_age'] = age
                reasoning_steps.append(f"Considering patient age: {age}")
        else:
            # Default confidence threshold
            query_parts.append(".has('confidence', P.gte(0.5))")
        
        # Complete the traversal to side effect vertices
        query_parts.extend([
            ".order().by('frequency', Order.desc)",
            ".inV()",
            ".dedup()"
        ])
        
        query_string = "".join(query_parts) + ".toList()"
        
        return GremlinQuery(
            query_string=query_string,
            parameters=parameters,
            explanation=f"Retrieve side effects for {drug_name} ordered by frequency",
            optimization_hints=[
                "Using label and property filters for efficient lookup",
                "Ordering by frequency to prioritize common side effects"
            ],
            estimated_complexity="low"
        )
    
    def _build_interactions_query(self, analysis: QueryAnalysis,
                                  patient_context: Optional[Dict[str, Any]] = None) -> GremlinQuery:
        """Build query for drug interactions intent"""
        reasoning_steps = ["Building drug interactions query"]
        parameters = {}
        
        # Extract drug entities
        drugs = [e for e in analysis.entities if e.entity_type == EntityType.DRUG]
        
        if len(drugs) < 2:
            # Check if patient context has medications
            if patient_context and patient_context.get('medications'):
                reasoning_steps.append("Using patient's current medications for interaction check")
                current_meds = [med.get('name') for med in patient_context['medications']]
                
                if drugs:
                    # Check interaction between specified drug and patient's medications
                    drug_name = drugs[0].normalized_form or drugs[0].text
                    parameters['drug_name'] = drug_name
                    parameters['patient_medications'] = current_meds
                    
                    query_string = (
                        f"g.V().hasLabel('Drug').has('name', '{drug_name}')"
                        f".outE('INTERACTS_WITH')"
                        f".where(inV().has('name', within({current_meds})))"
                        f".order().by('severity', Order.desc)"
                        f".toList()"
                    )
                    
                    return GremlinQuery(
                        query_string=query_string,
                        parameters=parameters,
                        explanation=f"Check interactions between {drug_name} and patient's medications",
                        optimization_hints=["Filtering by patient's current medications"],
                        estimated_complexity="medium"
                    )
            
            # Not enough drugs specified
            return GremlinQuery(
                query_string="g.V().limit(0).toList()",
                parameters={},
                explanation="Need at least two drugs to check interactions",
                optimization_hints=[],
                estimated_complexity="low"
            )
        
        # Check interaction between two specified drugs
        drug_a = drugs[0].normalized_form or drugs[0].text
        drug_b = drugs[1].normalized_form or drugs[1].text
        parameters['drug_a'] = drug_a
        parameters['drug_b'] = drug_b
        
        query_string = (
            f"g.V().hasLabel('Drug').has('name', '{drug_a}')"
            f".outE('INTERACTS_WITH')"
            f".where(inV().has('name', '{drug_b}'))"
            f".order().by('severity', Order.desc)"
            f".toList()"
        )
        
        return GremlinQuery(
            query_string=query_string,
            parameters=parameters,
            explanation=f"Check interactions between {drug_a} and {drug_b}",
            optimization_hints=["Direct interaction lookup between two drugs"],
            estimated_complexity="low"
        )
    
    def _build_dosing_query(self, analysis: QueryAnalysis,
                           patient_context: Optional[Dict[str, Any]] = None) -> GremlinQuery:
        """Build query for dosing information intent"""
        reasoning_steps = ["Building dosing information query"]
        parameters = {}
        
        # Extract drug entities
        drugs = [e for e in analysis.entities if e.entity_type == EntityType.DRUG]
        
        if not drugs:
            return GremlinQuery(
                query_string="g.V().limit(0).toList()",
                parameters={},
                explanation="No drugs specified for dosing query",
                optimization_hints=[],
                estimated_complexity="low"
            )
        
        drug_name = drugs[0].normalized_form or drugs[0].text
        parameters['drug_name'] = drug_name
        
        # Query for drug and its dosing information
        query_parts = [
            "g.V()",
            ".hasLabel('Drug')",
            f".has('name', '{drug_name}')"
        ]
        
        # If patient context available, look for personalized dosing
        if patient_context:
            reasoning_steps.append("Including patient-specific dosing factors")
            demographics = patient_context.get('demographics', {})
            
            # Add traversal to dosing recommendations based on patient characteristics
            if demographics:
                query_parts.append(".outE('HAS_DOSING')")
                
                # Filter by patient characteristics
                if 'age' in demographics:
                    age = demographics['age']
                    parameters['age'] = age
                    query_parts.append(f".has('age_min', P.lte({age})).has('age_max', P.gte({age}))")
                
                if 'weight' in demographics:
                    weight = demographics['weight']
                    parameters['weight'] = weight
                    reasoning_steps.append(f"Considering patient weight: {weight}")
                
                query_parts.append(".inV()")
        
        query_string = "".join(query_parts) + ".toList()"
        
        return GremlinQuery(
            query_string=query_string,
            parameters=parameters,
            explanation=f"Retrieve dosing information for {drug_name}",
            optimization_hints=["Including patient-specific dosing factors" if patient_context else "General dosing information"],
            estimated_complexity="low"
        )
    
    def _build_contraindications_query(self, analysis: QueryAnalysis,
                                      patient_context: Optional[Dict[str, Any]] = None) -> GremlinQuery:
        """Build query for contraindications intent"""
        reasoning_steps = ["Building contraindications query"]
        parameters = {}
        
        # Extract drug and condition entities
        drugs = [e for e in analysis.entities if e.entity_type == EntityType.DRUG]
        conditions = [e for e in analysis.entities if e.entity_type == EntityType.CONDITION]
        
        if not drugs:
            return GremlinQuery(
                query_string="g.V().limit(0).toList()",
                parameters={},
                explanation="No drugs specified for contraindications query",
                optimization_hints=[],
                estimated_complexity="low"
            )
        
        drug_name = drugs[0].normalized_form or drugs[0].text
        parameters['drug_name'] = drug_name
        
        # Build query to find contraindications
        query_parts = [
            "g.V()",
            ".hasLabel('Drug')",
            f".has('name', '{drug_name}')",
            ".outE('CONTRAINDICATED_WITH')"
        ]
        
        # If specific condition mentioned, filter for it
        if conditions:
            condition_name = conditions[0].normalized_form or conditions[0].text
            parameters['condition'] = condition_name
            query_parts.append(f".where(inV().has('name', '{condition_name}'))")
            reasoning_steps.append(f"Checking contraindication for specific condition: {condition_name}")
        elif patient_context and patient_context.get('conditions'):
            # Check against patient's conditions
            patient_conditions = patient_context['conditions']
            parameters['patient_conditions'] = patient_conditions
            query_parts.append(f".where(inV().has('name', within({patient_conditions})))")
            reasoning_steps.append("Checking contraindications against patient's conditions")
        
        query_parts.extend([
            ".order().by('severity', Order.desc)",
            ".inV()"
        ])
        
        query_string = "".join(query_parts) + ".toList()"
        
        return GremlinQuery(
            query_string=query_string,
            parameters=parameters,
            explanation=f"Find contraindications for {drug_name}",
            optimization_hints=["Ordered by severity for prioritization"],
            estimated_complexity="medium"
        )
    
    def _build_alternatives_query(self, analysis: QueryAnalysis,
                                  patient_context: Optional[Dict[str, Any]] = None) -> GremlinQuery:
        """Build query for alternative medications intent"""
        reasoning_steps = ["Building alternatives query"]
        parameters = {}
        
        # Extract drug entities
        drugs = [e for e in analysis.entities if e.entity_type == EntityType.DRUG]
        
        if not drugs:
            return GremlinQuery(
                query_string="g.V().limit(0).toList()",
                parameters={},
                explanation="No drugs specified for alternatives query",
                optimization_hints=[],
                estimated_complexity="low"
            )
        
        drug_name = drugs[0].normalized_form or drugs[0].text
        parameters['drug_name'] = drug_name
        
        # Find alternatives by looking for drugs that treat the same conditions
        query_parts = [
            "g.V()",
            ".hasLabel('Drug')",
            f".has('name', '{drug_name}')",
            ".outE('TREATS')",
            ".inV()",  # Get conditions
            ".inE('TREATS')",  # Find other drugs that treat these conditions
            ".outV()",  # Get the alternative drugs
            f".where(neq('{drug_name}'))",  # Exclude the original drug
            ".dedup()"
        ]
        
        # If patient context available, filter out contraindicated drugs
        if patient_context and patient_context.get('conditions'):
            reasoning_steps.append("Filtering alternatives based on patient conditions")
            patient_conditions = patient_context['conditions']
            parameters['patient_conditions'] = patient_conditions
            
            # Exclude drugs contraindicated with patient's conditions
            query_parts.append(
                f".where(not(outE('CONTRAINDICATED_WITH').inV().has('name', within({patient_conditions}))))"
            )
        
        query_string = "".join(query_parts) + ".limit(10).toList()"
        
        return GremlinQuery(
            query_string=query_string,
            parameters=parameters,
            explanation=f"Find alternative medications to {drug_name}",
            optimization_hints=[
                "Finding drugs that treat the same conditions",
                "Excluding contraindicated alternatives" if patient_context else "No patient filtering applied"
            ],
            estimated_complexity="high"
        )
    
    def _build_effectiveness_query(self, analysis: QueryAnalysis,
                                   patient_context: Optional[Dict[str, Any]] = None) -> GremlinQuery:
        """Build query for medication effectiveness intent"""
        reasoning_steps = ["Building effectiveness query"]
        parameters = {}
        
        # Extract drug and condition entities
        drugs = [e for e in analysis.entities if e.entity_type == EntityType.DRUG]
        conditions = [e for e in analysis.entities if e.entity_type == EntityType.CONDITION]
        
        if not drugs:
            return GremlinQuery(
                query_string="g.V().limit(0).toList()",
                parameters={},
                explanation="No drugs specified for effectiveness query",
                optimization_hints=[],
                estimated_complexity="low"
            )
        
        drug_name = drugs[0].normalized_form or drugs[0].text
        parameters['drug_name'] = drug_name
        
        query_parts = [
            "g.V()",
            ".hasLabel('Drug')",
            f".has('name', '{drug_name}')",
            ".outE('TREATS')"
        ]
        
        # If specific condition mentioned, filter for it
        if conditions:
            condition_name = conditions[0].normalized_form or conditions[0].text
            parameters['condition'] = condition_name
            query_parts.append(f".where(inV().has('name', '{condition_name}'))")
            reasoning_steps.append(f"Checking effectiveness for condition: {condition_name}")
        
        query_parts.extend([
            ".order().by('efficacy', Order.desc)",
            ".inV()"
        ])
        
        query_string = "".join(query_parts) + ".toList()"
        
        return GremlinQuery(
            query_string=query_string,
            parameters=parameters,
            explanation=f"Find effectiveness information for {drug_name}",
            optimization_hints=["Ordered by efficacy rating"],
            estimated_complexity="low"
        )
    
    def _build_general_info_query(self, analysis: QueryAnalysis,
                                  patient_context: Optional[Dict[str, Any]] = None) -> GremlinQuery:
        """Build query for general information intent"""
        reasoning_steps = ["Building general information query"]
        parameters = {}
        
        # Extract drug entities
        drugs = [e for e in analysis.entities if e.entity_type == EntityType.DRUG]
        
        if not drugs:
            return GremlinQuery(
                query_string="g.V().limit(0).toList()",
                parameters={},
                explanation="No drugs specified for general info query",
                optimization_hints=[],
                estimated_complexity="low"
            )
        
        drug_name = drugs[0].normalized_form or drugs[0].text
        parameters['drug_name'] = drug_name
        
        # Simple query to get drug information
        query_string = (
            f"g.V().hasLabel('Drug').has('name', '{drug_name}').toList()"
        )
        
        return GremlinQuery(
            query_string=query_string,
            parameters=parameters,
            explanation=f"Retrieve general information for {drug_name}",
            optimization_hints=["Direct vertex lookup"],
            estimated_complexity="low"
        )
    
    def _create_provenance(self, analysis: QueryAnalysis, query: GremlinQuery) -> QueryProvenance:
        """Create provenance record for query"""
        # Determine data sources based on query type
        data_sources = []
        
        if "CAUSES" in query.query_string:
            data_sources.extend(["OnSIDES", "SIDER", "FAERS"])
        
        if "INTERACTS_WITH" in query.query_string:
            data_sources.extend(["DDInter", "DrugBank"])
        
        if "TREATS" in query.query_string:
            data_sources.extend(["DrugBank", "Drugs@FDA"])
        
        if "CONTRAINDICATED_WITH" in query.query_string:
            data_sources.extend(["DrugBank", "FAERS"])
        
        # Remove duplicates
        data_sources = list(set(data_sources))
        
        # Build reasoning steps
        reasoning_steps = [
            f"Classified query intent as: {analysis.intent}",
            f"Extracted {len(analysis.entities)} entities from query",
            f"Generated Gremlin query with {query.estimated_complexity} complexity",
            f"Applied {len(query.optimization_hints)} optimizations"
        ]
        
        if query.parameters:
            reasoning_steps.append(f"Query parameters: {', '.join(query.parameters.keys())}")
        
        return QueryProvenance(
            query_id=str(uuid.uuid4()),
            original_query=analysis.original_query,
            intent=str(analysis.intent),
            entities=[{
                'text': e.text,
                'type': str(e.entity_type),
                'confidence': e.confidence
            } for e in analysis.entities],
            gremlin_query=query.query_string,
            reasoning_steps=reasoning_steps,
            data_sources=data_sources
        )
    
    def explain_query(self, query: GremlinQuery, provenance: QueryProvenance) -> Dict[str, Any]:
        """Generate human-readable explanation of query"""
        explanation = {
            "query_id": provenance.query_id,
            "original_question": provenance.original_query,
            "intent": provenance.intent,
            "entities_found": provenance.entities,
            "graph_query_explanation": query.explanation,
            "optimization_applied": query.optimization_hints,
            "complexity": query.estimated_complexity,
            "data_sources": provenance.data_sources,
            "reasoning_steps": provenance.reasoning_steps,
            "estimated_cost": self.optimizer.estimate_query_cost(query)
        }
        
        return explanation


# Global query translator instance
query_translator = QueryTranslator()
