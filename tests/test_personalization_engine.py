"""
Tests for personalization engine
"""
import pytest
from unittest.mock import Mock, AsyncMock
from src.knowledge_graph.personalization_engine import (
    PersonalizationEngine,
    PersonalizedRiskScore,
    PhysiologicalFactors,
    DosingRecommendation,
    RankedMedication,
    RiskCategory,
    DosingAdjustmentType
)
from src.knowledge_graph.models import PatientContext
from src.knowledge_graph.database import KnowledgeGraphDatabase


@pytest.fixture
def mock_database():
    """Create mock database"""
    db = Mock(spec=KnowledgeGraphDatabase)
    db.find_drug_by_name = AsyncMock()
    return db


@pytest.fixture
def personalization_engine(mock_database):
    """Create personalization engine with mock database"""
    return PersonalizationEngine(mock_database)


@pytest.fixture
def sample_patient_context():
    """Sample patient context"""
    return PatientContext(
        id='patient_001',
        demographics={'age': 70, 'weight': 75, 'gender': 'male'},
        conditions=['hypertension', 'diabetes'],
        medications=[
            {'name': 'metformin', 'dose': '500mg', 'frequency': 'twice daily'},
            {'name': 'lisinopril', 'dose': '10mg', 'frequency': 'once daily'}
        ],
        allergies=['penicillin'],
        genetic_factors={'CYP2D6': 'poor_metabolizer'},
        risk_factors=['smoking', 'obesity']
    )


@pytest.fixture
def sample_drug_info():
    """Sample drug information"""
    return {
        'id': 'drug_warfarin',
        'name': 'Warfarin',
        'generic_name': 'warfarin',
        'drugbank_id': 'DB00682',
        'atc_codes': ['B01AA03'],
        'mechanism': 'Vitamin K antagonist',
        'indications': ['anticoagulation'],
        'contraindications': ['bleeding_disorders']
    }


