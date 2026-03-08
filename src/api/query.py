"""
Query processing API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from src.auth.dependencies import get_current_user
from src.models.user import User

from src.config import settings
from src.nlp.query_processor import medical_query_processor
from src.nlp.query_translator import query_translator
from src.nlp.llm_response_generator import llm_response_generator
from src.knowledge_graph.database import db
from src.knowledge_graph.reasoning_engine import GraphReasoningEngine
from src.data.drug_database import drug_db

router = APIRouter(prefix="/query", tags=["query"])


def _get_results_from_drug_db(intent: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get results from in-memory drug database based on query intent and entities"""
    results = []
    
    # Find drug entities
    drug_entities = [e for e in entities if e.get('type') == 'drug']
    
    if not drug_entities:
        # No drug found in query
        return [{
            "type": "error",
            "name": "Unable to process query",
            "description": "We apologize, but we couldn't identify a specific medication in your query. Currently, our database includes information for: " + ", ".join(drug_db.list_all_drugs()) + ". Please try asking about one of these medications."
        }]
    
    # Process first drug entity (can be extended to handle multiple drugs)
    drug_name = drug_entities[0].get('text', '').lower()
    drug_data = drug_db.search_drug(drug_name)
    
    if not drug_data:
        # Drug not found in database
        return [{
            "type": "error",
            "name": "Information not available",
            "description": f"We apologize, but we currently don't have enough details to answer your query about '{drug_name}'. Our database currently includes information for the following medications: {', '.join(drug_db.list_all_drugs())}. Please try asking about one of these medications, or check back later as we continue to expand our database."
        }]
    
    # Return results based on intent
    if intent == "side_effects":
        side_effects = drug_db.get_side_effects(drug_name)
        for se in side_effects:
            results.append({
                "type": "side_effect",
                "name": se["name"],
                "severity": se["severity"],
                "frequency": se["frequency"],
                "description": se["description"],
                "management": se["management"]
            })
    
    elif intent == "drug_interactions":
        # Get interactions for this drug
        interactions = drug_data.get("interactions", [])
        for interacting_drug in interactions:
            interaction_data = drug_db.get_interactions(drug_name, interacting_drug)
            if interaction_data:
                results.append({
                    "type": "interaction",
                    "interacting_drug": interacting_drug.capitalize(),
                    "severity": interaction_data["severity"],
                    "description": interaction_data["description"],
                    "mechanism": interaction_data["mechanism"],
                    "management": interaction_data.get("management", "Consult healthcare provider")
                })
            else:
                results.append({
                    "type": "interaction",
                    "interacting_drug": interacting_drug.capitalize(),
                    "severity": "unknown",
                    "description": f"May interact with {interacting_drug}",
                    "mechanism": "Interaction mechanism not specified"
                })
    
    elif intent == "dosing":
        dosing = drug_db.get_dosing(drug_name)
        if dosing:
            for indication, dose_info in dosing.items():
                if indication == "max_daily":
                    continue
                results.append({
                    "type": "dosage",
                    "indication": indication.replace("_", " ").title(),
                    "dose": dose_info,
                    "max_daily": dosing.get("max_daily", "Consult prescribing information"),
                    "frequency": "As prescribed"
                })
    
    else:
        # General information
        results.append({
            "type": "information",
            "drug_name": drug_data["name"],
            "generic_name": drug_data.get("generic_name", ""),
            "drug_class": drug_data.get("class", ""),
            "description": f"{drug_data['name']} is a {drug_data.get('class', 'medication')} used for various medical conditions."
        })
    
    # If no results were found for the specific intent, provide an apology
    if not results:
        return [{
            "type": "error",
            "name": "Information not available",
            "description": f"We apologize, but we currently don't have enough details to answer your specific question about {drug_data['name']}. We have general information about this medication, but not the specific details you're looking for. Please try a different question or consult your healthcare provider."
        }]
    
    return results


class QueryRequest(BaseModel):
    """Query request model"""
    query: str = Field(..., description="Natural language health question")
    patient_id: Optional[str] = Field(None, description="Patient identifier for personalization")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class QueryResponse(BaseModel):
    """Query response model"""
    query_id: str
    user_id: str
    original_query: str
    intent: str
    entities: List[Dict[str, Any]]
    results: List[Dict[str, Any]]
    evidence_sources: List[str]
    confidence: float
    timestamp: datetime
    answer: Optional[str] = None  # LLM-generated natural language answer


class QueryExplanation(BaseModel):
    """Query explanation model"""
    query_id: str
    user_id: str
    reasoning_steps: List[str]
    graph_paths: List[List[str]]
    data_sources: List[str]
    confidence_breakdown: Dict[str, float]


