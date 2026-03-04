"""
Unit tests for graph reasoning engine
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.knowledge_graph.reasoning_engine import (
    GraphReasoningEngine,
    TraversalStrategy,
    InferenceMethod,
    GraphPath,
    RiskAssessment,
    TemporalPattern,
    create_reasoning_engine
)
from src.knowledge_graph.models import PatientContext, SeverityLevel
from src.knowledge_graph.database import KnowledgeGraphDatabase


@pytest.fixture
def mock_database():
    """Create mock database"""
    db = Mock(spec=KnowledgeGraphDatabase)
    db.connection = Mock()
    db.connection.g = Mock()
    return db


@pytest.fixture
def reasoning_engine(mock_database):
    """Create reasoning engine with mock database"""
    return GraphReasoningEngine(mock_database)


@pytest.mark.asyncio
async def test_create_reasoning_engine(mock_database):
    """Test reasoning engine creation"""
    engine = await create_reasoning_engine(mock_database)
    assert engine is not None
    assert isinstance(engine, GraphReasoningEngine)
    assert engine.database == mock_database


@pytest.mark.asyncio
async def test_multi_hop_traversal_breadth_first(reasoning_engine):
    """Test breadth-first multi-hop traversal"""
    # Mock the traversal methods
    expected_paths = [
        GraphPath(
            nodes=['drug1', 'interaction1', 'drug2'],
            edges=['edge1', 'edge2'],
            edge_types=['INTERACTS_WITH', 'CAUSES'],
            confidence=0.8,
            evidence_sources=['DrugBank', 'FAERS'],
            path_length=3
        )
    ]
    
    reasoning_engine._breadth_first_traversal = AsyncMock(return_value=expected_paths)
    
    paths = await reasoning_engine.multi_hop_traversal(
        start_node_id='drug1',
        target_node_type='SideEffect',
        max_hops=3,
        strategy=TraversalStrategy.BREADTH_FIRST
    )
    
    assert len(paths) == 1
    assert paths[0].nodes == ['drug1', 'interaction1', 'drug2']
    assert paths[0].confidence == 0.8
    assert paths[0].path_length == 3


@pytest.mark.asyncio
async def test_multi_hop_traversal_depth_first(reasoning_engine):
    """Test depth-first multi-hop traversal"""
    expected_paths = [
        GraphPath(
            nodes=['drug1', 'side_effect1'],
            edges=['edge1'],
            edge_types=['CAUSES'],
            confidence=0.9,
            evidence_sources=['OnSIDES'],
            path_length=2
        )
    ]
    
    reasoning_engine._depth_first_traversal = AsyncMock(return_value=expected_paths)
    
    paths = await reasoning_engine.multi_hop_traversal(
        start_node_id='drug1',
        target_node_type='SideEffect',
        max_hops=2,
        strategy=TraversalStrategy.DEPTH_FIRST
    )
    
    assert len(paths) == 1
    assert paths[0].path_length == 2


@pytest.mark.asyncio
async def test_calculate_risk_without_patient_context(reasoning_engine):
    """Test risk calculation without patient context"""
    # Mock the helper methods
    mock_paths = [
        GraphPath(
            nodes=['drug1', 'side_effect1'],
            edges=['edge1'],
            edge_types=['CAUSES'],
            confidence=0.7,
            evidence_sources=['SIDER'],
            path_length=2
        )
    ]
    
    reasoning_engine.multi_hop_traversal = AsyncMock(return_value=mock_paths)
    reasoning_engine._calculate_base_risk = AsyncMock(return_value=0.4)
    reasoning_engine._extract_risk_factors = AsyncMock(return_value=[
        {
            'type': 'side_effect',
            'name': 'Nausea',
            'severity': 'moderate',
            'confidence': 0.7,
            'sources': ['SIDER']
        }
    ])
    
    risk = await reasoning_engine.calculate_risk(
        drug_id='drug1',
        patient_context=None
    )
    
    assert isinstance(risk, RiskAssessment)
    assert 0.0 <= risk.risk_score <= 1.0
    assert risk.risk_level in ['low', 'moderate', 'high', 'critical']
    assert len(risk.recommendations) > 0


@pytest.mark.asyncio
async def test_calculate_risk_with_patient_context(reasoning_engine):
    """Test risk calculation with patient context"""
    patient = PatientContext(
        id='patient1',
        demographics={'age': 70, 'gender': 'male'},
        conditions=['diabetes', 'hypertension'],
        medications=[
            {'name': 'metformin', 'dosage': '500mg'},
            {'name': 'lisinopril', 'dosage': '10mg'}
        ],
        allergies=[],
        genetic_factors={},
        risk_factors=['smoking']
    )
    
    mock_paths = [
        GraphPath(
            nodes=['drug1', 'side_effect1'],
            edges=['edge1'],
            edge_types=['CAUSES'],
            confidence=0.6,
            evidence_sources=['FAERS'],
            path_length=2
        )
    ]
    
    reasoning_engine.multi_hop_traversal = AsyncMock(return_value=mock_paths)
    reasoning_engine._calculate_base_risk = AsyncMock(return_value=0.3)
    reasoning_engine._apply_patient_factors = AsyncMock(return_value=0.45)
    reasoning_engine._extract_risk_factors = AsyncMock(return_value=[])
    
    risk = await reasoning_engine.calculate_risk(
        drug_id='drug1',
        patient_context=patient
    )
    
    assert isinstance(risk, RiskAssessment)
    # Risk should be higher with patient factors
    assert risk.risk_score > 0.0





@pytest.mark.asyncio
async def test_determine_risk_level(reasoning_engine):
    """Test risk level determination"""
    assert reasoning_engine._determine_risk_level(0.1) == "low"
    assert reasoning_engine._determine_risk_level(0.3) == "moderate"
    assert reasoning_engine._determine_risk_level(0.6) == "high"
    assert reasoning_engine._determine_risk_level(0.9) == "critical"


@pytest.mark.asyncio
async def test_temporal_reasoning(reasoning_engine):
    """Test temporal reasoning"""
    start_time = datetime(2024, 1, 1)
    end_time = datetime(2024, 3, 1)
    
    # Mock temporal data
    reasoning_engine._get_temporal_data = AsyncMock(return_value=[
        {
            'timestamp': datetime(2024, 1, 15),
            'type': 'effectiveness',
            'effectiveness': 0.7
        },
        {
            'timestamp': datetime(2024, 2, 1),
            'type': 'side_effect',
            'name': 'headache'
        }
    ])
    
    patterns = await reasoning_engine.temporal_reasoning(
        entity_id='drug1',
        start_time=start_time,
        end_time=end_time
    )
    
    assert isinstance(patterns, list)
    # Should detect at least some patterns
    for pattern in patterns:
        assert isinstance(pattern, TemporalPattern)
        assert pattern.start_time >= start_time
        assert pattern.end_time is None or pattern.end_time <= end_time


@pytest.mark.asyncio
async def test_temporal_reasoning_with_pattern_filter(reasoning_engine):
    """Test temporal reasoning with pattern type filter"""
    start_time = datetime(2024, 1, 1)
    end_time = datetime(2024, 2, 1)
    
    reasoning_engine._get_temporal_data = AsyncMock(return_value=[])
    
    patterns = await reasoning_engine.temporal_reasoning(
        entity_id='drug1',
        start_time=start_time,
        end_time=end_time,
        pattern_type='effectiveness_trend'
    )
    
    # All patterns should match the filter
    for pattern in patterns:
        assert pattern.pattern_type == 'effectiveness_trend'


def test_calculate_trend_increasing(reasoning_engine):
    """Test trend calculation for increasing values"""
    values = [0.1, 0.3, 0.5, 0.7, 0.9]
    trend = reasoning_engine._calculate_trend(values)
    assert trend == "increasing"


def test_calculate_trend_decreasing(reasoning_engine):
    """Test trend calculation for decreasing values"""
    values = [0.9, 0.7, 0.5, 0.3, 0.1]
    trend = reasoning_engine._calculate_trend(values)
    assert trend == "decreasing"


def test_calculate_trend_stable(reasoning_engine):
    """Test trend calculation for stable values"""
    values = [0.5, 0.51, 0.49, 0.5, 0.52]
    trend = reasoning_engine._calculate_trend(values)
    assert trend == "stable"


def test_get_severity_weight(reasoning_engine):
    """Test severity weight calculation"""
    assert reasoning_engine._get_severity_weight('minor') == 0.25
    assert reasoning_engine._get_severity_weight('moderate') == 0.5
    assert reasoning_engine._get_severity_weight('major') == 0.75
    assert reasoning_engine._get_severity_weight('contraindicated') == 1.0
    assert reasoning_engine._get_severity_weight('unknown') == 0.5


def test_calculate_path_confidence_empty(reasoning_engine):
    """Test path confidence calculation with empty paths"""
    confidence = reasoning_engine._calculate_path_confidence([])
    assert confidence == 0.0


def test_calculate_path_confidence_single_path(reasoning_engine):
    """Test path confidence calculation with single path"""
    paths = [
        GraphPath(
            nodes=['a', 'b'],
            edges=['e1'],
            edge_types=['CAUSES'],
            confidence=0.8,
            evidence_sources=['source1'],
            path_length=2
        )
    ]
    confidence = reasoning_engine._calculate_path_confidence(paths)
    assert 0.0 <= confidence <= 1.0


def test_calculate_path_confidence_multiple_paths(reasoning_engine):
    """Test path confidence calculation with multiple paths"""
    paths = [
        GraphPath(
            nodes=['a', 'b'],
            edges=['e1'],
            edge_types=['CAUSES'],
            confidence=0.8,
            evidence_sources=['source1'],
            path_length=2
        ),
        GraphPath(
            nodes=['a', 'c', 'd'],
            edges=['e2', 'e3'],
            edge_types=['INTERACTS', 'CAUSES'],
            confidence=0.6,
            evidence_sources=['source2'],
            path_length=3
        )
    ]
    confidence = reasoning_engine._calculate_path_confidence(paths)
    assert 0.0 <= confidence <= 1.0
    # Shorter paths should have more weight


def test_generate_risk_recommendations_critical(reasoning_engine):
    """Test risk recommendations for critical risk level"""
    recommendations = reasoning_engine._generate_risk_recommendations(
        risk_score=0.9,
        risk_level="critical",
        factors=[]
    )
    
    assert len(recommendations) > 0
    assert any('immediate' in r.lower() or 'consultation' in r.lower() for r in recommendations)


def test_generate_risk_recommendations_low(reasoning_engine):
    """Test risk recommendations for low risk level"""
    recommendations = reasoning_engine._generate_risk_recommendations(
        risk_score=0.1,
        risk_level="low",
        factors=[]
    )
    
    assert len(recommendations) > 0
    assert any('standard' in r.lower() for r in recommendations)


def test_create_time_windows(reasoning_engine):
    """Test time window creation"""
    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 31)
    
    windows = reasoning_engine._create_time_windows(start, end, days=7)
    
    assert len(windows) > 0
    # Check that windows cover the entire period
    assert windows[0][0] == start
    assert windows[-1][1] == end
    
    # Check that windows don't overlap
    for i in range(len(windows) - 1):
        assert windows[i][1] == windows[i + 1][0]


@pytest.mark.asyncio
async def test_get_node_info_exists(reasoning_engine, mock_database):
    """Test getting node info when node exists"""
    mock_result = [{
        'id': 'drug1',
        'label': 'Drug',
        'name': 'Aspirin'
    }]
    
    mock_database.connection.g.V().has().toList.return_value = mock_result
    
    # Mock the chain of method calls
    mock_v = Mock()
    mock_has = Mock()
    mock_has.toList.return_value = mock_result
    mock_v.has.return_value = mock_has
    mock_database.connection.g.V.return_value = mock_v
    
    node_info = await reasoning_engine._get_node_info('drug1')
    
    assert node_info is not None
    assert node_info['id'] == 'drug1'


@pytest.mark.asyncio
async def test_get_node_info_not_exists(reasoning_engine, mock_database):
    """Test getting node info when node doesn't exist"""
    mock_v = Mock()
    mock_has = Mock()
    mock_has.toList.return_value = []
    mock_v.has.return_value = mock_has
    mock_database.connection.g.V.return_value = mock_v
    
    node_info = await reasoning_engine._get_node_info('nonexistent')
    
    assert node_info is None


