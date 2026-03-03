# Query Translation Service

## Overview

The Query Translation Service is a core component of PharmaGuide that converts natural language medical queries into optimized graph database queries. It bridges the gap between user intent and knowledge graph traversal, enabling semantic search across medical datasets.

## Architecture

### Components

1. **QueryTranslator**: Main translation engine
2. **GraphQuery**: Structured representation of graph queries
3. **QueryExplanation**: Human-readable explanation of translation
4. **ProvenanceInfo**: Tracking information for query execution

### Translation Pipeline

```
Natural Language Query
    ↓
Query Analysis (from QueryProcessor)
    ↓
Intent-Based Query Building
    ↓
Query Optimization
    ↓
Graph Query + Explanation
```

## Features

### 1. Natural Language to Graph Query Translation

Converts analyzed natural language queries into:
- **Gremlin queries** for Amazon Neptune
- **Cypher queries** for future compatibility with other graph databases

### 2. Intent-Based Query Patterns

Supports multiple query intents:
- **Side Effects**: Retrieve drug side effects with frequency and confidence
- **Drug Interactions**: Check interactions between medications
- **Dosing**: Get dosing information and recommendations
- **Contraindications**: Identify drug-condition conflicts
- **Alternatives**: Find alternative medications
- **Effectiveness**: Query treatment effectiveness data
- **General Info**: Retrieve comprehensive drug information

### 3. Query Optimization

Applies multiple optimization strategies:
- **Index Lookup**: Ensures indexed properties are used early
- **Early Filtering**: Applies filters before expensive operations
- **Batch Operations**: Combines multiple lookups efficiently
- **Result Limiting**: Prevents excessive traversals
- **Cache Identification**: Marks queries suitable for caching

### 4. Patient Context Integration

Personalizes queries based on:
- Demographics (age, gender, weight)
- Medical conditions
- Current medications
- Risk factors
- Genetic information (when available)

### 5. Provenance Tracking

Maintains complete audit trail:
- Query ID and timestamp
- Data sources used
- Traversal path through graph
- Confidence scores
- Reasoning steps

## Usage

### Basic Query Translation

```python
from src.nlp.query_processor import MedicalQueryProcessor
from src.nlp.query_translator import QueryTranslator

# Initialize components
processor = MedicalQueryProcessor()
translator = QueryTranslator()

# Process natural language query
query_analysis = processor.process_query(
    "What are the side effects of Lisinopril?"
)

# Translate to graph query
graph_query, explanation = translator.translate_query(query_analysis)

# Access generated queries
print(f"Gremlin: {graph_query.gremlin_query}")
print(f"Cypher: {graph_query.cypher_query}")
print(f"Complexity: {graph_query.estimated_complexity}/10")
```

### Query Translation with Patient Context

```python
# Define patient context
patient_context = {
    'demographics': {
        'age': 65,
        'gender': 'male',
        'weight': 180
    },
    'conditions': ['diabetes', 'hypertension'],
    'medications': [
        {'name': 'metformin', 'dosage': '500mg'}
    ],
    'risk_factors': ['smoking', 'obesity']
}

# Translate with personalization
graph_query, explanation = translator.translate_query(
    query_analysis,
    patient_context=patient_context
)

# Query is now personalized based on patient characteristics
```

### Creating Provenance Information

```python
# Create provenance tracking
provenance = translator.create_provenance_info(
    query_id="query-123",
    graph_query=graph_query,
    data_sources=["OnSIDES", "SIDER", "DrugBank"],
    confidence_scores={"result1": 0.9, "result2": 0.85}
)

# Access provenance details
print(f"Data Sources: {provenance.data_sources}")
print(f"Traversal Path: {provenance.traversal_path}")
print(f"Reasoning: {provenance.reasoning_steps}")
```

## Query Types

### Simple Lookup
Direct property retrieval from single node type.

**Example**: "What is Lisinopril?"
```gremlin
g.V().hasLabel('Drug').has('name', 'lisinopril')
  .project('name', 'generic_name', 'mechanism')
  .by('name').by('generic_name').by('mechanism')
```

### Relationship Traversal
Single-hop traversal through one relationship type.

**Example**: "What are the side effects of Lisinopril?"
```gremlin
g.V().hasLabel('Drug').has('name', 'lisinopril')
  .outE('CAUSES').has('confidence', gt(0.7))
  .order().by('frequency', desc)
  .inV()
  .project('side_effect', 'frequency', 'confidence')
  .by('name')
  .by(inE('CAUSES').values('frequency'))
  .by(inE('CAUSES').values('confidence'))
```

### Multi-Hop Traversal
Complex traversal through multiple relationship types.

**Example**: "What are alternatives to Lisinopril?"
```gremlin
g.V().hasLabel('Drug').has('name', 'lisinopril')
  .as('original')
  .union(
    __.out('TREATS').in('TREATS').where(neq('original')),
    __.out('SIMILAR_MECHANISM').where(neq('original')),
    __.out('SAME_CLASS').where(neq('original'))
  )
  .dedup()
  .limit(10)
```

## Optimization Strategies

