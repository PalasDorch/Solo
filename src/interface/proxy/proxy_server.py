"""
GPT Proxy Server with Session Persistence
Proxies ChatGPT requests and maintains conversation history
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
PROXY_PORT = int(os.getenv("PROXY_PORT", "8601"))
CORS_ORIGIN = os.getenv("CORS_ORIGIN", "http://127.0.0.1:5173")

if not OPENAI_API_KEY or OPENAI_API_KEY == "sk-PLACEHOLDER":
    print("WARNING: OPENAI_API_KEY not set or is placeholder")

# Initialize OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="GPT Proxy", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN, "http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session storage
SESSIONS: Dict[str, List[dict]] = {}
SESSIONS_FILE = Path(__file__).parent / "sessions.json"
MAX_MESSAGES_PER_SESSION = 100


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    session: Optional[str] = "solomon"
    messages: List[Message]
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2000


class SessionResetRequest(BaseModel):
    session: Optional[str] = "solomon"


def load_sessions():
    """Load sessions from disk"""
    global SESSIONS
    if SESSIONS_FILE.exists():
        try:
            with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                SESSIONS = json.load(f)
            print(f"[SESSION] Loaded {len(SESSIONS)} sessions from disk")
        except Exception as e:
            print(f"[SESSION] Failed to load: {e}")
            SESSIONS = {}
    else:
        SESSIONS = {}


def save_sessions():
    """Save sessions to disk"""
    try:
        with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(SESSIONS, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[SESSION] Failed to save: {e}")


def trim_session(session_id: str):
    """Trim session to last MAX_MESSAGES_PER_SESSION messages"""
    if session_id in SESSIONS and len(SESSIONS[session_id]) > MAX_MESSAGES_PER_SESSION:
        SESSIONS[session_id] = SESSIONS[session_id][-MAX_MESSAGES_PER_SESSION:]


@app.on_event("startup")
async def startup_event():
    load_sessions()


@app.on_event("shutdown")
async def shutdown_event():
    save_sessions()


@app.get("/health")
async def health():
    """Health check"""
    return {"ok": True, "service": "gpt-proxy", "sessions": len(SESSIONS)}


@app.post("/gpt/chat")
async def gpt_chat(request: ChatRequest):
    """
    Proxy ChatGPT requests with session persistence
    """
    try:
        session_id = request.session or "solomon"
        model = request.model or OPENAI_MODEL
        
        # Initialize session if needed
        if session_id not in SESSIONS:
            SESSIONS[session_id] = []
        
        # Append incoming messages to session
        for msg in request.messages:
            SESSIONS[session_id].append({"role": msg.role, "content": msg.content})
        
        # Trim if needed
        trim_session(session_id)
        
        # Call OpenAI API with full session history
        response = client.chat.completions.create(
            model=model,
            messages=SESSIONS[session_id],
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        # Extract reply
        reply = response.choices[0].message.content
        
        # Append assistant reply to session
        SESSIONS[session_id].append({"role": "assistant", "content": reply})
        
        # Save to disk
        save_sessions()
        
        return {
            "reply": reply,
            "model": model,
            "session": session_id,
            "context_length": len(SESSIONS[session_id]),
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
    
    except openai.AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid OpenAI API key")
    except openai.RateLimitError:
        raise HTTPException(status_code=429, detail="OpenAI rate limit exceeded")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")


@app.get("/gpt/sessions")
async def list_sessions():
    """List all sessions and their message counts"""
    counts = {sid: len(msgs) for sid, msgs in SESSIONS.items()}
    return {
        "sessions": list(SESSIONS.keys()),
        "counts": counts
    }


@app.post("/gpt/session/reset")
async def reset_session(request: SessionResetRequest):
    """Reset a session (clear all messages)"""
    session_id = request.session or "solomon"
    
    if session_id in SESSIONS:
        SESSIONS[session_id] = []
        save_sessions()
        return {"status": "reset", "session": session_id}
    else:
        return {"status": "not_found", "session": session_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=PROXY_PORT, log_level="info")
