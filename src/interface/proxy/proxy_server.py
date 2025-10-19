"""
GPT Proxy Server
Proxies ChatGPT requests to hide API key from browser
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
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


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000


@app.get("/health")
async def health():
    """Health check"""
    return {"ok": True, "service": "gpt-proxy"}


@app.post("/gpt/chat")
async def gpt_chat(request: ChatRequest):
    """
    Proxy ChatGPT requests
    """
    try:
        # Use model from request or default
        model = request.model or OPENAI_MODEL
        
        # Convert messages to OpenAI format
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        # Extract reply
        reply = response.choices[0].message.content
        
        return {
            "reply": reply,
            "model": model,
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=PROXY_PORT, log_level="info")

