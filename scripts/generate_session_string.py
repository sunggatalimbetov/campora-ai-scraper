"""
One-time local utility to generate a Telethon StringSession.

Run this locally, authenticate interactively, then store the printed
session string as the TELEGRAM_SESSION secret in your CI/CD provider.

Usage:
    python -m scripts.generate_session_string
"""

import os
import sys

from dotenv import load_dotenv
from telethon.sessions import StringSession
from telethon.sync import TelegramClient

load_dotenv()

api_id = int(os.getenv("APP_API_ID", "0"))
api_hash = os.getenv("APP_API_HASH", "")

if not api_id or not api_hash:
    print("Set APP_API_ID and APP_API_HASH in your .env file first.")
    sys.exit(1)

with TelegramClient(StringSession(), api_id, api_hash) as client:
    session_string = client.session.save()
    print("\n=== Copy the string below and store it as TELEGRAM_SESSION ===\n")
    print(session_string)
    print("\n=== End of session string ===")
