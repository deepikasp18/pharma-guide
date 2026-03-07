# Gemini Quick Start (2 Minutes)

## 🚀 Get Started in 3 Steps

### 1. Get API Key (1 minute)
```
Visit: https://makersuite.google.com/app/apikey
Click: "Create API Key"
Copy: AIzaSy...
```

### 2. Add to .env (30 seconds)
```bash
GEMINI_API_KEY=AIzaSy...your-key-here
GEMINI_MODEL=models/gemini-3-flash-preview
```

### 3. Test (30 seconds)
```bash
python3 test_llm_integration.py
```

## ✅ Done!

Your system now uses Google Gemini for natural language responses.

## 💰 Cost

- **Free tier:** 15 requests/minute
- **No credit card required**
- **Paid tier:** 10x cheaper than OpenAI

## 📊 What You Get

### Before (Templates)
```
Here are the known side effects of aspirin:

**Major Side Effects:**
- Bleeding risk (uncommon (1-10%))
- Allergic reaction (rare (<1%))
```

### After (Gemini)
```
Aspirin can cause several side effects that you should be aware of. 
The most common is stomach upset, occurring in 10-25% of users, which 
can often be managed by taking the medication with food.

More serious but less common side effects include increased bleeding 
risk (1-10% of users) and allergic reactions (<1%). If you experience 
unusual symptoms, seek medical attention immediately.

This information is based on evidence from OnSIDES, SIDER, and DrugBank.
```

## 🎯 Key Benefits

✅ More natural, conversational responses  
✅ Better user experience  
✅ Free tier available  
✅ 10x cheaper than OpenAI  
✅ No credit card required  
✅ Fast response times  

## 🔧 Troubleshooting

### No API key?
System uses template fallback (still works!)

### Rate limit?
Free tier: 15 requests/minute. Wait a bit.

### Import error?
```bash
uv pip install google-generativeai
```

## 📚 More Info

- **Full Setup:** `GEMINI_SETUP.md`
- **Get API Key:** `GET_GEMINI_KEY.md`
- **Migration Details:** `MIGRATION_TO_GEMINI.md`

---

**Time to setup:** 2 minutes  
**Cost:** Free  
**Difficulty:** Easy 😊
