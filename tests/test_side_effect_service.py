"""
Unit tests for side effect retrieval service
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.knowledge_graph.side_effect_service import (
    SideEffectRetrievalService,
    SideEffectResult,
    DemographicCorrelation,
    DataSourceType,
    create_side_effect_service
)
from src.knowledge_graph.models import (
    DrugEntity, SideEffectEntity, PatientContext,
    FrequencyCategory, SeverityLevel
)
from src.knowledge_graph.database import KnowledgeGraphDatabase


@pytest.fixture
def mock_database():
    """Create mock database"""
    db = MagicMock(spec=KnowledgeGraphDatabase)
    db.connection = MagicMock()
    db.connection.g = MagicMock()
    return db


@pytest.fixture
def side_effect_service(mock_database):
    """Create side effect service with mock database"""
    return SideEffectRetrievalService(mock_database)


@pytest.fixture
def sample_patient_context():
    """Create sample patient context"""
    return PatientContext(
        id="patient_001",
        demographics={
            'age': 70,
            'gender': 'male',
            'weight': 80,
            'height': 175
        },
        conditions=['hypertension', 'diabetes'],
        medications=[
            {'name': 'Lisinopril', 'dosage': '10mg', 'frequency': 'daily'}
        ],
        allergies=[],
        genetic_factors={},
        risk_factors=['smoking', 'obesity']
    )


@pytest.mark.asyncio
async def test_get_side_effects_for_drug_basic(side_effect_service, mock_database):
    """Test basic side effect retrieval"""
    # Mock database response
    mock_database.find_side_effects_for_drug = AsyncMock(return_value=[
        {
            'id': 'se_001',
            'name': 'Headache',
            'severity': 'minor',
            'system_organ_class': 'Nervous system'
        },
        {
            'id': 'se_002',
            'name': 'Nausea',
            'severity': 'moderate',
            'system_organ_class': 'Gastrointestinal'
        }
    ])
    
    # Mock edge properties
    async def mock_get_edge_props(drug_id, se_id):
        return {
            'frequency': 0.05,
            'confidence': 0.8,
            'evidence_sources': ['SIDER', 'OnSIDES'],
            'patient_count': 1000
        }
    
    side_effect_service._get_causes_edge_properties = mock_get_edge_props
    
    # Execute
    results = await side_effect_service.get_side_effects_for_drug(
        drug_id='drug_001',
        include_frequency=False,
        include_demographics=False
    )
    
    # Verify
    assert len(results) == 2
    assert results[0].side_effect_name in ['Headache', 'Nausea']
    assert all(r.confidence >= 0.5 for r in results)
    assert all(len(r.data_sources) > 0 for r in results)


@pytest.mark.asyncio
async def test_get_side_effects_with_frequency(side_effect_service, mock_database):
    """Test side effect retrieval with frequency data"""
    # Mock database response
    mock_database.find_side_effects_for_drug = AsyncMock(return_value=[
        {
            'id': 'se_001',
            'name': 'Dizziness',
            'severity': 'moderate'
        }
    ])
    
    async def mock_get_edge_props(drug_id, se_id):
        return {
            'frequency': 0.15,  # Very common
            'confidence': 0.9,
            'evidence_sources': ['SIDER'],
            'patient_count': 2000
        }
    
    side_effect_service._get_causes_edge_properties = mock_get_edge_props
    side_effect_service._query_sider_frequencies = AsyncMock(return_value={})
    
    # Execute
    results = await side_effect_service.get_side_effects_for_drug(
        drug_id='drug_001',
        include_frequency=True
    )
    
    # Verify
    assert len(results) == 1
    assert results[0].frequency == 0.15
    assert results[0].frequency_category == FrequencyCategory.VERY_COMMON


@pytest.mark.asyncio
async def test_get_side_effects_with_demographics(
    side_effect_service, mock_database, sample_patient_context
):
    """Test side effect retrieval with demographic correlations"""
    # Mock database response
    mock_database.find_side_effects_for_drug = AsyncMock(return_value=[
        {
            'id': 'se_001',
            'name': 'Hypotension',
            'severity': 'major'
        }
    ])
    
    async def mock_get_edge_props(drug_id, se_id):
        return {
            'frequency': 0.08,
            'confidence': 0.85,
            'evidence_sources': ['FAERS', 'OnSIDES'],
            'patient_count': 1500
        }
    
    async def mock_demographic_corr(drug_id, se_id, patient_ctx):
        return [
            DemographicCorrelation(
                demographic_factor='age',
                factor_value='elderly',
                correlation_strength=0.7,
                relative_risk=1.5,
                patient_count=500,
                confidence=0.8
            )
        ]
    
    side_effect_service._get_causes_edge_properties = mock_get_edge_props
    side_effect_service._query_demographic_correlations = mock_demographic_corr
    
    # Execute
    results = await side_effect_service.get_side_effects_for_drug(
        drug_id='drug_001',
        include_demographics=True,
        patient_context=sample_patient_context
    )
    
    # Verify
    assert len(results) == 1
    assert results[0].demographic_correlation is not None
    assert 'correlations' in results[0].demographic_correlation
    assert len(results[0].demographic_correlation['correlations']) > 0


@pytest.mark.asyncio
async def test_confidence_threshold_filtering(side_effect_service, mock_database):
    """Test filtering by confidence threshold"""
    # Mock database response with varying confidence
    mock_database.find_side_effects_for_drug = AsyncMock(return_value=[
        {'id': 'se_001', 'name': 'Effect1'},
        {'id': 'se_002', 'name': 'Effect2'},
        {'id': 'se_003', 'name': 'Effect3'}
    ])
    
    async def mock_get_edge_props(drug_id, se_id):
        confidences = {
            'se_001': 0.9,
            'se_002': 0.6,
            'se_003': 0.3
        }
        return {
            'frequency': 0.05,
            'confidence': confidences.get(se_id, 0.5),
            'evidence_sources': ['SIDER'],
            'patient_count': 100
        }
    
    side_effect_service._get_causes_edge_properties = mock_get_edge_props
    
    # Execute with high confidence threshold
    results = await side_effect_service.get_side_effects_for_drug(
        drug_id='drug_001',
        min_confidence=0.7
    )
    
    # Verify - only high confidence results
    assert len(results) == 1
    assert results[0].confidence >= 0.7


def test_categorize_frequency(side_effect_service):
    """Test frequency categorization"""
    assert side_effect_service._categorize_frequency(0.15) == FrequencyCategory.VERY_COMMON
    assert side_effect_service._categorize_frequency(0.05) == FrequencyCategory.COMMON
    assert side_effect_service._categorize_frequency(0.005) == FrequencyCategory.UNCOMMON
    assert side_effect_service._categorize_frequency(0.0005) == FrequencyCategory.RARE
    assert side_effect_service._categorize_frequency(0.00005) == FrequencyCategory.VERY_RARE
    assert side_effect_service._categorize_frequency(0.0) == FrequencyCategory.UNKNOWN


def test_classify_data_sources(side_effect_service):
    """Test data source classification"""
    sources = ['SIDER', 'FAERS', 'OnSIDES']
    types = side_effect_service._classify_data_sources(sources)
    
    assert DataSourceType.CLINICAL_TRIAL in types
    assert DataSourceType.REAL_WORLD in types
    assert DataSourceType.SPONTANEOUS_REPORT in types


def test_parse_severity(side_effect_service):
    """Test severity parsing"""
    assert side_effect_service._parse_severity('minor') == SeverityLevel.MINOR
    assert side_effect_service._parse_severity('moderate') == SeverityLevel.MODERATE
    assert side_effect_service._parse_severity('major') == SeverityLevel.MAJOR
    assert side_effect_service._parse_severity('contraindicated') == SeverityLevel.CONTRAINDICATED
    assert side_effect_service._parse_severity(None) is None


def test_sort_by_relevance(side_effect_service, sample_patient_context):
    """Test sorting side effects by relevance"""
    side_effects = [
        SideEffectResult(
            side_effect_id='se_001',
            side_effect_name='Minor Effect',
            frequency=0.01,
            frequency_category=FrequencyCategory.COMMON,
            severity=SeverityLevel.MINOR,
            confidence=0.8,
            data_sources=['SIDER'],
            source_types=[DataSourceType.CLINICAL_TRIAL],
            patient_count=100,
            demographic_correlation=None,
            system_organ_class='System1',
            description='Minor side effect'
        ),
        SideEffectResult(
            side_effect_id='se_002',
            side_effect_name='Major Effect',
            frequency=0.05,
            frequency_category=FrequencyCategory.COMMON,
            severity=SeverityLevel.MAJOR,
            confidence=0.9,
            data_sources=['SIDER', 'FAERS'],
            source_types=[DataSourceType.CLINICAL_TRIAL, DataSourceType.REAL_WORLD],
            patient_count=500,
            demographic_correlation=None,
            system_organ_class='System2',
            description='Major side effect'
        )
    ]
    
    sorted_effects = side_effect_service._sort_by_relevance(
        side_effects, sample_patient_context
    )
    
    # Major effect should be first
    assert sorted_effects[0].severity == SeverityLevel.MAJOR
    assert sorted_effects[1].severity == SeverityLevel.MINOR


@pytest.mark.asyncio
async def test_get_real_world_evidence(side_effect_service):
    """Test real-world evidence retrieval"""
    side_effect_service._query_faers_data = AsyncMock(return_value=[
        {
            'drug_id': 'drug_001',
            'side_effect_id': 'se_001',
            'patient_count': 1000,
            'frequency': 0.08
        }
    ])
    
    evidence = await side_effect_service.get_real_world_evidence(
        drug_id='drug_001',
        min_patient_count=10
    )
    
    assert len(evidence) == 1
    assert evidence[0]['patient_count'] >= 10


@pytest.mark.asyncio
async def test_compare_clinical_vs_realworld(side_effect_service):
    """Test comparison of clinical vs real-world data"""
    side_effect_service._get_clinical_trial_data = AsyncMock(return_value={
        'frequency': 0.05,
        'patient_count': 1000,
        'confidence': 0.9,
        'sources': ['SIDER']
    })
    
    side_effect_service._get_realworld_data = AsyncMock(return_value={
        'frequency': 0.08,
        'patient_count': 5000,
        'confidence': 0.7,
        'sources': ['FAERS']
    })
    
    comparison = await side_effect_service.compare_clinical_vs_realworld(
        drug_id='drug_001',
        side_effect_id='se_001'
    )
    
    assert 'clinical' in comparison
    assert 'real_world' in comparison
    assert 'frequency_ratio' in comparison
    assert comparison['frequency_ratio'] > 1.0  # Real-world higher


def test_calculate_frequency_ratio(side_effect_service):
    """Test frequency ratio calculation"""
    clinical = {'frequency': 0.05}
    realworld = {'frequency': 0.10}
    
    ratio = side_effect_service._calculate_frequency_ratio(clinical, realworld)
    assert ratio == 2.0


def test_calculate_reporting_difference(side_effect_service):
    """Test reporting difference calculation"""
    clinical = {'frequency': 0.05}
    
    # Significantly higher in real-world
    realworld_high = {'frequency': 0.10}
    diff = side_effect_service._calculate_reporting_difference(clinical, realworld_high)
    assert diff == "significantly_higher_in_realworld"
    
    # Similar
    realworld_similar = {'frequency': 0.05}
    diff = side_effect_service._calculate_reporting_difference(clinical, realworld_similar)
    assert diff == "similar"
    
    # Lower in real-world (ratio = 0.02/0.05 = 0.4, which is < 0.5)
    realworld_low = {'frequency': 0.02}
    diff = side_effect_service._calculate_reporting_difference(clinical, realworld_low)
    assert diff == "significantly_lower_in_realworld"


def test_calculate_patient_match(side_effect_service, sample_patient_context):
    """Test patient demographic match calculation"""
    correlations = [
        DemographicCorrelation(
            demographic_factor='age',
            factor_value=70,
            correlation_strength=0.8,
            relative_risk=1.5,
            patient_count=500,
            confidence=0.9
        ),
        DemographicCorrelation(
            demographic_factor='gender',
            factor_value='male',
            correlation_strength=0.6,
            relative_risk=1.2,
            patient_count=300,
            confidence=0.8
        )
    ]
    
    match_score = side_effect_service._calculate_patient_match(
        correlations, sample_patient_context
    )
    
    assert 0.0 <= match_score <= 1.0
    assert match_score > 0.0  # Should have some match


@pytest.mark.asyncio
async def test_create_side_effect_service():
    """Test factory function"""
    mock_db = MagicMock(spec=KnowledgeGraphDatabase)
    service = await create_side_effect_service(mock_db)
    
    assert isinstance(service, SideEffectRetrievalService)
    assert service.database == mock_db


@pytest.mark.asyncio
async def test_error_handling_in_query(side_effect_service, mock_database):
    """Test error handling in side effect queries"""
    # Mock database to raise exception
    async def raise_error(*args, **kwargs):
        raise Exception("Database error")
    
    mock_database.find_side_effects_for_drug = raise_error
    
    # Should handle error gracefully by returning empty list
    results = await side_effect_service.get_side_effects_for_drug(drug_id='drug_001')
    assert len(results) == 0


@pytest.mark.asyncio
async def test_empty_results(side_effect_service, mock_database):
    """Test handling of empty results"""
    mock_database.find_side_effects_for_drug = AsyncMock(return_value=[])
    
    results = await side_effect_service.get_side_effects_for_drug(drug_id='drug_001')
    
    assert len(results) == 0
