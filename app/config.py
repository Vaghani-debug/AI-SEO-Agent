"""
Application Configuration.

Loads environment variables from the .env file at startup and
exposes them as a typed Settings object. All modules should import
the `settings` singleton rather than reading os.getenv directly.
"""

import os
from dotenv import load_dotenv

# Load variables from .env into the process environment
load_dotenv()


class Settings:
    """Centralised application settings populated from environment variables."""

    # --- Google Gemini ---------------------------------------------------
    GEMINI_API_KEY: str   = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str     = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GEMINI_TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", "0.3"))
    GEMINI_MAX_TOKENS: int    = int(os.getenv("GEMINI_MAX_TOKENS", "2048"))

    # --- Application -----------------------------------------------------
    APP_ENV: str   = os.getenv("APP_ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


# Singleton -- import `settings` everywhere; never instantiate Settings again
settings = Settings()
