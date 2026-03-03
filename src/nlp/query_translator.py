"""
Query translation service for converting natural language to graph queries
"""
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.nlp.query_processor import QueryAnalysis, QueryIntent, EntityType
from src.knowledge_graph.models import SemanticQuery

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """Types of graph queries"""
    SIMPLE_LOOKUP = "simple_lookup"
    RELATIONSHIP_TRAVERSAL = "relationship_traversal"
    MULTI_HOP = "multi_hop"
    AGGREGATION = "aggregation"
    PATTERN_MATCH = "pattern_match"


@dataclass
class GraphQuery:
    """Structured graph query representation"""
    query_type: QueryType
    gremlin_query: str
    cypher_query: Optional[str]  # For future Cypher support
    parameters: Dict[str, Any]
    optimization_hints: List[str]
    estimated_complexity: int  # 1-10 scale


@dataclass
class QueryExplanation:
    """Explanation of query translation and execution"""
    original_query: str
    intent: str
    extracted_entities: List[Dict[str, Any]]
    translation_steps: List[str]
    graph_traversal_description: str
    expected_result_types: List[str]
    confidence: float


@dataclass
class ProvenanceInfo:
    """Provenance tracking information"""
    query_id: str
    timestamp: str
    data_sources: List[str]
    traversal_path: List[str]
    confidence_scores: Dict[str, float]
    reasoning_steps: List[str]


