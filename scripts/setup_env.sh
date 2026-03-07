#!/bin/bash

# PharmaGuide Environment Setup Script
# This script helps you set up the environment for running PharmaGuide

set -e

echo "=========================================="
echo "PharmaGuide Environment Setup"
echo "=========================================="
echo ""

# Check if .env already exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled. Existing .env file preserved."
        exit 0
    fi
fi

# Copy .env.example to .env
echo "📋 Creating .env file from .env.example..."
cp .env.example .env
echo "✅ .env file created"
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

# Update .env file with generated keys
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s|SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|g" .env
    sed -i '' "s|ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$ENCRYPTION_KEY|g" .env
else
    # Linux
    sed -i "s|SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|g" .env
    sed -i "s|ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$ENCRYPTION_KEY|g" .env
fi

echo "✅ Security keys generated and added to .env"
echo ""

# Prompt for environment type
echo "📝 Environment Configuration"
echo ""
echo "Select your environment:"
echo "1) Development (local testing with mocks)"
echo "2) Staging (with real services)"
echo "3) Production (full deployment)"
read -p "Enter choice [1-3]: " env_choice

case $env_choice in
    1)
        ENV_TYPE="development"
        USE_MOCKS="true"
        LOG_LEVEL="DEBUG"
        ;;
    2)
        ENV_TYPE="staging"
        USE_MOCKS="false"
        LOG_LEVEL="INFO"
        ;;
    3)
        ENV_TYPE="production"
        USE_MOCKS="false"
        LOG_LEVEL="WARNING"
        ;;
    *)
        ENV_TYPE="development"
        USE_MOCKS="true"
        LOG_LEVEL="DEBUG"
        ;;
esac

# Update environment type
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s|ENVIRONMENT=.*|ENVIRONMENT=$ENV_TYPE|g" .env
    sed -i '' "s|USE_MOCK_SERVICES=.*|USE_MOCK_SERVICES=$USE_MOCKS|g" .env
    sed -i '' "s|LOG_LEVEL=.*|LOG_LEVEL=$LOG_LEVEL|g" .env
else
    sed -i "s|ENVIRONMENT=.*|ENVIRONMENT=$ENV_TYPE|g" .env
    sed -i "s|USE_MOCK_SERVICES=.*|USE_MOCK_SERVICES=$USE_MOCKS|g" .env
    sed -i "s|LOG_LEVEL=.*|LOG_LEVEL=$LOG_LEVEL|g" .env
fi

echo "✅ Environment set to: $ENV_TYPE"
echo ""

# AWS Configuration
if [ "$USE_MOCKS" = "false" ]; then
    echo "🔧 AWS Configuration"
    echo ""
    read -p "Enter AWS Region [us-east-1]: " aws_region
    aws_region=${aws_region:-us-east-1}
    
    read -p "Enter AWS Access Key ID: " aws_key
    read -p "Enter AWS Secret Access Key: " aws_secret
    read -p "Enter Neptune Endpoint: " neptune_endpoint
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|AWS_REGION=.*|AWS_REGION=$aws_region|g" .env
        sed -i '' "s|AWS_ACCESS_KEY_ID=.*|AWS_ACCESS_KEY_ID=$aws_key|g" .env
        sed -i '' "s|AWS_SECRET_ACCESS_KEY=.*|AWS_SECRET_ACCESS_KEY=$aws_secret|g" .env
        sed -i '' "s|NEPTUNE_ENDPOINT=.*|NEPTUNE_ENDPOINT=$neptune_endpoint|g" .env
    else
        sed -i "s|AWS_REGION=.*|AWS_REGION=$aws_region|g" .env
        sed -i "s|AWS_ACCESS_KEY_ID=.*|AWS_ACCESS_KEY_ID=$aws_key|g" .env
        sed -i "s|AWS_SECRET_ACCESS_KEY=.*|AWS_SECRET_ACCESS_KEY=$aws_secret|g" .env
        sed -i "s|NEPTUNE_ENDPOINT=.*|NEPTUNE_ENDPOINT=$neptune_endpoint|g" .env
    fi
    
    echo "✅ AWS configuration updated"
    echo ""
fi

# Install spaCy model
echo "📦 Installing NLP dependencies..."
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
fi
echo ""

# Summary
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Your .env file has been configured with:"
echo "  - Environment: $ENV_TYPE"
echo "  - Security keys: Generated"
echo "  - Mock services: $USE_MOCKS"
echo "  - Log level: $LOG_LEVEL"
echo ""
echo "Next steps:"
echo "  1. Review and update .env file if needed"
echo "  2. Install dependencies: uv sync"
echo "  3. Run tests: uv run pytest tests/"
echo "  4. Start the API: uv run python -m uvicorn src.main:app --reload"
echo ""
echo "📚 For more information, see docs/ENVIRONMENT_SETUP.md"
echo ""
echo "⚠️  IMPORTANT: Never commit your .env file to version control!"
echo ""
