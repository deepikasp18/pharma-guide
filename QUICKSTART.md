# PharmaGuide Quick Start Guide

## 🚀 Get Started in 3 Steps (No AWS Required!)

### Step 1: Setup
```bash
./scripts/setup_local_dev.sh
```

### Step 2: Run
```bash
./scripts/run_local.sh
```

### Step 3: Test
Open your browser: http://localhost:8000/docs

**Note:** The API uses in-memory mock data. See [Mock Data Guide](docs/MOCK_DATA_GUIDE.md) to understand how it works.

---

## That's It! 🎉

You now have PharmaGuide running locally with:
- ✅ All 388 tests passing
- ✅ Full API functionality
- ✅ Mock services (no AWS needed)
- ✅ Interactive API documentation

---

## What You Can Do Now

### 1. Explore the API
Visit http://localhost:8000/docs to see all available endpoints:
- Query processing
- Patient management
- Drug interaction analysis
- Side effect retrieval
- Alert generation

### 2. Run Tests
```bash
export USE_MOCK_SERVICES=true
uv run pytest tests/ -v
```

### 3. Try Example Queries

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Process a Query:**
```bash
curl -X POST http://localhost:8000/query/process \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the side effects of aspirin?",
    "patient_id": "test_patient_123"
  }'
```

**Create Patient Profile:**
```bash
curl -X POST http://localhost:8000/patient/profile \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "test_patient_123",
    "demographics": {
      "age": 45,
      "gender": "male",
      "weight": 75
    },
    "conditions": ["hypertension"],
    "medications": ["lisinopril"]
  }'
```

---

## Common Commands

### Development
```bash
# Start server with auto-reload
./scripts/run_local.sh

# Run tests
uv run pytest tests/ -v

# Run specific tests
uv run pytest tests/test_property_*.py -v

# Check code coverage
uv run pytest tests/ --cov=src --cov-report=html
```

### Configuration
```bash
# Generate new security keys
python scripts/generate_keys.py

# View current configuration
cat .env.local

# Edit configuration
nano .env.local
```

---

## Project Structure

```
pharma-guide/
├── src/
│   ├── api/              # API endpoints
│   ├── knowledge_graph/  # Graph services
│   ├── nlp/              # NLP processing
│   ├── security/         # Security & encryption
│   └── config.py         # Configuration
├── tests/                # All tests (388 total)
├── docs/                 # Documentation
├── scripts/              # Utility scripts
└── .env.local           # Local configuration
```

---

## Need Help?

### Documentation
- [Local Development Guide](docs/LOCAL_DEVELOPMENT.md) - Detailed local setup
- [Mock Data System Guide](docs/MOCK_DATA_GUIDE.md) - How mock data works
- [Environment Setup](docs/ENVIRONMENT_SETUP.md) - Configuration guide
- [Environment Variables](docs/ENVIRONMENT_VARIABLES.md) - Variable reference
- [FAQ](docs/FAQ.md) - Frequently asked questions

### Troubleshooting

**"Module not found" error:**
```bash
uv sync
```

**"spaCy model not found":**
```bash
uv run python -m spacy download en_core_web_sm
```

**"Cannot connect to database":**
Make sure `USE_MOCK_SERVICES=true` in `.env.local`

**Tests failing:**
```bash
export USE_MOCK_SERVICES=true
uv run pytest tests/ -v
```

---

## Next Steps

### For Learning & Development
1. ✅ You're all set! Start exploring the API
2. Read the [documentation](docs/)
3. Modify code and see changes with auto-reload
4. Run tests to verify your changes

### For Production Deployment
1. Set up AWS services (Neptune, OpenSearch)
2. Get AWS credentials
3. Update `.env` with real credentials
4. Set `USE_MOCK_SERVICES=false`
5. Deploy to your infrastructure

See [Environment Setup Guide](docs/ENVIRONMENT_SETUP.md) for production setup.

---

## Features Available Locally

All features work with mock services:

- ✅ Natural language query processing
- ✅ Patient context management
- ✅ Drug interaction detection
- ✅ Side effect analysis
- ✅ Personalized recommendations
- ✅ Temporal tracking
- ✅ Alert generation
- ✅ Security & encryption
- ✅ All 388 tests

---

## Support

- 📚 Documentation: [docs/](docs/)
- 🐛 Issues: GitHub Issues
- 💬 Discussions: GitHub Discussions

---

**Happy Coding! 🎉**

No AWS account, no problem! Start building with PharmaGuide today.
