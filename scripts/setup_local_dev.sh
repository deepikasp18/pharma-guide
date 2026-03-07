#!/bin/bash

# PharmaGuide Local Development Setup (No AWS Required)
# This script sets up the environment for local development without AWS services

set -e

echo "=========================================="
echo "PharmaGuide Local Development Setup"
echo "=========================================="
echo ""
echo "This setup does NOT require:"
echo "  ❌ AWS Account"
echo "  ❌ AWS Access Keys"
echo "  ❌ Amazon Neptune"
echo "  ❌ OpenSearch/Elasticsearch"
echo ""
echo "✅ Perfect for local development and testing!"
echo ""

# Check if .env.local already exists
if [ -f .env.local ]; then
    echo "⚠️  .env.local file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled. Existing .env.local file preserved."
        exit 0
    fi
fi

# Create .env.local file
echo "📋 Creating .env.local file for local development..."
cat > .env.local << 'EOF'
# =============================================================================
# LOCAL DEVELOPMENT CONFIGURATION (No AWS Required)
# =============================================================================

# Environment
ENVIRONMENT=development

# Use mock services (NO AWS REQUIRED!)
USE_MOCK_SERVICES=true

# Security Keys (will be generated)
SECRET_KEY=PLACEHOLDER_WILL_BE_REPLACED
ENCRYPTION_KEY=PLACEHOLDER_WILL_BE_REPLACED

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

# Testing
HYPOTHESIS_MAX_EXAMPLES=100
EOF

echo "✅ .env.local file created"
echo ""

# Generate security keys
echo "🔐 Generating security keys..."
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Generate keys using Python
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Update .env.local file with generated keys
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s|SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|g" .env.local
    sed -i '' "s|ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$ENCRYPTION_KEY|g" .env.local
else
    # Linux
    sed -i "s|SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|g" .env.local
    sed -i "s|ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$ENCRYPTION_KEY|g" .env.local
fi

echo "✅ Security keys generated and added to .env.local"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
echo ""

if command -v uv &> /dev/null; then
    echo "Using uv package manager..."
    uv sync
else
    echo "⚠️  uv not found. Please install uv: https://github.com/astral-sh/uv"
    echo "Installation: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

echo ""

# Install spaCy model
echo "📚 Installing NLP model..."
echo ""
read -p "Install spaCy English model? (Y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    if command -v uv &> /dev/null; then
        uv run python -m spacy download en_core_web_sm
    else
        python3 -m spacy download en_core_web_sm
    fi
    echo "✅ spaCy model installed"
else
    echo "⏭️  Skipped spaCy model installation"
    echo "   You can install it later with: python -m spacy download en_core_web_sm"
fi
echo ""

# Summary
echo "=========================================="
echo "✅ Local Development Setup Complete!"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  📁 File: .env.local"
echo "  🔧 Mode: Mock services (no AWS required)"
echo "  🔐 Keys: Generated and configured"
echo "  📊 Log level: DEBUG"
echo ""
echo "Next steps:"
echo ""
echo "  1. Run the application:"
echo "     ./scripts/run_local.sh"
echo ""
echo "  2. Or manually:"
echo "     export \$(cat .env.local | grep -v '^#' | xargs)"
echo "     uv run uvicorn src.main:app --reload"
echo ""
echo "  3. Run tests:"
echo "     export USE_MOCK_SERVICES=true"
echo "     uv run pytest tests/ -v"
echo ""
echo "  4. Access API docs:"
echo "     http://localhost:8000/docs"
echo ""
echo "📚 For more information:"
echo "   - docs/LOCAL_DEVELOPMENT.md"
echo "   - docs/ENVIRONMENT_SETUP.md"
echo ""
echo "🎉 Happy coding! No AWS account needed!"
echo ""
