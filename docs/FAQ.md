# Frequently Asked Questions (FAQ)

## General Questions

### Q: Do I need an AWS account to run PharmaGuide?

**A: No!** PharmaGuide can run completely locally with mock services. This is perfect for:
- Learning and development
- Testing and experimentation
- Running all 388 tests
- Full API functionality

See [Local Development Guide](LOCAL_DEVELOPMENT.md) for setup instructions.

### Q: What's the difference between local and production mode?

**A: Local Mode (Mock Services)**
- No AWS account required
- All services mocked in-memory
- Perfect for development
- All features work
- No costs

**Production Mode (Real Services)**
- Requires AWS account
- Uses real Neptune and OpenSearch
- Scalable and persistent
- Production-ready
- AWS costs apply

### Q: Can I use AWS free tier?

**A: Partially.** AWS free tier includes:
- ✅ OpenSearch: 750 hours/month of t2.small.search
- ❌ Neptune: Not included in free tier (paid service)

**Recommendation**: Use local mock mode for development, then upgrade to paid services for production.

### Q: How do I get AWS access keys?

**A:** If you have an AWS account:
1. Log into AWS Console
2. Go to IAM → Users → Add User
3. Select "Programmatic access"
4. Attach necessary policies
5. Save the Access Key ID and Secret Access Key

**But remember**: You don't need these for local development!

## Setup Questions

### Q: How do I set up for local development?

**A: Three simple steps:**
```bash
# 1. Run setup script
./scripts/setup_local_dev.sh

# 2. Start the server
./scripts/run_local.sh

# 3. Open browser
# http://localhost:8000/docs
```

See [QUICKSTART.md](../QUICKSTART.md) for details.

### Q: What are the minimum requirements?

**A: Very minimal:**
- Python 3.11+
- uv package manager
- 2GB RAM
- 1GB disk space

No AWS, Docker, or other services required for local development.

### Q: How do I generate security keys?

**A: Two options:**

**Option 1: Automated**
```bash
python scripts/generate_keys.py
```

**Option 2: Manual**
```bash
# SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Q: Where do I put the environment variables?

**A: For local development:**
- File: `.env.local`
- Created by: `./scripts/setup_local_dev.sh`
- Or manually: `cp .env.local.example .env.local`

**For production:**
- File: `.env`
- Created by: `cp .env.example .env`
- Add real AWS credentials

## Running Questions

### Q: How do I start the application?

**A: For local development:**
```bash
./scripts/run_local.sh
```

**For production:**
```bash
export $(cat .env | grep -v '^#' | xargs)
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Q: How do I run tests?

**A: All tests:**
```bash
export USE_MOCK_SERVICES=true
uv run pytest tests/ -v
```

**Specific tests:**
```bash
# Property-based tests only
uv run pytest tests/test_property_*.py -v

# Unit tests only
uv run pytest tests/ --ignore=tests/test_property_*.py -v

# With coverage
uv run pytest tests/ --cov=src --cov-report=html
```

### Q: How do I access the API documentation?

**A: Once the server is running:**
- Interactive docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

### Q: Can I use Docker?

**A: Yes!** Docker is optional but supported:

**For local services:**
```bash
# Run Gremlin Server (Neptune alternative)
docker run -d -p 8182:8182 tinkerpop/gremlin-server

# Run OpenSearch
docker run -d -p 9200:9200 opensearchproject/opensearch:latest
```

**For the application:**
```bash
docker-compose up -d
```

## Configuration Questions

### Q: What does USE_MOCK_SERVICES do?

**A:** When set to `true`:
- All AWS services are mocked
- No real database connections
- Data stored in-memory
- Perfect for development
- No AWS credentials needed

When set to `false`:
- Uses real AWS services
- Requires AWS credentials
- Data persisted in Neptune
- Production mode

### Q: How do I switch from local to production?

**A: Update your environment:**

**From:**
```bash
USE_MOCK_SERVICES=true
NEPTUNE_ENDPOINT=localhost
```

**To:**
```bash
USE_MOCK_SERVICES=false
NEPTUNE_ENDPOINT=your-cluster.cluster-xxxxx.us-east-1.neptune.amazonaws.com
AWS_ACCESS_KEY_ID=your_real_key
AWS_SECRET_ACCESS_KEY=your_real_secret
```

### Q: What NLP models are required?

**A: Minimum:**
```bash
python -m spacy download en_core_web_sm
```

**Optional (better accuracy):**
```bash
# Larger model
python -m spacy download en_core_web_md

# Medical NER (requires scispacy)
uv pip install scispacy
uv pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.1/en_ner_bc5cdr_md-0.5.1.tar.gz
```

## Troubleshooting Questions

### Q: "AWS credentials not found" error

**A: Two solutions:**

**Solution 1 (Recommended for local dev):**
```bash
# In .env.local
USE_MOCK_SERVICES=true
```

**Solution 2 (For production):**
```bash
# Add real credentials to .env
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

### Q: "Cannot connect to Neptune" error

**A: Check your configuration:**

**For local development:**
```bash
# In .env.local
USE_MOCK_SERVICES=true
```

**For production:**
- Verify Neptune endpoint is correct
- Check AWS credentials
- Ensure security groups allow connection
- Verify VPC configuration

### Q: "spaCy model not found" error

**A: Install the model:**
```bash
uv run python -m spacy download en_core_web_sm
```

Or set a different model:
```bash
# In .env.local
SPACY_MODEL=en_core_web_md
```

### Q: Tests are failing

**A: Common fixes:**

**1. Ensure mock services are enabled:**
```bash
export USE_MOCK_SERVICES=true
uv run pytest tests/ -v
```

**2. Reinstall dependencies:**
```bash
uv sync
```

**3. Check Python version:**
```bash
python --version  # Should be 3.11+
```

**4. Clear cache:**
```bash
rm -rf .pytest_cache __pycache__ .hypothesis
uv run pytest tests/ -v
```

### Q: "Module not found" error

**A: Install dependencies:**
```bash
uv sync
```

Or if uv is not installed:
```bash
# Install uv first
curl -LsSf https://astral.sh/uv/install.sh | sh

