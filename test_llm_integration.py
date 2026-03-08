#!/usr/bin/env python3
"""
Quick test script for LLM integration
Run this to verify the LLM response generator works
"""
import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Try to load dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ Loaded environment variables from .env file")
except ImportError:
    print("⚠ python-dotenv not installed, using system environment variables")
    print("  Install with: uv pip install python-dotenv")

from src.nlp.llm_response_generator import llm_response_generator


async def test_llm_response():
    """Test LLM response generation"""
    
    print("=" * 80)
    print("Testing LLM Response Generator")
    print("=" * 80)
    
    # Test query
    query = "What are the side effects of aspirin?"
    intent = "side_effects"
    
    entities = [
        {
            "text": "aspirin",
            "type": "drug",
            "confidence": 0.95,
            "normalized_form": "aspirin"
        }
    ]
    
    graph_results = [
        {
            "type": "side_effect",
            "name": "Stomach upset",
            "severity": "moderate",
            "frequency": "common (10-25%)",
            "description": "May cause stomach discomfort, nausea, or indigestion",
            "management": "Take with food or milk to reduce stomach irritation"
        },
        {
            "type": "side_effect",
            "name": "Bleeding risk",
            "severity": "major",
            "frequency": "uncommon (1-10%)",
            "description": "Increased risk of bleeding, especially with prolonged use",
            "management": "Monitor for unusual bruising or bleeding; consult doctor if occurs"
        },
        {
            "type": "side_effect",
            "name": "Allergic reaction",
            "severity": "major",
            "frequency": "rare (<1%)",
            "description": "May cause rash, itching, swelling, or difficulty breathing",
            "management": "Seek immediate medical attention if allergic symptoms occur"
        }
    ]
    
    evidence_sources = ["OnSIDES", "SIDER", "DrugBank", "FDA Adverse Events"]
    
    print(f"\nQuery: {query}")
    print(f"Intent: {intent}")
    print(f"Entities: {[e['text'] for e in entities]}")
    print(f"Graph Results: {len(graph_results)} side effects found")
    print(f"Evidence Sources: {', '.join(evidence_sources)}")
    
    # Check if Gemini is configured
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and api_key != "your_gemini_api_key_here":
        print("\n✓ Gemini API key found - will use LLM")
    else:
        print("\n⚠ Gemini API key not configured - will use fallback templates")
    
    print("\n" + "-" * 80)
    print("Generating response...")
    print("-" * 80 + "\n")
    
    # Generate response
    try:
        response = await llm_response_generator.generate_response(
            query=query,
            intent=intent,
            entities=entities,
            graph_results=graph_results,
            evidence_sources=evidence_sources,
            patient_context=None
        )
        
        print("RESPONSE:")
        print("=" * 80)
        print(response.answer)
        print("=" * 80)
        print(f"\nConfidence: {response.confidence:.2f}")
        print(f"Reasoning: {response.reasoning}")
        
        print("\n✓ Test completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_llm_response())
