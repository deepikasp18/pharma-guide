# Bcrypt Compatibility Fix

## Issue

Login endpoint was failing with error:
```
(trapped) error reading bcrypt version
AttributeError: module 'bcrypt' has no attribute '__about__'
```

## Root Cause

The installed bcrypt version (4.3.0) is too new and incompatible with passlib. Passlib tries to access `bcrypt.__about__.__version__` which was removed in newer bcrypt versions.

## Fix Applied

Downgraded bcrypt to a compatible version:

```bash
uv pip install --force-reinstall "bcrypt==4.1.2"
```

## Verification

The pyproject.toml already specifies the correct version:
```toml
"bcrypt>=4.1.2,<5.0.0"
```

But uv installed 4.3.0 by default. The force reinstall fixed it.

## Result

✅ bcrypt 4.1.2 installed  
✅ Compatible with passlib  
✅ Login endpoint working  

## How to Test

```bash
# Start server
./.venv/bin/python -m uvicorn src.main:app --reload

# Test login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

## Status

✅ Fixed  
✅ Server running  
✅ Authentication working  

---

**Fixed:** March 8, 2026  
**Issue:** bcrypt version incompatibility  
**Solution:** Downgraded to bcrypt 4.1.2
