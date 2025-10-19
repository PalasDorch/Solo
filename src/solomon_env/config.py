from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Always load .env from the project root (two levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH)

@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_base_url: str
    openai_model: str

    @staticmethod
    def load() -> "Settings":
        key = os.getenv("OPENAI_API_KEY", "").strip()
        if not key:
            raise RuntimeError(f"OPENAI_API_KEY missing. Looked for: {ENV_PATH}")
        base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        return Settings(openai_api_key=key, openai_base_url=base, openai_model=model)
