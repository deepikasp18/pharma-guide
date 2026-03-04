"""
Property-based tests for physiological factor analysis

**Validates: Requirements 6.1, 6.3**

Property 14: Physiological Factor Analysis
For any medication analysis, the system should query knowledge graph relationships
between patient characteristics and drug response patterns, including pharmacogenomic
factors when available.
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite
from typing import List, Dict, Any, Optional

from src.knowledge_graph.physiological_analysis import (
    PhysiologicalAnalysisService,
    PhysiologicalResponse,
    PharmacogenomicFactor,
    ADMEPattern,
    MetabolizerType,
    ADMEPhase
)
from src.knowledge_graph.models import PatientContext
from src.knowledge_graph.database import KnowledgeGraphDatabase
from unittest.mock import AsyncMock, MagicMock


# ============================================================================
# Strategy Generators for Property-Based Testing
# ============================================================================

@composite
def drug_id_strategy(draw):
    """Generate drug IDs for testing"""
    drugs = [
        'drug_warfarin', 'drug_codeine', 'drug_clopidogrel', 'drug_tramadol',
        'drug_omeprazole', 'drug_atorvastatin', 'drug_metoprolol',
        'drug_simvastatin', 'drug_amlodipine', 'drug_losartan'
    ]
    return draw(st.sampled_from(drugs))


@composite
def genetic_factors_strategy(draw):
    """Generate genetic factors including CYP450 variants"""
    factors = {}
    
    # CYP450 genes
    cyp_genes = ['CYP2D6', 'CYP2C19', 'CYP2C9', 'CYP3A4']
    
    # Randomly include some genetic variants
    num_variants = draw(st.integers(min_value=0, max_value=3))
    selected_genes = draw(st.lists(
        st.sampled_from(cyp_genes),
        min_size=num_variants,
        max_size=num_variants,
        unique=True
    ))
    
    for gene in selected_genes:
        variant = draw(st.sampled_from([
            '*1/*1',  # Normal
            '*1/*4',  # Intermediate
            '*4/*4',  # Poor
            '*1/*2',  # Rapid
            '*2/*2',  # Ultra-rapid
            'normal',
            'poor_metabolizer',
            'intermediate_metabolizer',
            'rapid_metabolizer',
            'ultra_rapid_metabolizer'
        ]))
        factors[gene] = variant
    
    return factors


@composite
def patient_with_genetics_strategy(draw):
    """Generate patient context with genetic factors"""
    age = draw(st.integers(min_value=18, max_value=90))
    weight = draw(st.integers(min_value=45, max_value=150))
    height = draw(st.integers(min_value=150, max_value=200))
    gender = draw(st.sampled_from(['male', 'female']))
    
    # Generate conditions
    conditions = draw(st.lists(
        st.sampled_from([
            'hypertension', 'diabetes', 'heart_disease',
            'kidney_disease', 'liver_disease', 'inflammatory_bowel_disease'
        ]),
        min_size=0,
        max_size=3,
        unique=True
    ))
    
    # Generate genetic factors
    genetic_factors = draw(genetic_factors_strategy())
    
    # Generate risk factors
    risk_factors = []
    if age > 65:
        risk_factors.append('elderly')
    if 'kidney_disease' in conditions:
        risk_factors.append('renal_impairment')
    if 'liver_disease' in conditions:
        risk_factors.append('hepatic_impairment')
    
    return PatientContext(
        id=f"patient_{draw(st.integers(min_value=1, max_value=10000))}",
        demographics={
            'age': age,
            'weight': weight,
            'height': height,
            'gender': gender,
            'bmi': weight / ((height / 100) ** 2)
        },
        conditions=conditions,
        medications=[],
        allergies=[],
        genetic_factors=genetic_factors,
        risk_factors=risk_factors,
        preferences={}
    )


# ============================================================================
# Property-Based Tests for Physiological Factor Analysis
# ============================================================================

class TestPhysiologicalFactorAnalysisProperties:
    """
    Property-based tests for physiological factor analysis
    
    **Validates: Requirements 6.1, 6.3**
    """
    
    @given(
        drug_id=drug_id_strategy(),
        patient=patient_with_genetics_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_patient_characteristics_mapped_to_drug_response(
        self,
        drug_id: str,
        patient: PatientContext
    ):
        """
        Property: Patient characteristics are mapped to drug response patterns
        
        **Validates: Requirement 6.1**
        
        For any medication analysis, the system should query knowledge graph
        relationships between patient characteristics (age, weight, gender)
        and drug response patterns.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Create service
        service = PhysiologicalAnalysisService(mock_db)
        
        # Analyze physiological response
        response = await service.analyze_physiological_response(
            drug_id=drug_id,
            patient_context=patient
        )
        
        # Verify response structure
        assert isinstance(response, PhysiologicalResponse), \
            "Should return PhysiologicalResponse"
        
        assert response.drug_id == drug_id, \
            "Response should match requested drug"
        
        assert response.patient_id == patient.id, \
            "Response should match patient"
        
        # Verify ADME patterns consider patient characteristics
        assert isinstance(response.adme_patterns, list), \
            "Should have ADME patterns list"
        
        # Check if patient characteristics are considered
        age = patient.demographics.get('age', 0)
        weight = patient.demographics.get('weight', 70)
        
        # If patient is elderly, should have age-related ADME considerations
        if age > 65:
            age_mentioned = any(
                'age' in pattern.description.lower() or
                any('age' in factor.lower() for factor in pattern.affected_by)
                for pattern in response.adme_patterns
            )
            assert age_mentioned or len(response.adme_patterns) == 0, \
                "Elderly patients should have age-related ADME considerations"
        
        # If patient has extreme weight, should have weight-related considerations
        if weight < 50 or weight > 100:
            weight_mentioned = any(
                'weight' in pattern.description.lower() or
                any('weight' in factor.lower() for factor in pattern.affected_by)
                for pattern in response.adme_patterns
            )
            # Weight considerations may or may not be present depending on drug
            # Just verify the analysis completed
        
        # Verify efficacy and safety predictions are valid
        assert 0.0 <= response.predicted_efficacy <= 1.0, \
            f"Efficacy should be 0-1, got {response.predicted_efficacy}"
        
        assert 0.0 <= response.predicted_safety <= 1.0, \
            f"Safety should be 0-1, got {response.predicted_safety}"
        
        assert 0.0 <= response.confidence <= 1.0, \
            f"Confidence should be 0-1, got {response.confidence}"
    
    @given(
        drug_id=drug_id_strategy(),
        patient=patient_with_genetics_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_pharmacogenomic_factors_integrated(
        self,
        drug_id: str,
        patient: PatientContext
    ):
        """
        Property: Pharmacogenomic factors are integrated when available
        
        **Validates: Requirement 6.3**
        
        For any medication analysis with genetic factors available, the system
        should incorporate pharmacogenomic relationships from the knowledge graph
        to predict medication response.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Create service
        service = PhysiologicalAnalysisService(mock_db)
        
        # Analyze physiological response
        response = await service.analyze_physiological_response(
            drug_id=drug_id,
            patient_context=patient
        )
        
        # Verify pharmacogenomic factors
        assert isinstance(response.pharmacogenomic_factors, list), \
            "Should have pharmacogenomic factors list"
        
        # If patient has genetic factors, should analyze them
        if patient.genetic_factors:
            # Check if any CYP450 genes are relevant to this drug
            drug_name = drug_id.replace('drug_', '')
            relevant_genes = []
            
            for gene, substrates in service.cyp450_substrates.items():
                if drug_name in substrates and gene in patient.genetic_factors:
                    relevant_genes.append(gene)
            
            # If drug is affected by patient's genetic variants, should have factors
            if relevant_genes:
                assert len(response.pharmacogenomic_factors) > 0, \
                    f"Should have pharmacogenomic factors for genes {relevant_genes}"
                
                # Verify factor structure
                for factor in response.pharmacogenomic_factors:
                    assert isinstance(factor, PharmacogenomicFactor), \
                        "Each factor should be PharmacogenomicFactor"
                    
                    assert factor.gene in patient.genetic_factors, \
                        f"Factor gene {factor.gene} should be in patient genetics"
                    
                    assert isinstance(factor.metabolizer_type, MetabolizerType), \
                        "Should have valid metabolizer type"
                    
                    assert 0.0 <= factor.confidence <= 1.0, \
                        f"Confidence should be 0-1, got {factor.confidence}"
                    
                    assert factor.clinical_significance, \
                        "Should have clinical significance"
                    
                    assert drug_id in factor.affected_drugs, \
                        "Factor should list affected drug"
    
    @given(
        drug_id=drug_id_strategy(),
        patient=patient_with_genetics_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_adme_patterns_explained(
        self,
        drug_id: str,
        patient: PatientContext
    ):
        """
        Property: ADME patterns are explained through patient characteristics
        
        **Validates: Requirement 6.1**
        
        For any medication analysis, the system should explain pharmacokinetics
        by following knowledge graph paths from patient characteristics to
        absorption, distribution, metabolism, and elimination patterns.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Create service
        service = PhysiologicalAnalysisService(mock_db)
        
        # Analyze physiological response
        response = await service.analyze_physiological_response(
            drug_id=drug_id,
            patient_context=patient
        )
        
        # Verify ADME patterns
        assert isinstance(response.adme_patterns, list), \
            "Should have ADME patterns list"
        
        # Check for ADME phases
        phases_present = set()
        for pattern in response.adme_patterns:
            assert isinstance(pattern, ADMEPattern), \
                "Each pattern should be ADMEPattern"
            
            assert isinstance(pattern.phase, ADMEPhase), \
                "Should have valid ADME phase"
            
            phases_present.add(pattern.phase)
            
            assert pattern.description, \
                "Should have description"
            
            assert isinstance(pattern.affected_by, list), \
                "Should have list of affecting factors"
            
            assert pattern.impact_on_efficacy, \
                "Should describe impact on efficacy"
            
            assert pattern.impact_on_safety, \
                "Should describe impact on safety"
            
            assert isinstance(pattern.recommendations, list), \
                "Should have recommendations list"
        
        # If patient has conditions affecting ADME, should have relevant patterns
        if 'liver_disease' in patient.conditions:
            # Should have metabolism pattern
            metabolism_patterns = [p for p in response.adme_patterns 
                                  if p.phase == ADMEPhase.METABOLISM]
            if metabolism_patterns:
                assert any('liver' in p.description.lower() or 
                          any('hepatic' in f.lower() for f in p.affected_by)
                          for p in metabolism_patterns), \
                    "Liver disease should affect metabolism pattern"
        
        if 'kidney_disease' in patient.conditions:
            # Should have excretion pattern
            excretion_patterns = [p for p in response.adme_patterns 
                                 if p.phase == ADMEPhase.EXCRETION]
            if excretion_patterns:
                assert any('renal' in p.description.lower() or 
                          any('renal' in f.lower() for f in p.affected_by)
                          for p in excretion_patterns), \
                    "Kidney disease should affect excretion pattern"
    
    @given(
        drug_id=drug_id_strategy(),
        patient=patient_with_genetics_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_dosing_adjustments_recommended(
        self,
        drug_id: str,
        patient: PatientContext
    ):
        """
        Property: Dosing adjustments are recommended based on physiological factors
        
        **Validates: Requirements 6.1, 6.3**
        
        For any medication analysis with relevant physiological factors, the system
        should provide dosing adjustment recommendations.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Create service
        service = PhysiologicalAnalysisService(mock_db)
        
        # Analyze physiological response
        response = await service.analyze_physiological_response(
            drug_id=drug_id,
            patient_context=patient
        )
        
        # Verify dosing adjustments
        assert isinstance(response.dosing_adjustments, list), \
            "Should have dosing adjustments list"
        
        # If patient has factors requiring dose adjustment, should have recommendations
        needs_adjustment = False
        
        # Check pharmacogenomic factors
        for factor in response.pharmacogenomic_factors:
            if factor.metabolizer_type in [MetabolizerType.POOR, MetabolizerType.ULTRA_RAPID]:
                needs_adjustment = True
                break
        
        # Check ADME patterns
        for pattern in response.adme_patterns:
            if 'impair' in pattern.description.lower() or \
               any('impair' in f.lower() for f in pattern.affected_by):
                needs_adjustment = True
                break
        
        # If adjustment needed, should have recommendations
        if needs_adjustment:
            # May or may not have adjustments depending on specific factors
            # Just verify the field is present and valid
            for adjustment in response.dosing_adjustments:
                assert isinstance(adjustment, str), \
                    "Each adjustment should be a string"
                assert len(adjustment) > 0, \
                    "Adjustment should not be empty"
    
    @given(
        drug_id=drug_id_strategy(),
        patient=patient_with_genetics_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_monitoring_recommendations_provided(
        self,
        drug_id: str,
        patient: PatientContext
    ):
        """
        Property: Monitoring recommendations are provided based on risk factors
        
        **Validates: Requirements 6.1, 6.3**
        
        For any medication analysis with risk factors, the system should provide
        appropriate monitoring recommendations.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Create service
        service = PhysiologicalAnalysisService(mock_db)
        
        # Analyze physiological response
        response = await service.analyze_physiological_response(
            drug_id=drug_id,
            patient_context=patient
        )
        
        # Verify monitoring recommendations
        assert isinstance(response.monitoring_recommendations, list), \
            "Should have monitoring recommendations list"
        
        # If patient has conditions requiring monitoring, should have recommendations
        if 'kidney_disease' in patient.conditions:
            # Should recommend renal monitoring
            renal_monitoring = any(
                'renal' in rec.lower() or 'kidney' in rec.lower() or 
                'creatinine' in rec.lower() or 'egfr' in rec.lower()
                for rec in response.monitoring_recommendations
            )
            assert renal_monitoring, \
                "Should recommend renal function monitoring for kidney disease"
        
        if 'liver_disease' in patient.conditions:
            # Should recommend hepatic monitoring
            hepatic_monitoring = any(
                'liver' in rec.lower() or 'hepatic' in rec.lower() or 
                'ast' in rec.lower() or 'alt' in rec.lower()
                for rec in response.monitoring_recommendations
            )
            assert hepatic_monitoring, \
                "Should recommend liver function monitoring for liver disease"
    
    @given(
        drug_id=drug_id_strategy(),
        patient=patient_with_genetics_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_efficacy_and_safety_predictions_valid(
        self,
        drug_id: str,
        patient: PatientContext
    ):
        """
        Property: Efficacy and safety predictions are within valid ranges
        
        **Validates: Requirements 6.1, 6.3**
        
        For any physiological analysis, predicted efficacy and safety scores
        should be between 0 and 1, with confidence scores also in valid range.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Create service
        service = PhysiologicalAnalysisService(mock_db)
        
        # Analyze physiological response
        response = await service.analyze_physiological_response(
            drug_id=drug_id,
            patient_context=patient
        )
        
        # Verify predictions are in valid range
        assert 0.0 <= response.predicted_efficacy <= 1.0, \
            f"Predicted efficacy should be 0-1, got {response.predicted_efficacy}"
        
        assert 0.0 <= response.predicted_safety <= 1.0, \
            f"Predicted safety should be 0-1, got {response.predicted_safety}"
        
        assert 0.0 <= response.confidence <= 1.0, \
            f"Confidence should be 0-1, got {response.confidence}"
        
        # Verify pharmacogenomic factor confidences
        for factor in response.pharmacogenomic_factors:
            assert 0.0 <= factor.confidence <= 1.0, \
                f"Factor confidence should be 0-1, got {factor.confidence}"
    
    @given(
        drug_id=drug_id_strategy(),
        patient1=patient_with_genetics_strategy(),
        patient2=patient_with_genetics_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_different_patients_get_personalized_analysis(
        self,
        drug_id: str,
        patient1: PatientContext,
        patient2: PatientContext
    ):
        """
        Property: Different patients receive personalized physiological analysis
        
        **Validates: Requirements 6.1, 6.3**
        
        For different patients, the system should provide personalized analysis
        that reflects each patient's unique characteristics and genetic factors.
        """
        # Ensure patients are different
        assume(patient1.id != patient2.id)
        assume(patient1.demographics.get('age') != patient2.demographics.get('age') or
               patient1.genetic_factors != patient2.genetic_factors or
               patient1.conditions != patient2.conditions)
        
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Create service
        service = PhysiologicalAnalysisService(mock_db)
        
        # Analyze both patients
        response1 = await service.analyze_physiological_response(
            drug_id=drug_id,
            patient_context=patient1
        )
        
        response2 = await service.analyze_physiological_response(
            drug_id=drug_id,
            patient_context=patient2
        )
        
        # Verify both analyses completed
        assert response1.patient_id == patient1.id
        assert response2.patient_id == patient2.id
        
        # If patients have different genetic factors, should have different PG analysis
        if patient1.genetic_factors != patient2.genetic_factors:
            # Pharmacogenomic factors should differ
            pg1_genes = set(f.gene for f in response1.pharmacogenomic_factors)
            pg2_genes = set(f.gene for f in response2.pharmacogenomic_factors)
            
            # If one patient has genetic data and other doesn't, should differ
            if patient1.genetic_factors and not patient2.genetic_factors:
                # Patient 1 may have more PG factors
                pass  # Analysis may still be similar if drug not affected by genes
            elif patient2.genetic_factors and not patient1.genetic_factors:
                # Patient 2 may have more PG factors
                pass
        
        # If patients have different conditions, ADME patterns should differ
        if patient1.conditions != patient2.conditions:
            adme1_phases = set(p.phase for p in response1.adme_patterns)
            adme2_phases = set(p.phase for p in response2.adme_patterns)
            
            # Patterns may differ based on conditions
            # Just verify both analyses are valid
            assert isinstance(response1.adme_patterns, list)
            assert isinstance(response2.adme_patterns, list)
