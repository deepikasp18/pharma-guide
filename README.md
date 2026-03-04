# PharmaGuide Health Companion

An AI-powered health companion platform built on a comprehensive medical knowledge graph architecture.

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
- Docker and Docker Compose
- AWS Account (for Neptune)

### Installation

1. Clone the repository
2. Copy `.env.example` to `.env` and configure your settings
3. Install dependencies:
   ```bash
   uv sync
   ```
4. Start the development environment:
   ```bash
   docker-compose up -d
   ```
5. Run the application:
   ```bash
   uv run python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Testing

Run the test suite:
```bash
uv run pytest tests/ -v
```

## API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API documentation.

## License

This project is licensed under the MIT License.