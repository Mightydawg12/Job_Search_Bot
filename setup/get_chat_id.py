#!/usr/bin/env python3
"""
One-time helper: finds your Telegram chat ID and sends a test message.

  1. Send any message (e.g. "hi") to your new bot in Telegram first.
  2. Run:  python3 setup/get_chat_id.py
  3. Paste your bot token when asked (it is not saved anywhere).
"""
import getpass
import json
import os
import urllib.parse
import urllib.request

token = os.environ.get("TELEGRAM_BOT_TOKEN") or getpass.getpass("Bot token from @BotFather (hidden): ").strip()
base = f"https://api.telegram.org/bot{token}"

with urllib.request.urlopen(f"{base}/getUpdates", timeout=30) as r:
    updates = json.load(r).get("result", [])

chats = {}
for u in updates:
    msg = u.get("message") or u.get("edited_message") or {}
    chat = msg.get("chat") or {}
    if chat.get("id"):
        chats[chat["id"]] = chat.get("first_name") or chat.get("title") or chat.get("username")

if not chats:
    raise SystemExit("No messages found. Open your bot in Telegram, press Start / send 'hi', then run this again.")

for cid, name in chats.items():
    print(f"\n  TELEGRAM_CHAT_ID = {cid}    ({name})")
    data = urllib.parse.urlencode({"chat_id": cid, "text": "✅ Job bot connected! You'll get job alerts here."}).encode()
    urllib.request.urlopen(f"{base}/sendMessage", data=data, timeout=30)
print("\nA test message was sent — check Telegram. Save that number as the TELEGRAM_CHAT_ID secret.")
