# Local Development Without AWS

This guide explains how to run PharmaGuide locally without AWS services, perfect for free tier accounts or local development.

## Overview

PharmaGuide can run in **mock mode** for local development and testing without requiring:
- AWS Access Keys
- Amazon Neptune
- OpenSearch/Elasticsearch
- Any paid AWS services

## Quick Setup for Local Development

### 1. Create Local Environment File

```bash
# Copy the example
cp .env.example .env.local

# Or use the automated script
./scripts/setup_local_dev.sh
```

### 2. Configure for Local Development

Edit `.env.local` with these settings:

```bash
# =============================================================================
# LOCAL DEVELOPMENT CONFIGURATION (No AWS Required)
# =============================================================================

# Environment
ENVIRONMENT=development

# Use mock services (NO AWS REQUIRED!)
USE_MOCK_SERVICES=true

# Security Keys (generate these)
SECRET_KEY=your_generated_secret_key_here
ENCRYPTION_KEY=your_generated_encryption_key_here

# Mock AWS Configuration (not actually used, but required by config)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=mock_key_not_used
AWS_SECRET_ACCESS_KEY=mock_secret_not_used

# Mock Neptune (not actually used)
NEPTUNE_ENDPOINT=localhost
NEPTUNE_PORT=8182

# Mock OpenSearch (not actually used)
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200

# Logging
LOG_LEVEL=DEBUG

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=*

# NLP Model
SPACY_MODEL=en_core_web_sm
```

### 3. Generate Security Keys

```bash
# Run the key generator
python scripts/generate_keys.py

# Or generate manually:
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
```

### 4. Install Dependencies

```bash
# Install Python dependencies
uv sync

# Install spaCy model
uv run python -m spacy download en_core_web_sm
```

### 5. Run the Application

```bash
# Load local environment and run
export $(cat .env.local | grep -v '^#' | xargs)
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the helper script:
```bash
./scripts/run_local.sh
```

## What Gets Mocked?

When `USE_MOCK_SERVICES=true`, the following services are mocked:

### 1. **Neptune Graph Database**
- All graph queries return mock data
- No actual database connection required
- Data is stored in-memory for the session

### 2. **OpenSearch**
- Search queries return mock results
- No Elasticsearch/OpenSearch instance needed

### 3. **AWS Services**
- No AWS credentials validated
- No actual AWS API calls made

## Running Tests Locally

All 388 tests can run without AWS:

```bash
# Run all tests with mock services
export USE_MOCK_SERVICES=true
uv run pytest tests/ -v

# Run specific test categories
uv run pytest tests/test_property_*.py -v  # Property-based tests
uv run pytest tests/test_*.py -v --ignore=tests/test_property_*.py  # Unit tests

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html
```

## API Testing Locally

Once the server is running, you can test the API:

### 1. Health Check
```bash
curl http://localhost:8000/health
```

### 2. Process a Query
```bash
curl -X POST http://localhost:8000/query/process \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the side effects of aspirin?",
    "patient_id": "test_patient_123"
  }'
```

### 3. Interactive API Docs
Visit: http://localhost:8000/docs

## Alternative: Using Docker for Local Services

If you want to run actual services locally (without AWS), you can use Docker:

### Option 1: Gremlin Server (Neptune Alternative)

```bash
# Run Gremlin Server in Docker
docker run -d \
  --name gremlin-server \
  -p 8182:8182 \
  tinkerpop/gremlin-server:latest

# Update .env.local
NEPTUNE_ENDPOINT=localhost
NEPTUNE_PORT=8182
USE_MOCK_SERVICES=false  # Use real Gremlin server
```

### Option 2: OpenSearch (Local Search)

```bash
# Run OpenSearch in Docker
docker run -d \
  --name opensearch \
  -p 9200:9200 \
  -p 9600:9600 \
  -e "discovery.type=single-node" \
  -e "DISABLE_SECURITY_PLUGIN=true" \
  opensearchproject/opensearch:latest

