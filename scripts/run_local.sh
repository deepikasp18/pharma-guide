#!/bin/bash

# Run PharmaGuide in local development mode (no AWS required)

set -e

echo "=========================================="
echo "Starting PharmaGuide (Local Mode)"
echo "=========================================="
echo ""

# Check if .env.local exists
if [ ! -f .env.local ]; then
    echo "❌ .env.local file not found!"
    echo ""
    echo "Please run setup first:"
    echo "  ./scripts/setup_local_dev.sh"
    echo ""
    exit 1
fi

# Load environment variables
echo "📋 Loading environment from .env.local..."
export $(cat .env.local | grep -v '^#' | xargs)
echo "✅ Environment loaded"
echo ""

# Verify mock mode is enabled
if [ "$USE_MOCK_SERVICES" != "true" ]; then
    echo "⚠️  Warning: USE_MOCK_SERVICES is not set to 'true'"
    echo "   This may require AWS credentials."
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled. Set USE_MOCK_SERVICES=true in .env.local"
        exit 0
    fi
fi

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ uv not found. Please install uv: https://github.com/astral-sh/uv"
    exit 1
fi

# Display configuration
echo "Configuration:"
echo "  Environment: $ENVIRONMENT"
echo "  Mock Services: $USE_MOCK_SERVICES"
echo "  Log Level: $LOG_LEVEL"
echo "  API Port: ${API_PORT:-8000}"
echo ""

# Start the server
echo "🚀 Starting PharmaGuide API server..."
echo ""
echo "API will be available at:"
echo "  📍 http://localhost:${API_PORT:-8000}"
echo "  📚 API Docs: http://localhost:${API_PORT:-8000}/docs"
echo "  🏥 Health Check: http://localhost:${API_PORT:-8000}/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "=========================================="
echo ""

# Run the application with auto-reload
uv run uvicorn src.main:app \
    --reload \
    --host ${API_HOST:-0.0.0.0} \
    --port ${API_PORT:-8000} \
    --log-level ${LOG_LEVEL:-info}
