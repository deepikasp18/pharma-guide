# Graph Reasoning Engine

## Overview

The Graph Reasoning Engine is a core component of PharmaGuide that performs complex reasoning and inference over the medical knowledge graph. It provides three main capabilities:

1. **Multi-hop Graph Traversal**: Navigate complex relationships across multiple nodes
2. **Probabilistic Risk Calculation**: Assess medication risks with patient-specific factors
3. **Temporal Reasoning**: Analyze patterns and trends over time

## Architecture

The reasoning engine is built on top of the Neptune graph database and provides high-level abstractions for complex graph operations.

### Key Components

- `GraphReasoningEngine`: Main engine class
- `GraphPath`: Represents a path through the knowledge graph
- `RiskAssessment`: Risk calculation results
- `TemporalPattern`: Temporal analysis results

## Multi-Hop Traversal

Multi-hop traversal allows you to navigate complex relationships in the knowledge graph, finding paths between entities that may be several steps apart.

### Traversal Strategies

1. **Breadth-First Search (BFS)**: Explores all neighbors at the current depth before moving deeper
2. **Depth-First Search (DFS)**: Explores as far as possible along each branch before backtracking
3. **Shortest Path**: Finds the shortest paths between nodes
4. **All Paths**: Finds all possible paths (within max hops)

### Example Usage

```python
from src.knowledge_graph.reasoning_engine import (
    GraphReasoningEngine,
    TraversalStrategy
)
from src.knowledge_graph.database import db

# Create reasoning engine
engine = GraphReasoningEngine(db)

# Find all side effects within 3 hops of a drug
paths = await engine.multi_hop_traversal(
    start_node_id='drug_aspirin',
    target_node_type='SideEffect',
    max_hops=3,
    strategy=TraversalStrategy.BREADTH_FIRST
)

# Examine the paths
for path in paths:
    print(f"Path: {' -> '.join(path.nodes)}")
    print(f"Confidence: {path.confidence}")
    print(f"Evidence: {path.evidence_sources}")
```

### Edge Filtering

You can filter edges during traversal to focus on specific relationship types:

```python
# Only traverse CAUSES relationships
paths = await engine.multi_hop_traversal(
    start_node_id='drug_aspirin',
    target_node_type='SideEffect',
    max_hops=2,
    edge_filters={'label': 'CAUSES'}
)
```

## Probabilistic Risk Calculation

The risk calculation feature assesses medication risks by analyzing side effect relationships and applying patient-specific factors.

### Risk Assessment Components

- **Base Risk**: Calculated from side effect frequencies and severities
- **Patient Factors**: Age, conditions, polypharmacy adjustments
- **Risk Level**: Categorical classification (low, moderate, high, critical)
- **Contributing Factors**: Specific risk factors identified
- **Recommendations**: Actionable guidance based on risk level

### Example Usage

```python
from src.knowledge_graph.models import PatientContext

# Create patient context
patient = PatientContext(
    id='patient_123',
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

# Calculate risk
risk = await engine.calculate_risk(
    drug_id='drug_warfarin',
    patient_context=patient
)

print(f"Risk Score: {risk.risk_score}")
print(f"Risk Level: {risk.risk_level}")
print(f"Recommendations:")
for rec in risk.recommendations:
    print(f"  - {rec}")
```

### Risk Factors

The engine considers multiple factors when calculating risk:

1. **Side Effect Severity**: Major and critical side effects increase risk
2. **Patient Age**: Elderly (>65) and pediatric (<18) patients have higher risk
3. **Comorbidities**: Kidney, liver, and heart disease increase risk
4. **Polypharmacy**: Taking >5 medications increases interaction risk
5. **Evidence Confidence**: Lower confidence reduces risk score reliability

### Risk Levels

- **Low** (0.0 - 0.25): Standard monitoring sufficient
- **Moderate** (0.25 - 0.5): Regular monitoring advised
- **High** (0.5 - 0.75): Close monitoring recommended
- **Critical** (0.75 - 1.0): Immediate consultation required

## Temporal Reasoning

Temporal reasoning analyzes patterns and trends in medication data over time, helping identify effectiveness changes, side effect patterns, and dosage correlations.

### Pattern Types

