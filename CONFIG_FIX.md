# Configuration Fix

## Issue

The API server was failing to start with validation errors:
```
pydantic_core._pydantic_core.ValidationError: 7 validation errors for Settings
api_host: Extra inputs are not permitted
gemini_api_key: Extra inputs are not permitted
gemini_model: Extra inputs are not permitted
...
```

## Root Cause

The `Settings` class in `src/config.py` was missing:
1. Field definitions for Gemini configuration
2. Field definitions for API, logging, and NLP configuration
3. The `extra='ignore'` setting to allow additional .env variables

## Fix Applied

### 1. Updated `src/config.py`

Added missing fields:
```python
# API Configuration
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))
CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# NLP Configuration
SPACY_MODEL: str = os.getenv("SPACY_MODEL", "en_core_web_sm")

# Gemini Configuration
GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "models/gemini-3-flash-preview")
```

Added `extra='ignore'` to model config:
```python
model_config = ConfigDict(
    env_file=".env",
    extra='ignore'  # Allow extra fields from .env
)
```

## Result

✅ Server now starts successfully  
✅ All configuration fields properly defined  
✅ Gemini integration working  

## How to Start the Server

```bash
# Using venv Python
./venv/bin/python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Or activate venv first
source venv/bin/activate
uvicorn src.main:app --reload
```

## Verification

```bash
# Check config loads
./venv/bin/python -c "from src.config import settings; print('✓ Config loaded'); print(f'Gemini model: {settings.GEMINI_MODEL}')"

# Start server
./venv/bin/python -m uvicorn src.main:app --reload
```

Expected output:
```
INFO:     Will watch for changes in these directories: ['/path/to/pharma-guide']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## Status

✅ Configuration fixed  
✅ Server starts successfully  
✅ Ready for testing  

---

**Fixed:** March 8, 2026  
**Issue:** Pydantic validation errors  
**Solution:** Added missing fields and extra='ignore'
