"""
LLM-based response generator for natural language query responses
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import os

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """LLM-generated response"""
    answer: str
    confidence: float
    sources_used: List[str]
    reasoning: str


class LLMResponseGenerator:
    """
    Generate natural language responses using LLM based on query analysis and graph results
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("GEMINI_MODEL", "models/gemini-3-flash-preview")
        
        # Check if Gemini is available
        self.gemini_available = False
        try:
            from google import genai
            if self.api_key:
                self.client = genai.Client(api_key=self.api_key)
                self.gemini_available = True
                self.logger.info(f"Gemini client initialized successfully with model: {self.model}")
            else:
                self.logger.warning("GEMINI_API_KEY not found in environment")
        except ImportError:
            self.logger.warning("Google Genai library not installed. Install with: pip install google-genai")
    
    async def generate_response(
        self,
        query: str,
        intent: str,
        entities: List[Dict[str, Any]],
        graph_results: List[Dict[str, Any]],
        evidence_sources: List[str],
        patient_context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """
        Generate a natural language response based on query analysis and graph results
        
        Args:
            query: Original user query
            intent: Detected query intent
            entities: Extracted entities from the query
            graph_results: Results from knowledge graph traversal
            evidence_sources: List of evidence sources
            patient_context: Optional patient context for personalization
        
        Returns:
            LLMResponse with generated answer and metadata
        """
        try:
            if not self.gemini_available:
                return self._generate_fallback_response(
                    query, intent, entities, graph_results, evidence_sources
                )
            
            # Build context for LLM
            context = self._build_context(
                query, intent, entities, graph_results, evidence_sources, patient_context
            )
            
            # Generate response using Gemini
            response = await self._call_gemini(context, query)
            
            return response
        
        except Exception as e:
            self.logger.error(f"Error generating LLM response: {e}")
            return self._generate_fallback_response(
                query, intent, entities, graph_results, evidence_sources
            )
    
    def _build_context(
        self,
        query: str,
        intent: str,
        entities: List[Dict[str, Any]],
        graph_results: List[Dict[str, Any]],
        evidence_sources: List[str],
        patient_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build context string for LLM prompt"""
        
        context_parts = []
        
        # Add query intent
        context_parts.append(f"Query Intent: {intent}")
        
        # Add extracted entities
        if entities:
            entity_strs = [
                f"- {e['text']} ({e['type']}, confidence: {e['confidence']:.2f})"
                for e in entities
            ]
            context_parts.append("Extracted Entities:\n" + "\n".join(entity_strs))
        
        # Add graph results
        if graph_results:
            context_parts.append("\nKnowledge Graph Results:")
            for i, result in enumerate(graph_results[:5], 1):  # Limit to top 5
                result_type = result.get('type', 'unknown')
                name = result.get('name', 'Unknown')
                
                result_str = f"{i}. {name} ({result_type})"
                
                # Add relevant details based on type
                if result_type == 'side_effect':
                    severity = result.get('severity', 'unknown')
                    frequency = result.get('frequency', 'unknown')
                    description = result.get('description', '')
                    result_str += f"\n   - Severity: {severity}\n   - Frequency: {frequency}"
                    if description:
                        result_str += f"\n   - Description: {description}"
                
                elif result_type == 'interaction':
                    severity = result.get('severity', 'unknown')
                    description = result.get('description', '')
                    result_str += f"\n   - Severity: {severity}"
                    if description:
                        result_str += f"\n   - Description: {description}"
                
                elif result_type == 'drug':
                    drug_class = result.get('drug_class', 'unknown')
                    mechanism = result.get('mechanism', '')
                    result_str += f"\n   - Class: {drug_class}"
                    if mechanism:
                        result_str += f"\n   - Mechanism: {mechanism}"
                
                context_parts.append(result_str)
        
        # Add evidence sources
        if evidence_sources:
            context_parts.append(f"\nEvidence Sources: {', '.join(set(evidence_sources))}")
        
        # Add patient context if available
        if patient_context:
            context_parts.append("\nPatient Context:")
            if 'age' in patient_context:
                context_parts.append(f"- Age: {patient_context['age']}")
            if 'conditions' in patient_context:
                context_parts.append(f"- Conditions: {', '.join(patient_context['conditions'])}")
            if 'medications' in patient_context:
                context_parts.append(f"- Current Medications: {', '.join(patient_context['medications'])}")
        
        return "\n\n".join(context_parts)
    
    async def _call_gemini(self, context: str, query: str) -> LLMResponse:
        """Call Google Gemini API to generate response"""
        
        system_prompt = """You are a medical information assistant for PharmaGuide, a health companion platform.
Your role is to provide clear, accurate, and helpful responses about medications, side effects, and drug interactions
based on evidence from medical knowledge graphs and databases.

Guidelines:
1. Provide clear, concise answers in natural language
2. Always cite evidence sources when available
3. Use appropriate medical terminology but explain complex terms
4. Include relevant warnings and precautions
5. Emphasize that this is informational and users should consult healthcare providers
6. Be empathetic and supportive in tone
7. Structure responses with clear sections when appropriate
8. Highlight important safety information

IMPORTANT: Always include a disclaimer that this information is for educational purposes
and users should consult their healthcare provider for medical advice."""

        user_prompt = f"""Based on the following information from our medical knowledge graph, 
please provide a comprehensive answer to the user's question.

User Question: {query}

Context and Evidence:
{context}

Please provide a well-structured response that:
1. Directly answers the user's question
2. Includes relevant details from the knowledge graph results
3. Cites the evidence sources
4. Includes appropriate medical disclaimers
5. Is written in a clear, empathetic tone"""

        try:
            from google import genai
            from google.genai import types
            
            # Combine system and user prompts for Gemini
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            # Generate response using the new API
            response = self.client.models.generate_content(
                model=self.model,
                contents=types.Part.from_text(text=full_prompt)
            )
            
            answer = response.text
            
            # Extract reasoning (simplified - could be enhanced)
            reasoning = "Generated response using medical knowledge graph data and Gemini LLM synthesis"
            
            return LLMResponse(
                answer=answer,
                confidence=0.85,  # Could be calculated based on various factors
                sources_used=[],  # Extracted from context
                reasoning=reasoning
            )
        
        except Exception as e:
            self.logger.error(f"Gemini API call failed: {e}")
            raise
    
    def _generate_fallback_response(
        self,
        query: str,
        intent: str,
        entities: List[Dict[str, Any]],
        graph_results: List[Dict[str, Any]],
        evidence_sources: List[str]
    ) -> LLMResponse:
        """Generate a template-based response when LLM is not available"""
        
        self.logger.info("Using fallback template-based response generation")
        
        # Extract key information
        drug_entities = [e for e in entities if e['type'] == 'drug']
        
        # Build response based on intent
        if intent == 'side_effects' and graph_results:
            answer = self._format_side_effects_response(drug_entities, graph_results)
        elif intent == 'drug_interactions' and graph_results:
            answer = self._format_interactions_response(drug_entities, graph_results)
        elif intent == 'dosage' and graph_results:
            answer = self._format_dosage_response(drug_entities, graph_results)
        else:
            answer = self._format_generic_response(query, graph_results)
        
        # Add evidence sources
        if evidence_sources:
            answer += f"\n\nSources: {', '.join(set(evidence_sources))}"
        
        # Add disclaimer
        answer += "\n\n⚠️ This information is for educational purposes only. Please consult your healthcare provider for medical advice."
        
        return LLMResponse(
            answer=answer,
            confidence=0.75,
            sources_used=evidence_sources,
            reasoning="Template-based response generation (LLM not available)"
        )
    
    def _format_side_effects_response(
        self,
        drug_entities: List[Dict[str, Any]],
        results: List[Dict[str, Any]]
    ) -> str:
        """Format side effects response"""
        
        drug_name = drug_entities[0]['text'] if drug_entities else "this medication"
        
        response = f"Here are the known side effects of {drug_name}:\n\n"
        
        # Group by severity
        by_severity = {}
        for result in results:
            if result.get('type') == 'side_effect':
                severity = result.get('severity', 'unknown')
                if severity not in by_severity:
                    by_severity[severity] = []
                by_severity[severity].append(result)
        
        # Format by severity
        severity_order = ['major', 'moderate', 'minor']
        for severity in severity_order:
            if severity in by_severity:
                response += f"**{severity.title()} Side Effects:**\n"
                for effect in by_severity[severity]:
                    name = effect.get('name', 'Unknown')
                    frequency = effect.get('frequency', 'unknown frequency')
                    description = effect.get('description', '')
                    
                    response += f"- {name} ({frequency})"
                    if description:
                        response += f": {description}"
                    response += "\n"
                response += "\n"
        
        return response.strip()
    
    def _format_interactions_response(
        self,
        drug_entities: List[Dict[str, Any]],
        results: List[Dict[str, Any]]
    ) -> str:
        """Format drug interactions response"""
        
        drug_name = drug_entities[0]['text'] if drug_entities else "this medication"
        
        response = f"Drug interactions for {drug_name}:\n\n"
        
        for result in results:
            if result.get('type') == 'interaction':
                interacting_drug = result.get('interacting_drug', 'another medication')
                severity = result.get('severity', 'unknown')
                description = result.get('description', 'No details available')
                
                response += f"**{interacting_drug}** (Severity: {severity})\n"
                response += f"{description}\n\n"
        
        return response.strip()
    
    def _format_dosage_response(
        self,
        drug_entities: List[Dict[str, Any]],
        results: List[Dict[str, Any]]
    ) -> str:
        """Format dosage information response"""
        
        drug_name = drug_entities[0]['text'] if drug_entities else "this medication"
        
        response = f"Dosage information for {drug_name}:\n\n"
        
        for result in results:
            if result.get('type') == 'dosage':
                indication = result.get('indication', 'General use')
                dose = result.get('dose', 'Consult prescribing information')
                frequency = result.get('frequency', '')
                
                response += f"**{indication}:**\n"
                response += f"- Dose: {dose}"
                if frequency:
                    response += f"\n- Frequency: {frequency}"
                response += "\n\n"
        
        return response.strip()
    
    def _format_generic_response(
        self,
        query: str,
        results: List[Dict[str, Any]]
    ) -> str:
        """Format generic response"""
        
        if not results:
            return "I couldn't find specific information to answer your question. Please try rephrasing or consult your healthcare provider."
        
        response = "Based on the available information:\n\n"
        
        for i, result in enumerate(results[:5], 1):
            name = result.get('name', 'Unknown')
            result_type = result.get('type', 'information')
            description = result.get('description', '')
            
            response += f"{i}. {name} ({result_type})"
            if description:
                response += f": {description}"
            response += "\n"
        
        return response.strip()


# Global instance
llm_response_generator = LLMResponseGenerator()
