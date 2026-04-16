import os
import json
import logging
import requests
import threading
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

# ─── Load env ────────────────────────────────────────────────────────────────
load_dotenv()

RUBIKA_TOKEN    = os.getenv("RUBIKA_BOT_TOKEN")
RUBIKA_API_URL  = os.getenv("RUBIKA_API_URL", "https://botapi.rubika.ir/v3")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL    = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
WEBHOOK_URL     = os.getenv("WEBHOOK_URL", "")
WEBHOOK_SECRET  = os.getenv("WEBHOOK_SECRET", "secret")
PORT            = int(os.getenv("PORT", 5000))

# ─── Setup ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)
gemini = genai.GenerativeModel(GEMINI_MODEL)

app = Flask(__name__)

# ─── Simple in-memory storage (resets on restart) ────────────────────────────
# For persistence, replace with a simple JSON file or SQLite
users = {}          # { user_id: { "name": str, "username": str, "chat_history": [] } }

# ─── Rubika API helpers ───────────────────────────────────────────────────────
def rubika(method, payload={}):
    url = f"{RUBIKA_API_URL}/{RUBIKA_TOKEN}/{method}"
    try:
        r = requests.post(url, json=payload, timeout=15)
        return r.json()
    except Exception as e:
        log.error(f"Rubika API error [{method}]: {e}")
        return {}

def send(chat_id, text):
    payload = {"chat_id": chat_id, "text": text}
    return rubika("sendMessage", payload)

def send_menu(chat_id, text, buttons):
    """Send message with inline keyboard
    buttons: list of (text, id) tuples, will be arranged in a grid
    """
    rows = []
    for i in range(0, len(buttons), 2):  # 2 buttons per row
        row_buttons = []
        for j in range(2):
            if i + j < len(buttons):
                row_buttons.append({
                    "id": buttons[i + j][1],
                    "type": "Simple",
                    "button_text": buttons[i + j][0]
                })
        rows.append({"buttons": row_buttons})
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "inline_keypad": {"rows": rows}
    }
    return rubika("sendMessage", payload)

# ─── User management ─────────────────────────────────────────────────────────
def register_user(user_id, first_name, username):
    if user_id not in users:
        users[user_id] = {
            "name": first_name or "Unknown",
            "username": username or "",
            "chat_history": [],
            "message_count": 0
        }
        log.info(f"New user registered: {user_id} (@{username})")

# ─── Gemini AI ────────────────────────────────────────────────────────────────
def ask_gemini(user_id, user_message):
    try:
        user_data = users.get(user_id, {})
        history = user_data.get("chat_history", [])

        # Build conversation history for context (last 10 messages)
        chat = gemini.start_chat(history=history[-10:] if history else [])
        response = chat.send_message(user_message)
        reply = response.text

        # Save to history
        history.append({"role": "user", "parts": [user_message]})
        history.append({"role": "model", "parts": [reply]})
        users[user_id]["chat_history"] = history[-20:]  # keep last 20
        users[user_id]["message_count"] = users[user_id].get("message_count", 0) + 1

        return reply
    except Exception as e:
        log.error(f"Gemini error for user {user_id}: {e}")
        return "⚠️ Sorry, I couldn't process your request. Please try again."

# ─── Command handlers ─────────────────────────────────────────────────────────
def handle_start(user_id, first_name, username):
    register_user(user_id, first_name, username)
    send(user_id, (
        f"👋 Hello *{first_name}*!\n\n"
        "I'm a smart assistant powered by *Gemini AI*.\n"
        "Just send me any message and I'll respond!\n\n"
        "📌 *Commands:*\n"
        "/start - Show this message\n"
        "/clear - Clear your chat history\n"
        "/help - Show help\n"
    ))

def handle_clear(user_id):
    if user_id in users:
        users[user_id]["chat_history"] = []
    send(user_id, "🗑️ Your chat history has been cleared! Let's start fresh.")

