from __future__ import annotations
import httpx
from typing import Dict, Any
from .config import Settings

class LLMClient:
    def __init__(self, settings: Settings):
        self.s = settings

    async def chat(self, prompt: str, *, max_tokens: int = 128, temperature: float = 0.2) -> Dict[str, Any]:
        url = f"{self.s.openai_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.s.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.s.openai_model,
            "messages": [
                {"role": "system", "content": "You are Solomon's bootstrap assistant."},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            return r.json()
