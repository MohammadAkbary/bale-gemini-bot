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
ADMIN_USER_ID   = os.getenv("ADMIN_USER_ID", "")
WEBHOOK_URL     = os.getenv("WEBHOOK_URL", "")
WEBHOOK_SECRET  = os.getenv("WEBHOOK_SECRET", "secret")
PORT            = int(os.getenv("PORT", 5000))
OFFSET_ID       = "0"  # for long polling (getUpdates)

# ─── Setup ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)
gemini = genai.GenerativeModel(GEMINI_MODEL)

app = Flask(__name__)

# ─── Simple in-memory storage (resets on restart) ────────────────────────────
# For persistence, replace with a simple JSON file or SQLite
users = {}          # { user_id: { "name": str, "username": str, "blocked": bool, "chat_history": [] } }
bot_enabled = True  # admin can toggle this

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
            "blocked": False,
            "chat_history": [],
            "message_count": 0
        }
        log.info(f"New user registered: {user_id} (@{username})")
        # Notify admin of new user
        send(ADMIN_USER_ID, f"👤 *New user joined!*\nID: `{user_id}`\nName: {first_name}\nUsername: @{username}")

def is_blocked(user_id):
    return users.get(user_id, {}).get("blocked", False)

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

# ─── Admin panel ──────────────────────────────────────────────────────────────
def handle_admin(user_id):
    if user_id != ADMIN_USER_ID:
        send(user_id, "⛔ You are not authorized.")
        return

    total = len(users)
    blocked = sum(1 for u in users.values() if u.get("blocked"))
    active = total - blocked

    send_menu(user_id,
        f"🛠️ *Admin Panel*\n\n"
        f"👥 Total users: {total}\n"
        f"✅ Active: {active}\n"
        f"🚫 Blocked: {blocked}\n"
        f"🤖 Bot enabled: {'Yes' if bot_enabled else 'No'}",
        [
            ("📋 List Users", "admin_list"),
            ("🔄 Toggle Bot", "admin_toggle"),
            ("📢 Broadcast", "admin_broadcast_prompt"),
        ]
    )

def handle_admin_callback(user_id, data, message_id):
    if user_id != ADMIN_USER_ID:
        return

    global bot_enabled

    if data == "admin_list":
        if not users:
            send(user_id, "No users yet.")
            return
        text = "👥 *User List:*\n\n"
        for uid, info in list(users.items())[:20]:  # limit to 20
            status = "🚫" if info.get("blocked") else "✅"
            text += f"{status} `{uid}` - {info['name']} (@{info.get('username','?')}) - msgs: {info.get('message_count',0)}\n"
        send(user_id, text)

    elif data == "admin_toggle":
        bot_enabled = not bot_enabled
        send(user_id, f"🤖 Bot is now {'*enabled* ✅' if bot_enabled else '*disabled* 🚫'}")

    elif data.startswith("admin_block_"):
        target_id = int(data.split("_")[2])
        if target_id in users:
            users[target_id]["blocked"] = True
            send(user_id, f"🚫 User `{target_id}` has been blocked.")
            send(target_id, "🚫 You have been blocked by the admin.")

    elif data.startswith("admin_unblock_"):
        target_id = int(data.split("_")[2])
        if target_id in users:
            users[target_id]["blocked"] = False
            send(user_id, f"✅ User `{target_id}` has been unblocked.")
            send(target_id, "✅ You have been unblocked! You can chat again.")

# Admin commands: /block <id> /unblock <id> /broadcast <msg>
def handle_admin_command(user_id, text):
    if user_id != ADMIN_USER_ID:
        send(user_id, "⛔ Not authorized.")
        return

    parts = text.strip().split(" ", 2)
    cmd = parts[0].lower()

    if cmd == "/block" and len(parts) >= 2:
        target_id = int(parts[1])
        if target_id in users:
            users[target_id]["blocked"] = True
            send(user_id, f"🚫 User `{target_id}` blocked.")
            send(target_id, "🚫 You have been blocked by the admin.")
        else:
            send(user_id, "User not found.")

    elif cmd == "/unblock" and len(parts) >= 2:
        target_id = int(parts[1])
        if target_id in users:
            users[target_id]["blocked"] = False
            send(user_id, f"✅ User `{target_id}` unblocked.")
        else:
            send(user_id, "User not found.")

    elif cmd == "/broadcast" and len(parts) >= 2:
        message = " ".join(parts[1:])
        count = 0
        for uid in users:
            if not users[uid].get("blocked"):
                send(uid, f"📢 *Message from Admin:*\n\n{message}")
                count += 1
        send(user_id, f"📢 Broadcast sent to {count} users.")

    elif cmd == "/stats":
        total = len(users)
        blocked = sum(1 for u in users.values() if u.get("blocked"))
        total_msgs = sum(u.get("message_count", 0) for u in users.values())
        send(user_id, (
            f"📊 *Bot Statistics*\n\n"
            f"👥 Total users: {total}\n"
            f"🚫 Blocked: {blocked}\n"
            f"💬 Total messages: {total_msgs}\n"
            f"🤖 Bot status: {'On' if bot_enabled else 'Off'}"
        ))

    elif cmd == "/users":
        handle_admin_callback(user_id, "admin_list", None)

    else:
        send(user_id, "Unknown admin command.")

# ─── Main update processor ────────────────────────────────────────────────────
def process_update(data):
    try:
        # Handle inline button clicks (InlineMessage)
        if "inline_message" in data:
            inline_msg = data["inline_message"]
            user_id = inline_msg.get("sender_id", "")
            button_id = inline_msg.get("aux_data", {}).get("button_id", "")
            chat_id = inline_msg.get("chat_id", "")
            message_id = inline_msg.get("message_id", "")
            
            if user_id and button_id:
                handle_admin_callback(user_id, button_id, message_id)
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
        if user_id not in users and user_id != ADMIN_USER_ID:
            register_user(user_id, first_name, "")

        # Admin commands
        if user_id == ADMIN_USER_ID:
            if text == "/admin":
                handle_admin(user_id)
                return
            if text.startswith("/block") or text.startswith("/unblock") or \
               text.startswith("/broadcast") or text == "/stats" or text == "/users":
                handle_admin_command(user_id, text)
                return

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

        # Block check
        if is_blocked(user_id):
            send(user_id, "🚫 You are blocked from using this bot.")
            return

        # Bot toggle check
        if not bot_enabled and user_id != ADMIN_USER_ID:
            send(user_id, "🔴 The bot is currently offline. Please try later.")
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
        "users": len(users),
        "bot_enabled": bot_enabled
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