#!/usr/bin/env python3
"""
Test script to simulate Rubika webhook messages
Usage: python test_webhook.py
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:5000")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "secret")

def test_start_message():
    """Test /start command"""
    print("=" * 60)
    print("🧪 Testing /start command...")
    print("=" * 60)
    
    payload = {
        "update": {
            "type": "NewMessage",
            "chat_id": "test_chat_123",
            "new_message": {
                "message_id": "msg_001",
                "text": "/start",
                "time": "1643122902",
                "is_edited": False,
                "sender_type": "User",
                "sender_id": "user_test_123"
            }
        }
    }
    
    url = f"{WEBHOOK_URL}/webhook?secret={WEBHOOK_SECRET}"
    
    print(f"📤 POST {url}")
    print(f"📦 Payload:\n{json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        print(f"\n✅ Status: {response.status_code}")
        print(f"📬 Response: {response.json()}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_regular_message():
    """Test regular message"""
    print("\n" + "=" * 60)
    print("🧪 Testing regular message...")
    print("=" * 60)
    
    payload = {
        "update": {
            "type": "NewMessage",
            "chat_id": "test_chat_123",
            "new_message": {
                "message_id": "msg_002",
                "text": "Hello bot! Are you working?",
                "time": "1643122903",
                "is_edited": False,
                "sender_type": "User",
                "sender_id": "user_test_123"
            }
        }
    }
    
    url = f"{WEBHOOK_URL}/webhook?secret={WEBHOOK_SECRET}"
    
    print(f"📤 POST {url}")
    print(f"📦 Payload:\n{json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        print(f"\n✅ Status: {response.status_code}")
        print(f"📬 Response: {response.json()}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_health_check():
    """Test health check endpoint"""
    print("\n" + "=" * 60)
    print("🧪 Testing health check...")
    print("=" * 60)
    
    url = f"{WEBHOOK_URL}/"
    
    print(f"🔍 GET {url}")
    
    try:
        response = requests.get(url, timeout=5)
        print(f"\n✅ Status: {response.status_code}")
        print(f"📬 Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("\n🤖 Rubika Bot Webhook Tester\n")
    
    print(f"🔗 Webhook URL: {WEBHOOK_URL}/webhook")
    print(f"🔐 Secret: {WEBHOOK_SECRET[:5]}...***\n")
    
    # Test health check first
    test_health_check()
    
    # Test start message
    test_start_message()
    
    # Test regular message
    test_regular_message()
    
    print("\n" + "=" * 60)
    print("✅ Tests completed! Check bot logs for details.")
    print("=" * 60)
