import os

from dotenv import load_dotenv

load_dotenv()

def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    raise RuntimeError(f"Missing required environment variable: {name}")


# OpenAI API Configuration
OPENAI_API_KEY: str = _require_env("OPENAI_API_KEY")

# Supabase Configuration
SUPABASE_URL: str = _require_env("SUPABASE_URL")
SUPABASE_SERVICE_KEY: str = _require_env("SUPABASE_SERVICE_KEY")

# Telegram App Configuration (Telethon / MTProto)
APP_API_ID: int = int(os.getenv("APP_API_ID", "0"))
APP_API_HASH: str = os.getenv("APP_API_HASH", "")
TELEGRAM_SESSION: str = os.getenv("TELEGRAM_SESSION", "")
CHAT_USERNAME: int = int(os.getenv("CHAT_USERNAME", "0"))
