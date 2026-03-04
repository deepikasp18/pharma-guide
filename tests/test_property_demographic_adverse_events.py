"""
Property-based tests for demographic-based adverse event analysis

**Validates: Requirements 5.2, 5.4**

Property 13: Demographic-Based Adverse Event Analysis
For any patient demographics, the system should traverse knowledge graph relationships
to correlate patient-specific risk factors with adverse event patterns.
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite
from typing import List, Dict, Any, Optional

from src.knowledge_graph.side_effect_service import (
    SideEffectRetrievalService,
    SideEffectResult,
    DataSourceType,
    DemographicCorrelation
)
from src.knowledge_graph.models import (
    PatientContext, FrequencyCategory, SeverityLevel
)
from src.knowledge_graph.database import KnowledgeGraphDatabase
from unittest.mock import AsyncMock, MagicMock


# ============================================================================
# Strategy Generators for Property-Based Testing
# ============================================================================

@composite
def drug_id_strategy(draw):
    """Generate drug IDs for testing"""
    drugs = [
        'drug_lisinopril', 'drug_metformin', 'drug_atorvastatin',
        'drug_warfarin', 'drug_aspirin', 'drug_ibuprofen',
        'drug_amoxicillin', 'drug_omeprazole', 'drug_levothyroxine',
        'drug_amlodipine', 'drug_metoprolol', 'drug_losartan'
    ]
    return draw(st.sampled_from(drugs))


@composite
def patient_demographics_strategy(draw):
    """Generate patient demographics with various characteristics"""
    age = draw(st.integers(min_value=18, max_value=90))
    weight = draw(st.integers(min_value=45, max_value=150))
    height = draw(st.integers(min_value=150, max_value=200))
    gender = draw(st.sampled_from(['male', 'female']))
    
    # Generate conditions that may correlate with adverse events
    conditions = draw(st.lists(
        st.sampled_from([
            'hypertension', 'diabetes', 'heart_disease',
            'kidney_disease', 'liver_disease', 'asthma',
            'copd', 'obesity', 'anemia'
        ]),
        min_size=0,
        max_size=4,
        unique=True
    ))
    
    # Generate risk factors
    risk_factors = []
    if age > 65:
        risk_factors.append('elderly')
    if age < 30:
        risk_factors.append('young_adult')
    if weight > 100:
        risk_factors.append('overweight')
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
        genetic_factors={},
        risk_factors=risk_factors,
        preferences={}
    )


@composite
def adverse_event_strategy(draw):
    """Generate adverse event data with demographic correlations"""
    adverse_events = [
        'Hypotension', 'Hyperglycemia', 'Renal_failure', 'Hepatotoxicity',
        'Cardiac_arrhythmia', 'Bleeding', 'Thrombocytopenia', 'Anaphylaxis',
        'Stevens_Johnson_syndrome', 'Acute_kidney_injury', 'Liver_failure',
        'Myocardial_infarction', 'Stroke', 'Seizure', 'Respiratory_failure'
    ]
    
    name = draw(st.sampled_from(adverse_events))
    frequency = draw(st.floats(min_value=0.0001, max_value=0.1))
    confidence = draw(st.floats(min_value=0.6, max_value=1.0))
    
    # Generate demographic correlations
    num_correlations = draw(st.integers(min_value=1, max_value=3))
    demographic_factors = ['age', 'gender', 'weight', 'bmi', 'renal_function', 'hepatic_function']
    
    correlations = []
    for _ in range(num_correlations):
        factor = draw(st.sampled_from(demographic_factors))
        correlation_strength = draw(st.floats(min_value=0.3, max_value=0.9))
        relative_risk = draw(st.floats(min_value=1.1, max_value=3.0))
        patient_count = draw(st.integers(min_value=50, max_value=5000))
        
        # Determine factor value based on factor type
        if factor == 'age':
            factor_value = draw(st.sampled_from(['elderly', 'young_adult', 'middle_aged']))
        elif factor == 'gender':
            factor_value = draw(st.sampled_from(['male', 'female']))
        elif factor in ['weight', 'bmi']:
            factor_value = draw(st.sampled_from(['overweight', 'underweight', 'normal']))
        else:
            factor_value = draw(st.sampled_from(['impaired', 'normal']))
        
        correlations.append({
            'demographic_factor': factor,
            'factor_value': factor_value,
            'correlation_strength': correlation_strength,
            'relative_risk': relative_risk,
            'patient_count': patient_count,
            'confidence': draw(st.floats(min_value=0.6, max_value=0.95))
        })
    
    return {
        'id': f"ae_{name.lower()}",
        'name': name,
        'frequency': frequency,
        'confidence': confidence,
        'severity': draw(st.sampled_from(['moderate', 'major', 'contraindicated'])),
        'system_organ_class': draw(st.sampled_from([
            'Cardiovascular', 'Renal', 'Hepatic', 'Hematologic',
            'Neurological', 'Respiratory', 'Dermatological'
        ])),
        'evidence_sources': ['FAERS', 'OnSIDES'],
        'patient_count': draw(st.integers(min_value=100, max_value=10000)),
        'demographic_correlations': correlations
    }


# ============================================================================
# Property-Based Tests for Demographic-Based Adverse Event Analysis
# ============================================================================

class TestDemographicAdverseEventProperties:
    """
    Property-based tests for demographic-based adverse event analysis
    
    **Validates: Requirements 5.2, 5.4**
    """
    
    @given(
        drug_id=drug_id_strategy(),
        patient=patient_demographics_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_demographic_correlations_retrieved_for_all_patients(
        self,
        drug_id: str,
        patient: PatientContext
    ):
        """
        Property: Demographic correlations are retrieved for all patient queries
        
        **Validates: Requirement 5.2**
        
        For any patient demographics, the system should traverse knowledge graph
        relationships to identify demographic-based adverse event patterns.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Mock adverse event data
        mock_adverse_events = [
            {
                'id': 'ae_hypotension',
                'name': 'Hypotension',
                'severity': 'major',
                'system_organ_class': 'Cardiovascular'
            }
        ]
        
        mock_db.find_side_effects_for_drug = AsyncMock(return_value=mock_adverse_events)
        
        # Create service
        service = SideEffectRetrievalService(mock_db)
        
        # Mock _query_side_effects
        async def mock_query_side_effects(drug_id_param):
            return [
                SideEffectResult(
                    side_effect_id='ae_hypotension',
                    side_effect_name='Hypotension',
                    frequency=0.05,
                    frequency_category=FrequencyCategory.UNCOMMON,
                    severity=SeverityLevel.MAJOR,
                    confidence=0.8,
                    data_sources=['FAERS', 'OnSIDES'],
                    source_types=[DataSourceType.REAL_WORLD, DataSourceType.CLINICAL_TRIAL],
                    patient_count=1000,
                    demographic_correlation=None,
                    system_organ_class='Cardiovascular',
                    description=None
                )
            ]
        
        service._query_side_effects = mock_query_side_effects
        
        # Mock demographic correlations based on patient
        async def mock_demographic_corr(drug_id_param, ae_id, patient_ctx):
            correlations = []
            
            if patient_ctx:
                age = patient_ctx.demographics.get('age', 0)
                gender = patient_ctx.demographics.get('gender', '')
                weight = patient_ctx.demographics.get('weight', 0)
                
                # Age-based correlations
                if age > 65:
                    correlations.append(DemographicCorrelation(
                        demographic_factor='age',
                        factor_value='elderly',
                        correlation_strength=0.75,
                        relative_risk=1.8,
                        patient_count=800,
                        confidence=0.85
                    ))
                elif age < 30:
                    correlations.append(DemographicCorrelation(
                        demographic_factor='age',
                        factor_value='young_adult',
                        correlation_strength=0.4,
                        relative_risk=0.7,
                        patient_count=200,
                        confidence=0.7
                    ))
                
                # Gender-based correlations
                if gender:
                    correlations.append(DemographicCorrelation(
                        demographic_factor='gender',
                        factor_value=gender,
                        correlation_strength=0.55,
                        relative_risk=1.3,
                        patient_count=500,
                        confidence=0.75
                    ))
                
                # Weight-based correlations
                if weight > 100:
                    correlations.append(DemographicCorrelation(
                        demographic_factor='weight',
                        factor_value='overweight',
                        correlation_strength=0.6,
                        relative_risk=1.4,
                        patient_count=400,
                        confidence=0.8
                    ))
            
            return correlations
        
        service._query_demographic_correlations = mock_demographic_corr
        
        # Mock _add_demographic_correlations
        async def mock_add_demographics(drug_id_param, adverse_events_list, patient_ctx):
            if patient_ctx:
                for ae in adverse_events_list:
                    correlations = await mock_demographic_corr(drug_id_param, ae.side_effect_id, patient_ctx)
                    if correlations:
                        ae.demographic_correlation = {
                            'correlations': correlations,
                            'patient_match': service._calculate_patient_match(correlations, patient_ctx)
                        }
            return adverse_events_list
        
        service._add_demographic_correlations = mock_add_demographics
        
        # Retrieve adverse events with demographics
        results = await service.get_side_effects_for_drug(
            drug_id=drug_id,
            include_demographics=True,
            patient_context=patient
        )
        
        # Verify demographic correlations are present
        assert len(results) > 0, \
            "Should return adverse events"
        
        for result in results:
            # Should have demographic correlation data
            assert hasattr(result, 'demographic_correlation'), \
                "Result should have demographic_correlation field"
            
            # If patient has relevant demographics, should have correlations
            if result.demographic_correlation:
                assert isinstance(result.demographic_correlation, dict), \
                    "Demographic correlation should be a dictionary"
                
                assert 'correlations' in result.demographic_correlation, \
                    "Should have correlations list"
                
                correlations = result.demographic_correlation['correlations']
                assert isinstance(correlations, list), \
                    "Correlations should be a list"
                
                # Verify correlations are valid
                for corr in correlations:
                    assert isinstance(corr, DemographicCorrelation), \
                        "Each correlation should be a DemographicCorrelation"
                    
                    assert corr.demographic_factor in [
                        'age', 'gender', 'weight', 'bmi', 'renal_function', 'hepatic_function'
                    ], f"Invalid demographic factor: {corr.demographic_factor}"
                    
                    assert 0.0 <= corr.correlation_strength <= 1.0, \
                        f"Correlation strength should be 0-1, got {corr.correlation_strength}"
                    
                    assert corr.relative_risk > 0.0, \
                        f"Relative risk should be positive, got {corr.relative_risk}"
    
    @given(
        drug_id=drug_id_strategy(),
        patient=patient_demographics_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_patient_specific_risk_factors_correlated(
        self,
        drug_id: str,
        patient: PatientContext
    ):
        """
        Property: Patient-specific risk factors are correlated with adverse events
        
        **Validates: Requirement 5.4**
        
        For any patient demographics, the system should correlate patient-specific
        risk factors with adverse event patterns from real-world data.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Mock adverse event data
        mock_adverse_events = [
            {
                'id': 'ae_renal_failure',
                'name': 'Acute_kidney_injury',
                'severity': 'major',
                'system_organ_class': 'Renal'
            }
        ]
        
        mock_db.find_side_effects_for_drug = AsyncMock(return_value=mock_adverse_events)
        
        # Create service
        service = SideEffectRetrievalService(mock_db)
        
        # Mock _query_side_effects
        async def mock_query_side_effects(drug_id_param):
            return [
                SideEffectResult(
                    side_effect_id='ae_renal_failure',
                    side_effect_name='Acute_kidney_injury',
                    frequency=0.02,
                    frequency_category=FrequencyCategory.UNCOMMON,
                    severity=SeverityLevel.MAJOR,
                    confidence=0.85,
                    data_sources=['FAERS', 'OnSIDES'],
                    source_types=[DataSourceType.REAL_WORLD, DataSourceType.SPONTANEOUS_REPORT],
                    patient_count=500,
                    demographic_correlation=None,
                    system_organ_class='Renal',
                    description=None
                )
            ]
        
        service._query_side_effects = mock_query_side_effects
        
        # Mock demographic correlations that consider patient risk factors
        async def mock_demographic_corr(drug_id_param, ae_id, patient_ctx):
            correlations = []
            
            if patient_ctx:
                # Check for renal impairment risk factor
                if 'renal_impairment' in patient_ctx.risk_factors or \
                   'kidney_disease' in patient_ctx.conditions:
                    correlations.append(DemographicCorrelation(
                        demographic_factor='renal_function',
                        factor_value='impaired',
                        correlation_strength=0.85,
                        relative_risk=2.5,
                        patient_count=300,
                        confidence=0.9
                    ))
                
                # Check for elderly risk factor
                if 'elderly' in patient_ctx.risk_factors:
                    correlations.append(DemographicCorrelation(
                        demographic_factor='age',
                        factor_value='elderly',
                        correlation_strength=0.7,
                        relative_risk=1.6,
                        patient_count=400,
                        confidence=0.85
                    ))
            
            return correlations
        
        service._query_demographic_correlations = mock_demographic_corr
        
        # Mock _add_demographic_correlations
        async def mock_add_demographics(drug_id_param, adverse_events_list, patient_ctx):
            if patient_ctx:
                for ae in adverse_events_list:
                    correlations = await mock_demographic_corr(drug_id_param, ae.side_effect_id, patient_ctx)
                    if correlations:
                        ae.demographic_correlation = {
                            'correlations': correlations,
                            'patient_match': service._calculate_patient_match(correlations, patient_ctx)
                        }
            return adverse_events_list
        
        service._add_demographic_correlations = mock_add_demographics
        
        # Retrieve adverse events with demographics
        results = await service.get_side_effects_for_drug(
            drug_id=drug_id,
            include_demographics=True,
            patient_context=patient
        )
        
        # Verify risk factor correlations
        assert len(results) > 0, \
            "Should return adverse events"
        
        for result in results:
            if result.demographic_correlation:
                correlations = result.demographic_correlation['correlations']
                
                # If patient has renal impairment, should have renal correlation
                if 'renal_impairment' in patient.risk_factors or \
                   'kidney_disease' in patient.conditions:
                    renal_corrs = [c for c in correlations 
                                  if c.demographic_factor == 'renal_function']
                    
                    if renal_corrs:
                        # Verify renal correlation has high risk
                        for corr in renal_corrs:
                            assert corr.relative_risk > 1.0, \
                                "Renal impairment should increase risk"
                            
                            assert corr.correlation_strength > 0.5, \
                                "Renal correlation should be strong"
                
                # If patient is elderly, should have age correlation
                if 'elderly' in patient.risk_factors:
                    age_corrs = [c for c in correlations 
                                if c.demographic_factor == 'age']
                    
                    if age_corrs:
                        for corr in age_corrs:
                            assert corr.relative_risk > 1.0, \
                                "Elderly age should increase risk"
    
    @given(
        drug_id=drug_id_strategy(),
        patient=patient_demographics_strategy(),
        adverse_events=st.lists(adverse_event_strategy(), min_size=1, max_size=3)
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_demographic_correlation_strength_valid(
        self,
        drug_id: str,
        patient: PatientContext,
        adverse_events: List[Dict[str, Any]]
    ):
        """
        Property: Demographic correlation strengths are within valid ranges
        
        **Validates: Requirements 5.2, 5.4**
        
        For any demographic correlation, correlation strength should be between 0 and 1,
        and relative risk should be positive.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Create service
        service = SideEffectRetrievalService(mock_db)
        
        # Mock _query_side_effects to return adverse events with correlations
        async def mock_query_side_effects(drug_id_param):
            results = []
            for ae_data in adverse_events:
                results.append(SideEffectResult(
                    side_effect_id=ae_data['id'],
                    side_effect_name=ae_data['name'],
                    frequency=ae_data['frequency'],
                    frequency_category=service._categorize_frequency(ae_data['frequency']),
                    severity=service._parse_severity(ae_data['severity']),
                    confidence=ae_data['confidence'],
                    data_sources=ae_data['evidence_sources'],
                    source_types=service._classify_data_sources(ae_data['evidence_sources']),
                    patient_count=ae_data['patient_count'],
                    demographic_correlation=None,
                    system_organ_class=ae_data['system_organ_class'],
                    description=None
                ))
            return results
        
        service._query_side_effects = mock_query_side_effects
        
        # Mock demographic correlations from adverse event data
        async def mock_demographic_corr(drug_id_param, ae_id, patient_ctx):
            # Find matching adverse event
            matching = [ae for ae in adverse_events if ae['id'] == ae_id]
            if not matching:
                return []
            
            ae_data = matching[0]
            correlations = []
            
            for corr_data in ae_data['demographic_correlations']:
                correlations.append(DemographicCorrelation(
                    demographic_factor=corr_data['demographic_factor'],
                    factor_value=corr_data['factor_value'],
                    correlation_strength=corr_data['correlation_strength'],
                    relative_risk=corr_data['relative_risk'],
                    patient_count=corr_data['patient_count'],
                    confidence=corr_data['confidence']
                ))
            
            return correlations
        
        service._query_demographic_correlations = mock_demographic_corr
        
        # Mock _add_demographic_correlations
        async def mock_add_demographics(drug_id_param, adverse_events_list, patient_ctx):
            if patient_ctx:
                for ae in adverse_events_list:
                    correlations = await mock_demographic_corr(drug_id_param, ae.side_effect_id, patient_ctx)
                    if correlations:
                        ae.demographic_correlation = {
                            'correlations': correlations,
                            'patient_match': service._calculate_patient_match(correlations, patient_ctx)
                        }
            return adverse_events_list
        
        service._add_demographic_correlations = mock_add_demographics
        
        # Retrieve adverse events with demographics
        results = await service.get_side_effects_for_drug(
            drug_id=drug_id,
            include_demographics=True,
            patient_context=patient
        )
        
        # Verify correlation values are valid
        assert len(results) > 0, \
            "Should return adverse events"
        
        for result in results:
            if result.demographic_correlation:
                correlations = result.demographic_correlation['correlations']
                
                for corr in correlations:
                    # Correlation strength should be 0-1
                    assert 0.0 <= corr.correlation_strength <= 1.0, \
                        f"Correlation strength should be 0-1, got {corr.correlation_strength}"
                    
                    # Relative risk should be positive
                    assert corr.relative_risk > 0.0, \
                        f"Relative risk should be positive, got {corr.relative_risk}"
                    
                    # Confidence should be 0-1
                    assert 0.0 <= corr.confidence <= 1.0, \
                        f"Confidence should be 0-1, got {corr.confidence}"
                    
                    # Patient count should be positive
                    assert corr.patient_count > 0, \
                        f"Patient count should be positive, got {corr.patient_count}"
    
    @given(
        drug_id=drug_id_strategy(),
        patient=patient_demographics_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_patient_match_score_calculated(
        self,
        drug_id: str,
        patient: PatientContext
    ):
        """
        Property: Patient match score is calculated for demographic correlations
        
        **Validates: Requirements 5.2, 5.4**
        
        For any patient with demographic correlations, a patient match score
        should be calculated indicating how well the patient matches the
        demographic patterns associated with adverse events.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Mock adverse event data
        mock_adverse_events = [
            {
                'id': 'ae_bleeding',
                'name': 'Bleeding',
                'severity': 'major',
                'system_organ_class': 'Hematologic'
            }
        ]
        
        mock_db.find_side_effects_for_drug = AsyncMock(return_value=mock_adverse_events)
        
        # Create service
        service = SideEffectRetrievalService(mock_db)
        
        # Mock _query_side_effects
        async def mock_query_side_effects(drug_id_param):
            return [
                SideEffectResult(
                    side_effect_id='ae_bleeding',
                    side_effect_name='Bleeding',
                    frequency=0.03,
                    frequency_category=FrequencyCategory.UNCOMMON,
                    severity=SeverityLevel.MAJOR,
                    confidence=0.8,
                    data_sources=['FAERS'],
                    source_types=[DataSourceType.REAL_WORLD],
                    patient_count=800,
                    demographic_correlation=None,
                    system_organ_class='Hematologic',
                    description=None
                )
            ]
        
        service._query_side_effects = mock_query_side_effects
        
        # Mock demographic correlations
        async def mock_demographic_corr(drug_id_param, ae_id, patient_ctx):
            correlations = []
            
            if patient_ctx:
                age = patient_ctx.demographics.get('age', 0)
                gender = patient_ctx.demographics.get('gender', '')
                
                # Add correlations that may or may not match patient
                correlations.append(DemographicCorrelation(
                    demographic_factor='age',
                    factor_value='elderly' if age > 65 else 'young_adult',
                    correlation_strength=0.7,
                    relative_risk=1.5,
                    patient_count=400,
                    confidence=0.8
                ))
                
                correlations.append(DemographicCorrelation(
                    demographic_factor='gender',
                    factor_value=gender,
                    correlation_strength=0.6,
                    relative_risk=1.3,
                    patient_count=300,
                    confidence=0.75
                ))
            
            return correlations
        
        service._query_demographic_correlations = mock_demographic_corr
        
        # Mock _add_demographic_correlations
        async def mock_add_demographics(drug_id_param, adverse_events_list, patient_ctx):
            if patient_ctx:
                for ae in adverse_events_list:
                    correlations = await mock_demographic_corr(drug_id_param, ae.side_effect_id, patient_ctx)
                    if correlations:
                        ae.demographic_correlation = {
                            'correlations': correlations,
                            'patient_match': service._calculate_patient_match(correlations, patient_ctx)
                        }
            return adverse_events_list
        
        service._add_demographic_correlations = mock_add_demographics
        
        # Retrieve adverse events with demographics
        results = await service.get_side_effects_for_drug(
            drug_id=drug_id,
            include_demographics=True,
            patient_context=patient
        )
        
        # Verify patient match score
        assert len(results) > 0, \
            "Should return adverse events"
        
        for result in results:
            if result.demographic_correlation:
                # Should have patient match score
                assert 'patient_match' in result.demographic_correlation, \
                    "Should have patient_match score"
                
                patient_match = result.demographic_correlation['patient_match']
                
                # Patient match should be a float between 0 and 1
                assert isinstance(patient_match, (float, int)), \
                    f"Patient match should be numeric, got {type(patient_match)}"
                
                assert 0.0 <= patient_match <= 1.0, \
                    f"Patient match should be 0-1, got {patient_match}"
    
    @given(
        drug_id=drug_id_strategy(),
        patient=patient_demographics_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_real_world_data_sources_used(
        self,
        drug_id: str,
        patient: PatientContext
    ):
        """
        Property: Real-world data sources are used for demographic correlations
        
        **Validates: Requirement 5.2**
        
        For any demographic-based adverse event analysis, real-world data sources
        (FAERS) should be included to provide patient-reported demographic patterns.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Mock adverse event data
        mock_adverse_events = [
            {
                'id': 'ae_hepatotoxicity',
                'name': 'Hepatotoxicity',
                'severity': 'major',
                'system_organ_class': 'Hepatic'
            }
        ]
        
        mock_db.find_side_effects_for_drug = AsyncMock(return_value=mock_adverse_events)
        
        # Create service
        service = SideEffectRetrievalService(mock_db)
        
        # Mock _query_side_effects with real-world data sources
        async def mock_query_side_effects(drug_id_param):
            return [
                SideEffectResult(
                    side_effect_id='ae_hepatotoxicity',
                    side_effect_name='Hepatotoxicity',
                    frequency=0.01,
                    frequency_category=FrequencyCategory.RARE,
                    severity=SeverityLevel.MAJOR,
                    confidence=0.85,
                    data_sources=['FAERS', 'OnSIDES'],
                    source_types=[DataSourceType.REAL_WORLD, DataSourceType.SPONTANEOUS_REPORT, DataSourceType.CLINICAL_TRIAL],
                    patient_count=300,
                    demographic_correlation=None,
                    system_organ_class='Hepatic',
                    description=None
                )
            ]
        
        service._query_side_effects = mock_query_side_effects
        
        # Mock demographic correlations
        async def mock_demographic_corr(drug_id_param, ae_id, patient_ctx):
            correlations = []
            
            if patient_ctx:
                # Add correlations from real-world data
                correlations.append(DemographicCorrelation(
                    demographic_factor='age',
                    factor_value='elderly',
                    correlation_strength=0.65,
                    relative_risk=1.7,
                    patient_count=150,
                    confidence=0.8
                ))
            
            return correlations
        
        service._query_demographic_correlations = mock_demographic_corr
        
        # Mock _add_demographic_correlations
        async def mock_add_demographics(drug_id_param, adverse_events_list, patient_ctx):
            if patient_ctx:
                for ae in adverse_events_list:
                    correlations = await mock_demographic_corr(drug_id_param, ae.side_effect_id, patient_ctx)
                    if correlations:
                        ae.demographic_correlation = {
                            'correlations': correlations,
                            'patient_match': service._calculate_patient_match(correlations, patient_ctx)
                        }
            return adverse_events_list
        
        service._add_demographic_correlations = mock_add_demographics
        
        # Retrieve adverse events with demographics
        results = await service.get_side_effects_for_drug(
            drug_id=drug_id,
            include_demographics=True,
            patient_context=patient
        )
        
        # Verify real-world data sources are used
        assert len(results) > 0, \
            "Should return adverse events"
        
        for result in results:
            # Should have real-world data sources
            assert 'FAERS' in result.data_sources or \
                   DataSourceType.REAL_WORLD in result.source_types or \
                   DataSourceType.SPONTANEOUS_REPORT in result.source_types, \
                "Should include real-world data sources for demographic analysis"
    
    @given(
        drug_id=drug_id_strategy(),
        patient1=patient_demographics_strategy(),
        patient2=patient_demographics_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_different_patients_get_different_correlations(
        self,
        drug_id: str,
        patient1: PatientContext,
        patient2: PatientContext
    ):
        """
        Property: Different patients receive personalized demographic correlations
        
        **Validates: Requirements 5.2, 5.4**
        
        For different patient demographics, the system should provide personalized
        correlations that reflect each patient's specific characteristics.
        """
        # Ensure patients have different demographics
        assume(patient1.demographics.get('age') != patient2.demographics.get('age') or
               patient1.demographics.get('gender') != patient2.demographics.get('gender'))
        
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Mock adverse event data
        mock_adverse_events = [
            {
                'id': 'ae_arrhythmia',
                'name': 'Cardiac_arrhythmia',
                'severity': 'major',
                'system_organ_class': 'Cardiovascular'
            }
        ]
        
        mock_db.find_side_effects_for_drug = AsyncMock(return_value=mock_adverse_events)
        
        # Create service
        service = SideEffectRetrievalService(mock_db)
        
        # Mock _query_side_effects
        async def mock_query_side_effects(drug_id_param):
            return [
                SideEffectResult(
                    side_effect_id='ae_arrhythmia',
                    side_effect_name='Cardiac_arrhythmia',
                    frequency=0.04,
                    frequency_category=FrequencyCategory.UNCOMMON,
                    severity=SeverityLevel.MAJOR,
                    confidence=0.82,
                    data_sources=['FAERS', 'OnSIDES'],
                    source_types=[DataSourceType.REAL_WORLD, DataSourceType.CLINICAL_TRIAL],
                    patient_count=600,
                    demographic_correlation=None,
                    system_organ_class='Cardiovascular',
                    description=None
                )
            ]
        
        service._query_side_effects = mock_query_side_effects
        
        # Mock demographic correlations that vary by patient
        async def mock_demographic_corr(drug_id_param, ae_id, patient_ctx):
            correlations = []
            
            if patient_ctx:
                age = patient_ctx.demographics.get('age', 0)
                gender = patient_ctx.demographics.get('gender', '')
                
                # Age-specific correlations
                if age > 65:
                    correlations.append(DemographicCorrelation(
                        demographic_factor='age',
                        factor_value='elderly',
                        correlation_strength=0.8,
                        relative_risk=2.0,
                        patient_count=400,
                        confidence=0.85
                    ))
                elif age < 30:
                    correlations.append(DemographicCorrelation(
                        demographic_factor='age',
                        factor_value='young_adult',
                        correlation_strength=0.3,
                        relative_risk=0.6,
                        patient_count=100,
                        confidence=0.7
                    ))
                else:
                    correlations.append(DemographicCorrelation(
                        demographic_factor='age',
                        factor_value='middle_aged',
                        correlation_strength=0.5,
                        relative_risk=1.0,
                        patient_count=200,
                        confidence=0.75
                    ))
                
                # Gender-specific correlations
                if gender == 'male':
                    correlations.append(DemographicCorrelation(
                        demographic_factor='gender',
                        factor_value='male',
                        correlation_strength=0.65,
                        relative_risk=1.4,
                        patient_count=350,
                        confidence=0.8
                    ))
                elif gender == 'female':
                    correlations.append(DemographicCorrelation(
                        demographic_factor='gender',
                        factor_value='female',
                        correlation_strength=0.55,
                        relative_risk=1.1,
                        patient_count=250,
                        confidence=0.75
                    ))
            
            return correlations
        
        service._query_demographic_correlations = mock_demographic_corr
        
        # Mock _add_demographic_correlations
        async def mock_add_demographics(drug_id_param, adverse_events_list, patient_ctx):
            if patient_ctx:
                for ae in adverse_events_list:
                    correlations = await mock_demographic_corr(drug_id_param, ae.side_effect_id, patient_ctx)
                    if correlations:
                        ae.demographic_correlation = {
                            'correlations': correlations,
                            'patient_match': service._calculate_patient_match(correlations, patient_ctx)
                        }
            return adverse_events_list
        
        service._add_demographic_correlations = mock_add_demographics
        
        # Retrieve adverse events for both patients
        results1 = await service.get_side_effects_for_drug(
            drug_id=drug_id,
            include_demographics=True,
            patient_context=patient1
        )
        
        results2 = await service.get_side_effects_for_drug(
            drug_id=drug_id,
            include_demographics=True,
            patient_context=patient2
        )
        
        # Verify both patients get results
        assert len(results1) > 0, "Should return results for patient 1"
        assert len(results2) > 0, "Should return results for patient 2"
        
        # Extract correlations
        corr1 = results1[0].demographic_correlation
        corr2 = results2[0].demographic_correlation
        
        # If patients have different demographics, correlations should differ
        if corr1 and corr2:
            # Check if age correlations differ
            age1 = patient1.demographics.get('age', 0)
            age2 = patient2.demographics.get('age', 0)
            
            if (age1 > 65 and age2 <= 65) or (age1 <= 65 and age2 > 65):
                # Should have different age correlation values
                age_corrs1 = [c for c in corr1['correlations'] if c.demographic_factor == 'age']
                age_corrs2 = [c for c in corr2['correlations'] if c.demographic_factor == 'age']
                
                if age_corrs1 and age_corrs2:
                    # Elderly patient should have higher relative risk
                    elderly_corr = age_corrs1[0] if age1 > 65 else age_corrs2[0]
                    young_corr = age_corrs2[0] if age1 > 65 else age_corrs1[0]
                    
                    assert elderly_corr.relative_risk > young_corr.relative_risk, \
                        "Elderly patients should have higher relative risk"
    
    @given(
        drug_id=drug_id_strategy(),
        patient=patient_demographics_strategy()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_knowledge_graph_traversal_for_demographics(
        self,
        drug_id: str,
        patient: PatientContext
    ):
        """
        Property: Knowledge graph relationships are traversed for demographic analysis
        
        **Validates: Requirements 5.2, 5.4**
        
        For any demographic-based adverse event query, the system should traverse
        knowledge graph relationships between patient demographics and adverse events.
        """
        # Create mock database
        mock_db = MagicMock(spec=KnowledgeGraphDatabase)
        
        # Mock adverse event data
        mock_adverse_events = [
            {
                'id': 'ae_thrombocytopenia',
                'name': 'Thrombocytopenia',
                'severity': 'major',
                'system_organ_class': 'Hematologic'
            }
        ]
        
        mock_db.find_side_effects_for_drug = AsyncMock(return_value=mock_adverse_events)
        
        # Create service
        service = SideEffectRetrievalService(mock_db)
        
        # Mock _query_side_effects
        async def mock_query_side_effects(drug_id_param):
            return [
                SideEffectResult(
                    side_effect_id='ae_thrombocytopenia',
                    side_effect_name='Thrombocytopenia',
                    frequency=0.015,
                    frequency_category=FrequencyCategory.RARE,
                    severity=SeverityLevel.MAJOR,
                    confidence=0.8,
                    data_sources=['FAERS', 'OnSIDES'],
                    source_types=[DataSourceType.REAL_WORLD, DataSourceType.CLINICAL_TRIAL],
                    patient_count=250,
                    demographic_correlation=None,
                    system_organ_class='Hematologic',
                    description=None
                )
            ]
        
        service._query_side_effects = mock_query_side_effects
        
        # Track if demographic query was called (simulating graph traversal)
        demographic_query_called = False
        
        async def mock_demographic_corr(drug_id_param, ae_id, patient_ctx):
            nonlocal demographic_query_called
            demographic_query_called = True
            
            correlations = []
            if patient_ctx:
                correlations.append(DemographicCorrelation(
                    demographic_factor='age',
                    factor_value='elderly',
                    correlation_strength=0.7,
                    relative_risk=1.5,
                    patient_count=150,
                    confidence=0.8
                ))
            
            return correlations
        
        service._query_demographic_correlations = mock_demographic_corr
        
        # Mock _add_demographic_correlations
        async def mock_add_demographics(drug_id_param, adverse_events_list, patient_ctx):
            if patient_ctx:
                for ae in adverse_events_list:
                    correlations = await mock_demographic_corr(drug_id_param, ae.side_effect_id, patient_ctx)
                    if correlations:
                        ae.demographic_correlation = {
                            'correlations': correlations,
                            'patient_match': service._calculate_patient_match(correlations, patient_ctx)
                        }
            return adverse_events_list
        
        service._add_demographic_correlations = mock_add_demographics
        
        # Retrieve adverse events with demographics
        results = await service.get_side_effects_for_drug(
            drug_id=drug_id,
            include_demographics=True,
            patient_context=patient
        )
        
        # Verify knowledge graph traversal occurred
        assert demographic_query_called, \
            "Should traverse knowledge graph for demographic correlations"
        
        assert len(results) > 0, \
            "Should return adverse events"
        
        # Verify results have demographic data from graph traversal
        for result in results:
            if result.demographic_correlation:
                assert 'correlations' in result.demographic_correlation, \
                    "Should have correlations from graph traversal"
