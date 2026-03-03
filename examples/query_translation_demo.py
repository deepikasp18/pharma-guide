"""
Demo script showing query translation functionality
"""
from src.nlp.query_processor import MedicalQueryProcessor
from src.nlp.query_translator import QueryTranslator


def demo_query_translation():
    """Demonstrate query translation capabilities"""
    
    # Initialize components
    query_processor = MedicalQueryProcessor()
    query_translator = QueryTranslator()
    
    # Example queries
    queries = [
        "What are the side effects of Lisinopril?",
        "Can I take Lisinopril with Ibuprofen?",
        "What is the dosage for Metformin?",
        "Are there alternatives to Aspirin?",
        "Can I take Lisinopril if I have diabetes?",
    ]
    
    print("=" * 80)
    print("Query Translation Demo")
    print("=" * 80)
    
    for query in queries:
        print(f"\n{'=' * 80}")
        print(f"Query: {query}")
        print(f"{'=' * 80}")
        
        # Step 1: Process natural language query
        query_analysis = query_processor.process_query(query)
        
        print(f"\n1. Query Analysis:")
        print(f"   Intent: {query_analysis.intent} (confidence: {query_analysis.intent_confidence:.2f})")
        print(f"   Entities: {len(query_analysis.entities)}")
        for entity in query_analysis.entities:
            print(f"      - {entity.entity_type}: {entity.text} (confidence: {entity.confidence:.2f})")
        
        # Step 2: Translate to graph query
        graph_query, explanation = query_translator.translate_query(query_analysis)
        
        print(f"\n2. Graph Query Translation:")
        print(f"   Query Type: {graph_query.query_type}")
        print(f"   Complexity: {graph_query.estimated_complexity}/10")
        print(f"   Optimizations: {', '.join(graph_query.optimization_hints)}")
        
        print(f"\n3. Gremlin Query:")
        print(f"   {graph_query.gremlin_query[:200]}...")
        
        if graph_query.cypher_query:
            print(f"\n4. Cypher Query (for reference):")
            print(f"   {graph_query.cypher_query[:200]}...")
        
        print(f"\n5. Query Explanation:")
        print(f"   Traversal: {explanation.graph_traversal_description}")
        print(f"   Expected Results: {', '.join(explanation.expected_result_types)}")
        print(f"   Translation Steps:")
        for i, step in enumerate(explanation.translation_steps, 1):
            print(f"      {i}. {step}")
        
        # Step 3: Create provenance info
        provenance = query_translator.create_provenance_info(
            query_id=f"demo-{hash(query)}",
            graph_query=graph_query,
            data_sources=["OnSIDES", "SIDER", "DrugBank"],
            confidence_scores={"overall": 0.85}
        )
        
        print(f"\n6. Provenance Information:")
        print(f"   Query ID: {provenance.query_id}")
        print(f"   Data Sources: {', '.join(provenance.data_sources)}")
        print(f"   Traversal Path: {' -> '.join(provenance.traversal_path)}")
        print(f"   Timestamp: {provenance.timestamp}")
    
    print(f"\n{'=' * 80}")
    print("Demo Complete")
    print(f"{'=' * 80}")


def demo_with_patient_context():
    """Demonstrate query translation with patient context"""
    
    query_processor = MedicalQueryProcessor()
    query_translator = QueryTranslator()
    
    # Patient context
    patient_context = {
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
        'risk_factors': ['smoking', 'obesity', 'family_history_heart_disease']
    }
    
    query = "What are the side effects of Lisinopril?"
    
    print("\n" + "=" * 80)
    print("Query Translation with Patient Context")
    print("=" * 80)
    
    print(f"\nPatient Context:")
    print(f"   Age: {patient_context['demographics']['age']}")
    print(f"   Conditions: {', '.join(patient_context['conditions'])}")
    print(f"   Current Medications: {len(patient_context['medications'])}")
    print(f"   Risk Factors: {len(patient_context['risk_factors'])}")
    
    print(f"\nQuery: {query}")
    
    # Process query
    query_analysis = query_processor.process_query(query)
    
    # Translate without context
    graph_query_no_context, _ = query_translator.translate_query(query_analysis)
    
    # Translate with context
    graph_query_with_context, explanation = query_translator.translate_query(
        query_analysis,
        patient_context=patient_context
    )
    
    print(f"\nWithout Patient Context:")
    print(f"   Confidence Threshold: 0.7 (default)")
    print(f"   Query Complexity: {graph_query_no_context.estimated_complexity}")
    
    print(f"\nWith Patient Context:")
    print(f"   Confidence Threshold: 0.8 (adjusted for high-risk patient)")
    print(f"   Query Complexity: {graph_query_with_context.estimated_complexity}")
    print(f"   Additional Filters: Patient-specific risk factors applied")
    
    print(f"\nPersonalized Query:")
    print(f"   {graph_query_with_context.gremlin_query[:300]}...")


if __name__ == "__main__":
    # Run basic demo
    demo_query_translation()
    
    # Run demo with patient context
    demo_with_patient_context()