# Then sync dependencies
uv sync
```

### Q: Server won't start

**A: Check these:**

**1. Port already in use:**
```bash
# Change port in .env.local
API_PORT=8001
```

**2. Environment not loaded:**
```bash
export $(cat .env.local | grep -v '^#' | xargs)
```

**3. Dependencies missing:**
```bash
uv sync
```

## Feature Questions

### Q: What features work in mock mode?

**A: All of them!**
- ✅ Natural language query processing
- ✅ Patient context management
- ✅ Drug interaction detection
- ✅ Side effect analysis
- ✅ Personalized recommendations
- ✅ Temporal tracking
- ✅ Alert generation
- ✅ Security & encryption
- ✅ All 388 tests

### Q: How accurate is the mock data?

**A:** Mock data is:
- Realistic and representative
- Suitable for development and testing
- Not for medical decisions
- Replaced with real data in production

### Q: Can I add my own data?

**A: Yes!** 
- In mock mode: Modify test fixtures
- In production: Load data via ETL pipeline
- See `src/data_processing/` for ETL code

### Q: How do I integrate real medical datasets?

**A:** The ETL pipeline supports:
- OnSIDES
- SIDER
- FAERS
- DrugBank
- DDInter
- Drugs@FDA

See `src/data_processing/etl_pipeline.py` for implementation.

## Security Questions

### Q: Is my data secure in mock mode?

**A:** In mock mode:
- Data is in-memory only
- Not persisted to disk
- Encryption still works
- Perfect for testing security features

### Q: How is PII/PHI protected?

**A:** Multiple layers:
- AES-256 encryption at rest and in transit
- Tokenization and pseudonymization
- Role-based access control (RBAC)
- Comprehensive audit trails
- Secure logging (no PII/PHI in logs)

### Q: Is this HIPAA compliant?

**A:** The code implements HIPAA-required security measures:
- ✅ Encryption
- ✅ Access controls
- ✅ Audit trails
- ✅ Data separation

**However**: Full HIPAA compliance requires:
- Proper infrastructure setup
- Business Associate Agreements
- Security policies and procedures
- Regular audits
- Staff training

Consult with compliance experts for production deployment.

### Q: How do I rotate security keys?

**A:**
```bash
# 1. Generate new keys
python scripts/generate_keys.py

# 2. Update .env with new keys
# 3. Restart application
# 4. Re-encrypt existing data (if any)
```

## Performance Questions

### Q: How fast is the mock mode?

**A:** Very fast!
- No network latency
- In-memory operations
- Instant responses
- Perfect for development

### Q: How many requests can it handle?

**A:** In mock mode:
- Limited by your machine
- Typically 100+ req/sec on modern hardware

In production:
- Scales with AWS infrastructure
- Neptune can handle thousands of req/sec
- Use load balancing for high traffic

### Q: Can I run multiple instances?

**A: Yes!**
- Each instance can run independently
- Use different ports
- Load balance in production

## Deployment Questions

### Q: How do I deploy to production?

**A: Several options:**

**1. AWS ECS/Fargate:**
- Containerize the application
- Deploy to ECS
- Connect to Neptune in same VPC

**2. AWS EC2:**
- Launch EC2 instance
- Install dependencies
- Run with systemd or supervisor

**3. Kubernetes:**
- Create Docker image
- Deploy to EKS or other K8s cluster
- Use secrets for credentials

**4. AWS Lambda:**
- Package as Lambda function
- Use API Gateway
- Connect to Neptune via VPC

### Q: What AWS services do I need for production?

**A: Minimum:**
- Amazon Neptune (knowledge graph)
- Amazon OpenSearch (search)
- EC2 or ECS (compute)
- VPC (networking)
- IAM (access management)

**Optional:**
- CloudWatch (monitoring)
- Secrets Manager (credential management)
- CloudFront (CDN)
- Route 53 (DNS)
- ALB (load balancing)

### Q: What are the costs?

**A: Approximate monthly costs:**

**Development (Mock Mode):**
- $0 (runs locally)

**Small Production:**
- Neptune: ~$200-500/month
- OpenSearch: ~$50-100/month
- EC2: ~$20-50/month
- Total: ~$270-650/month

**Large Production:**
- Scales with usage
- Can be $1000+/month

Use AWS Cost Calculator for accurate estimates.

## Contributing Questions

### Q: How can I contribute?

**A:**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `uv run pytest tests/ -v`
5. Submit a pull request

See CONTRIBUTING.md for guidelines.

### Q: How do I report bugs?

**A:**
- GitHub Issues: Preferred method
- Include error messages
- Provide steps to reproduce
- Mention your environment

### Q: Can I use this commercially?

**A:** Yes! MIT License allows:
- Commercial use
- Modification
- Distribution
- Private use

See LICENSE file for full terms.

## Additional Resources

- [Quick Start Guide](../QUICKSTART.md)
- [Local Development Guide](LOCAL_DEVELOPMENT.md)
- [Environment Setup Guide](ENVIRONMENT_SETUP.md)
- [Environment Variables Reference](ENVIRONMENT_VARIABLES.md)
- [API Documentation](http://localhost:8000/docs) (when running)

## Still Have Questions?

- 📚 Check the [documentation](.)
- 🐛 Open an [issue](https://github.com/yourusername/pharma-guide/issues)
- 💬 Start a [discussion](https://github.com/yourusername/pharma-guide/discussions)
