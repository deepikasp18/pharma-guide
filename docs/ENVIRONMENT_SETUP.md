# Environment Setup Guide

This guide will help you set up the required environment variables for running PharmaGuide Health Companion.

## Quick Start

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Generate required security keys (see below)
3. Update the `.env` file with your actual values
4. Never commit the `.env` file to version control!

## Required Environment Variables

### 1. Security Keys

#### SECRET_KEY (Required)
Used for JWT token generation and session management.

**Generate:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Example output:**
```
xK8vN2mP9qR5sT7uW1yZ3aB4cD6eF8gH0iJ2kL4mN6oP8qR0sT2uW4yZ6aB8cD0e
```

Add to `.env`:
```bash
SECRET_KEY=xK8vN2mP9qR5sT7uW1yZ3aB4cD6eF8gH0iJ2kL4mN6oP8qR0sT2uW4yZ6aB8cD0e
```

#### ENCRYPTION_KEY (Required)
Used for AES-256 encryption of PII/PHI data.

**Generate:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Example output:**
```
zK8vN2mP9qR5sT7uW1yZ3aB4cD6eF8gH0iJ2kL4mN6o=
```

Add to `.env`:
```bash
ENCRYPTION_KEY=zK8vN2mP9qR5sT7uW1yZ3aB4cD6eF8gH0iJ2kL4mN6o=
```

### 2. AWS Configuration

#### For Production (AWS Neptune)

```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
NEPTUNE_ENDPOINT=your-cluster.cluster-xxxxx.us-east-1.neptune.amazonaws.com
NEPTUNE_PORT=8182
```

#### For Local Development (Mock/LocalStack)

```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
NEPTUNE_ENDPOINT=localhost
NEPTUNE_PORT=8182
USE_MOCK_SERVICES=true
```

### 3. OpenSearch Configuration

#### For Production

```bash
OPENSEARCH_HOST=search-pharmaguide-xxxxx.us-east-1.es.amazonaws.com
OPENSEARCH_PORT=443
OPENSEARCH_USE_SSL=true
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=your_password_here
```

#### For Local Development

```bash
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
OPENSEARCH_USE_SSL=false
```

## Optional Configuration

### NLP Models

Install spaCy model:
```bash
python -m spacy download en_core_web_sm
```

For medical NER (optional):
```bash
uv pip install scispacy
uv pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.1/en_ner_bc5cdr_md-0.5.1.tar.gz
```

Then set:
```bash
SPACY_MODEL=en_ner_bc5cdr_md
```

### Monitoring & Observability

#### Sentry (Error Tracking)
```bash
SENTRY_DSN=https://your_key@sentry.io/your_project_id
```

#### Prometheus (Metrics)
```bash
ENABLE_METRICS=true
METRICS_PORT=9090
```

#### OpenTelemetry (Distributed Tracing)
```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=pharmaguide-api
```

### Email Notifications

#### Gmail SMTP
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=noreply@pharmaguide.com
```

**Note:** For Gmail, you need to create an [App Password](https://support.google.com/accounts/answer/185833).

### SMS Notifications (Twilio)

```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890
```

## Environment-Specific Configurations

### Development Environment

```bash
ENVIRONMENT=development
LOG_LEVEL=DEBUG
DEBUG=true
RELOAD=true
ENABLE_DOCS=true
USE_MOCK_SERVICES=true
```

### Staging Environment

```bash
ENVIRONMENT=staging
LOG_LEVEL=INFO
DEBUG=false
RELOAD=false
ENABLE_DOCS=true
USE_MOCK_SERVICES=false
```

### Production Environment

```bash
ENVIRONMENT=production
LOG_LEVEL=WARNING
DEBUG=false
RELOAD=false
ENABLE_DOCS=false
USE_MOCK_SERVICES=false
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

## Testing Configuration

For running tests, you can create a `.env.test` file:

```bash
ENVIRONMENT=test
USE_MOCK_SERVICES=true
NEPTUNE_ENDPOINT=localhost
NEPTUNE_PORT=8182
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
LOG_LEVEL=ERROR
HYPOTHESIS_MAX_EXAMPLES=100
```

Then run tests with:
```bash
export $(cat .env.test | xargs) && pytest tests/
```

Or use the test configuration in pytest:
```bash
pytest tests/ --envfile=.env.test
```

## Verification

After setting up your environment, verify the configuration:

```bash
# Check if all required variables are set
python -c "from src.config import settings; print('Environment:', settings.ENVIRONMENT)"

# Test database connection
python -c "from src.knowledge_graph.database import KnowledgeGraphDatabase; print('Database config OK')"

# Test encryption service
python -c "from src.security.encryption_service import create_encryption_service; svc = create_encryption_service(); print('Encryption OK')"
```

## Security Best Practices

1. **Never commit `.env` files** - They contain sensitive credentials
2. **Use different keys for each environment** - Development, staging, and production should have unique keys
3. **Rotate keys regularly** - Especially in production environments
4. **Use AWS Secrets Manager or similar** - For production deployments
5. **Limit AWS IAM permissions** - Use principle of least privilege
6. **Enable MFA** - For AWS accounts and critical services
7. **Monitor access logs** - Set up alerts for suspicious activity

## Troubleshooting

### "Environment variable not found" error

Make sure you've:
1. Created the `.env` file from `.env.example`
2. Set all required variables
3. Restarted your application after changing `.env`

### "Invalid encryption key" error

The encryption key must be a valid Fernet key (base64-encoded 32 bytes). Regenerate using:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### "Cannot connect to Neptune" error

For local development:
1. Set `USE_MOCK_SERVICES=true` in `.env`
2. Or run a local Gremlin server
3. Or use the test fixtures that mock the database

### "spaCy model not found" error

Install the required model:
```bash
python -m spacy download en_core_web_sm
```

## Additional Resources

- [AWS Neptune Documentation](https://docs.aws.amazon.com/neptune/)
- [OpenSearch Documentation](https://opensearch.org/docs/)
- [FastAPI Configuration](https://fastapi.tiangolo.com/advanced/settings/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Cryptography Library](https://cryptography.io/)
