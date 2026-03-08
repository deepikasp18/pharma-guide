# Query Translation Service

## Overview

The Query Translation Service is a core component of the PharmaGuide system that converts natural language medical queries into optimized Gremlin graph database queries. It bridges the gap between user-friendly natural language and efficient graph traversals, enabling the system to retrieve relevant medical information from the knowledge graph.

## Architecture

### Components

1. **QueryTranslator**: Main translation engine that converts NLP analysis to Gremlin queries
2. **QueryOptimizer**: Optimizes generated queries for performance and efficiency
3. **Provenance Tracking**: Maintains complete audit trail of query translation and data sources

### Data Flow

```
Natural Language Query
    ↓
NLP Query Processor (Intent + Entities)
    ↓
Query Translator (Intent → Gremlin Template)
    ↓
Query Optimizer (Performance Optimization)
    ↓
Gremlin Query + Provenance
    ↓
Knowledge Graph Database
```

## Features

### 1. Intent-Based Query Generation

The service supports multiple query intents:

- **SIDE_EFFECTS**: Retrieve side effects for medications
- **DRUG_INTERACTIONS**: Check interactions between drugs
- **DOSING**: Get dosing information and recommendations
- **CONTRAINDICATIONS**: Find contraindications for drugs and conditions
- **ALTERNATIVES**: Discover alternative medications
- **EFFECTIVENESS**: Query medication effectiveness for conditions
- **GENERAL_INFO**: Retrieve general drug information

### 2. Patient Context Integration

Queries can be personalized using patient context:

```python
patient_context = {
    'demographics': {'age': 65, 'gender': 'male', 'weight': 180},
    'conditions': ['diabetes', 'hypertension'],
    'medications': [
        {'name': 'Metformin', 'dosage': '500mg'},
        {'name': 'Lisinopril', 'dosage': '10mg'}
    ],
    'risk_factors': ['obesity', 'family_history_heart_disease']
}

query, provenance = query_translator.translate_query(analysis, patient_context)
```

Patient context affects:
- Confidence thresholds for side effects
- Filtering by patient's current medications
- Age-based dosing adjustments
- Contraindication checking against patient conditions

### 3. Query Optimization

The QueryOptimizer automatically applies several optimizations:

- **Result Limiting**: Adds `.limit()` to prevent excessive data retrieval
- **Deduplication**: Adds `.dedup()` to remove duplicate results
- **Index Hints**: Uses label and property filters for efficient lookups
- **Complexity Detection**: Identifies and flags high-complexity queries

### 4. Cost Estimation

The service estimates query computational cost based on:

- Number of vertex scans
- Edge traversals (multi-hop queries)
- Property filters
- Aggregation operations
- Presence of result limits

Cost factors help identify expensive queries and provide optimization recommendations.

### 5. Provenance Tracking

Every query maintains complete provenance:

```python
provenance = QueryProvenance(
    query_id="unique-id",
    original_query="What are the side effects of Lisinopril?",
    intent="SIDE_EFFECTS",
    entities=[...],
    gremlin_query="g.V()...",
    reasoning_steps=[...],
    data_sources=["OnSIDES", "SIDER", "FAERS"]
)
```

Provenance includes:
- Original natural language query
- Classified intent and extracted entities
- Generated Gremlin query
- Reasoning steps taken
- Data sources that will be queried

## Usage Examples

### Basic Side Effects Query

```python
from src.nlp.query_processor import medical_query_processor
from src.nlp.query_translator import query_translator

# Process natural language
analysis = medical_query_processor.process_query(
    "What are the side effects of Lisinopril?"
)

# Translate to Gremlin
query, provenance = query_translator.translate_query(analysis)

print(query.query_string)
# Output: g.V().hasLabel('Drug').has('name', 'lisinopril')
#         .outE('CAUSES').has('confidence', P.gte(0.5))
#         .order().by('frequency', Order.desc).inV().dedup().limit(100).toList()
```

### Drug Interaction Check

```python
analysis = medical_query_processor.process_query(
    "Can I take Aspirin with Ibuprofen?"
)

query, provenance = query_translator.translate_query(analysis)

print(query.query_string)
# Output: g.V().hasLabel('Drug').has('name', 'aspirin')
#         .outE('INTERACTS_WITH')
#         .where(inV().has('name', 'ibuprofen'))
#         .order().by('severity', Order.desc).limit(100).toList()
```

### Personalized Dosing Query

```python
patient_context = {
    'demographics': {'age': 65, 'weight': 180},
    'conditions': ['diabetes']
}

analysis = medical_query_processor.process_query(
    "What is the dosage for Metformin?"
)

query, provenance = query_translator.translate_query(analysis, patient_context)

# Query includes patient-specific filters
print(query.parameters)
# Output: {'drug_name': 'metformin', 'age': 65, 'weight': 180}
```

