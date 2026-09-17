"""Central configuration, loaded from environment variables / .env file."""
import os
from dotenv import load_dotenv

load_dotenv()


def _bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    ANTHROPIC_MAX_TOKENS: int = int(os.getenv("ANTHROPIC_MAX_TOKENS", "4000"))

    ENABLE_LLM_REVIEW: bool = _bool(os.getenv("ENABLE_LLM_REVIEW"), default=True)
    MAX_FILE_SIZE_KB: int = int(os.getenv("MAX_FILE_SIZE_KB", "500"))
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    CORS_ORIGINS: list = [
        o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()
    ]

    @property
    def llm_available(self) -> bool:
        return bool(self.ANTHROPIC_API_KEY) and self.ENABLE_LLM_REVIEW


settings = Settings()
