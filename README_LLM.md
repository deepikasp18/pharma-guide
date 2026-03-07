# LLM Integration with Google Gemini

## Overview

The `/api/query/process` endpoint now generates natural language responses using Google Gemini AI instead of returning only structured data.

## Quick Start

### 1. Get Gemini API Key (2 minutes)
Visit: https://makersuite.google.com/app/apikey

### 2. Configure
Add to `.env`:
```bash
GEMINI_API_KEY=AIzaSy...your-key-here
GEMINI_MODEL=models/gemini-3-flash-preview
```

### 3. Test
```bash
python3 test_llm_integration.py
```

## Why Gemini?

- ✅ **Free tier** - 15 requests/minute, no credit card
- ✅ **Fast** - Gemini 1.5 Flash is very quick
- ✅ **Affordable** - 10x cheaper than alternatives
- ✅ **Good quality** - Natural, conversational responses

## Features

- Natural language responses from medical knowledge graph data
- Automatic fallback to template-based responses if Gemini unavailable
- Medical disclaimers and evidence citations included
- Patient context awareness
- No breaking changes to existing API

## Documentation

- `GEMINI_SETUP.md` - Complete setup guide
- `GET_GEMINI_KEY.md` - How to get API key
- `GEMINI_QUICK_START.md` - 2-minute quick start
- `MIGRATION_TO_GEMINI.md` - Migration details from OpenAI

## API Response

The response now includes an `answer` field with natural language:

```json
{
  "query_id": "query_123",
  "original_query": "What are the side effects of aspirin?",
  "intent": "side_effects",
  "entities": [...],
  "results": [...],
  "answer": "Aspirin can cause several side effects...",
  "evidence_sources": ["OnSIDES", "SIDER", "DrugBank"],
  "confidence": 0.85,
  "timestamp": "2024-03-08T10:30:00Z"
}
```

## Cost

### Free Tier (No Credit Card)
- 15 requests per minute
- 1,500 requests per day
- Perfect for development and small deployments

### Paid Tier (If Needed)
- ~$0.0001 per query
- For 10,000 queries/day: ~$1/day = $30/month

## Fallback Behavior

If Gemini is unavailable (no API key, rate limit, error):
- System automatically uses template-based responses
- All functionality preserved
- No errors or failures
- Slightly lower confidence score (0.75 vs 0.85)

## Status

✅ Implementation complete  
✅ Tested and working  
✅ Production ready  
✅ No breaking changes  

## Support

For setup help, see `GEMINI_SETUP.md`
