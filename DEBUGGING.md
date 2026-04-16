# Bot Debugging Guide

Your bot now has **comprehensive logging** to help identify issues. Here's how to debug:

## 📋 Setup Checklist

### 1️⃣ **Environment Variables** 
Make sure all required variables are set:

```bash
✅ RUBIKA_BOT_TOKEN      - Your bot token from @BotFather
✅ RUBIKA_API_URL         - Should be: https://botapi.rubika.ir/v3
✅ GEMINI_API_KEY         - Your Google Gemini API key
✅ WEBHOOK_URL            - Your app URL (e.g., https://app.onrender.com)
✅ WEBHOOK_SECRET         - Random secret string
✅ PORT                   - Usually 5000
```

**Check with:**
```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('RUBIKA_BOT_TOKEN:', os.getenv('RUBIKA_BOT_TOKEN')[:10]+'...' if os.getenv('RUBIKA_BOT_TOKEN') else 'NOT SET')"
```

### 2️⃣ **Run Locally**
Test locally first before deploying:

```bash
# Install dependencies
pip install -r requirements.txt

# Run bot
python main.py
```

You should see startup logs like:
```
============================================================
🚀 Starting Rubika Gemini Bot...
============================================================
🔑 Bot Token: abc123def...***
📡 API URL: https://botapi.rubika.ir/v3
🌐 Webhook URL: https://your-app.com/webhook
🔐 Webhook Secret: secre...***
⚙️  Gemini Model: gemini-1.5-flash
🚪 Port: 5000
============================================================
✅ Bot started! Listening for updates...
============================================================
```

## 🧪 Testing the Bot

### Method 1: Run Test Script Locally
```bash
# Terminal 1: Start bot
python main.py

# Terminal 2: Run tests
python test_webhook.py
```

This will simulate:
- ✅ Health check (GET /)
- ✅ /start command
- ✅ Regular message

Watch the bot logs for:
```
📡 Webhook received: /webhook?secret=...
📦 Data received: {...}
📌 Update type: NewMessage
👤 User: user_test_123, Chat: test_chat_123, Text: /start
✨ Registering new user: user_test_123
🚀 User sent /start
📤 Sending message to user_test_123: 👋 Hello test_chat_123!...
✅ Message sent successfully
```

### Method 2: Send Message on Rubika (If Deployed)
1. Find your bot on Rubika
2. Send `/start`
3. Check logs on Render dashboard

## 🔍 Common Issues & Solutions

### ❌ Issue: "Bot doesn't respond"

**Check #1: Environment Variables**
```
⚠️  Bot Token NOT SET!
⚠️  Webhook URL NOT SET!
```
👉 Solution: Add all env vars to `.env` or deployment platform

**Check #2: Webhook Not Set Up**
Look for in logs:
```
❌ NewMessage webhook failed: {...}
❌ GetSelectionItem webhook failed: {...}
```
👉 Solution: 
- Verify bot token is correct
- Check internet connection
- Wait 10 seconds and restart bot

**Check #3: Webhook Secret Mismatch**
```
⚠️  Invalid webhook secret: wrong_secret
```
👉 Solution: 
- Use same secret in `.env` and bot requests
- Check for typos/spaces

**Check #4: Gemini API Error**
```
❌ Gemini error for user user_123: ...
```
👉 Solution:
- Verify GEMINI_API_KEY is correct
- Check Google AI Studio quota
- Verify model name (gemini-1.5-flash)

### ❌ Issue: "Webhook not being called"

1. **Check if Render is running:**
   ```bash
   curl https://your-app-name.onrender.com/
   ```
   Should return:
   ```json
   {"status": "running", "bot": "Rubika Gemini Bot", "users": 0}
   ```

2. **Verify webhook endpoint:**
   ```bash
   curl -X POST https://your-app-name.onrender.com/webhook?secret=YOUR_SECRET \
     -H "Content-Type: application/json" \
     -d '{"update":{"type":"NewMessage","chat_id":"test","new_message":{"sender_id":"user1","text":"/start"}}}'
   ```

3. **Check Render logs:**
   - Go to Render dashboard
   - Click on your app
   - View logs in real-time
   - Look for: `🚀 Starting Rubika Gemini Bot...`

## 📊 Log Levels

The bot logs different information at different levels:

### 🟢 INFO (Important events)
```
✅ Message sent successfully
🚀 User sent /start
💬 Sending to Gemini for user...
```

### 🟡 DEBUG (Detailed info)
```
🔗 Rubika API call: sendMessage
📊 Rubika response: 200
```

### 🔴 ERROR (Problems)
```
❌ Rubika API error [sendMessage]: timeout
❌ Error processing update: ...
```

To see DEBUG logs, add to `main.py`:
```python
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
```

## 🛠️ Troubleshooting Steps

**If bot doesn't respond:**

1. ✅ Check startup logs for errors
   ```bash
   # Local: Watch terminal where you ran `python main.py`
   # Render: Dashboard > Logs
   ```

2. ✅ Verify all env vars are set
   ```bash
   grep -E "RUBIKA|WEBHOOK|GEMINI" .env
   ```

3. ✅ Test health endpoint
   ```bash
   curl https://your-app-name.onrender.com/
   ```

4. ✅ Check webhook was registered
   Look for logs:
   ```
   ✅ Webhook set for NewMessage: ...
   ✅ Webhook set for GetSelectionItem: ...
   ```

5. ✅ Run local test
   ```bash
   python test_webhook.py
   ```

6. ✅ Check Gemini API
   - Go to https://ai.google.dev
   - Verify API key works
   - Check quota/rate limits

7. ✅ Check Rubika bot token
   - Ask @BotFather on Rubika
   - Get a new token if unsure

## 📝 What to Share When Asking for Help

If still stuck, share:

```
1. Bot startup logs (first 50 lines)
2. Output of test_webhook.py
3. Render dashboard logs (last 100 lines)
4. Error messages (full text)
5. .env file (with sensitive values redacted):
   - RUBIKA_BOT_TOKEN: abc...XYZ (redacted)
   - WEBHOOK_URL: https://my-app.onrender.com
   - WEBHOOK_SECRET: secret...123 (redacted)
```

## 🔗 Useful Resources

- **Rubika API Docs**: https://rubika.ir/botapi
- **Rubika Methods**: https://rubika.ir/botapi/methods
- **Google Gemini**: https://ai.google.dev
- **Render Docs**: https://render.com/docs

---

**Questions?** Check the logs! 🔍