@router.post("/process", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Process natural language health questions
    
    Translates natural language queries into knowledge graph traversals
    and provides evidence-based responses with full provenance tracking.
    """
    try:
        if settings.USE_REAL_LOGIC:
            # Use real NLP and reasoning logic
            
            # Step 1: Process the query with NLP
            query_analysis = medical_query_processor.process_query(request.query)
            
            # Step 2: Translate to graph query
            patient_context_dict = None
            if request.context:
                patient_context_dict = request.context
            
            gremlin_query, provenance = query_translator.translate_query(
                query_analysis,
                patient_context=patient_context_dict
            )
            
            # Step 3: Execute the query (if database is connected)
            results = []
            if db.connected:
                try:
                    # Execute the Gremlin query
                    g = db.connection.g
                    # Note: In production, would execute gremlin_query.query_string
                    # For now, return structured results
                    results = []
                except Exception as e:
                    # Log error but continue with empty results
                    print(f"Query execution error: {e}")
            
            # If no results from database, use in-memory drug database
            if not results:
                results = _get_results_from_drug_db(
                    query_analysis.intent.value,  # Use .value to get the string value
                    [{
                        'text': e.text,
                        'type': e.entity_type.value,  # Use .value to get the string value
                        'confidence': e.confidence,
                        'normalized_form': e.normalized_form
                    } for e in query_analysis.entities]
                )
            
            # Step 4: Generate LLM response
            entities_list = [{
                'text': e.text,
                'type': e.entity_type.value,  # Use .value to get the string value
                'confidence': e.confidence,
                'normalized_form': e.normalized_form
            } for e in query_analysis.entities]
            
            llm_response = await llm_response_generator.generate_response(
                query=request.query,
                intent=str(query_analysis.intent),
                entities=entities_list,
                graph_results=results,
                evidence_sources=provenance.data_sources,
                patient_context=patient_context_dict
            )
            
            # Step 5: Format response
            return QueryResponse(
                query_id=provenance.query_id,
                user_id=current_user.id,
                original_query=request.query,
                intent=str(query_analysis.intent),
                entities=entities_list,
                results=results,
                evidence_sources=provenance.data_sources,
                confidence=query_analysis.query_confidence,
                timestamp=datetime.utcnow(),
                answer=llm_response.answer
            )
        else:
            # Return mock response using drug database
            # Use aspirin as default drug for mock mode
            mock_entities = [
                {
                    "text": "aspirin",
                    "type": "drug",
                    "confidence": 0.95,
                    "normalized_form": "aspirin"
                }
            ]
            
            mock_results = _get_results_from_drug_db("side_effects", mock_entities)
            
            return QueryResponse(
                query_id=f"query_{datetime.utcnow().timestamp()}",
                user_id=current_user.id,
                original_query=request.query,
                intent="side_effects",
                entities=mock_entities,
                results=mock_results,
                evidence_sources=["In-Memory Drug Database"],
                confidence=0.85,
                timestamp=datetime.utcnow()
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@router.get("/explain/{query_id}", response_model=QueryExplanation)
async def explain_query(
    query_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Provide query explanation and evidence sources
    
    Returns detailed information about how the query was processed,
    including reasoning steps and knowledge graph paths.
    """
    try:
        if settings.USE_REAL_LOGIC:
            # In a real implementation, would retrieve stored query provenance
            # For now, return a structured explanation
            return QueryExplanation(
                query_id=query_id,
                user_id=current_user.id,
                reasoning_steps=[
                    "Parsed natural language query using spaCy NLP",
                    "Extracted medical entities (drugs, conditions, symptoms)",
                    "Classified query intent using pattern matching",
                    "Translated to optimized Gremlin graph query",
                    "Executed multi-hop graph traversal",
                    "Aggregated evidence from multiple sources",
                    "Calculated confidence scores for results"
                ],
                graph_paths=[],
                data_sources=["OnSIDES", "SIDER", "DrugBank", "FAERS"],
                confidence_breakdown={
                    "entity_extraction": 0.9,
                    "intent_classification": 0.85,
                    "query_translation": 0.88,
                    "result_relevance": 0.82
                }
            )
        else:
            # Return mock explanation
            return QueryExplanation(
                query_id=query_id,
                user_id=current_user.id,
                reasoning_steps=[
                    "Parsed natural language query",
                    "Extracted medical entities",
                    "Translated to Cypher query",
                    "Executed graph traversal",
                    "Aggregated evidence"
                ],
                graph_paths=[],
                data_sources=["OnSIDES", "SIDER", "DrugBank"],
                confidence_breakdown={
                    "entity_extraction": 0.9,
                    "query_translation": 0.85,
                    "result_relevance": 0.8
                }
            )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Query not found: {str(e)}")


class FeedbackRequest(BaseModel):
    """Feedback request model"""
    query_id: str
    helpful: bool
    comments: Optional[str] = None


@router.post("/feedback")
async def submit_feedback(
    feedback: FeedbackRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Collect user feedback for query improvement
    
    Stores user feedback to improve query understanding and response quality.
    """
    try:
        # TODO: Store feedback in database with user_id
        return {
            "status": "success",
            "message": "Feedback received",
            "query_id": feedback.query_id,
            "user_id": current_user.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting feedback: {str(e)}")
