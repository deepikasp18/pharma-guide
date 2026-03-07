# How to Run the System

## Quick Commands

### Test LLM Integration
```bash
./.venv/bin/python test_llm_integration.py
```

### Start API Server
```bash
./.venv/bin/python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Test API Endpoint
```bash
# Register a user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "full_name": "Test User"
  }'

# Login and get token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'

# Use the token from login response
export TOKEN="your_token_here"

# Query the API
curl -X POST http://localhost:8000/api/query/process \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "What are the side effects of aspirin?"}'
```

## Important Notes

### Always Use venv Python!
❌ **Don't use:** `python3` or `python`  
✅ **Use:** `./venv/bin/python`

Or activate venv first:
```bash
source venv/bin/activate
python test_llm_integration.py
```

### Check Your Configuration
```bash
# Verify API key is set
grep GEMINI_API_KEY .env

# Should show:
# GEMINI_API_KEY=AIzaSy...your-key-here
# GEMINI_MODEL=models/gemini-3-flash-preview
```

## Troubleshooting

### "Module not found" errors
You're using system Python instead of venv Python.
```bash
# Use this:
./venv/bin/python test_llm_integration.py
```

### "Gemini API key not found"
Check your `.env` file has the API key set.
```bash
cat .env | grep GEMINI_API_KEY
```

### "Model not found" error
Update the model name in `.env`:
```bash
GEMINI_MODEL=models/gemini-3-flash-preview
```

### Rate limit exceeded
Free tier: 15 requests/minute. Wait a bit and try again.

## Available Models

Fast and recommended:
- `models/gemini-3-flash-preview` (recommended - newest!)
- `models/gemini-flash-latest` (stable)
- `models/gemini-flash-lite-latest` (lighter)

High quality:
- `models/gemini-2.5-pro`
- `models/gemini-pro-latest`

## System Status Check

```bash
# 1. Check venv is active
which python
# Should show: /path/to/pharma-guide/venv/bin/python

# 2. Check Gemini package
./venv/bin/python -c "from google import genai; print('✓ Gemini ready')"

# 3. Check API key
./venv/bin/python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✓ API key:', os.getenv('GEMINI_API_KEY')[:20] + '...')"

# 4. Run test
./venv/bin/python test_llm_integration.py
```

## Production Deployment

```bash
# Install dependencies
uv sync

# Set environment variables
export GEMINI_API_KEY=your_key_here
export GEMINI_MODEL=models/gemini-3-flash-preview
export USE_REAL_LOGIC=true

# Start server (production)
./venv/bin/python -m uvicorn src.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4

# Or with gunicorn
gunicorn src.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

## Monitoring

### Check API Usage
Visit: https://console.cloud.google.com/

### View Logs
```bash
# If using systemd
journalctl -u pharmaguide -f

# If using Docker
docker logs -f pharmaguide

# If running directly
# Logs go to stdout
```

## Quick Reference

| Task | Command |
|------|---------|
| Test LLM | `./venv/bin/python test_llm_integration.py` |
| Start API | `./venv/bin/python -m uvicorn src.main:app --reload` |
| Check config | `cat .env \| grep GEMINI` |
| Install deps | `uv sync` |
| Activate venv | `source venv/bin/activate` |

## Support

- **Setup:** See `GEMINI_SETUP.md`
- **Quick Start:** See `GEMINI_QUICK_START.md`
- **Success Story:** See `SUCCESS_SUMMARY.md`
- **Get API Key:** See `GET_GEMINI_KEY.md`

---

**Remember:** Always use `./venv/bin/python` or activate venv first!