class TestPersonalizedRiskCalculation:
    """Tests for personalized risk calculation"""
    
    @pytest.mark.asyncio
    async def test_calculate_personalized_risk_basic(
        self, personalization_engine, mock_database, sample_patient_context, sample_drug_info
    ):
        """Test basic personalized risk calculation"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        
        # Execute
        risk_score = await personalization_engine.calculate_personalized_risk(
            'drug_warfarin', sample_patient_context
        )
        
        # Verify
        assert isinstance(risk_score, PersonalizedRiskScore)
        assert risk_score.drug_id == 'drug_warfarin'
        assert risk_score.drug_name == 'Warfarin'
        assert 0.0 <= risk_score.base_risk <= 1.0
        assert 0.0 <= risk_score.final_risk_score <= 1.0
        assert isinstance(risk_score.risk_category, RiskCategory)
        assert len(risk_score.risk_factors) > 0
        assert len(risk_score.evidence_sources) > 0
        assert 0.0 <= risk_score.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_age_adjustment_elderly(
        self, personalization_engine, mock_database, sample_drug_info
    ):
        """Test age adjustment for elderly patients"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        elderly_patient = PatientContext(
            id='patient_elderly',
            demographics={'age': 75, 'weight': 70, 'gender': 'female'},
            conditions=[],
            medications=[],
            allergies=[],
            genetic_factors={},
            risk_factors=[]
        )
        
        # Execute
        risk_score = await personalization_engine.calculate_personalized_risk(
            'drug_warfarin', elderly_patient
        )
        
        # Verify - elderly should have higher risk
        assert risk_score.age_adjusted_risk > risk_score.base_risk
        assert 'Elderly patient' in ' '.join(risk_score.risk_factors)
    
    @pytest.mark.asyncio
    async def test_age_adjustment_pediatric(
        self, personalization_engine, mock_database, sample_drug_info
    ):
        """Test age adjustment for pediatric patients"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        pediatric_patient = PatientContext(
            id='patient_pediatric',
            demographics={'age': 12, 'weight': 40, 'gender': 'male'},
            conditions=[],
            medications=[],
            allergies=[],
            genetic_factors={},
            risk_factors=[]
        )
        
        # Execute
        risk_score = await personalization_engine.calculate_personalized_risk(
            'drug_warfarin', pediatric_patient
        )
        
        # Verify - pediatric should have higher risk
        assert risk_score.age_adjusted_risk > risk_score.base_risk
        assert 'Pediatric patient' in ' '.join(risk_score.risk_factors)
    
    @pytest.mark.asyncio
    async def test_comorbidity_adjustment(
        self, personalization_engine, mock_database, sample_drug_info
    ):
        """Test comorbidity-based risk adjustment"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        patient_with_comorbidities = PatientContext(
            id='patient_comorbid',
            demographics={'age': 60, 'weight': 80, 'gender': 'male'},
            conditions=['kidney_disease', 'liver_disease', 'heart_failure'],
            medications=[],
            allergies=[],
            genetic_factors={},
            risk_factors=[]
        )
        
        # Execute
        risk_score = await personalization_engine.calculate_personalized_risk(
            'drug_warfarin', patient_with_comorbidities
        )
        
        # Verify - comorbidities should increase risk
        assert risk_score.comorbidity_adjusted_risk > risk_score.age_adjusted_risk
        assert 'Comorbidities' in ' '.join(risk_score.risk_factors)
    
    @pytest.mark.asyncio
    async def test_polypharmacy_adjustment(
        self, personalization_engine, mock_database, sample_drug_info
    ):
        """Test polypharmacy-based risk adjustment"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        patient_with_polypharmacy = PatientContext(
            id='patient_poly',
            demographics={'age': 65, 'weight': 75, 'gender': 'female'},
            conditions=[],
            medications=[
                {'name': 'drug1'}, {'name': 'drug2'}, {'name': 'drug3'},
                {'name': 'drug4'}, {'name': 'drug5'}, {'name': 'drug6'}
            ],
            allergies=[],
            genetic_factors={},
            risk_factors=[]
        )
        
        # Execute
        risk_score = await personalization_engine.calculate_personalized_risk(
            'drug_warfarin', patient_with_polypharmacy
        )
        
        # Verify - polypharmacy should increase risk
        assert risk_score.polypharmacy_adjusted_risk > risk_score.comorbidity_adjusted_risk
        assert 'Polypharmacy' in ' '.join(risk_score.risk_factors)

    @pytest.mark.asyncio
    async def test_genetic_adjustment(
        self, personalization_engine, mock_database, sample_drug_info
    ):
        """Test genetic factor-based risk adjustment"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        patient_with_genetics = PatientContext(
            id='patient_genetic',
            demographics={'age': 50, 'weight': 70, 'gender': 'male'},
            conditions=[],
            medications=[],
            allergies=[],
            genetic_factors={'CYP2D6': 'poor_metabolizer', 'CYP2C19': 'intermediate_metabolizer'},
            risk_factors=[]
        )
        
        # Execute
        risk_score = await personalization_engine.calculate_personalized_risk(
            'drug_warfarin', patient_with_genetics
        )
        
        # Verify - genetic factors should increase risk
        assert risk_score.genetic_adjusted_risk > risk_score.polypharmacy_adjusted_risk
        assert 'Pharmacogenomic factors' in ' '.join(risk_score.risk_factors)
    
    @pytest.mark.asyncio
    async def test_risk_categorization(
        self, personalization_engine, mock_database, sample_drug_info
    ):
        """Test risk score categorization"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        
        # Test different risk levels
        low_risk_patient = PatientContext(
            id='patient_low',
            demographics={'age': 30, 'weight': 70, 'gender': 'male'},
            conditions=[],
            medications=[],
            allergies=[],
            genetic_factors={},
            risk_factors=[]
        )
        
        high_risk_patient = PatientContext(
            id='patient_high',
            demographics={'age': 80, 'weight': 60, 'gender': 'female'},
            conditions=['kidney_disease', 'liver_disease', 'heart_failure'],
            medications=[{'name': f'drug{i}'} for i in range(8)],
            allergies=[],
            genetic_factors={'CYP2D6': 'poor_metabolizer'},
            risk_factors=['smoking']
        )
        
        # Execute
        low_risk = await personalization_engine.calculate_personalized_risk(
            'drug_warfarin', low_risk_patient
        )
        high_risk = await personalization_engine.calculate_personalized_risk(
            'drug_warfarin', high_risk_patient
        )
        
        # Verify
        assert low_risk.final_risk_score < high_risk.final_risk_score
        assert low_risk.risk_category in [RiskCategory.VERY_LOW, RiskCategory.LOW, RiskCategory.MODERATE]
        assert high_risk.risk_category in [RiskCategory.HIGH, RiskCategory.VERY_HIGH]


class TestPhysiologicalFactorAnalysis:
    """Tests for physiological factor analysis"""
    
    @pytest.mark.asyncio
    async def test_analyze_physiological_factors_basic(
        self, personalization_engine, sample_patient_context
    ):
        """Test basic physiological factor analysis"""
        # Execute
        factors = await personalization_engine.analyze_physiological_factors(
            'drug_warfarin', sample_patient_context
        )
        
        # Verify
        assert isinstance(factors, PhysiologicalFactors)
        assert 0.0 < factors.age_factor <= 1.0
        assert factors.weight_factor > 0.0
        assert 0.0 < factors.renal_function_factor <= 1.0
        assert 0.0 < factors.hepatic_function_factor <= 1.0
        assert factors.metabolizer_status is not None
        assert factors.absorption_rate > 0.0
        assert factors.distribution_volume > 0.0
        assert factors.elimination_rate > 0.0

    @pytest.mark.asyncio
    async def test_age_factor_elderly(self, personalization_engine):
        """Test age factor calculation for elderly patients"""
        # Setup
        elderly_patient = PatientContext(
            id='patient_elderly',
            demographics={'age': 75, 'weight': 70, 'gender': 'female'},
            conditions=[],
            medications=[],
            allergies=[],
            genetic_factors={},
            risk_factors=[]
        )
        
        # Execute
        factors = await personalization_engine.analyze_physiological_factors(
            'drug_test', elderly_patient
        )
        
        # Verify - elderly should have reduced age factor
        assert factors.age_factor < 1.0
        assert factors.elimination_rate < 1.0
    
    @pytest.mark.asyncio
    async def test_renal_function_with_kidney_disease(self, personalization_engine):
        """Test renal function estimation with kidney disease"""
        # Setup
        patient_with_kidney_disease = PatientContext(
            id='patient_renal',
            demographics={'age': 60, 'weight': 75, 'gender': 'male'},
            conditions=['chronic_kidney_disease'],
            medications=[],
            allergies=[],
            genetic_factors={},
            risk_factors=[]
        )
        
        # Execute
        factors = await personalization_engine.analyze_physiological_factors(
            'drug_test', patient_with_kidney_disease
        )
        
        # Verify - should have reduced renal function
        assert factors.renal_function_factor < 1.0
        assert factors.elimination_rate < 1.0
    
    @pytest.mark.asyncio
    async def test_hepatic_function_with_liver_disease(self, personalization_engine):
        """Test hepatic function estimation with liver disease"""
        # Setup
        patient_with_liver_disease = PatientContext(
            id='patient_hepatic',
            demographics={'age': 55, 'weight': 80, 'gender': 'male'},
            conditions=['cirrhosis'],
            medications=[],
            allergies=[],
            genetic_factors={},
            risk_factors=[]
        )
        
        # Execute
        factors = await personalization_engine.analyze_physiological_factors(
            'drug_test', patient_with_liver_disease
        )
        
        # Verify - should have reduced hepatic function
        assert factors.hepatic_function_factor < 1.0
        assert factors.elimination_rate < 1.0
    
    @pytest.mark.asyncio
    async def test_metabolizer_status_determination(self, personalization_engine):
        """Test metabolizer status determination from genetic factors"""
        # Setup - poor metabolizer
        poor_metabolizer_patient = PatientContext(
            id='patient_poor',
            demographics={'age': 50, 'weight': 70, 'gender': 'male'},
            conditions=[],
            medications=[],
            allergies=[],
            genetic_factors={'CYP2D6': 'poor_metabolizer'},
            risk_factors=[]
        )
        
        # Execute
        factors = await personalization_engine.analyze_physiological_factors(
            'drug_test', poor_metabolizer_patient
        )
        
        # Verify
        assert factors.metabolizer_status == 'poor_metabolizer'


class TestDosingRecommendations:
    """Tests for dosing adjustment recommendations"""
    
    @pytest.mark.asyncio
    async def test_generate_dosing_recommendation_basic(
        self, personalization_engine, mock_database, sample_patient_context, sample_drug_info
    ):
        """Test basic dosing recommendation generation"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        
        # Execute
        dosing_rec = await personalization_engine.generate_dosing_recommendation(
            'drug_warfarin', sample_patient_context
        )
        
        # Verify
        assert isinstance(dosing_rec, DosingRecommendation)
        assert dosing_rec.drug_id == 'drug_warfarin'
        assert dosing_rec.drug_name == 'Warfarin'
        assert dosing_rec.standard_dose is not None
        assert dosing_rec.recommended_dose is not None
        assert isinstance(dosing_rec.adjustment_type, DosingAdjustmentType)
        assert isinstance(dosing_rec.adjustment_percentage, float)
        assert dosing_rec.rationale is not None
        assert len(dosing_rec.physiological_basis) > 0
        assert len(dosing_rec.monitoring_requirements) > 0
        assert 0.0 <= dosing_rec.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_dose_reduction_for_renal_impairment(
        self, personalization_engine, mock_database, sample_drug_info
    ):
        """Test dose reduction recommendation for renal impairment"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        patient_with_renal_impairment = PatientContext(
            id='patient_renal',
            demographics={'age': 70, 'weight': 75, 'gender': 'male'},
            conditions=['chronic_kidney_disease'],
            medications=[],
            allergies=[],
            genetic_factors={},
            risk_factors=[]
        )
        
        # Execute
        dosing_rec = await personalization_engine.generate_dosing_recommendation(
            'drug_warfarin', patient_with_renal_impairment
        )
        
        # Verify - should recommend dose reduction
        assert dosing_rec.adjustment_type == DosingAdjustmentType.REDUCE_DOSE
        assert dosing_rec.adjustment_percentage < 0
        assert 'renal' in dosing_rec.rationale.lower()
        assert any('renal' in basis.lower() for basis in dosing_rec.physiological_basis)
        assert any('renal' in req.lower() for req in dosing_rec.monitoring_requirements)
    
    @pytest.mark.asyncio
    async def test_dose_reduction_for_hepatic_impairment(
        self, personalization_engine, mock_database, sample_drug_info
    ):
        """Test dose reduction recommendation for hepatic impairment"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        patient_with_hepatic_impairment = PatientContext(
            id='patient_hepatic',
            demographics={'age': 60, 'weight': 80, 'gender': 'male'},
            conditions=['cirrhosis'],
            medications=[],
            allergies=[],
            genetic_factors={},
            risk_factors=[]
        )
        
        # Execute
        dosing_rec = await personalization_engine.generate_dosing_recommendation(
            'drug_warfarin', patient_with_hepatic_impairment
        )
        
        # Verify - should recommend dose reduction
        assert dosing_rec.adjustment_type == DosingAdjustmentType.REDUCE_DOSE
        assert dosing_rec.adjustment_percentage < 0
        assert 'hepatic' in dosing_rec.rationale.lower() or 'liver' in dosing_rec.rationale.lower()
        assert any('hepatic' in basis.lower() or 'liver' in basis.lower() 
                   for basis in dosing_rec.physiological_basis)

    @pytest.mark.asyncio
    async def test_dose_reduction_for_poor_metabolizer(
        self, personalization_engine, mock_database, sample_drug_info
    ):
        """Test dose reduction for poor metabolizer"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        poor_metabolizer_patient = PatientContext(
            id='patient_poor',
            demographics={'age': 50, 'weight': 70, 'gender': 'male'},
            conditions=[],
            medications=[],
            allergies=[],
            genetic_factors={'CYP2D6': 'poor_metabolizer'},
            risk_factors=[]
        )
        
        # Execute
        dosing_rec = await personalization_engine.generate_dosing_recommendation(
            'drug_warfarin', poor_metabolizer_patient
        )
        
        # Verify - should recommend dose reduction
        assert dosing_rec.adjustment_type == DosingAdjustmentType.REDUCE_DOSE
        assert dosing_rec.adjustment_percentage < 0
        assert 'metabolizer' in dosing_rec.rationale.lower()
        assert any('genetic' in basis.lower() or 'metabolism' in basis.lower() 
                   for basis in dosing_rec.physiological_basis)
    
    @pytest.mark.asyncio
    async def test_dose_increase_for_rapid_metabolizer(
        self, personalization_engine, mock_database, sample_drug_info
    ):
        """Test dose increase for rapid metabolizer"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        rapid_metabolizer_patient = PatientContext(
            id='patient_rapid',
            demographics={'age': 45, 'weight': 75, 'gender': 'female'},
            conditions=[],
            medications=[],
            allergies=[],
            genetic_factors={'CYP2D6': 'rapid_metabolizer'},
            risk_factors=[]
        )
        
        # Execute
        dosing_rec = await personalization_engine.generate_dosing_recommendation(
            'drug_warfarin', rapid_metabolizer_patient
        )
        
        # Verify - should recommend dose increase
        assert dosing_rec.adjustment_type == DosingAdjustmentType.INCREASE_DOSE
        assert dosing_rec.adjustment_percentage > 0
        assert 'metabolizer' in dosing_rec.rationale.lower()
    
    @pytest.mark.asyncio
    async def test_no_adjustment_for_normal_patient(
        self, personalization_engine, mock_database, sample_drug_info
    ):
        """Test no adjustment for patient with normal factors"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        normal_patient = PatientContext(
            id='patient_normal',
            demographics={'age': 40, 'weight': 70, 'gender': 'male'},
            conditions=[],
            medications=[],
            allergies=[],
            genetic_factors={},
            risk_factors=[]
        )
        
        # Execute
        dosing_rec = await personalization_engine.generate_dosing_recommendation(
            'drug_warfarin', normal_patient
        )
        
        # Verify - should not require adjustment
        assert dosing_rec.adjustment_type == DosingAdjustmentType.NO_ADJUSTMENT
        assert dosing_rec.adjustment_percentage == 0.0


class TestMedicationRanking:
    """Tests for medication ranking by risk"""
    
    @pytest.mark.asyncio
    async def test_rank_medications_basic(
        self, personalization_engine, mock_database, sample_patient_context, sample_drug_info
    ):
        """Test basic medication ranking"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        drug_ids = ['drug_a', 'drug_b', 'drug_c']
        
        # Execute
        ranked_meds = await personalization_engine.rank_medications_by_risk(
            drug_ids, sample_patient_context
        )
        
        # Verify
        assert len(ranked_meds) == 3
        assert all(isinstance(med, RankedMedication) for med in ranked_meds)
        
        # Verify ranking order
        for i in range(len(ranked_meds)):
            assert ranked_meds[i].rank == i + 1
        
        # Verify suitability is in descending order
        for i in range(len(ranked_meds) - 1):
            assert ranked_meds[i].overall_suitability >= ranked_meds[i + 1].overall_suitability

    @pytest.mark.asyncio
    async def test_ranked_medication_structure(
        self, personalization_engine, mock_database, sample_patient_context, sample_drug_info
    ):
        """Test ranked medication structure"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        drug_ids = ['drug_a']
        
        # Execute
        ranked_meds = await personalization_engine.rank_medications_by_risk(
            drug_ids, sample_patient_context
        )
        
        # Verify structure
        med = ranked_meds[0]
        assert med.drug_id is not None
        assert med.drug_name is not None
        assert med.rank > 0
        assert isinstance(med.risk_score, PersonalizedRiskScore)
        assert isinstance(med.dosing_recommendation, DosingRecommendation)
        assert isinstance(med.side_effects, list)
        assert isinstance(med.interactions, list)
        assert 0.0 <= med.overall_suitability <= 1.0


class TestIntegration:
    """Integration tests for personalization engine"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_personalization_flow(
        self, personalization_engine, mock_database, sample_patient_context, sample_drug_info
    ):
        """Test complete personalization flow"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        
        # Execute - calculate risk
        risk_score = await personalization_engine.calculate_personalized_risk(
            'drug_warfarin', sample_patient_context
        )
        
        # Execute - analyze physiological factors
        phys_factors = await personalization_engine.analyze_physiological_factors(
            'drug_warfarin', sample_patient_context
        )
        
        # Execute - generate dosing recommendation
        dosing_rec = await personalization_engine.generate_dosing_recommendation(
            'drug_warfarin', sample_patient_context
        )
        
        # Verify all components work together
        assert risk_score.final_risk_score > 0
        assert phys_factors.elimination_rate > 0
        assert dosing_rec.adjustment_type is not None
        
        # Verify consistency
        # If patient has poor metabolizer status, should have dose reduction
        if phys_factors.metabolizer_status == 'poor_metabolizer':
            assert dosing_rec.adjustment_type in [
                DosingAdjustmentType.REDUCE_DOSE,
                DosingAdjustmentType.MONITOR_LEVELS
            ]
    
    @pytest.mark.asyncio
    async def test_high_risk_patient_comprehensive(
        self, personalization_engine, mock_database, sample_drug_info
    ):
        """Test comprehensive personalization for high-risk patient"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        high_risk_patient = PatientContext(
            id='patient_high_risk',
            demographics={'age': 80, 'weight': 55, 'gender': 'female'},
            conditions=['chronic_kidney_disease', 'heart_failure', 'diabetes'],
            medications=[
                {'name': f'drug{i}'} for i in range(7)
            ],
            allergies=['sulfa'],
            genetic_factors={'CYP2D6': 'poor_metabolizer'},
            risk_factors=['frailty']
        )
        
        # Execute
        risk_score = await personalization_engine.calculate_personalized_risk(
            'drug_warfarin', high_risk_patient
        )
        phys_factors = await personalization_engine.analyze_physiological_factors(
            'drug_warfarin', high_risk_patient
        )
        dosing_rec = await personalization_engine.generate_dosing_recommendation(
            'drug_warfarin', high_risk_patient
        )
        
        # Verify high-risk characteristics
        assert risk_score.risk_category in [RiskCategory.HIGH, RiskCategory.VERY_HIGH]
        assert len(risk_score.risk_factors) >= 3
        assert phys_factors.renal_function_factor < 1.0
        assert phys_factors.elimination_rate < 1.0
        assert dosing_rec.adjustment_type == DosingAdjustmentType.REDUCE_DOSE
        assert len(dosing_rec.monitoring_requirements) >= 3
    
    @pytest.mark.asyncio
    async def test_low_risk_patient_comprehensive(
        self, personalization_engine, mock_database, sample_drug_info
    ):
        """Test comprehensive personalization for low-risk patient"""
        # Setup
        mock_database.find_drug_by_name.return_value = sample_drug_info
        low_risk_patient = PatientContext(
            id='patient_low_risk',
            demographics={'age': 35, 'weight': 70, 'gender': 'male'},
            conditions=[],
            medications=[],
            allergies=[],
            genetic_factors={},
            risk_factors=[]
        )
        
        # Execute
        risk_score = await personalization_engine.calculate_personalized_risk(
            'drug_warfarin', low_risk_patient
        )
        phys_factors = await personalization_engine.analyze_physiological_factors(
            'drug_warfarin', low_risk_patient
        )
        dosing_rec = await personalization_engine.generate_dosing_recommendation(
            'drug_warfarin', low_risk_patient
        )
        
        # Verify low-risk characteristics
        assert risk_score.risk_category in [RiskCategory.VERY_LOW, RiskCategory.LOW, RiskCategory.MODERATE]
        assert phys_factors.age_factor == 1.0
        assert phys_factors.renal_function_factor == 1.0
        assert phys_factors.hepatic_function_factor == 1.0
        assert dosing_rec.adjustment_type == DosingAdjustmentType.NO_ADJUSTMENT
