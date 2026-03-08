# Mock Data System Guide

## Overview

When running PharmaGuide locally with `USE_MOCK_SERVICES=true`, all AWS services (Neptune graph database, OpenSearch) are replaced with in-memory mock implementations. This allows you to develop and test the API without any cloud infrastructure.

## How Mock Data Works

### 1. Mock Database Architecture

The mock system is implemented in `src/knowledge_graph/database.py`:

```
MockNeptuneConnection
├── data (in-memory storage)
│   ├── vertices: {}  # Dictionary of graph vertices
│   └── edges: []     # List of graph edges
└── g (MockTraversal) # Gremlin-like query interface
```

### 2. Data Storage Structure

**Vertices (Nodes):**
```python
{
    'drug_1': {
        'id': 'drug_1',
        'label': 'Drug',
        'properties': {
            'name': 'Lisinopril',
            'generic_name': 'lisinopril',
            'drugbank_id': 'DB00722'
        }
    }
}
```

**Edges (Relationships):**
```python
[
    {
        'id': 'causes_drug_1_sideeffect_1',
        'label': 'CAUSES',
        'from': 'drug_1',
        'to': 'sideeffect_1',
        'properties': {
            'frequency': 0.15,
            'confidence': 0.85
        }
    }
]
```

### 3. Data Lifecycle

**During Runtime:**
- Data exists only in memory (Python dictionaries)
- No persistence to disk or database
- Data is lost when the server stops

**Data Sources:**
1. **Test Fixtures** (`tests/conftest.py`): Sample data for automated tests
2. **API Calls**: Data created via POST endpoints
3. **Hardcoded Responses**: Some endpoints return predefined mock responses

### 4. Mock Query Operations

The `MockTraversal` class simulates Gremlin graph queries:

```python
# Example: Find all drugs
g.V().hasLabel('Drug').toList()

# Example: Find side effects for a drug
g.V().has('id', 'drug_1').outE('CAUSES').inV().toList()
```

**Supported Operations:**
- `V()` - Get vertices
- `E()` - Get edges
- `hasLabel(label)` - Filter by label
- `has(key, value)` - Filter by property
- `outE(label)` - Get outgoing edges
- `inV()` - Get target vertices
- `addV(label)` - Create vertex
- `addE(label)` - Create edge
- `property(key, value)` - Set property
- `limit(n)` - Limit results
- `toList()` - Execute and return results

## Current API Behavior

### Endpoints with Mock Data

**1. Health Check** (`GET /health`)
- Returns hardcoded status
- No database interaction

**2. Query Processing** (`POST /query/process`)
- Returns mock response with predefined structure
- Does NOT query actual graph data
- Useful for testing API structure

**3. Patient Management** (`POST /patient/register`)
- Would create patient vertex in mock graph
- Data stored in memory during runtime

**4. Reasoning** (`POST /reasoning/analyze`)
- Returns mock analysis results
- Simulates reasoning without actual graph traversal

### Example Mock Response

When you query: `POST /query/process`
```json
{
    "query": "What are the side effects of Lisinopril?"
}
```

You get:
```json
{
    "query_id": "query_1234567890.123",
    "original_query": "What are the side effects of Lisinopril?",
    "intent": "medication_query",
    "entities": [],
    "results": [],
    "evidence_sources": ["OnSIDES", "SIDER", "DrugBank"],
    "confidence": 0.85,
    "timestamp": "2026-03-07T12:00:00"
}
```

**Note:** This is a hardcoded response, not actual data from the graph.

## Adding Custom Mock Data

If you want to test with specific data, you can:

### Option 1: Modify Test Fixtures

Edit `tests/conftest.py`:

```python
@pytest.fixture
def sample_drug_entity():
    return {
        "id": "aspirin-001",
        "name": "Aspirin",
        "generic_name": "acetylsalicylic acid",
        "drugbank_id": "DB00945"
    }
```

### Option 2: Create Initialization Script

Create `scripts/init_mock_data.py`:

```python
"""Initialize mock database with sample data"""
import asyncio
from src.knowledge_graph.database import db
from src.knowledge_graph.models import DrugEntity, SideEffectEntity

async def init_data():
    await db.connect()
    
    # Create drug
    drug = DrugEntity(
        id="aspirin-001",
        name="Aspirin",
        generic_name="acetylsalicylic acid"
    )
    await db.create_drug_vertex(drug)
    
    # Create side effect
    side_effect = SideEffectEntity(
        id="se-001",
        name="Stomach upset",
        severity="mild"
    )
    await db.create_side_effect_vertex(side_effect)
    
    # Create relationship
    await db.create_causes_edge(
        drug_id="aspirin-001",
        side_effect_id="se-001",
        frequency=0.10,
        confidence=0.90,
        evidence_sources=["FDA", "Clinical trials"]
    )
    
    print("Mock data initialized!")

if __name__ == "__main__":
    asyncio.run(init_data())
```

Run it:
```bash
python scripts/init_mock_data.py
```

### Option 3: Use API Endpoints

Make POST requests to create data:

```bash
# Create a drug (if endpoint exists)
curl -X POST http://localhost:8000/drugs \
  -H "Content-Type: application/json" \
  -d '{
    "id": "drug-123",
    "name": "Metformin",
    "generic_name": "metformin"
  }'
```

## Production vs Mock Mode

### Mock Mode (`USE_MOCK_SERVICES=true`)
- ✅ No AWS credentials needed
- ✅ Fast startup
- ✅ No costs
- ✅ Perfect for development
- ❌ Data not persisted
- ❌ Limited to in-memory storage
- ❌ Some features return hardcoded responses

### Production Mode (`USE_MOCK_SERVICES=false`)
- ✅ Real Neptune graph database
- ✅ Data persistence
- ✅ Full query capabilities
- ✅ Scalable storage
- ❌ Requires AWS credentials
- ❌ Incurs AWS costs
- ❌ More complex setup

## Testing with Swagger UI

1. **Start the server:**
   ```bash
   ./scripts/run_local.sh
   ```

2. **Open Swagger UI:**
   ```
   http://localhost:8000/docs
   ```

3. **Try endpoints:**
   - `GET /health` - Check server status
   - `POST /query/process` - Submit a health question
   - `GET /query/explain/{query_id}` - Get query explanation

4. **Expected behavior:**
   - All endpoints return responses
   - Responses are mock/hardcoded data
   - No actual graph traversal occurs
   - Perfect for testing API structure and integration

## Limitations of Mock Mode

1. **No Real Graph Queries**: Most endpoints return predefined responses
2. **No Data Persistence**: Data lost on server restart
3. **Limited Relationships**: Can't test complex graph traversals
4. **Simplified Logic**: Some business logic may be simplified

## When to Use Real Database

Switch to production mode when you need:
- Persistent data storage
- Complex graph queries
- Real medical knowledge graph
- Production deployment
- Performance testing at scale

## Summary

The mock system provides a **zero-setup development environment** where:
- Data lives in Python dictionaries during runtime
- No external dependencies required
- Perfect for API development and testing
- Easy to add custom test data
- Seamless transition to production when ready

For most development tasks, mock mode is sufficient. Only switch to production mode when you need real data persistence or complex graph operations.