def handle_help(user_id):
    send(user_id, (
        "🤖 *Gemini AI Bot Help*\n\n"
        "Just type any message and I'll answer using Google Gemini AI.\n\n"
        "📌 *Available Commands:*\n"
        "/start - Welcome message\n"
        "/clear - Clear conversation memory\n"
        "/help - This help message\n"
    ))

# ─── Main update processor ────────────────────────────────────────────────────
def process_update(data):
    try:
    # Handle inline button clicks (InlineMessage) - not used in current version
        if "inline_message" in data:
            return

        # Handle regular messages (Update with NewMessage)
        if "update" not in data:
            return
        
        update = data["update"]
        update_type = update.get("type", "")
        
        if update_type != "NewMessage":
            return
        
        chat_id = update.get("chat_id", "")
        new_message = update.get("new_message", {})
        
        user_id = new_message.get("sender_id", "")
        text = new_message.get("text", "").strip()
        
        if not text or not user_id:
            return

        # For now, use chat_id as first_name (Rubika doesn't send first_name in updates)
        # We'll extract it from actual data if available
        first_name = chat_id if chat_id else user_id

        # Register user if new
        if user_id not in users:
            register_user(user_id, first_name, "")

        # Standard commands
        if text == "/start":
            handle_start(user_id, first_name, "")
            return
        elif text == "/clear":
            handle_clear(user_id)
            return
        elif text == "/help":
            handle_help(user_id)
            return

        # Send to Gemini
        send(user_id, "⏳ Thinking...")
        reply = ask_gemini(user_id, text)
        send(user_id, reply)

    except Exception as e:
        log.error(f"Error processing update: {e}")

# ─── Flask routes ─────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    """Keep-alive page so Render doesn't sleep the service"""
    return jsonify({
        "status": "running",
        "bot": "Rubika Gemini Bot",
        "users": len(users)
    })

@app.route(f"/webhook/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    if data:
        threading.Thread(target=process_update, args=(data,)).start()
    return jsonify({"ok": True})

# ─── Keep-alive pinger (prevents Render free tier sleep) ─────────────────────
def keep_alive():
    """Pings the app every 10 minutes to prevent Render from sleeping it"""
    time.sleep(60)  # wait 1 min after startup
    while True:
        try:
            if WEBHOOK_URL:
                requests.get(WEBHOOK_URL, timeout=10)
                log.info("Keep-alive ping sent.")
        except Exception as e:
            log.warning(f"Keep-alive ping failed: {e}")
        time.sleep(600)  # every 10 minutes

# ─── Webhook setup ────────────────────────────────────────────────────────────
def setup_webhook():
    time.sleep(3)  # wait for Flask to start
    webhook_endpoint = f"{WEBHOOK_URL}/webhook/{WEBHOOK_SECRET}"
    
    # Rubika uses updateBotEndpoints with type "NewMessage" for regular messages
    # and "GetSelectionItem" for inline button clicks
    
    # Setup for NewMessage events
    result = rubika("updateBotEndpoints", {"url": webhook_endpoint, "type": "NewMessage"})
    if result.get("ok"):
        log.info(f"✅ Webhook set for NewMessage: {webhook_endpoint}")
    else:
        log.error(f"❌ NewMessage webhook failed: {result}")
    
    # Setup for InlineMessage events (button clicks)
    result = rubika("updateBotEndpoints", {"url": webhook_endpoint, "type": "GetSelectionItem"})
    if result.get("ok"):
        log.info(f"✅ Webhook set for GetSelectionItem: {webhook_endpoint}")
    else:
        log.error(f"❌ GetSelectionItem webhook failed: {result}")

# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("🚀 Starting Rubika Gemini Bot...")

    # Start webhook setup in background
    threading.Thread(target=setup_webhook, daemon=True).start()

    # Start keep-alive pinger
    threading.Thread(target=keep_alive, daemon=True).start()

    app.run(host="0.0.0.0", port=PORT, debug=False)