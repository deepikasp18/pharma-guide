"""
Demo script showing query translation service in action
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.nlp.query_processor import medical_query_processor
from src.nlp.query_translator import query_translator


def demo_query_translation():
    """Demonstrate query translation with various examples"""
    
    print("=" * 80)
    print("PharmaGuide Query Translation Service Demo")
    print("=" * 80)
    print()
    
    # Example queries
    queries = [
        "What are the side effects of Lisinopril?",
        "Can I take Aspirin with Ibuprofen?",
        "What is the dosage for Metformin for a 65-year-old?",
        "Can I take Aspirin if I have asthma?",
        "What are alternatives to Ibuprofen?",
        "How effective is Metformin for diabetes?",
    ]
    
    # Patient context for personalization
    patient_context = {
        'demographics': {
            'age': 65,
            'gender': 'male',
            'weight': 180
        },
        'conditions': ['diabetes', 'hypertension'],
        'medications': [
            {'name': 'Metformin', 'dosage': '500mg'},
            {'name': 'Lisinopril', 'dosage': '10mg'}
        ],
        'risk_factors': ['obesity', 'family_history_heart_disease']
    }
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'=' * 80}")
        print(f"Example {i}: {query}")
        print('=' * 80)
        
        # Step 1: Process natural language query
        print("\n[Step 1] Natural Language Processing")
        print("-" * 80)
        analysis = medical_query_processor.process_query(query)
        
        print(f"Intent: {analysis.intent} (confidence: {analysis.intent_confidence:.2f})")
        print(f"Entities found: {len(analysis.entities)}")
        for entity in analysis.entities:
            print(f"  - {entity.text} ({entity.entity_type}): {entity.confidence:.2f}")
        print(f"Overall confidence: {analysis.query_confidence:.2f}")
        
        # Step 2: Translate to Gremlin query
        print("\n[Step 2] Query Translation")
        print("-" * 80)
        
        # Use patient context for some queries
        use_context = i in [3, 4]  # Use context for dosing and contraindications
        context = patient_context if use_context else None
        
        gremlin_query, provenance = query_translator.translate_query(analysis, context)
        
        print(f"Generated Gremlin Query:")
        print(f"  {gremlin_query.query_string}")
        print(f"\nQuery Complexity: {gremlin_query.estimated_complexity}")
        print(f"Parameters: {gremlin_query.parameters}")
        
        # Step 3: Show optimization hints
        print("\n[Step 3] Query Optimization")
        print("-" * 80)
        if gremlin_query.optimization_hints:
            print("Optimizations applied:")
            for hint in gremlin_query.optimization_hints:
                print(f"  • {hint}")
        else:
            print("No additional optimizations needed")
        
        # Step 4: Show provenance
        print("\n[Step 4] Query Provenance")
        print("-" * 80)
        print(f"Query ID: {provenance.query_id}")
        print(f"Data Sources: {', '.join(provenance.data_sources)}")
        print(f"\nReasoning Steps:")
        for step in provenance.reasoning_steps:
            print(f"  • {step}")
        
        # Step 5: Show full explanation
        print("\n[Step 5] Query Explanation")
        print("-" * 80)
        explanation = query_translator.explain_query(gremlin_query, provenance)
        
        print(f"Explanation: {explanation['graph_query_explanation']}")
        print(f"\nEstimated Cost:")
        cost = explanation['estimated_cost']
        print(f"  Score: {cost['cost_score']:.1f}")
        print(f"  Complexity: {cost['complexity']}")
        if cost['recommendations']:
            print(f"  Recommendations:")
            for rec in cost['recommendations']:
                print(f"    • {rec}")
    
    print("\n" + "=" * 80)
    print("Demo Complete!")
    print("=" * 80)


def demo_query_optimization():
    """Demonstrate query optimization features"""
    
    print("\n" + "=" * 80)
    print("Query Optimization Demo")
    print("=" * 80)
    print()
    
    # Example: Complex multi-hop query
    query = "What are alternatives to Ibuprofen that don't interact with my current medications?"
    
    print(f"Query: {query}")
    print()
    
    # Process query
    analysis = medical_query_processor.process_query(query)
    
    # Patient context with multiple medications
    patient_context = {
        'medications': [
            {'name': 'Lisinopril', 'dosage': '10mg'},
            {'name': 'Metformin', 'dosage': '500mg'},
            {'name': 'Aspirin', 'dosage': '81mg'}
        ],
        'conditions': ['hypertension', 'diabetes']
    }
    
    # Translate query
    gremlin_query, provenance = query_translator.translate_query(analysis, patient_context)
    
    print("Generated Query:")
    print(f"  {gremlin_query.query_string}")
    print()
    
    # Show cost analysis
    cost = query_translator.optimizer.estimate_query_cost(gremlin_query)
    
    print("Cost Analysis:")
    print(f"  Cost Score: {cost['cost_score']:.1f}")
    print(f"  Complexity: {cost['complexity']}")
    print(f"  Vertex Scans: {cost['factors']['vertex_scans']}")
    print(f"  Edge Traversals: {cost['factors']['edge_traversals']}")
    print(f"  Property Filters: {cost['factors']['property_filters']}")
    print(f"  Has Limit: {cost['factors']['has_limit']}")
    print()
    
    if cost['recommendations']:
        print("Optimization Recommendations:")
        for rec in cost['recommendations']:
            print(f"  • {rec}")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    # Run demos
    demo_query_translation()
    demo_query_optimization()