# Update .env.local
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
USE_MOCK_SERVICES=false  # Use real OpenSearch
```

### Option 3: Docker Compose (All Services)

```bash
# Start all services
docker-compose -f docker-compose.local.yml up -d

# This starts:
# - Gremlin Server (Neptune alternative)
# - OpenSearch
# - PharmaGuide API
```

## Getting AWS Free Tier Access Keys (Optional)

If you want to use real AWS services with free tier:

### 1. Create IAM User

1. Log into AWS Console
2. Go to IAM → Users → Add User
3. User name: `pharmaguide-dev`
4. Access type: ✅ Programmatic access
5. Permissions: Attach policies
   - `AmazonNeptuneReadOnlyAccess` (for Neptune)
   - `AmazonOpenSearchServiceReadOnlyAccess` (for OpenSearch)
6. Create user and **save the credentials**

### 2. Configure AWS CLI (Alternative to Keys in .env)

```bash
# Install AWS CLI
uv pip install awscli

# Configure credentials
aws configure
# AWS Access Key ID: [your key]
# AWS Secret Access Key: [your secret]
# Default region: us-east-1
# Default output format: json
```

When AWS CLI is configured, the application can use those credentials automatically without putting them in `.env`.

### 3. Use AWS Free Tier Services

**Neptune Free Tier:**
- Not available in free tier (paid service)
- Use mock mode or local Gremlin server instead

**OpenSearch Free Tier:**
- 750 hours per month of t2.small.search or t3.small.search instance
- 10GB of EBS storage

**Alternative Free Options:**
- Use AWS Academy or AWS Educate credits
- Use LocalStack for AWS service emulation
- Stick with mock mode for development

## Using LocalStack (AWS Emulation)

LocalStack provides local AWS service emulation:

```bash
# Install LocalStack
uv pip install localstack

# Start LocalStack
localstack start -d

# Configure for LocalStack
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
```

## Troubleshooting

### "AWS credentials not found"
**Solution**: Set `USE_MOCK_SERVICES=true` in your `.env.local`

### "Cannot connect to Neptune"
**Solution**: 
- Ensure `USE_MOCK_SERVICES=true`
- Or run local Gremlin server with Docker

### "spaCy model not found"
**Solution**: 
```bash
uv run python -m spacy download en_core_web_sm
```

### "Tests failing with connection errors"
**Solution**: 
```bash
export USE_MOCK_SERVICES=true
uv run pytest tests/ -v
```

## Development Workflow

Recommended workflow for local development:

```bash
# 1. Set up environment (one time)
./scripts/setup_local_dev.sh

# 2. Start development server
./scripts/run_local.sh

# 3. In another terminal, run tests
export USE_MOCK_SERVICES=true
uv run pytest tests/ -v --watch

# 4. Make changes and test
# Server auto-reloads with --reload flag
# Tests can be re-run as needed

# 5. Test API endpoints
curl http://localhost:8000/docs
```

## Production Deployment

When ready for production:

1. Set up real AWS services (Neptune, OpenSearch)
2. Create IAM user with appropriate permissions
3. Update `.env` with real credentials
4. Set `USE_MOCK_SERVICES=false`
5. Deploy using your preferred method (ECS, EKS, EC2, etc.)

## Summary

**For Local Development (No AWS):**
- ✅ Use `USE_MOCK_SERVICES=true`
- ✅ No AWS credentials needed
- ✅ All 388 tests pass
- ✅ Full API functionality available
- ✅ Perfect for development and testing

**For Production:**
- Set up real AWS services
- Use proper IAM credentials
- Set `USE_MOCK_SERVICES=false`
- Follow security best practices

## Additional Resources

- [Environment Setup Guide](ENVIRONMENT_SETUP.md)
- [Environment Variables Reference](ENVIRONMENT_VARIABLES.md)
- [Docker Documentation](https://docs.docker.com/)
- [LocalStack Documentation](https://docs.localstack.cloud/)
- [AWS Free Tier](https://aws.amazon.com/free/)
