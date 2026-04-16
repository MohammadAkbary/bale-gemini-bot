# Rubika Bot Setup Guide

Your bot has been successfully migrated from **Bale** to **Rubika** messenger! 🎉

## What Changed?

✅ **Bale API** → **Rubika API**
✅ **Event structure** updated to match Rubika format
✅ **Button layout** adapted to Rubika's inline_keypad system
✅ **Webhook setup** uses Rubika's `updateBotEndpoints`

## Setup Steps

### 1️⃣ Get Your Rubika Bot Token

1. Open **Rubika** app
2. Contact **@BotFather**
3. Create a new bot
4. Copy the bot token provided

### 2️⃣ Update Environment Variables

Create or update your `.env` file with:

```env
# Rubika Bot Configuration
RUBIKA_BOT_TOKEN=your_bot_token_here

RUBIKA_API_URL=https://botapi.rubika.ir/v3

# Gemini AI (Google)
GEMINI_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-1.5-flash

# Admin Settings
ADMIN_USER_ID=your_rubika_user_id

# Webhook Configuration (e.g., Render)
WEBHOOK_URL=https://your-app-name.onrender.com
WEBHOOK_SECRET=your_random_secret_string

PORT=5000
```

### 3️⃣ Deploy to Render (or Your Host)

If using Render:

1. Push your code to GitHub
2. Connect to Render
3. Set the environment variables in Render dashboard
4. Deploy!

The bot will automatically:

- ✅ Set up webhooks for message events (`NewMessage`)
- ✅ Set up webhooks for button clicks (`GetSelectionItem`)
- ✅ Start handling user interactions

## API Reference

The bot uses these Rubika API methods:

- **`sendMessage`** - Send text with optional inline buttons
- **`getUpdates`** - Long-polling alternative (if not using webhooks)
- **`updateBotEndpoints`** - Register webhook endpoints
- **`editMessageText`** - Edit sent messages
- **`editMessageKeypad`** - Edit inline buttons
- **`deleteMessage`** - Delete messages

## Testing the Bot

1. Send `/start` to the bot → should receive welcome message
2. Send any message → bot responds with Gemini AI answer
3. Admin commands (if `ADMIN_USER_ID` matches):
   - `/admin` - Show admin panel
   - `/stats` - Bot statistics
   - `/broadcast <message>` - Broadcast to all users

## Features

- 💬 **AI Responses** - Powered by Google Gemini
- 🧹 **Chat History** - Per-user conversation memory (last 20 messages)
- 🔐 **Admin Panel** - User management and bot control
- 🔄 **Block/Unblock** - Control user access
- 📊 **Statistics** - Track active users and messages

## Troubleshooting

### Bot not responding?

- ✅ Check if `RUBIKA_BOT_TOKEN` is correct
- ✅ Verify webhook URL is publicly accessible
- ✅ Check logs for errors

### Buttons not working?

- ✅ Ensure webhook setup succeeded (check logs)
- ✅ Rubika requires `GetSelectionItem` webhook for button clicks

### Webhook setup failed?

- ✅ Verify your app is running on correct PORT
- ✅ Check if `WEBHOOK_URL` is accessible from internet
- ✅ Ensure `HTTPS` is enabled

## Need Help?

- **Rubika API Docs**: https://rubika.ir/botapi
- **Rubika Bot Methods**: https://rubika.ir/botapi/methods
- **Google Gemini API**: https://ai.google.dev

---

Happy coding! 🚀
