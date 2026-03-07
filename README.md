# PharmaGuide Health Companion

An AI-powered health companion platform built on a comprehensive medical knowledge graph architecture.

> **🎉 No AWS Account Required for Development!**  
> Run PharmaGuide locally with mock services - perfect for learning, testing, and development.  
> See [Local Development Guide](docs/LOCAL_DEVELOPMENT.md) for quick setup.

## Overview

PharmaGuide integrates multiple authoritative medical datasets (OnSIDES, SIDER, FAERS, DrugBank, DDInter, Drugs@FDA) to create a unified knowledge representation that enables sophisticated reasoning about medications, drug interactions, side effects, and personalized treatment recommendations.

## Features

- Natural language query processing for medication questions
- Personalized medication insights based on patient profiles
- Real-world evidence integration from multiple medical datasets
- Drug interaction and contraindication detection
- Side effect analysis with demographic correlation
- Temporal tracking and symptom analysis
- HIPAA-compliant security and privacy protection

## Technology Stack

- **Backend**: Python with FastAPI
- **Knowledge Graph**: Amazon Neptune
- **Search Engine**: OpenSearch
- **AI/ML**: spaCy, scikit-learn, transformers
- **Data Processing**: Pandas, NumPy
- **Testing**: pytest, Hypothesis

## Quick Start

### Prerequisites

- Python 3.11+
- uv (Python package manager) - [Install uv](https://github.com/astral-sh/uv)
- **No AWS account required for local development!** ✅

### Local Development (No AWS Required)

Perfect for development and testing without AWS services:

```bash
# 1. Automated setup (recommended)
./scripts/setup_local_dev.sh

# 2. Run the application
./scripts/run_local.sh

# 3. Access the API
# http://localhost:8000/docs
```

That's it! The application runs with mock services - no AWS credentials needed.

See [Local Development Guide](docs/LOCAL_DEVELOPMENT.md) for details.

### Production Setup (With AWS)

For production deployment with real AWS services:

### Production Setup (With AWS)

For production deployment with real AWS services:

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/pharma-guide.git
   cd pharma-guide
   ```

2. **Set up environment variables**
   
   **Option A: Automated setup**
   ```bash
   ./scripts/setup_env.sh
   ```
   
   **Option B: Manual setup**
   ```bash
   cp .env.example .env
   python scripts/generate_keys.py
   # Edit .env and add your AWS credentials
   ```
   
   See [Environment Setup Guide](docs/ENVIRONMENT_SETUP.md) for detailed configuration.

3. **Install dependencies**
   ```bash
   uv sync
   ```

4. **Install NLP models**
   ```bash
   uv run python -m spacy download en_core_web_sm
   ```

5. **Run the application**
   ```bash
   uv run python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Testing

Run the complete test suite (388 tests):
```bash
uv run pytest tests/ -v
```

Run specific test categories:
```bash
# Property-based tests only
uv run pytest tests/test_property_*.py -v

# Unit tests only
uv run pytest tests/ -v --ignore=tests/test_property_*.py

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html
```

### Development

For local development with mock services:
```bash
# Set in .env
USE_MOCK_SERVICES=true
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# Run with auto-reload
uv run uvicorn src.main:app --reload
```

## API Documentation

Once running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Key Endpoints

- `POST /query/process` - Process natural language health questions
- `POST /patient/profile` - Create or update patient profile
- `GET /patient/{patient_id}/context` - Retrieve patient context
- `POST /reasoning/interactions` - Analyze drug interactions
- `POST /alerts/configure` - Configure health alerts
- `GET /alerts/active` - Get active alerts for a patient

## Environment Variables

All required environment variables are documented in:
- `.env.example` - Example configuration with all available options
- `docs/ENVIRONMENT_SETUP.md` - Detailed setup guide with instructions

### Required Variables

```bash
# Security (generate with scripts/generate_keys.py)
SECRET_KEY=your_secret_key_here
ENCRYPTION_KEY=your_encryption_key_here

# AWS & Neptune
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
NEPTUNE_ENDPOINT=your_neptune_endpoint

# OpenSearch
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
```

## Project Structure

```
pharma-guide/
├── src/
│   ├── api/              # FastAPI endpoints and middleware
│   ├── knowledge_graph/  # Graph services and models
│   ├── nlp/              # Natural language processing
│   ├── security/         # Encryption and access control
│   ├── data_processing/  # ETL and data quality
│   └── config.py         # Configuration management
├── tests/
│   ├── test_*.py         # Unit tests
│   └── test_property_*.py # Property-based tests
├── docs/                 # Documentation
├── scripts/              # Utility scripts
├── .env.example          # Environment template
└── pyproject.toml        # Project dependencies
```

## Documentation

- [Full-Stack Development Guide](FULLSTACK_GUIDE.md) - Running frontend + backend together
- [Quick Start Guide](QUICKSTART.md) - Get started in 3 steps
- [Environment Setup Guide](docs/ENVIRONMENT_SETUP.md) - Detailed configuration instructions
- [Environment Variables Reference](docs/ENVIRONMENT_VARIABLES.md) - Complete variable documentation
- [Local Development Guide](docs/LOCAL_DEVELOPMENT.md) - Running without AWS
- [Mock Data System Guide](docs/MOCK_DATA_GUIDE.md) - How mock data works in development
- [FAQ](docs/FAQ.md) - Frequently asked questions
- [Graph Reasoning Engine](docs/graph_reasoning_engine.md) - Knowledge graph architecture
- [Query Translation Service](docs/query_translation_service.md) - NLP to graph queries

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Security

- All PII/PHI data is encrypted using AES-256
- Role-based access control (RBAC) for data access
- Comprehensive audit trails
- HIPAA-compliant security measures

**Security Issues**: Please report security vulnerabilities to security@pharmaguide.com

## License

This project is licensed under the MIT License - see the LICENSE file for details.