### 1. Index-Based Filtering
```gremlin
# Good: Uses index on 'name' property
g.V().hasLabel('Drug').has('name', 'lisinopril')

# Bad: Full scan
g.V().hasLabel('Drug').filter(values('name').is('lisinopril'))
```

### 2. Early Result Limiting
```gremlin
# Good: Limits early in traversal
g.V().hasLabel('Drug').limit(100).outE('CAUSES')

# Bad: Limits after expensive operations
g.V().hasLabel('Drug').outE('CAUSES').inV().limit(100)
```

### 3. Confidence Thresholding
```gremlin
# Filters low-confidence relationships early
.outE('CAUSES').has('confidence', gt(0.7))
```

### 4. Patient-Specific Optimization
```python
# Adjusts confidence threshold based on patient risk
if len(risk_factors) > 5:
    confidence_threshold = 0.85  # Higher threshold for high-risk patients
else:
    confidence_threshold = 0.7   # Standard threshold
```

## Query Explanation

The service provides detailed explanations of query translation:

```python
explanation = QueryExplanation(
    original_query="What are the side effects of Lisinopril?",
    intent="side_effects",
    extracted_entities=[
        {"type": "drug", "text": "Lisinopril", "confidence": 0.95}
    ],
    translation_steps=[
        "Identified query intent as 'side_effects' with 0.90 confidence",
        "Extracted entities: drug: Lisinopril",
        "Selected relationship_traversal query pattern",
        "Applied optimizations: index_lookup, edge_filter"
    ],
    graph_traversal_description=(
        "Traverse from Drug node through CAUSES relationships "
        "to SideEffect nodes, filtering by confidence and ordering by frequency"
    ),
    expected_result_types=["SideEffect", "Frequency", "Confidence"],
    confidence=0.92
)
```

## Error Handling

### Fallback Queries
When specific translation fails, the service provides fallback queries:

```python
# If no entities extracted or intent unclear
fallback_query = """
g.V().hasLabel('Drug')
  .limit(10)
  .project('name', 'generic_name')
  .by('name').by('generic_name')
"""
```

### Graceful Degradation
- Missing patient context: Uses default confidence thresholds
- Single drug in interaction query: Checks against patient's medications
- Unknown intent: Falls back to general information query

## Performance Considerations

### Query Complexity Estimation
Queries are rated 1-10 for complexity:
- **1-3**: Simple lookups and single-hop traversals
- **4-6**: Multi-hop traversals with moderate filtering
- **7-10**: Complex pattern matching and aggregations

### Caching Strategy
High-confidence queries (>0.8) are marked as cache candidates:
```python
if query_analysis.query_confidence > 0.8:
    optimization_hints.append("cache_candidate")
```

### Batch Operations
Multiple drug lookups are batched:
```gremlin
# Batch lookup for multiple drugs
g.V().hasLabel('Drug')
  .has('name', within('drug1', 'drug2', 'drug3'))
```

## Integration with Knowledge Graph

### Data Sources
Queries reference multiple datasets:
- **OnSIDES**: Modern side effects (3.6M+ drug-ADE pairs)
- **SIDER**: Baseline side effects with frequency
- **FAERS**: Real-world adverse events
- **DrugBank**: Drug interactions and properties
- **DDInter**: Drug-drug interactions
- **Drugs@FDA**: Official FDA data

### Relationship Types
Supported graph relationships:
- `CAUSES`: Drug → SideEffect
- `INTERACTS_WITH`: Drug → Drug
- `TREATS`: Drug → Condition
- `CONTRAINDICATED_WITH`: Drug → Condition
- `REQUIRES_ADJUSTMENT`: Drug → DosingAdjustment
- `SIMILAR_MECHANISM`: Drug → Drug
- `SAME_CLASS`: Drug → Drug

## Testing

### Unit Tests
Comprehensive test coverage in `tests/test_query_translator.py`:
- Query translation for all intent types
- Patient context integration
- Query optimization
- Provenance tracking
- Edge cases and error handling

### Example Test
```python
def test_translate_side_effects_query(query_translator, sample_query):
    graph_query, explanation = query_translator.translate_query(sample_query)
    
    assert graph_query.query_type == QueryType.RELATIONSHIP_TRAVERSAL
    assert "hasLabel('Drug')" in graph_query.gremlin_query
    assert "outE('CAUSES')" in graph_query.gremlin_query
    assert explanation.confidence > 0.8
```

## Future Enhancements

1. **Machine Learning Integration**: Learn optimal query patterns from usage
2. **Query Result Caching**: Implement intelligent caching layer
3. **Multi-Language Support**: Extend to non-English queries
4. **Advanced Reasoning**: Implement probabilistic reasoning over graph
5. **Query Rewriting**: Automatic query optimization based on execution stats

## References

- Requirements: 1.1, 1.5 (Semantic query processing and provenance)
- Design Document: Query Processing Models section
- Related Components:
  - `src/nlp/query_processor.py`: Natural language processing
  - `src/knowledge_graph/database.py`: Graph database interface
  - `src/knowledge_graph/models.py`: Entity models
