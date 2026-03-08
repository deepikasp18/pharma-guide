"""
Property-based tests for risk-based ranking with real-world evidence

**Validates: Requirement 2.4**

Property 6: Risk-Based Ranking with Real-World Evidence
For any medication and patient combination, adverse effects should be ranked using
knowledge graph-derived risk factors and real-world evidence from FAERS data.
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite
from typing import List, Dict, Any

from src.knowledge_graph.personalization_engine import (
    PersonalizationEngine,
    PersonalizedRiskScore,
    RankedMedication,
    RiskCategory
)
from src.knowledge_graph.models import PatientContext
from src.knowledge_graph.database import KnowledgeGraphDatabase
from unittest.mock import AsyncMock, MagicMock


# ============================================================================
# Strategy Generators for Property-Based Testing
# ============================================================================

@composite
def patient_context_strategy(draw):
    """Generate patient context for risk ranking"""
    age = draw(st.integers(min_value=18, max_value=90))
    weight = draw(st.floats(min_value=40.0, max_value=150.0))
    gender = draw(st.sampled_from(['male', 'female']))
    
    # Conditions
    conditions = ['hypertension', 'diabetes', 'heart_failure', 'chronic_kidney_disease', 'cirrhosis']
    num_conditions = draw(st.integers(min_value=0, max_value=3))
    selected_conditions = draw(st.lists(
        st.sampled_from(conditions),
        min_size=num_conditions,
        max_size=num_conditions,
        unique=True
    )) if num_conditions > 0 else []
    
    # Medications
    drugs = ['Lisinopril', 'Metformin', 'Atorvastatin', 'Aspirin', 'Warfarin']
    num_meds = draw(st.integers(min_value=0, max_value=5))
    medications = []
    if num_meds > 0:
        selected_drugs = draw(st.lists(
            st.sampled_from(drugs),
            min_size=num_meds,
            max_size=num_meds,
            unique=True
        ))
        medications = [{'name': drug, 'dosage': '10mg'} for drug in selected_drugs]
    
    # Genetic factors
    genetic_factors = {}
    if draw(st.booleans()):
        genetic_factors = {
            'CYP2D6': draw(st.sampled_from(['poor_metabolizer', 'normal_metabolizer', 'rapid_metabolizer']))
        }
    
    # Risk factors
    risk_factors = []
    if draw(st.booleans()):
        risk_factors = draw(st.lists(
            st.sampled_from(['smoking', 'obesity', 'alcohol_use']),
            min_size=0,
            max_size=2,
            unique=True
        ))
    
    return PatientContext(
        id=f"patient_{draw(st.integers(min_value=1, max_value=10000))}",
        demographics={'age': age, 'weight': weight, 'gender': gender},
        conditions=selected_conditions,
        medications=medications,
        allergies=[],
        genetic_factors=genetic_factors,
        risk_factors=risk_factors,
        preferences={}
    )


@composite
def drug_id_strategy(draw):
    """Generate drug IDs"""
    drugs = [
        'drug_warfarin', 'drug_aspirin', 'drug_lisinopril',
        'drug_metformin', 'drug_atorvastatin', 'drug_amlodipine',
        'drug_losartan', 'drug_simvastatin'
    ]
    return draw(st.sampled_from(drugs))


@composite
def drug_list_strategy(draw):
    """Generate list of drug IDs"""
    drugs = [
        'drug_warfarin', 'drug_aspirin', 'drug_lisinopril',
        'drug_metformin', 'drug_atorvastatin', 'drug_amlodipine'
    ]
    num_drugs = draw(st.integers(min_value=2, max_value=5))
    return draw(st.lists(
        st.sampled_from(drugs),
        min_size=num_drugs,
        max_size=num_drugs,
        unique=True
    ))


# ============================================================================
# Property-Based Tests for Risk-Based Ranking
# ============================================================================

class TestRiskBasedRankingProperties:
    """
    Property-based tests for risk-based ranking with real-world evidence
    
    **Validates: Requirement 2.4**
    """
    
    @given(
        patient=patient_context_strategy(),
        drug_id=drug_id_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_risk_score_calculated_for_all_combinations(
        self,
        patient: PatientContext,
        drug_id: str
    ):
        """
        Property: Risk scores are calculated for all patient-drug combinations
        
        **Validates: Requirement 2.4**
        
        For any medication and patient combination, the system should calculate
        a personalized risk score.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.find_drug_by_name = AsyncMock(return_value={
            'id': drug_id,
            'name': drug_id.replace('drug_', '').title(),
            'generic_name': drug_id.replace('drug_', ''),
            'drugbank_id': 'DB00001',
            'atc_codes': ['C09AA03'],
            'mechanism': 'Test mechanism',
            'indications': ['test'],
            'contraindications': []
        })
        
        # Create personalization engine
        engine = PersonalizationEngine(mock_db)
        
        # Calculate risk score
        risk_score = await engine.calculate_personalized_risk(drug_id, patient)
        
        # Verify risk score structure
        assert isinstance(risk_score, PersonalizedRiskScore)
        assert risk_score.drug_id == drug_id
        assert 0.0 <= risk_score.base_risk <= 1.0
        assert 0.0 <= risk_score.final_risk_score <= 1.0
        assert isinstance(risk_score.risk_category, RiskCategory)
        assert isinstance(risk_score.risk_factors, list)
        assert isinstance(risk_score.evidence_sources, list)
        assert 0.0 <= risk_score.confidence <= 1.0
    
    @given(
        patient=patient_context_strategy(),
        drug_list=drug_list_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_medications_ranked_by_suitability(
        self,
        patient: PatientContext,
        drug_list: List[str]
    ):
        """
        Property: Medications are ranked by overall suitability
        
        **Validates: Requirement 2.4**
        
        For any list of medications and patient, medications should be
        ranked in descending order of suitability.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.find_drug_by_name = AsyncMock(side_effect=lambda drug_id: {
            'id': drug_id,
            'name': drug_id.replace('drug_', '').title(),
            'generic_name': drug_id.replace('drug_', ''),
            'drugbank_id': 'DB00001',
            'atc_codes': ['C09AA03'],
            'mechanism': 'Test mechanism',
            'indications': ['test'],
            'contraindications': []
        })
        
        # Create personalization engine
        engine = PersonalizationEngine(mock_db)
        
        # Rank medications
        ranked_meds = await engine.rank_medications_by_risk(drug_list, patient)
        
        # Verify ranking structure
        assert len(ranked_meds) == len(drug_list)
        assert all(isinstance(med, RankedMedication) for med in ranked_meds)
        
        # Verify ranking order (rank 1 is best)
        for i, med in enumerate(ranked_meds):
            assert med.rank == i + 1
        
        # Verify suitability is in descending order
        for i in range(len(ranked_meds) - 1):
            assert ranked_meds[i].overall_suitability >= ranked_meds[i + 1].overall_suitability, \
                f"Medications should be ranked by suitability: " \
                f"{ranked_meds[i].drug_name} ({ranked_meds[i].overall_suitability}) >= " \
                f"{ranked_meds[i + 1].drug_name} ({ranked_meds[i + 1].overall_suitability})"
    
    @given(
        patient=patient_context_strategy(),
        drug_id=drug_id_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_risk_factors_include_patient_characteristics(
        self,
        patient: PatientContext,
        drug_id: str
    ):
        """
        Property: Risk factors reflect patient characteristics
        
        **Validates: Requirement 2.4**
        
        For any patient-drug combination, identified risk factors should
        reflect the patient's characteristics.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.find_drug_by_name = AsyncMock(return_value={
            'id': drug_id,
            'name': drug_id.replace('drug_', '').title(),
            'generic_name': drug_id.replace('drug_', ''),
            'drugbank_id': 'DB00001',
            'atc_codes': ['C09AA03'],
            'mechanism': 'Test mechanism',
            'indications': ['test'],
            'contraindications': []
        })
        
        # Create personalization engine
        engine = PersonalizationEngine(mock_db)
        
        # Calculate risk score
        risk_score = await engine.calculate_personalized_risk(drug_id, patient)
        
        # Verify risk factors reflect patient characteristics
        risk_factors_text = ' '.join(risk_score.risk_factors).lower()
        
        # Check age-related risk factors
        age = patient.demographics.get('age', 0)
        if age >= 65:
            assert 'elderly' in risk_factors_text or 'age' in risk_factors_text, \
                "Elderly patients should have age-related risk factors"
        elif age < 18:
            assert 'pediatric' in risk_factors_text or 'age' in risk_factors_text, \
                "Pediatric patients should have age-related risk factors"
        
        # Check comorbidity risk factors
        if len(patient.conditions) > 0:
            assert 'comorbid' in risk_factors_text or 'condition' in risk_factors_text, \
                "Patients with conditions should have comorbidity risk factors"
        
        # Check polypharmacy risk factors (implementation uses > 5)
        if len(patient.medications) > 5:
            assert 'polypharmacy' in risk_factors_text or 'medication' in risk_factors_text, \
                "Patients with many medications should have polypharmacy risk factors"
        
        # Check genetic risk factors
        if patient.genetic_factors:
            assert 'genetic' in risk_factors_text or 'pharmacogenomic' in risk_factors_text, \
                "Patients with genetic factors should have genetic risk factors"
    
    @given(
        patient=patient_context_strategy(),
        drug_id=drug_id_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_risk_category_matches_risk_score(
        self,
        patient: PatientContext,
        drug_id: str
    ):
        """
        Property: Risk category matches the calculated risk score
        
        **Validates: Requirement 2.4**
        
        For any risk score, the assigned risk category should be
        consistent with the numerical score.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.find_drug_by_name = AsyncMock(return_value={
            'id': drug_id,
            'name': drug_id.replace('drug_', '').title(),
            'generic_name': drug_id.replace('drug_', ''),
            'drugbank_id': 'DB00001',
            'atc_codes': ['C09AA03'],
            'mechanism': 'Test mechanism',
            'indications': ['test'],
            'contraindications': []
        })
        
        # Create personalization engine
        engine = PersonalizationEngine(mock_db)
        
        # Calculate risk score
        risk_score = await engine.calculate_personalized_risk(drug_id, patient)
        
        # Verify risk category matches score
        score = risk_score.final_risk_score
        category = risk_score.risk_category
        
        if score < 0.2:
            assert category == RiskCategory.VERY_LOW, \
                f"Score {score} should be VERY_LOW, got {category}"
        elif score < 0.4:
            assert category == RiskCategory.LOW, \
                f"Score {score} should be LOW, got {category}"
        elif score < 0.6:
            assert category == RiskCategory.MODERATE, \
                f"Score {score} should be MODERATE, got {category}"
        elif score < 0.8:
            assert category == RiskCategory.HIGH, \
                f"Score {score} should be HIGH, got {category}"
        else:
            assert category == RiskCategory.VERY_HIGH, \
                f"Score {score} should be VERY_HIGH, got {category}"
    
    @given(
        patient=patient_context_strategy(),
        drug_id=drug_id_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_evidence_sources_provided(
        self,
        patient: PatientContext,
        drug_id: str
    ):
        """
        Property: Evidence sources are provided for risk assessments
        
        **Validates: Requirement 2.4**
        
        For any risk assessment, evidence sources should be provided
        to support the risk calculation.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.find_drug_by_name = AsyncMock(return_value={
            'id': drug_id,
            'name': drug_id.replace('drug_', '').title(),
            'generic_name': drug_id.replace('drug_', ''),
            'drugbank_id': 'DB00001',
            'atc_codes': ['C09AA03'],
            'mechanism': 'Test mechanism',
            'indications': ['test'],
            'contraindications': []
        })
        
        # Create personalization engine
        engine = PersonalizationEngine(mock_db)
        
        # Calculate risk score
        risk_score = await engine.calculate_personalized_risk(drug_id, patient)
        
        # Verify evidence sources are provided
        assert len(risk_score.evidence_sources) > 0, \
            "Risk assessment should include evidence sources"
        
        # Evidence sources should be valid dataset names
        valid_sources = [
            'FAERS', 'OnSIDES', 'SIDER', 'DrugBank', 'Clinical_Guidelines',
            'Patient_Demographics', 'Pharmacogenomics'
        ]
        
        for source in risk_score.evidence_sources:
            assert any(valid in source for valid in valid_sources), \
                f"Evidence source '{source}' should be from valid datasets"
    
    @given(
        patient=patient_context_strategy(),
        drug_id=drug_id_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_confidence_score_provided(
        self,
        patient: PatientContext,
        drug_id: str
    ):
        """
        Property: Confidence scores are provided for risk assessments
        
        **Validates: Requirement 2.4**
        
        For any risk assessment, a confidence score should indicate
        the reliability of the assessment.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.find_drug_by_name = AsyncMock(return_value={
            'id': drug_id,
            'name': drug_id.replace('drug_', '').title(),
            'generic_name': drug_id.replace('drug_', ''),
            'drugbank_id': 'DB00001',
            'atc_codes': ['C09AA03'],
            'mechanism': 'Test mechanism',
            'indications': ['test'],
            'contraindications': []
        })
        
        # Create personalization engine
        engine = PersonalizationEngine(mock_db)
        
        # Calculate risk score
        risk_score = await engine.calculate_personalized_risk(drug_id, patient)
        
        # Verify confidence score
        assert 0.0 <= risk_score.confidence <= 1.0, \
            f"Confidence should be between 0 and 1, got {risk_score.confidence}"
        
        # Confidence should be higher when more evidence is available
        if len(risk_score.evidence_sources) >= 3:
            assert risk_score.confidence >= 0.5, \
                "Confidence should be higher with more evidence sources"
    
    @given(patient=patient_context_strategy())
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_high_risk_patients_identified(self, patient: PatientContext):
        """
        Property: High-risk patients are correctly identified
        
        **Validates: Requirement 2.4**
        
        For patients with multiple risk factors, the system should
        identify them as high risk.
        """
        # Create a high-risk patient profile
        high_risk_patient = PatientContext(
            id=patient.id,
            demographics={'age': 80, 'weight': 55, 'gender': 'female'},
            conditions=['chronic_kidney_disease', 'heart_failure', 'diabetes'],
            medications=[{'name': f'Drug{i}', 'dosage': '10mg'} for i in range(7)],
            allergies=[],
            genetic_factors={'CYP2D6': 'poor_metabolizer'},
            risk_factors=['frailty'],
            preferences={}
        )
        
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.find_drug_by_name = AsyncMock(return_value={
            'id': 'drug_warfarin',
            'name': 'Warfarin',
            'generic_name': 'warfarin',
            'drugbank_id': 'DB00682',
            'atc_codes': ['B01AA03'],
            'mechanism': 'Vitamin K antagonist',
            'indications': ['anticoagulation'],
            'contraindications': []
        })
        
        # Create personalization engine
        engine = PersonalizationEngine(mock_db)
        
        # Calculate risk score
        risk_score = await engine.calculate_personalized_risk('drug_warfarin', high_risk_patient)
        
        # High-risk patient should have high risk category
        assert risk_score.risk_category in [RiskCategory.HIGH, RiskCategory.VERY_HIGH], \
            f"High-risk patient should have HIGH or VERY_HIGH category, got {risk_score.risk_category}"
        
        # Should have multiple risk factors identified
        assert len(risk_score.risk_factors) >= 3, \
            f"High-risk patient should have multiple risk factors, got {len(risk_score.risk_factors)}"
    
    @given(patient=patient_context_strategy())
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_low_risk_patients_identified(self, patient: PatientContext):
        """
        Property: Low-risk patients are correctly identified
        
        **Validates: Requirement 2.4**
        
        For patients with few risk factors, the system should
        identify them as low risk.
        """
        # Create a low-risk patient profile
        low_risk_patient = PatientContext(
            id=patient.id,
            demographics={'age': 35, 'weight': 70, 'gender': 'male'},
            conditions=[],
            medications=[],
            allergies=[],
            genetic_factors={},
            risk_factors=[],
            preferences={}
        )
        
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.find_drug_by_name = AsyncMock(return_value={
            'id': 'drug_aspirin',
            'name': 'Aspirin',
            'generic_name': 'aspirin',
            'drugbank_id': 'DB00945',
            'atc_codes': ['N02BA01'],
            'mechanism': 'COX inhibitor',
            'indications': ['pain', 'fever'],
            'contraindications': []
        })
        
        # Create personalization engine
        engine = PersonalizationEngine(mock_db)
        
        # Calculate risk score
        risk_score = await engine.calculate_personalized_risk('drug_aspirin', low_risk_patient)
        
        # Low-risk patient should have low risk category
        assert risk_score.risk_category in [RiskCategory.VERY_LOW, RiskCategory.LOW, RiskCategory.MODERATE], \
            f"Low-risk patient should have VERY_LOW, LOW, or MODERATE category, got {risk_score.risk_category}"
        
        # Final risk score should be relatively low
        assert risk_score.final_risk_score < 0.6, \
            f"Low-risk patient should have low risk score, got {risk_score.final_risk_score}"
    
    @given(
        patient=patient_context_strategy(),
        drug_list=drug_list_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_ranking_consistency(
        self,
        patient: PatientContext,
        drug_list: List[str]
    ):
        """
        Property: Ranking is consistent across multiple calls
        
        **Validates: Requirement 2.4**
        
        For the same patient and drug list, ranking should be
        consistent across multiple calls.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.find_drug_by_name = AsyncMock(side_effect=lambda drug_id: {
            'id': drug_id,
            'name': drug_id.replace('drug_', '').title(),
            'generic_name': drug_id.replace('drug_', ''),
            'drugbank_id': 'DB00001',
            'atc_codes': ['C09AA03'],
            'mechanism': 'Test mechanism',
            'indications': ['test'],
            'contraindications': []
        })
        
        # Create personalization engine
        engine = PersonalizationEngine(mock_db)
        
        # Rank medications twice
        ranked_meds_1 = await engine.rank_medications_by_risk(drug_list, patient)
        ranked_meds_2 = await engine.rank_medications_by_risk(drug_list, patient)
        
        # Rankings should be identical
        assert len(ranked_meds_1) == len(ranked_meds_2)
        
        for i in range(len(ranked_meds_1)):
            assert ranked_meds_1[i].drug_id == ranked_meds_2[i].drug_id, \
                f"Ranking should be consistent: position {i}"
            assert ranked_meds_1[i].rank == ranked_meds_2[i].rank, \
                f"Rank should be consistent: position {i}"
            assert abs(ranked_meds_1[i].overall_suitability - ranked_meds_2[i].overall_suitability) < 0.01, \
                f"Suitability score should be consistent: position {i}"
    
    @given(
        patient=patient_context_strategy(),
        drug_list=drug_list_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_ranked_medications_include_complete_information(
        self,
        patient: PatientContext,
        drug_list: List[str]
    ):
        """
        Property: Ranked medications include complete information
        
        **Validates: Requirement 2.4**
        
        For any ranked medication list, each medication should include
        complete risk and recommendation information.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        mock_db.find_drug_by_name = AsyncMock(side_effect=lambda drug_id: {
            'id': drug_id,
            'name': drug_id.replace('drug_', '').title(),
            'generic_name': drug_id.replace('drug_', ''),
            'drugbank_id': 'DB00001',
            'atc_codes': ['C09AA03'],
            'mechanism': 'Test mechanism',
            'indications': ['test'],
            'contraindications': []
        })
        
        # Create personalization engine
        engine = PersonalizationEngine(mock_db)
        
        # Rank medications
        ranked_meds = await engine.rank_medications_by_risk(drug_list, patient)
        
        # Verify each medication has complete information
        for med in ranked_meds:
            assert med.drug_id is not None
            assert med.drug_name is not None
            assert med.rank > 0
            assert isinstance(med.risk_score, PersonalizedRiskScore)
            assert med.dosing_recommendation is not None
            assert isinstance(med.side_effects, list)
            assert isinstance(med.interactions, list)
            assert 0.0 <= med.overall_suitability <= 1.0