1. **Effectiveness Trends**: Changes in medication effectiveness over time
2. **Side Effect Occurrence**: Recurring side effect patterns
3. **Dosage Correlations**: Relationships between dosage changes and outcomes

### Example Usage

```python
from datetime import datetime, timedelta

# Analyze last 3 months
start_time = datetime.now() - timedelta(days=90)
end_time = datetime.now()

# Find temporal patterns
patterns = await engine.temporal_reasoning(
    entity_id='patient_123',
    start_time=start_time,
    end_time=end_time
)

# Examine patterns
for pattern in patterns:
    print(f"Pattern Type: {pattern.pattern_type}")
    print(f"Trend: {pattern.trend}")
    print(f"Frequency: {pattern.frequency}")
    print(f"Confidence: {pattern.confidence}")
```

### Trend Detection

The engine uses linear regression to detect trends:

- **Increasing**: Slope > 0.05 (improving or worsening)
- **Decreasing**: Slope < -0.05 (improving or worsening)
- **Stable**: -0.05 ≤ slope ≤ 0.05 (no significant change)

### Time Windows

Temporal analysis divides the time period into windows (default 7 days) for pattern detection:

```python
# Custom time window size
patterns = await engine.temporal_reasoning(
    entity_id='patient_123',
    start_time=start_time,
    end_time=end_time,
    pattern_type='effectiveness_trend'  # Filter by pattern type
)
```

## Performance Considerations

### Path Caching

The engine includes a path cache to avoid redundant traversals:

```python
# Cache is automatically used for repeated queries
paths1 = await engine.multi_hop_traversal(start_node_id='drug_aspirin', ...)
paths2 = await engine.multi_hop_traversal(start_node_id='drug_aspirin', ...)  # Uses cache
```

### Max Hops Limitation

Limit max_hops to avoid exponential complexity:

- **1-2 hops**: Fast, suitable for direct relationships
- **3-4 hops**: Moderate, good for complex queries
- **5+ hops**: Slow, use only when necessary

### Edge Filtering

Use edge filters to reduce the search space:

```python
# More efficient - filters during traversal
paths = await engine.multi_hop_traversal(
    start_node_id='drug_aspirin',
    edge_filters={'confidence': 0.7}  # Only high-confidence edges
)
```

## Integration with Other Components

### Query Translator

The reasoning engine is used by the query translator to execute complex queries:

```python
from src.nlp.query_translator import QueryTranslator

translator = QueryTranslator(db, engine)
response = await translator.translate_and_execute(
    "What are the risks of aspirin for a 70-year-old with diabetes?"
)
```

### Recommendation Engine

The recommendation engine uses reasoning for alternative medication suggestions:

```python
from src.knowledge_graph.recommendation_engine import AlternativeMedicationEngine

rec_engine = AlternativeMedicationEngine(db)
# Internally uses reasoning engine for path analysis
alternatives = await rec_engine.find_alternatives(drug_id='drug_aspirin')
```

## Error Handling

The engine includes comprehensive error handling:

```python
try:
    paths = await engine.multi_hop_traversal(...)
except Exception as e:
    logger.error(f"Traversal failed: {e}")
    # Handle error appropriately
```

Common errors:
- `NeptuneConnectionError`: Database connection issues
- `NeptuneQueryError`: Query execution failures
- `ValueError`: Invalid parameters

## Testing

The reasoning engine includes comprehensive unit tests:

```bash
# Run reasoning engine tests
uv run pytest tests/test_reasoning_engine.py -v

# Run with coverage
uv run pytest tests/test_reasoning_engine.py --cov=src/knowledge_graph/reasoning_engine
```

## Future Enhancements

Planned improvements:

1. **Graph Neural Networks**: ML-based path ranking
2. **Parallel Traversal**: Concurrent path exploration
3. **Query Optimization**: Automatic query plan optimization
4. **Caching Strategies**: Advanced caching with TTL
5. **Real-time Updates**: Incremental graph updates during traversal

## References

- [Neptune Graph Database Documentation](https://docs.aws.amazon.com/neptune/)
- [Gremlin Query Language](https://tinkerpop.apache.org/gremlin.html)
- [Graph Algorithms](https://en.wikipedia.org/wiki/Graph_traversal)