class QueryTranslator:
    """Translates natural language queries to graph database queries"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Intent to query pattern mapping
        self.intent_patterns = {
            QueryIntent.SIDE_EFFECTS: self._build_side_effects_query,
            QueryIntent.DRUG_INTERACTIONS: self._build_interactions_query,
            QueryIntent.DOSING: self._build_dosing_query,
            QueryIntent.CONTRAINDICATIONS: self._build_contraindications_query,
            QueryIntent.ALTERNATIVES: self._build_alternatives_query,
            QueryIntent.EFFECTIVENESS: self._build_effectiveness_query,
            QueryIntent.GENERAL_INFO: self._build_general_info_query,
        }
    
    def translate_query(
        self, 
        query_analysis: QueryAnalysis,
        patient_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[GraphQuery, QueryExplanation]:
        """
        Translate analyzed query to graph database query
        
        Args:
            query_analysis: Analyzed natural language query
            patient_context: Optional patient context for personalization
            
        Returns:
            Tuple of (GraphQuery, QueryExplanation)
        """
        try:
            # Get appropriate query builder for intent
            query_builder = self.intent_patterns.get(
                query_analysis.intent,
                self._build_general_info_query
            )
            
            # Build graph query
            graph_query = query_builder(query_analysis, patient_context)
            
            # Create explanation
            explanation = self._create_explanation(query_analysis, graph_query)
            
            # Optimize query
            optimized_query = self._optimize_query(graph_query, query_analysis)
            
            self.logger.info(
                f"Translated query with intent {query_analysis.intent} "
                f"to {optimized_query.query_type}"
            )
            
            return optimized_query, explanation
            
        except Exception as e:
            self.logger.error(f"Error translating query: {e}")
            # Return fallback query
            return self._build_fallback_query(query_analysis), self._create_fallback_explanation(query_analysis)
    
    def _build_side_effects_query(
        self,
        query_analysis: QueryAnalysis,
        patient_context: Optional[Dict[str, Any]] = None
    ) -> GraphQuery:
        """Build query for side effects lookup"""
        # Extract drug entities
        drugs = [e for e in query_analysis.entities if e.entity_type == EntityType.DRUG]
        
        if not drugs:
            return self._build_fallback_query(query_analysis)
        
        drug_name = drugs[0].normalized_form
        
        # Build Gremlin query
        gremlin_parts = [
            "g.V()",
            ".hasLabel('Drug')",
            f".has('name', '{drug_name}')",
            ".outE('CAUSES')",
        ]
        
        # Add patient context filters if available
        if patient_context:
            # Filter by confidence threshold based on patient risk factors
            confidence_threshold = self._calculate_confidence_threshold(patient_context)
            gremlin_parts.append(f".has('confidence', gt({confidence_threshold}))")
        else:
            gremlin_parts.append(".has('confidence', gt(0.7))")
        
        # Complete traversal to side effects
        gremlin_parts.extend([
            ".order().by('frequency', desc)",
            ".inV()",
            ".project('side_effect', 'frequency', 'confidence', 'sources')",
            ".by('name')",
            ".by(inE('CAUSES').values('frequency'))",
            ".by(inE('CAUSES').values('confidence'))",
            ".by(inE('CAUSES').values('evidence_sources'))",
        ])
        
        gremlin_query = "".join(gremlin_parts)
        
        # Build Cypher equivalent (for future use)
        cypher_query = f"""
        MATCH (d:Drug {{name: '{drug_name}'}})-[c:CAUSES]->(se:SideEffect)
        WHERE c.confidence > 0.7
        RETURN se.name AS side_effect, c.frequency AS frequency, 
               c.confidence AS confidence, c.evidence_sources AS sources
        ORDER BY c.frequency DESC
        """
        
        return GraphQuery(
            query_type=QueryType.RELATIONSHIP_TRAVERSAL,
            gremlin_query=gremlin_query,
            cypher_query=cypher_query,
            parameters={"drug_name": drug_name},
            optimization_hints=["index_lookup", "edge_filter"],
            estimated_complexity=3
        )
    
    def _build_interactions_query(
        self,
        query_analysis: QueryAnalysis,
        patient_context: Optional[Dict[str, Any]] = None
    ) -> GraphQuery:
        """Build query for drug interactions"""
        # Extract drug entities
        drugs = [e for e in query_analysis.entities if e.entity_type == EntityType.DRUG]
        
        if len(drugs) < 2:
            # If only one drug, check against patient's current medications
            if patient_context and patient_context.get('medications'):
                drug_name = drugs[0].normalized_form if drugs else None
                patient_meds = [m.get('name') for m in patient_context.get('medications', [])]
                
                if drug_name and patient_meds:
                    return self._build_multi_drug_interaction_query(drug_name, patient_meds)
            
            return self._build_fallback_query(query_analysis)
        
        drug_a = drugs[0].normalized_form
        drug_b = drugs[1].normalized_form
        
        # Build Gremlin query for pairwise interaction
        gremlin_query = f"""
        g.V().hasLabel('Drug').has('name', '{drug_a}')
        .as('drug_a')
        .outE('INTERACTS_WITH')
        .as('interaction')
        .inV().has('name', '{drug_b}')
        .select('drug_a', 'interaction')
        .by('name')
        .by(valueMap('severity', 'mechanism', 'clinical_effect', 'management'))
        """
        
        cypher_query = f"""
        MATCH (a:Drug {{name: '{drug_a}'}})-[i:INTERACTS_WITH]->(b:Drug {{name: '{drug_b}'}})
        RETURN a.name AS drug_a, b.name AS drug_b, 
               i.severity AS severity, i.mechanism AS mechanism,
               i.clinical_effect AS clinical_effect, i.management AS management
        """
        
        return GraphQuery(
            query_type=QueryType.RELATIONSHIP_TRAVERSAL,
            gremlin_query=gremlin_query,
            cypher_query=cypher_query,
            parameters={"drug_a": drug_a, "drug_b": drug_b},
            optimization_hints=["bidirectional_search", "index_lookup"],
            estimated_complexity=4
        )
    
    def _build_multi_drug_interaction_query(
        self,
        new_drug: str,
        existing_drugs: List[str]
    ) -> GraphQuery:
        """Build query for checking one drug against multiple drugs"""
        # Build query to check new drug against all existing drugs
        drug_list = "', '".join(existing_drugs)
        
        gremlin_query = f"""
        g.V().hasLabel('Drug').has('name', '{new_drug}')
        .as('new_drug')
        .outE('INTERACTS_WITH')
        .as('interaction')
        .inV().hasLabel('Drug').has('name', within('{drug_list}'))
        .as('existing_drug')
        .select('new_drug', 'existing_drug', 'interaction')
        .by('name')
        .by('name')
        .by(valueMap('severity', 'mechanism', 'management'))
        """
        
        return GraphQuery(
            query_type=QueryType.MULTI_HOP,
            gremlin_query=gremlin_query,
            cypher_query=None,
            parameters={"new_drug": new_drug, "existing_drugs": existing_drugs},
            optimization_hints=["batch_lookup", "parallel_traversal"],
            estimated_complexity=6
        )
    
    def _build_dosing_query(
        self,
        query_analysis: QueryAnalysis,
        patient_context: Optional[Dict[str, Any]] = None
    ) -> GraphQuery:
        """Build query for dosing information"""
        drugs = [e for e in query_analysis.entities if e.entity_type == EntityType.DRUG]
        
        if not drugs:
            return self._build_fallback_query(query_analysis)
        
        drug_name = drugs[0].normalized_form
        
        # Build query to get drug properties including dosing
        gremlin_query = f"""
        g.V().hasLabel('Drug').has('name', '{drug_name}')
        .project('name', 'dosage_forms', 'indications', 'pharmacokinetics')
        .by('name')
        .by('dosage_forms')
        .by('indications')
        .by('pharmacokinetics')
        """
        
        # If patient context available, also check for dosing adjustments
        if patient_context:
            demographics = patient_context.get('demographics', {})
            age = demographics.get('age')
            weight = demographics.get('weight')
            
            # Add patient-specific dosing considerations
            gremlin_query += f"""
            .union(
                __.identity(),
                __.outE('REQUIRES_ADJUSTMENT')
                .has('patient_age', within({age - 5}, {age + 5}))
                .inV()
                .project('adjustment_reason', 'recommendation')
                .by('reason')
                .by('dosing_recommendation')
            )
            """
        
        return GraphQuery(
            query_type=QueryType.SIMPLE_LOOKUP,
            gremlin_query=gremlin_query,
            cypher_query=None,
            parameters={"drug_name": drug_name},
            optimization_hints=["property_projection"],
            estimated_complexity=2
        )
    
    def _build_contraindications_query(
        self,
        query_analysis: QueryAnalysis,
        patient_context: Optional[Dict[str, Any]] = None
    ) -> GraphQuery:
        """Build query for contraindications"""
        drugs = [e for e in query_analysis.entities if e.entity_type == EntityType.DRUG]
        conditions = [e for e in query_analysis.entities if e.entity_type == EntityType.CONDITION]
        
        if not drugs:
            return self._build_fallback_query(query_analysis)
        
        drug_name = drugs[0].normalized_form
        
        # If patient context available, check against their conditions
        if patient_context and patient_context.get('conditions'):
            patient_conditions = patient_context.get('conditions', [])
            condition_list = "', '".join(patient_conditions)
            
            gremlin_query = f"""
            g.V().hasLabel('Drug').has('name', '{drug_name}')
            .outE('CONTRAINDICATED_WITH')
            .as('contraindication')
            .inV().hasLabel('Condition').has('name', within('{condition_list}'))
            .as('condition')
            .select('condition', 'contraindication')
            .by('name')
            .by(valueMap('severity', 'reason', 'alternative_options'))
            """
        elif conditions:
            # Check specific condition from query
            condition_name = conditions[0].normalized_form
            gremlin_query = f"""
            g.V().hasLabel('Drug').has('name', '{drug_name}')
            .outE('CONTRAINDICATED_WITH')
            .inV().hasLabel('Condition').has('name', '{condition_name}')
            .path()
            .by(valueMap('name'))
            .by(valueMap('severity', 'reason'))
            """
        else:
            # Get all contraindications
            gremlin_query = f"""
            g.V().hasLabel('Drug').has('name', '{drug_name}')
            .values('contraindications')
            """
        
        return GraphQuery(
            query_type=QueryType.RELATIONSHIP_TRAVERSAL,
            gremlin_query=gremlin_query,
            cypher_query=None,
            parameters={"drug_name": drug_name},
            optimization_hints=["index_lookup", "path_optimization"],
            estimated_complexity=4
        )
    
    def _build_alternatives_query(
        self,
        query_analysis: QueryAnalysis,
        patient_context: Optional[Dict[str, Any]] = None
    ) -> GraphQuery:
        """Build query for alternative medications"""
        drugs = [e for e in query_analysis.entities if e.entity_type == EntityType.DRUG]
        
        if not drugs:
            return self._build_fallback_query(query_analysis)
        
        drug_name = drugs[0].normalized_form
        
        # Find alternatives by:
        # 1. Same indications
        # 2. Similar mechanism of action
        # 3. Same therapeutic class (ATC codes)
        gremlin_query = f"""
        g.V().hasLabel('Drug').has('name', '{drug_name}')
        .as('original')
        .union(
            __.out('TREATS').in('TREATS').where(neq('original')),
            __.out('SIMILAR_MECHANISM').where(neq('original')),
            __.out('SAME_CLASS').where(neq('original'))
        )
        .dedup()
        .project('name', 'generic_name', 'similarity_reason')
        .by('name')
        .by('generic_name')
        .by(
            __.choose(
                __.in('TREATS').where(eq('original')),
                constant('same_indication'),
                constant('similar_properties')
            )
        )
        .limit(10)
        """
        
        return GraphQuery(
            query_type=QueryType.MULTI_HOP,
            gremlin_query=gremlin_query,
            cypher_query=None,
            parameters={"drug_name": drug_name},
            optimization_hints=["union_optimization", "deduplication"],
            estimated_complexity=7
        )
    
    def _build_effectiveness_query(
        self,
        query_analysis: QueryAnalysis,
        patient_context: Optional[Dict[str, Any]] = None
    ) -> GraphQuery:
        """Build query for effectiveness information"""
        drugs = [e for e in query_analysis.entities if e.entity_type == EntityType.DRUG]
        conditions = [e for e in query_analysis.entities if e.entity_type == EntityType.CONDITION]
        
        if not drugs or not conditions:
            return self._build_fallback_query(query_analysis)
        
        drug_name = drugs[0].normalized_form
        condition_name = conditions[0].normalized_form
        
        # Query effectiveness data from clinical trials and real-world evidence
        gremlin_query = f"""
        g.V().hasLabel('Drug').has('name', '{drug_name}')
        .outE('TREATS').has('indication', '{condition_name}')
        .project('efficacy', 'evidence_level', 'patient_count', 'sources')
        .by('efficacy')
        .by('evidence_level')
        .by('patient_count')
        .by('evidence_sources')
        """
        
        return GraphQuery(
            query_type=QueryType.RELATIONSHIP_TRAVERSAL,
            gremlin_query=gremlin_query,
            cypher_query=None,
            parameters={"drug_name": drug_name, "condition_name": condition_name},
            optimization_hints=["edge_property_filter"],
            estimated_complexity=3
        )
    
    def _build_general_info_query(
        self,
        query_analysis: QueryAnalysis,
        patient_context: Optional[Dict[str, Any]] = None
    ) -> GraphQuery:
        """Build general information query"""
        drugs = [e for e in query_analysis.entities if e.entity_type == EntityType.DRUG]
        
        if not drugs:
            return self._build_fallback_query(query_analysis)
        
        drug_name = drugs[0].normalized_form
        
        # Get comprehensive drug information
        gremlin_query = f"""
        g.V().hasLabel('Drug').has('name', '{drug_name}')
        .project('name', 'generic_name', 'mechanism', 'indications', 
                 'contraindications', 'dosage_forms')
        .by('name')
        .by('generic_name')
        .by('mechanism')
        .by('indications')
        .by('contraindications')
        .by('dosage_forms')
        """
        
        return GraphQuery(
            query_type=QueryType.SIMPLE_LOOKUP,
            gremlin_query=gremlin_query,
            cypher_query=None,
            parameters={"drug_name": drug_name},
            optimization_hints=["property_projection"],
            estimated_complexity=1
        )
    
    def _build_fallback_query(self, query_analysis: QueryAnalysis) -> GraphQuery:
        """Build fallback query when specific translation fails"""
        # Simple search across all drug names
        gremlin_query = """
        g.V().hasLabel('Drug')
        .limit(10)
        .project('name', 'generic_name')
        .by('name')
        .by('generic_name')
        """
        
        return GraphQuery(
            query_type=QueryType.SIMPLE_LOOKUP,
            gremlin_query=gremlin_query,
            cypher_query=None,
            parameters={},
            optimization_hints=["limit_early"],
            estimated_complexity=1
        )
    
    def _optimize_query(
        self,
        graph_query: GraphQuery,
        query_analysis: QueryAnalysis
    ) -> GraphQuery:
        """Optimize graph query for better performance"""
        optimized_gremlin = graph_query.gremlin_query
        optimization_hints = list(graph_query.optimization_hints)
        
        # Apply optimization strategies
        
        # 1. Add early filtering
        if "index_lookup" in optimization_hints:
            # Ensure indexed properties are used early in traversal
            pass  # Already applied in query building
        
        # 2. Limit result sets early
        if graph_query.query_type == QueryType.MULTI_HOP:
            if ".limit(" not in optimized_gremlin:
                # Add limit to prevent excessive traversal
                optimized_gremlin = optimized_gremlin.replace(
                    ".dedup()",
                    ".dedup().limit(50)"
                )
                optimization_hints.append("early_limit_added")
        
        # 3. Use batch operations for multiple lookups
        if "batch_lookup" in optimization_hints:
            # Batch operations already applied in query building
            pass
        
        # 4. Add result caching hints
        if query_analysis.query_confidence > 0.8:
            optimization_hints.append("cache_candidate")
        
        return GraphQuery(
            query_type=graph_query.query_type,
            gremlin_query=optimized_gremlin,
            cypher_query=graph_query.cypher_query,
            parameters=graph_query.parameters,
            optimization_hints=optimization_hints,
            estimated_complexity=graph_query.estimated_complexity
        )
    
    def _calculate_confidence_threshold(self, patient_context: Dict[str, Any]) -> float:
        """Calculate confidence threshold based on patient risk factors"""
        base_threshold = 0.7
        
        # Adjust based on patient risk factors
        risk_factors = patient_context.get('risk_factors', [])
        
        # Higher risk patients need higher confidence
        if len(risk_factors) > 3:
            base_threshold = 0.8
        elif len(risk_factors) > 5:
            base_threshold = 0.85
        
        return base_threshold
    
    def _create_explanation(
        self,
        query_analysis: QueryAnalysis,
        graph_query: GraphQuery
    ) -> QueryExplanation:
        """Create human-readable explanation of query translation"""
        translation_steps = []
        
        # Step 1: Intent recognition
        translation_steps.append(
            f"Identified query intent as '{query_analysis.intent}' "
            f"with {query_analysis.intent_confidence:.2f} confidence"
        )
        
        # Step 2: Entity extraction
        entity_summary = ", ".join([
            f"{e.entity_type}: {e.text}" 
            for e in query_analysis.entities
        ])
        if entity_summary:
            translation_steps.append(f"Extracted entities: {entity_summary}")
        
        # Step 3: Query type selection
        translation_steps.append(
            f"Selected {graph_query.query_type} query pattern"
        )
        
        # Step 4: Graph traversal description
        traversal_desc = self._describe_traversal(graph_query, query_analysis)
        
        # Step 5: Optimization
        if graph_query.optimization_hints:
            translation_steps.append(
                f"Applied optimizations: {', '.join(graph_query.optimization_hints)}"
            )
        
        # Expected result types
        expected_results = self._determine_expected_results(query_analysis.intent)
        
        return QueryExplanation(
            original_query=query_analysis.original_query,
            intent=query_analysis.intent,
            extracted_entities=[
                {
                    "type": e.entity_type,
                    "text": e.text,
                    "confidence": e.confidence
                }
                for e in query_analysis.entities
            ],
            translation_steps=translation_steps,
            graph_traversal_description=traversal_desc,
            expected_result_types=expected_results,
            confidence=query_analysis.query_confidence
        )
    
    def _create_fallback_explanation(self, query_analysis: QueryAnalysis) -> QueryExplanation:
        """Create explanation for fallback query"""
        return QueryExplanation(
            original_query=query_analysis.original_query,
            intent=query_analysis.intent,
            extracted_entities=[],
            translation_steps=["Unable to translate query specifically", "Using general drug lookup"],
            graph_traversal_description="Retrieving general drug information",
            expected_result_types=["Drug"],
            confidence=0.3
        )
    
    def _describe_traversal(
        self,
        graph_query: GraphQuery,
        query_analysis: QueryAnalysis
    ) -> str:
        """Create human-readable description of graph traversal"""
        if graph_query.query_type == QueryType.SIMPLE_LOOKUP:
            return "Direct lookup of drug properties from knowledge graph"
        
        elif graph_query.query_type == QueryType.RELATIONSHIP_TRAVERSAL:
            if query_analysis.intent == QueryIntent.SIDE_EFFECTS:
                return (
                    "Traverse from Drug node through CAUSES relationships "
                    "to SideEffect nodes, filtering by confidence and ordering by frequency"
                )
            elif query_analysis.intent == QueryIntent.DRUG_INTERACTIONS:
                return (
                    "Traverse from first Drug node through INTERACTS_WITH relationship "
                    "to second Drug node, retrieving interaction details"
                )
            elif query_analysis.intent == QueryIntent.CONTRAINDICATIONS:
                return (
                    "Traverse from Drug node through CONTRAINDICATED_WITH relationships "
                    "to Condition nodes, checking patient conditions"
                )
        
        elif graph_query.query_type == QueryType.MULTI_HOP:
            return (
                "Multi-hop traversal through knowledge graph, "
                "following multiple relationship types to find related entities"
            )
        
        return "Complex graph traversal across multiple entity types and relationships"
    
    def _determine_expected_results(self, intent: QueryIntent) -> List[str]:
        """Determine expected result types based on intent"""
        result_mapping = {
            QueryIntent.SIDE_EFFECTS: ["SideEffect", "Frequency", "Confidence"],
            QueryIntent.DRUG_INTERACTIONS: ["Interaction", "Severity", "Management"],
            QueryIntent.DOSING: ["DosageForm", "Indication", "Pharmacokinetics"],
            QueryIntent.CONTRAINDICATIONS: ["Condition", "Severity", "Reason"],
            QueryIntent.ALTERNATIVES: ["Drug", "SimilarityReason"],
            QueryIntent.EFFECTIVENESS: ["Efficacy", "EvidenceLevel"],
            QueryIntent.GENERAL_INFO: ["Drug", "Properties"],
        }
        
        return result_mapping.get(intent, ["Unknown"])
    
    def create_provenance_info(
        self,
        query_id: str,
        graph_query: GraphQuery,
        data_sources: List[str],
        confidence_scores: Dict[str, float]
    ) -> ProvenanceInfo:
        """Create provenance tracking information"""
        from datetime import datetime
        
        # Extract traversal path from query
        traversal_path = self._extract_traversal_path(graph_query)
        
        # Create reasoning steps
        reasoning_steps = [
            f"Query type: {graph_query.query_type}",
            f"Complexity: {graph_query.estimated_complexity}/10",
            f"Optimizations applied: {', '.join(graph_query.optimization_hints)}",
        ]
        
        return ProvenanceInfo(
            query_id=query_id,
            timestamp=datetime.utcnow().isoformat(),
            data_sources=data_sources,
            traversal_path=traversal_path,
            confidence_scores=confidence_scores,
            reasoning_steps=reasoning_steps
        )
    
    def _extract_traversal_path(self, graph_query: GraphQuery) -> List[str]:
        """Extract traversal path from Gremlin query"""
        path = []
        
        # Parse Gremlin query to extract path
        query = graph_query.gremlin_query
        
        if "hasLabel('Drug')" in query:
            path.append("Drug")
        
        if "outE('CAUSES')" in query:
            path.append("CAUSES")
            path.append("SideEffect")
        
        if "outE('INTERACTS_WITH')" in query:
            path.append("INTERACTS_WITH")
            path.append("Drug")
        
        if "outE('CONTRAINDICATED_WITH')" in query:
            path.append("CONTRAINDICATED_WITH")
            path.append("Condition")
        
        if "out('TREATS')" in query:
            path.append("TREATS")
            path.append("Condition")
        
        return path if path else ["Unknown"]


# Global query translator instance
query_translator = QueryTranslator()
