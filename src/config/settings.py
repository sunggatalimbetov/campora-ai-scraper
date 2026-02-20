import os

from dotenv import load_dotenv

load_dotenv()

# OpenAI API Configuration
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")

# Supabase Configuration
SUPABASE_URL: str = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY")

# Telegram App Configuration (Telethon / MTProto)
APP_API_ID: int = int(os.getenv("APP_API_ID", "0"))
APP_API_HASH: str = os.getenv("APP_API_HASH", "")
TELEGRAM_SESSION: str = os.getenv("TELEGRAM_SESSION", "")
CHAT_USERNAME: int = int(os.getenv("CHAT_USERNAME", "0"))