### Query Explanation

```python
# Get human-readable explanation
explanation = query_translator.explain_query(query, provenance)

print(explanation['graph_query_explanation'])
print(f"Complexity: {explanation['complexity']}")
print(f"Data Sources: {explanation['data_sources']}")
print(f"Cost Score: {explanation['estimated_cost']['cost_score']}")
```

## Query Templates

### Side Effects Template

```gremlin
g.V()
  .hasLabel('Drug')
  .has('name', '<drug_name>')
  .outE('CAUSES')
  .has('confidence', P.gte(<threshold>))
  .order().by('frequency', Order.desc)
  .inV()
  .dedup()
  .limit(100)
  .toList()
```

### Drug Interactions Template

```gremlin
g.V()
  .hasLabel('Drug')
  .has('name', '<drug_a>')
  .outE('INTERACTS_WITH')
  .where(inV().has('name', '<drug_b>'))
  .order().by('severity', Order.desc)
  .limit(100)
  .toList()
```

### Contraindications Template

```gremlin
g.V()
  .hasLabel('Drug')
  .has('name', '<drug_name>')
  .outE('CONTRAINDICATED_WITH')
  .where(inV().has('name', '<condition>'))
  .order().by('severity', Order.desc)
  .inV()
  .limit(100)
  .toList()
```

### Alternatives Template (Multi-hop)

```gremlin
g.V()
  .hasLabel('Drug')
  .has('name', '<drug_name>')
  .outE('TREATS')
  .inV()  // Get conditions
  .inE('TREATS')  // Find other drugs treating these conditions
  .outV()  // Get alternative drugs
  .where(neq('<drug_name>'))  // Exclude original drug
  .dedup()
  .limit(10)
  .toList()
```

## Data Source Mapping

The service automatically determines which datasets contribute to each query:

| Query Type | Data Sources |
|------------|--------------|
| Side Effects | OnSIDES, SIDER, FAERS |
| Drug Interactions | DDInter, DrugBank |
| Dosing | DrugBank, Drugs@FDA |
| Contraindications | DrugBank, FAERS |
| Effectiveness | DrugBank, Drugs@FDA |
| Alternatives | DrugBank, Drugs@FDA |

## Performance Considerations

### Query Complexity Levels

- **Low**: Direct vertex/edge lookups with filters
- **Medium**: Single-hop traversals with conditions
- **High**: Multi-hop traversals, complex filtering

### Optimization Strategies

1. **Use Specific Filters**: Always filter by label and key properties
2. **Limit Early**: Apply limits as early as possible in traversal
3. **Deduplicate**: Remove duplicates before final collection
4. **Index Usage**: Leverage graph database indexes on frequently queried properties

### Cost Reduction Tips

- Add `.limit()` to all queries
- Use property filters to reduce vertex scans
- Avoid deep multi-hop traversals when possible
- Cache frequently accessed results

## Error Handling

The service handles various error scenarios:

1. **Missing Entities**: Returns empty query with explanation
2. **Unknown Intent**: Falls back to general information query
3. **Translation Errors**: Returns safe fallback query
4. **Invalid Context**: Gracefully ignores invalid patient context

## Testing

The service includes comprehensive unit tests:

```bash
# Run all query translator tests
uv run pytest tests/test_query_translator.py -v

# Run specific test class
uv run pytest tests/test_query_translator.py::TestQueryTranslator -v

# Run with coverage
uv run pytest tests/test_query_translator.py --cov=src/nlp/query_translator
```

## Integration

### With NLP Query Processor

```python
from src.nlp import medical_query_processor, query_translator

# End-to-end pipeline
query_text = "What are the side effects of Aspirin?"
analysis = medical_query_processor.process_query(query_text)
gremlin_query, provenance = query_translator.translate_query(analysis)
```

### With Knowledge Graph Database

```python
from src.knowledge_graph.database import db

# Execute translated query
await db.connect()
results = await db.execute_gremlin_query(gremlin_query.query_string)
await db.disconnect()
```

## Future Enhancements

1. **Machine Learning**: Train ML models to improve query translation accuracy
2. **Query Caching**: Cache frequently executed queries for performance
3. **Adaptive Optimization**: Learn from query execution times to improve optimization
4. **Multi-language Support**: Extend to support queries in multiple languages
5. **Query Rewriting**: Automatically rewrite expensive queries to more efficient forms

## References

- Requirements: 1.1, 1.5 (Semantic Query Processing and Provenance)
- Design Document: Section 2 (Semantic Query Processing Engine)
- Related Components:
  - NLP Query Processor (`src/nlp/query_processor.py`)
  - Knowledge Graph Database (`src/knowledge_graph/database.py`)
  - Graph Models (`src/knowledge_graph/models.py`)
