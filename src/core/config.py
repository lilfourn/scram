import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Debug: Check if keys are loaded (masked)
if os.getenv("OPENAI_API_KEY"):
    print(f"DEBUG: OPENAI_API_KEY found: {os.getenv('OPENAI_API_KEY')[:5]}...")
else:
    print("DEBUG: OPENAI_API_KEY NOT found in environment.")


class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Primary Models (Gemini)
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-3-pro-preview")
    FAST_MODEL = os.getenv("FAST_MODEL", "gemini-2.5-flash")

    # Fallback Models (OpenAI)
    FALLBACK_DEFAULT_MODEL = os.getenv("FALLBACK_DEFAULT_MODEL", "gpt-5.1-2025-11-13")
    FALLBACK_FAST_MODEL = os.getenv("FALLBACK_FAST_MODEL", "gpt-5-mini-2025-08-07")

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    PROJECT_ROOT = Path(__file__).parent.parent.parent

    # Fetching Configuration
    # Enforce upper bounds to prevent DoS via config
    MAX_CONCURRENCY = min(max(int(os.getenv("MAX_CONCURRENCY", "10")), 1), 50)
    BATCH_SIZE = min(max(int(os.getenv("BATCH_SIZE", "5")), 1), 20)
    GLOBAL_RATE_LIMIT = float(
        os.getenv("GLOBAL_RATE_LIMIT", "10.0")
    )  # Requests per second
    DOMAIN_RATE_LIMIT = float(
        os.getenv("DOMAIN_RATE_LIMIT", "2.0")
    )  # Requests per second per domain

    # Browser Configuration
    HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
    BROWSER_POOL_SIZE = min(max(int(os.getenv("BROWSER_POOL_SIZE", "2")), 1), 10)

    # User Agents (Simple list for rotation)
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    # Proxies (List of proxy strings e.g., "http://user:pass@host:port")
    PROXIES = os.getenv("PROXIES", "").split(",") if os.getenv("PROXIES") else []


config = Config()
