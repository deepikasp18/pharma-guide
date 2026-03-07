# Google Gemini Setup Guide

## Why Gemini?

Google Gemini offers several advantages over OpenAI:
- ✅ **Free tier available** - 60 requests per minute for free
- ✅ **No credit card required** for free tier
- ✅ **Fast and capable** - Gemini 1.5 Flash is very fast
- ✅ **Cost-effective** - Even paid tier is cheaper than OpenAI
- ✅ **Good quality** - Comparable to GPT-3.5-turbo

## Step 1: Get Your Gemini API Key

1. Go to **Google AI Studio**: https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Click **"Get API Key"** or **"Create API Key"**
4. Click **"Create API key in new project"** (or select existing project)
5. Copy the API key (starts with `AIza...`)

**That's it!** No credit card required for the free tier.

## Step 2: Configure Your Environment

Add to your `.env` file:

```bash
GEMINI_API_KEY=AIzaSy...your-actual-key-here
GEMINI_MODEL=models/gemini-3-flash-preview
```

## Step 3: Install the Package

```bash
# Already done if you followed the setup
uv pip install google-generativeai
```

## Step 4: Test It

```bash
python3 test_llm_integration.py
```

You should see:
```
✓ Gemini API key found - will use LLM
Generating response...
RESPONSE:
[Natural language response from Gemini]
```

## Free Tier Limits

### Gemini 1.5 Flash (Recommended)
- **Rate limit:** 15 requests per minute (RPM)
- **Daily limit:** 1,500 requests per day
- **Token limit:** 1 million tokens per minute
- **Cost:** FREE

### Gemini 1.5 Pro
- **Rate limit:** 2 requests per minute (RPM)
- **Daily limit:** 50 requests per day
- **Token limit:** 32,000 tokens per minute
- **Cost:** FREE

**For most applications, the free tier is more than enough!**

## Pricing (If You Need More)

If you exceed free tier limits, paid pricing is very affordable:

### Gemini 1.5 Flash
- **Input:** $0.075 per 1M tokens
- **Output:** $0.30 per 1M tokens
- **Typical query:** ~$0.0001 (10x cheaper than GPT-3.5-turbo!)

### Gemini 1.5 Pro
- **Input:** $1.25 per 1M tokens
- **Output:** $5.00 per 1M tokens
- **Typical query:** ~$0.002

## Comparison: Gemini vs OpenAI

| Feature | Gemini 1.5 Flash | GPT-3.5-turbo | GPT-4 |
|---------|------------------|---------------|-------|
| Free Tier | ✅ Yes (15 RPM) | ❌ No | ❌ No |
| Cost/Query | $0.0001 | $0.001 | $0.03 |
| Speed | ⚡ Very Fast | 🚀 Fast | 🐢 Slow |
| Quality | Good | Good | Excellent |
| Context | 1M tokens | 16K tokens | 128K tokens |

**Winner for this use case:** Gemini 1.5 Flash 🏆

## Testing Your Setup

### Test 1: Check API Key
```bash
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print('API Key:', os.getenv('GEMINI_API_KEY')[:20] + '...')"
```

### Test 2: Test Gemini Connection
```bash
python3 -c "
import google.generativeai as genai
import os
from dotenv import load_dotenv
load_dotenv()
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
response = client.models.generate_content(
    model='models/gemini-3-flash-preview',
    contents=genai.types.Part.from_text(text='Say hello!')
)
print(response.text)
"
```

### Test 3: Full Integration Test
```bash
python3 test_llm_integration.py
```

## Example Response

With Gemini configured, you'll get responses like:

```
Aspirin is a commonly used medication, but it's important to be aware of 
its potential side effects. Based on data from OnSIDES, SIDER, and DrugBank:

Common Side Effects (10-25% of users):
• Stomach upset - This can include discomfort, nausea, or indigestion. 
  Taking aspirin with food or milk can help reduce this.

Less Common but Serious (1-10%):
• Increased bleeding risk - Aspirin affects blood clotting, so watch for 
  unusual bruising or bleeding, especially with prolonged use.

Rare but Important (<1%):
• Allergic reactions - Symptoms may include rash, itching, swelling, or 
  difficulty breathing. Seek immediate medical attention if these occur.

This information is for educational purposes only. Please consult your 
healthcare provider for personalized medical advice about aspirin use.
```

## Troubleshooting

### "GEMINI_API_KEY not found"
- Make sure you added it to `.env`
- Run `source .env` or restart your terminal
- Check the key doesn't have extra spaces

### "API key not valid"
- Verify the key at https://makersuite.google.com/app/apikey
- Make sure you copied the entire key
- Try generating a new key

### "Quota exceeded"
- Free tier: 15 requests per minute
- Wait a minute and try again
- Consider upgrading to paid tier if needed

### "Module not found: google.generativeai"
```bash
uv pip install google-generativeai
```

## Rate Limiting Best Practices

To stay within free tier limits:

1. **Cache responses** for common queries
2. **Implement request queuing** if you expect high traffic
3. **Use fallback templates** when rate limited (already implemented!)
4. **Monitor usage** in Google Cloud Console

## Monitoring Usage

1. Go to https://console.cloud.google.com/
2. Select your project
3. Navigate to "APIs & Services" → "Dashboard"
4. View Gemini API usage statistics

## Upgrading to Paid Tier

If you need more than the free tier:

1. Go to https://console.cloud.google.com/billing
2. Enable billing for your project
3. Set up budget alerts
4. Limits automatically increase

**Cost estimate for 10,000 queries/day:**
- Gemini 1.5 Flash: ~$1/day (~$30/month)
- GPT-3.5-turbo: ~$10/day (~$300/month)

**Gemini is 10x cheaper!** 💰

## Security Best Practices

- ✅ Store API key in `.env` (never commit to git)
- ✅ Use environment variables in production
- ✅ Rotate keys periodically
- ✅ Set up API key restrictions in Google Cloud Console
- ✅ Monitor usage for unusual activity

## Next Steps

1. ✅ Get your Gemini API key
2. ✅ Add to `.env` file
3. ✅ Run `python3 test_llm_integration.py`
4. ✅ Start your API server
5. ✅ Test the `/api/query/process` endpoint

## Support

- **Gemini Documentation:** https://ai.google.dev/docs
- **API Reference:** https://ai.google.dev/api/python
- **Get API Key:** https://makersuite.google.com/app/apikey
- **Pricing:** https://ai.google.dev/pricing

---

**Status:** Ready to use with free tier! 🎉  
**No credit card required** ✅  
**Cost:** $0 for most use cases 💰
