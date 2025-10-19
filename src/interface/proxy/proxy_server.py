Text file: proxy_server.py
Latest content with line numbers:
101	    save_sessions()
102	
103	
104	@app.get("/health")
105	async def health():
106	    """Health check"""
107	    return {"ok": True, "service": "gpt-proxy", "sessions": len(SESSIONS)}
108	
109	
110	@app.post("/gpt/chat")
111	async def gpt_chat(request: ChatRequest):
112	    """
113	    Proxy ChatGPT requests with session persistence
114	    """
115	    try:
116	        session_id = request.session or "solomon"
117	        model = request.model or OPENAI_MODEL
118	        
119	        # Initialize session if needed
120	        if session_id not in SESSIONS:
121	            SESSIONS[session_id] = []
122	        
123	        # Append incoming messages to session
124	        for msg in request.messages:
125	            SESSIONS[session_id].append({"role": msg.role, "content": msg.content})
126	        
127	        # Trim if needed
128	        trim_session(session_id)
129	        
130	        # Call OpenAI API with full session history
131	        response = client.chat.completions.create(
132	            model=model,
133	            messages=SESSIONS[session_id],
134	            temperature=request.temperature,
135	            max_tokens=request.max_tokens
136	        )
137	        
138	        # Extract reply
139	        reply = response.choices[0].message.content
140	        
141	        # Append assistant reply to session
142	        SESSIONS[session_id].append({"role": "assistant", "content": reply})
143	        
144	        # Save to disk
145	        save_sessions()
146	        
147	        return {
148	            "reply": reply,
149	            "model": model,
150	            "session": session_id,
151	            "context_length": len(SESSIONS[session_id]),
152	            "usage": {
153	                "prompt_tokens": response.usage.prompt_tokens,
154	                "completion_tokens": response.usage.completion_tokens,
155	                "total_tokens": response.usage.total_tokens
156	            }
157	        }
158	    
159	    except openai.AuthenticationError:
160	        raise HTTPException(status_code=401, detail="Invalid OpenAI API key")