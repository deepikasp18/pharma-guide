# Quick Setup Guide for LLM Integration

## Step 1: Install Google Genai Package

```bash
# Using uv (recommended)
uv pip install google-genai

# Or using pip
pip install google-genai
```

## Step 2: Get Gemini API Key

1. Go to https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key (starts with `AIza`)

**No credit card required!** Free tier includes 15 requests/minute.

## Step 3: Configure Environment

Edit your `.env` file and add:

```bash
GEMINI_API_KEY=AIzaSy...your-actual-key-here
GEMINI_MODEL=models/gemini-3-flash-preview
```

## Step 4: Test the Integration

```bash
# Run the test script
python test_llm_integration.py
```

You should see a natural language response generated!

## Step 5: Start the API Server

```bash
# Start the server
uvicorn src.main:app --reload

# Or if you have a start script
python -m src.main
```

## Step 6: Test the API Endpoint

```bash
# First, get an auth token (register/login)
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "full_name": "Test User"
  }'

# Then test the query endpoint
curl -X POST http://localhost:8000/api/query/process \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "query": "What are the side effects of aspirin?"
  }'
```

## Troubleshooting

### No Gemini Key?

The system will automatically fall back to template-based responses. You'll still get answers, just not LLM-generated ones.

### Import Error?

Make sure you installed the google-genai package:
```bash
uv pip install google-genai
```

### Rate Limit Error?

Free tier allows 15 requests per minute. Wait a bit and try again.

## What You Get

With LLM integration, responses are:
- ✓ Natural and conversational
- ✓ Contextually aware
- ✓ Include proper medical disclaimers
- ✓ Cite evidence sources
- ✓ Tailored to the specific query

Without LLM (fallback):
- ✓ Still functional
- ✓ Template-based formatting
- ✓ All structured data included
- ✓ Medical disclaimers included

## Why Gemini?

- ✅ **Free tier** - 15 requests/minute, no credit card
- ✅ **Fast** - Gemini 1.5 Flash is very quick
- ✅ **Cheap** - 10x cheaper than OpenAI if you need paid tier
- ✅ **Good quality** - Comparable to GPT-3.5-turbo

## Next Steps

1. Test with different queries
2. Adjust the model in `.env` based on your needs
3. Monitor usage in Google Cloud Console
4. Consider caching for common queries
5. Implement rate limiting for production

For more details, see `GEMINI_SETUP.md`
