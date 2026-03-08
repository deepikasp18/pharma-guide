"""
Unit tests for temporal knowledge graph components
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.knowledge_graph.temporal_graph import (
    TemporalKnowledgeGraph,
    TemporalNode,
    TemporalNodeType,
    TrendDirection,
    EffectivenessTrend,
    ChangeDetection,
    create_temporal_knowledge_graph
)
from src.knowledge_graph.database import KnowledgeGraphDatabase


@pytest.fixture
def mock_database():
    """Create mock database"""
    db = MagicMock(spec=KnowledgeGraphDatabase)
    db.connection = MagicMock()
    db.connection.g = MagicMock()
    
    # Mock toList to return empty list by default
    db.connection.g.V.return_value.hasLabel.return_value.has.return_value.toList.return_value = []
    db.connection.g.V.return_value.has.return_value.addE.return_value.to.return_value.toList.return_value = []
    db.connection.g.addV.return_value.property.return_value.toList.return_value = []
    
    return db


@pytest.fixture
def temporal_graph(mock_database):
    """Create temporal knowledge graph with mock database"""
    return TemporalKnowledgeGraph(mock_database)


@pytest.mark.asyncio
async def test_create_symptom_log_node(temporal_graph, mock_database):
    """Test creating symptom log node"""
    timestamp = datetime.utcnow()
    
    node = await temporal_graph.create_symptom_log_node(
        patient_id="patient_001",
        symptom_name="headache",
        severity=7.5,
        timestamp=timestamp,
        metadata={'location': 'frontal'}
    )
    
    assert node.node_type == TemporalNodeType.SYMPTOM_LOG
    assert node.patient_id == "patient_001"
    assert node.entity_id == "headache"
    assert node.value == 7.5
    assert node.timestamp == timestamp
    assert 'location' in node.metadata


@pytest.mark.asyncio
async def test_create_medication_schedule_node(temporal_graph, mock_database):
    """Test creating medication schedule node"""
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(days=30)
    
    node = await temporal_graph.create_medication_schedule_node(
        patient_id="patient_001",
        medication_id="drug_001",
        dosage="10mg",
        frequency="daily",
        start_time=start_time,
        end_time=end_time
    )
    
    assert node.node_type == TemporalNodeType.MEDICATION_SCHEDULE
    assert node.patient_id == "patient_001"
    assert node.entity_id == "drug_001"
    assert node.value['dosage'] == "10mg"
    assert node.value['frequency'] == "daily"
    assert node.metadata['end_time'] == end_time.isoformat()


@pytest.mark.asyncio
async def test_create_dosage_change_node(temporal_graph, mock_database):
    """Test creating dosage change node"""
    timestamp = datetime.utcnow()
    
    node = await temporal_graph.create_dosage_change_node(
        patient_id="patient_001",
        medication_id="drug_001",
        previous_dosage="10mg",
        new_dosage="20mg",
        timestamp=timestamp,
        reason="Insufficient response"
    )
    
    assert node.node_type == TemporalNodeType.DOSAGE_CHANGE
    assert node.value['previous'] == "10mg"
    assert node.value['new'] == "20mg"
    assert node.metadata['reason'] == "Insufficient response"


@pytest.mark.asyncio
async def test_analyze_effectiveness_trend_increasing(temporal_graph):
    """Test analyzing increasing effectiveness trend"""
    # Mock data points showing increasing trend (older to newer)
    data_points = [
        {'timestamp': datetime.utcnow() - timedelta(days=10-i), 'value': 5.0 + i * 0.5, 'id': f'dp_{i}'}
        for i in range(10)
    ]
    
    temporal_graph._get_effectiveness_data_points = AsyncMock(return_value=data_points)
    
    trend = await temporal_graph.analyze_effectiveness_trend(
        patient_id="patient_001",
        medication_id="drug_001",
        start_time=datetime.utcnow() - timedelta(days=30)
    )
    
    assert trend is not None
    assert trend.trend_direction == TrendDirection.INCREASING
    assert trend.data_points == 10
    assert trend.average_effectiveness > 5.0


@pytest.mark.asyncio
async def test_analyze_effectiveness_trend_decreasing(temporal_graph):
    """Test analyzing decreasing effectiveness trend"""
    # Mock data points showing decreasing trend (older to newer)
    data_points = [
        {'timestamp': datetime.utcnow() - timedelta(days=10-i), 'value': 10.0 - i * 0.5, 'id': f'dp_{i}'}
        for i in range(10)
    ]
    
    temporal_graph._get_effectiveness_data_points = AsyncMock(return_value=data_points)
    
    trend = await temporal_graph.analyze_effectiveness_trend(
        patient_id="patient_001",
        medication_id="drug_001",
        start_time=datetime.utcnow() - timedelta(days=30)
    )
    
    assert trend is not None
    assert trend.trend_direction == TrendDirection.DECREASING
    assert trend.trend_strength > 0.0


@pytest.mark.asyncio
async def test_analyze_effectiveness_trend_stable(temporal_graph):
    """Test analyzing stable effectiveness trend"""
    # Mock data points showing stable trend
    data_points = [
        {'timestamp': datetime.utcnow() - timedelta(days=i), 'value': 7.0, 'id': f'dp_{i}'}
        for i in range(10, 0, -1)
    ]
    
    temporal_graph._get_effectiveness_data_points = AsyncMock(return_value=data_points)
    
    trend = await temporal_graph.analyze_effectiveness_trend(
        patient_id="patient_001",
        medication_id="drug_001",
        start_time=datetime.utcnow() - timedelta(days=30)
    )
    
    assert trend is not None
    assert trend.trend_direction == TrendDirection.STABLE
    assert trend.average_effectiveness == 7.0


@pytest.mark.asyncio
async def test_analyze_effectiveness_trend_insufficient_data(temporal_graph):
    """Test trend analysis with insufficient data"""
    # Only 2 data points (less than minimum of 3)
    data_points = [
        {'timestamp': datetime.utcnow() - timedelta(days=1), 'value': 5.0, 'id': 'dp_1'},
        {'timestamp': datetime.utcnow(), 'value': 6.0, 'id': 'dp_2'}
    ]
    
    temporal_graph._get_effectiveness_data_points = AsyncMock(return_value=data_points)
    
    trend = await temporal_graph.analyze_effectiveness_trend(
        patient_id="patient_001",
        medication_id="drug_001",
        start_time=datetime.utcnow() - timedelta(days=30),
        min_data_points=3
    )
    
    assert trend is None


def test_calculate_trend_increasing(temporal_graph):
    """Test trend calculation for increasing values"""
    data_points = [
        {'value': 1.0 + i * 0.5} for i in range(10)
    ]
    
    direction, strength = temporal_graph._calculate_trend(data_points)
    
    assert direction == TrendDirection.INCREASING
    assert strength > 0.5


def test_calculate_trend_decreasing(temporal_graph):
    """Test trend calculation for decreasing values"""
    data_points = [
        {'value': 10.0 - i * 0.5} for i in range(10)
    ]
    
    direction, strength = temporal_graph._calculate_trend(data_points)
    
    assert direction == TrendDirection.DECREASING
    assert strength > 0.5


def test_calculate_trend_stable(temporal_graph):
    """Test trend calculation for stable values"""
    data_points = [
        {'value': 5.0} for i in range(10)
    ]
    
    direction, strength = temporal_graph._calculate_trend(data_points)
    
    assert direction == TrendDirection.STABLE


def test_detect_significant_changes(temporal_graph):
    """Test detection of significant changes"""
    data_points = [
        {'timestamp': datetime.utcnow() - timedelta(days=5), 'value': 5.0},
        {'timestamp': datetime.utcnow() - timedelta(days=4), 'value': 5.2},
        {'timestamp': datetime.utcnow() - timedelta(days=3), 'value': 7.5},  # Significant change
        {'timestamp': datetime.utcnow() - timedelta(days=2), 'value': 7.8},
        {'timestamp': datetime.utcnow() - timedelta(days=1), 'value': 4.0},  # Significant change
    ]
    
    changes = temporal_graph._detect_significant_changes(data_points, threshold=0.3)
    
    assert len(changes) >= 2
    assert all('change_magnitude' in c for c in changes)
    assert all(c['change_magnitude'] >= 0.3 for c in changes)


def test_calculate_trend_confidence(temporal_graph):
    """Test trend confidence calculation"""
    # Many data points over long period
    data_points = [
        {'timestamp': datetime.utcnow() - timedelta(days=30-i), 'value': 5.0}
        for i in range(15)
    ]
    
    confidence = temporal_graph._calculate_trend_confidence(data_points, trend_strength=0.8)
    
    assert 0.0 <= confidence <= 1.0
    assert confidence > 0.5  # Should be reasonably confident with 15 points over 30 days


@pytest.mark.asyncio
async def test_detect_changes_significant(temporal_graph):
    """Test change detection with significant change"""
    # Mock data showing significant change
    data_points = [
        {'timestamp': datetime.utcnow() - timedelta(days=30-i), 'value': 5.0, 'node_type': 'symptom_log'}
        for i in range(15)
    ] + [
        {'timestamp': datetime.utcnow() - timedelta(days=15-i), 'value': 8.0, 'node_type': 'symptom_log'}
        for i in range(15)
    ]
    
    temporal_graph._get_temporal_data = AsyncMock(return_value=data_points)
    temporal_graph._infer_change_causes = AsyncMock(return_value=["Dosage change"])
    
    changes = await temporal_graph.detect_changes(
        patient_id="patient_001",
        entity_id="symptom_001",
        lookback_days=30,
        change_threshold=0.25
    )
    
    assert len(changes) > 0
    assert changes[0].change_magnitude > 0.25
    assert len(changes[0].potential_causes) > 0
    assert len(changes[0].recommendations) > 0


@pytest.mark.asyncio
async def test_detect_changes_no_significant_change(temporal_graph):
    """Test change detection with no significant change"""
    # Mock data showing stable values
    data_points = [
        {'timestamp': datetime.utcnow() - timedelta(days=30-i), 'value': 5.0, 'node_type': 'symptom_log'}
        for i in range(30)
    ]
    
    temporal_graph._get_temporal_data = AsyncMock(return_value=data_points)
    
    changes = await temporal_graph.detect_changes(
        patient_id="patient_001",
        entity_id="symptom_001",
        lookback_days=30,
        change_threshold=0.25
    )
    
    assert len(changes) == 0


@pytest.mark.asyncio
async def test_detect_changes_insufficient_data(temporal_graph):
    """Test change detection with insufficient data"""
    # Only one data point
    data_points = [
        {'timestamp': datetime.utcnow(), 'value': 5.0, 'node_type': 'symptom_log'}
    ]
    
    temporal_graph._get_temporal_data = AsyncMock(return_value=data_points)
    
    changes = await temporal_graph.detect_changes(
        patient_id="patient_001",
        entity_id="symptom_001",
        lookback_days=30
    )
    
    assert len(changes) == 0


def test_generate_change_recommendations_high_magnitude(temporal_graph):
    """Test recommendation generation for high magnitude change"""
    recommendations = temporal_graph._generate_change_recommendations(
        change_magnitude=0.6,
        current_value=8.0,
        previous_value=5.0
    )
    
    assert len(recommendations) > 0
    assert any('provider' in r.lower() for r in recommendations)
    assert any('worsening' in r.lower() for r in recommendations)


def test_generate_change_recommendations_moderate_magnitude(temporal_graph):
    """Test recommendation generation for moderate magnitude change"""
    recommendations = temporal_graph._generate_change_recommendations(
        change_magnitude=0.35,
        current_value=6.5,
        previous_value=5.0
    )
    
    assert len(recommendations) > 0
    assert any('follow-up' in r.lower() or 'monitor' in r.lower() for r in recommendations)


def test_generate_change_recommendations_improving(temporal_graph):
    """Test recommendation generation for improving symptoms"""
    recommendations = temporal_graph._generate_change_recommendations(
        change_magnitude=0.4,
        current_value=3.0,
        previous_value=5.0
    )
    
    assert any('improving' in r.lower() for r in recommendations)


@pytest.mark.asyncio
async def test_infer_change_causes_with_dosage_change(temporal_graph):
    """Test cause inference with dosage change"""
    data_points = [
        {'timestamp': datetime.utcnow() - timedelta(days=5), 'value': 5.0, 'node_type': 'symptom_log'},
        {'timestamp': datetime.utcnow() - timedelta(days=3), 'value': 5.0, 'node_type': 'dosage_change'},
        {'timestamp': datetime.utcnow() - timedelta(days=1), 'value': 7.0, 'node_type': 'symptom_log'},
    ]
    
    causes = await temporal_graph._infer_change_causes(
        patient_id="patient_001",
        entity_id="drug_001",
        data_points=data_points
    )
    
    assert len(causes) > 0
    assert any('dosage' in c.lower() for c in causes)


@pytest.mark.asyncio
async def test_infer_change_causes_with_adverse_event(temporal_graph):
    """Test cause inference with adverse event"""
    data_points = [
        {'timestamp': datetime.utcnow() - timedelta(days=5), 'value': 5.0, 'node_type': 'symptom_log'},
        {'timestamp': datetime.utcnow() - timedelta(days=3), 'value': 5.0, 'node_type': 'adverse_event'},
        {'timestamp': datetime.utcnow() - timedelta(days=1), 'value': 7.0, 'node_type': 'symptom_log'},
    ]
    
    causes = await temporal_graph._infer_change_causes(
        patient_id="patient_001",
        entity_id="drug_001",
        data_points=data_points
    )
    
    assert len(causes) > 0
    assert any('adverse' in c.lower() for c in causes)


@pytest.mark.asyncio
async def test_create_temporal_knowledge_graph():
    """Test factory function"""
    mock_db = MagicMock(spec=KnowledgeGraphDatabase)
    tkg = await create_temporal_knowledge_graph(mock_db)
    
    assert isinstance(tkg, TemporalKnowledgeGraph)
    assert tkg.database == mock_db


@pytest.mark.asyncio
async def test_temporal_node_relationships(temporal_graph, mock_database):
    """Test creation of temporal relationships"""
    # Mock previous nodes
    temporal_graph._find_previous_temporal_nodes = AsyncMock(return_value=[
        {
            'id': 'prev_node_001',
            'timestamp': datetime.utcnow() - timedelta(days=1),
            'value': 5.0
        }
    ])
    
    node = await temporal_graph.create_symptom_log_node(
        patient_id="patient_001",
        symptom_name="headache",
        severity=6.0
    )
    
    # Verify relationships were created
    assert node is not None


@pytest.mark.asyncio
async def test_error_handling_in_node_creation(temporal_graph, mock_database):
    """Test error handling in node creation"""
    # Mock database to raise exception
    mock_database.connection.g.addV.side_effect = Exception("Database error")
    
    with pytest.raises(Exception):
        await temporal_graph.create_symptom_log_node(
            patient_id="patient_001",
            symptom_name="headache",
            severity=7.0
        )
