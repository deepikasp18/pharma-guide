# How to Get Your Gemini API Key (2 Minutes)

## Quick Steps

1. **Open this link:** https://makersuite.google.com/app/apikey

2. **Sign in** with your Google account (Gmail)

3. **Click "Get API Key"** or **"Create API Key"**

4. **Click "Create API key in new project"**

5. **Copy the key** - it looks like: `AIzaSyABC123...`

6. **Add to .env file:**
   ```bash
   GEMINI_API_KEY=AIzaSyABC123...your-key-here
   ```

7. **Test it:**
   ```bash
   python3 test_llm_integration.py
   ```

## That's It!

- ✅ No credit card required
- ✅ Free tier: 15 requests/minute
- ✅ Takes 2 minutes
- ✅ Works immediately

## Visual Guide

```
1. Go to: https://makersuite.google.com/app/apikey
   
2. You'll see:
   ┌─────────────────────────────────────┐
   │  Google AI Studio                   │
   │                                     │
   │  [Get API Key]                      │
   └─────────────────────────────────────┘

3. Click "Get API Key", then:
   ┌─────────────────────────────────────┐
   │  Create API key                     │
   │                                     │
   │  ○ Create API key in new project   │
   │  ○ Create API key in existing...   │
   │                                     │
   │  [Create]                           │
   └─────────────────────────────────────┘

4. Copy your key:
   ┌─────────────────────────────────────┐
   │  Your API key                       │
   │                                     │
   │  AIzaSyABC123...                    │
   │                                     │
   │  [Copy]                             │
   └─────────────────────────────────────┘
```

## Add to Your .env File

Open `.env` and update:

```bash
# Change this line:
GEMINI_API_KEY=your_gemini_api_key_here

# To this (with your actual key):
GEMINI_API_KEY=AIzaSyABC123...your-actual-key
```

## Test It Works

```bash
python3 test_llm_integration.py
```

You should see:
```
✓ Gemini API key found - will use LLM
Generating response...
[Natural language response from Gemini]
```

## Need Help?

If the link doesn't work:
1. Go to https://ai.google.dev/
2. Click "Get started" or "Get API key"
3. Follow the prompts

---

**Time required:** 2 minutes  
**Cost:** Free  
**Credit card:** Not required
