# Environment Variables Reference

Complete reference of all environment variables used in PharmaGuide Health Companion.

## Quick Reference Table

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | No | `development` | Application environment (development/staging/production) |
| `SECRET_KEY` | Yes | - | JWT token secret key (min 32 chars) |
| `ENCRYPTION_KEY` | Yes | - | Fernet encryption key for PII/PHI |
| `AWS_REGION` | No | `us-east-1` | AWS region for services |
| `AWS_ACCESS_KEY_ID` | Yes* | - | AWS access key (*required for production) |
| `AWS_SECRET_ACCESS_KEY` | Yes* | - | AWS secret key (*required for production) |
| `NEPTUNE_ENDPOINT` | Yes* | - | Neptune cluster endpoint (*required for production) |
| `NEPTUNE_PORT` | No | `8182` | Neptune port |
| `OPENSEARCH_HOST` | No | `localhost` | OpenSearch host |
| `OPENSEARCH_PORT` | No | `9200` | OpenSearch port |
| `USE_MOCK_SERVICES` | No | `false` | Use mock services for testing |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `SPACY_MODEL` | No | `en_core_web_sm` | spaCy NLP model to use |

## Detailed Reference

### Application Configuration

#### ENVIRONMENT
- **Type**: String
- **Required**: No
- **Default**: `development`
- **Options**: `development`, `staging`, `production`
- **Description**: Determines the application environment and affects logging, debugging, and service behavior.

**Example**:
```bash
ENVIRONMENT=production
```

### Security Configuration

#### SECRET_KEY
- **Type**: String
- **Required**: Yes
- **Default**: None (must be set)
- **Format**: URL-safe base64 string, minimum 32 characters
- **Description**: Secret key used for JWT token generation and session management. Must be kept secure and never committed to version control.

**Generate**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Example**:
```bash
SECRET_KEY=xK8vN2mP9qR5sT7uW1yZ3aB4cD6eF8gH0iJ2kL4mN6oP8qR0sT2uW4yZ6aB8cD0e
```

#### ENCRYPTION_KEY
- **Type**: String
- **Required**: Yes
- **Default**: None (must be set)
- **Format**: Base64-encoded Fernet key
- **Description**: Encryption key for AES-256 encryption of PII/PHI data. Required for HIPAA compliance.

**Generate**:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Example**:
```bash
ENCRYPTION_KEY=zK8vN2mP9qR5sT7uW1yZ3aB4cD6eF8gH0iJ2kL4mN6o=
```

### AWS Configuration

#### AWS_REGION
- **Type**: String
- **Required**: No
- **Default**: `us-east-1`
- **Description**: AWS region where Neptune and other services are deployed.

**Example**:
```bash
AWS_REGION=us-west-2
```

#### AWS_ACCESS_KEY_ID
- **Type**: String
- **Required**: Yes (for production)
- **Default**: None
- **Description**: AWS access key ID for authenticating with AWS services.

**Example**:
```bash
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
```

#### AWS_SECRET_ACCESS_KEY
- **Type**: String
- **Required**: Yes (for production)
- **Default**: None
- **Description**: AWS secret access key for authenticating with AWS services.

**Example**:
```bash
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

### Database Configuration

#### NEPTUNE_ENDPOINT
- **Type**: String
- **Required**: Yes (for production)
- **Default**: None
- **Format**: Hostname without protocol (no `https://`)
- **Description**: Amazon Neptune cluster endpoint for knowledge graph database.

**Example**:
```bash
NEPTUNE_ENDPOINT=your-cluster.cluster-xxxxx.us-east-1.neptune.amazonaws.com
```

**Local Development**:
```bash
NEPTUNE_ENDPOINT=localhost
```

#### NEPTUNE_PORT
- **Type**: Integer
- **Required**: No
- **Default**: `8182`
- **Description**: Port for Neptune/Gremlin server connection.

**Example**:
```bash
NEPTUNE_PORT=8182
```

### Search Configuration

#### OPENSEARCH_HOST
- **Type**: String
- **Required**: No
- **Default**: `localhost`
- **Description**: OpenSearch/Elasticsearch host for full-text search.

**Example**:
```bash
OPENSEARCH_HOST=search-pharmaguide-xxxxx.us-east-1.es.amazonaws.com
```

#### OPENSEARCH_PORT
- **Type**: Integer
- **Required**: No
- **Default**: `9200`
- **Description**: OpenSearch port.

**Example**:
```bash
OPENSEARCH_PORT=443
```

### Testing Configuration

#### USE_MOCK_SERVICES
- **Type**: Boolean
- **Required**: No
- **Default**: `false`
- **Options**: `true`, `false`
- **Description**: When true, uses mock implementations of external services for testing.

**Example**:
```bash
USE_MOCK_SERVICES=true
```

### Logging Configuration

#### LOG_LEVEL
- **Type**: String
- **Required**: No
- **Default**: `INFO`
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Description**: Minimum logging level for application logs.

**Example**:
```bash
LOG_LEVEL=DEBUG
```

### NLP Configuration

#### SPACY_MODEL
- **Type**: String
- **Required**: No
- **Default**: `en_core_web_sm`
- **Options**: `en_core_web_sm`, `en_core_web_md`, `en_core_web_lg`, `en_ner_bc5cdr_md`
- **Description**: spaCy model to use for NLP processing.

**Example**:
```bash
SPACY_MODEL=en_core_web_md
```

## Environment-Specific Configurations

### Development Environment

Recommended settings for local development:

```bash
ENVIRONMENT=development
LOG_LEVEL=DEBUG
USE_MOCK_SERVICES=true
NEPTUNE_ENDPOINT=localhost
OPENSEARCH_HOST=localhost
```

### Staging Environment

Recommended settings for staging:

```bash
ENVIRONMENT=staging
LOG_LEVEL=INFO
USE_MOCK_SERVICES=false
# Real AWS credentials and endpoints
```

### Production Environment

Recommended settings for production:

```bash
ENVIRONMENT=production
LOG_LEVEL=WARNING
USE_MOCK_SERVICES=false
# Real AWS credentials and endpoints
# Use AWS Secrets Manager for sensitive values
```

## Validation

The application validates environment variables on startup. Missing required variables will cause the application to fail with a clear error message.

To validate your configuration:

```bash
python -c "from src.config import settings; print('Configuration valid')"
```

## Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use different keys** for each environment
3. **Rotate keys regularly** in production
4. **Use AWS Secrets Manager** for production secrets
5. **Limit IAM permissions** to minimum required
6. **Enable MFA** on AWS accounts
7. **Monitor access logs** for suspicious activity

## Troubleshooting

### Common Issues

**"SECRET_KEY not set"**
- Generate a key: `python scripts/generate_keys.py`
- Add to `.env` file

**"Cannot connect to Neptune"**
- For local dev: Set `USE_MOCK_SERVICES=true`
- For production: Verify endpoint and credentials

**"spaCy model not found"**
- Install model: `python -m spacy download en_core_web_sm`

## Additional Resources

- [Environment Setup Guide](ENVIRONMENT_SETUP.md) - Step-by-step setup instructions
- [AWS Neptune Documentation](https://docs.aws.amazon.com/neptune/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
