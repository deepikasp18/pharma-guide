"""
Demo script for drug interaction detection and alternative recommendations
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.knowledge_graph.database import KnowledgeGraphDatabase
from src.knowledge_graph.reasoning_engine import GraphReasoningEngine
from src.knowledge_graph.interaction_detector import InteractionDetector
from src.knowledge_graph.alternative_recommender import AlternativeRecommender
from src.knowledge_graph.models import PatientContext, SeverityLevel


async def main():
    """Demonstrate interaction detection and alternative recommendations"""
    
    print("=" * 80)
    print("Drug Interaction Detection and Alternative Recommendation Demo")
    print("=" * 80)
    print()
    
    # Initialize components
    print("Initializing knowledge graph components...")
    db = KnowledgeGraphDatabase()
    await db.connect()
    
    reasoning_engine = GraphReasoningEngine(db)
    interaction_detector = InteractionDetector(reasoning_engine)
    alternative_recommender = AlternativeRecommender(reasoning_engine)
    
    print("✓ Components initialized")
    print()
    
    # Create sample patient
    print("Creating sample patient profile...")
    patient = PatientContext(
        id="patient_demo_001",
        demographics={
            "age": 68,
            "gender": "female",
            "weight": 65,
            "height": 165
        },
        conditions=["diabetes", "hypertension", "osteoarthritis"],
        medications=[
            {"drug_id": "drug_001", "name": "Metformin", "dosage": "500mg twice daily"},
            {"drug_id": "drug_002", "name": "Lisinopril", "dosage": "10mg daily"},
            {"drug_id": "drug_003", "name": "Ibuprofen", "dosage": "400mg as needed"}
        ],
        risk_factors=["obesity", "sedentary lifestyle"],
        allergies=["penicillin"]
    )
    
    print(f"✓ Patient: {patient.id}")
    print(f"  Age: {patient.demographics['age']}")
    print(f"  Conditions: {', '.join(patient.conditions)}")
    print(f"  Medications: {len(patient.medications)}")
    print()
    
    # Analyze patient medications
    print("Analyzing patient medications for interactions...")
    print("-" * 80)
    
    analysis = await interaction_detector.analyze_patient_medications(patient)
    
    print(f"\nAnalysis Results:")
    print(f"  Drugs analyzed: {len(analysis.analyzed_drugs)}")
    print(f"  Interactions found: {len(analysis.interactions)}")
    print(f"  Contraindications found: {len(analysis.contraindications)}")
    print()
    
    # Display risk summary
    print("Risk Summary:")
    print(f"  Highest risk level: {analysis.risk_summary.get('highest_risk', 'unknown')}")
    print(f"  Requires immediate attention: {analysis.risk_summary.get('requires_immediate_attention', False)}")
    print()
    
    severity_breakdown = analysis.risk_summary.get('severity_breakdown', {})
    if any(severity_breakdown.values()):
        print("  Severity breakdown:")
        for severity, count in severity_breakdown.items():
            if count > 0:
                print(f"    - {severity.capitalize()}: {count}")
        print()
    
    # Display interactions
    if analysis.interactions:
        print("Detected Interactions:")
        for i, interaction in enumerate(analysis.interactions[:3], 1):  # Show top 3
            print(f"\n  {i}. {interaction.drug_a_name} ↔ {interaction.drug_b_name}")
            print(f"     Severity: {interaction.severity.value}")
            print(f"     Confidence: {interaction.confidence:.2f}")
            if interaction.mechanism:
                print(f"     Mechanism: {interaction.mechanism}")
            if interaction.clinical_effect:
                print(f"     Clinical effect: {interaction.clinical_effect}")
            if interaction.management:
                print(f"     Management: {interaction.management}")
        print()
    
    # Display contraindications
    if analysis.contraindications:
        print("Detected Contraindications:")
        for i, contra in enumerate(analysis.contraindications[:3], 1):  # Show top 3
            print(f"\n  {i}. {contra.drug_name} ⚠ {contra.condition_name}")
            print(f"     Severity: {contra.severity.value}")
            print(f"     Confidence: {contra.confidence:.2f}")
            if contra.reason:
                print(f"     Reason: {contra.reason}")
        print()
    
    # Display recommendations
    if analysis.recommendations:
        print("Recommendations:")
        for i, rec in enumerate(analysis.recommendations, 1):
            print(f"  {i}. {rec}")
        print()
    
    # Generate alternative recommendations for first interaction
    if analysis.interactions:
        print("=" * 80)
        print("Generating Alternative Medication Recommendations")
        print("=" * 80)
        print()
        
        first_interaction = analysis.interactions[0]
        print(f"Finding alternatives for: {first_interaction.drug_a_name}")
        print(f"Due to interaction with: {first_interaction.drug_b_name}")
        print()
        
        alt_recommendation = await alternative_recommender.recommend_alternatives_for_interaction(
            first_interaction, patient
        )
        
        # Display alternatives
        if alt_recommendation.alternatives:
            print(f"Found {len(alt_recommendation.alternatives)} alternative medication(s):")
            for i, alt in enumerate(alt_recommendation.alternatives, 1):
                print(f"\n  {i}. {alt.drug_name}")
                if alt.generic_name:
                    print(f"     Generic: {alt.generic_name}")
                print(f"     Overall score: {alt.overall_score:.2f}")
                print(f"     Similarity: {alt.similarity_score:.2f}")
                print(f"     Safety: {alt.safety_score:.2f}")
                print(f"     Confidence: {alt.confidence:.2f}")
                
                if alt.reasons:
                    print(f"     Reasons:")
                    for reason in alt.reasons:
                        print(f"       - {reason}")
                
                if alt.advantages:
                    print(f"     Advantages:")
                    for adv in alt.advantages:
                        print(f"       - {adv}")
        else:
            print("No suitable alternatives found in knowledge graph.")
        print()
        
        # Display management strategies
        if alt_recommendation.management_strategies:
            print("Management Strategies:")
            for i, strategy in enumerate(alt_recommendation.management_strategies, 1):
                print(f"\n  {i}. {strategy.strategy_type.upper()}")
                print(f"     {strategy.description}")
                if strategy.specific_actions:
                    print(f"     Actions:")
                    for action in strategy.specific_actions:
                        print(f"       - {action}")
                if strategy.monitoring_requirements:
                    print(f"     Monitoring:")
                    for req in strategy.monitoring_requirements:
                        print(f"       - {req}")
        print()
        
        # Display patient-specific notes
        if alt_recommendation.patient_specific_notes:
            print("Patient-Specific Notes:")
            for i, note in enumerate(alt_recommendation.patient_specific_notes, 1):
                print(f"  {i}. {note}")
        print()
    
    # Cleanup
    await db.disconnect()
    
    print("=" * 80)
    print("Demo completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
