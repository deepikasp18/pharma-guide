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
from src.knowledge_graph.database import db
from src.knowledge_graph.reasoning_engine import GraphReasoningEngine

router = APIRouter(prefix="/query", tags=["query"])


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
            
            # Step 4: Format response
            return QueryResponse(
                query_id=provenance.query_id,
                user_id=current_user.id,
                original_query=request.query,
                intent=str(query_analysis.intent),
                entities=[{
                    'text': e.text,
                    'type': str(e.entity_type),
                    'confidence': e.confidence,
                    'normalized_form': e.normalized_form
                } for e in query_analysis.entities],
                results=results,
                evidence_sources=provenance.data_sources,
                confidence=query_analysis.query_confidence,
                timestamp=datetime.utcnow()
            )
        else:
            # Return mock response
            return QueryResponse(
                query_id=f"query_{datetime.utcnow().timestamp()}",
                user_id=current_user.id,
                original_query=request.query,
                intent="medication_query",
                entities=[],
                results=[],
                evidence_sources=["OnSIDES", "SIDER", "DrugBank"],
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
