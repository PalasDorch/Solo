from __future__ import annotations
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

from solomon_env.config import Settings
from solomon_env.llm_client import LLMClient
from solomon_env.rwkv_adapter import RWKVAdapter, RWKVStateStore

app = FastAPI(title="Solomon Bridge", version="0.3.1")

# Simple in-memory state for RWKV sessions
_state = RWKVStateStore()

class ChatRequest(BaseModel):
    prompt: str
    max_tokens: int = 200
    temperature: float = 0.3
    provider: str = "rwkv"  # default to local RWKV to avoid requiring API key

class ChatResponse(BaseModel):
    text: str

@app.get("/health")
def health():
    return {"ok": True, "service": "solomon-bridge", "version": "0.3.1"}

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    provider = (req.provider or "rwkv").lower()

    if provider == "rwkv":
        rwkv = RWKVAdapter()
        session_id = _state.new_session_id()
        text, _ = await rwkv.generate(
            req.prompt, None,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            session_id=session_id,
            state_store=_state
        )
        return ChatResponse(text=text)

    # Default: OpenAI path
    cfg = Settings.load()
    client = LLMClient(cfg)
    resp = await client.chat(req.prompt, max_tokens=req.max_tokens, temperature=req.temperature)
    text = resp["choices"][0]["message"]["content"].strip()
    return ChatResponse(text=text)