@pytest.mark.asyncio
async def test_get_outgoing_edges(reasoning_engine, mock_database):
    """Test getting outgoing edges"""
    mock_edges = [
        {'id': 'edge1', 'label': 'CAUSES', 'target': 'node2'},
        {'id': 'edge2', 'label': 'INTERACTS', 'target': 'node3'}
    ]
    
    mock_v = Mock()
    mock_has = Mock()
    mock_out_e = Mock()
    mock_out_e.toList.return_value = mock_edges
    mock_has.outE.return_value = mock_out_e
    mock_v.has.return_value = mock_has
    mock_database.connection.g.V.return_value = mock_v
    
    edges = await reasoning_engine._get_outgoing_edges('node1')
    
    assert len(edges) == 2
    assert edges[0]['id'] == 'edge1'


@pytest.mark.asyncio
async def test_get_outgoing_edges_with_filter(reasoning_engine, mock_database):
    """Test getting outgoing edges with filter"""
    mock_edges = [
        {'id': 'edge1', 'label': 'CAUSES', 'target': 'node2'},
        {'id': 'edge2', 'label': 'INTERACTS', 'target': 'node3'}
    ]
    
    mock_v = Mock()
    mock_has = Mock()
    mock_out_e = Mock()
    mock_out_e.toList.return_value = mock_edges
    mock_has.outE.return_value = mock_out_e
    mock_v.has.return_value = mock_has
    mock_database.connection.g.V.return_value = mock_v
    
    edges = await reasoning_engine._get_outgoing_edges(
        'node1',
        edge_filters={'label': 'CAUSES'}
    )
    
    # Should only return edges matching the filter
    assert all(e['label'] == 'CAUSES' for e in edges)
