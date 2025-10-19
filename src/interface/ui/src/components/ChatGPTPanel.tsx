import { useState, useRef, useEffect } from 'react'

const PROXY_URL = import.meta.env.VITE_PROXY_URL || 'http://127.0.0.1:8601'
const SESSION_ID = 'solomon'

const SYSTEM_MESSAGE = {
  role: 'system' as const,
  content: "You are GPT-5-Pro assisting on project 'Solomon'. Use tools via the local Bridge when available. Keep edits auditable. Summarize rationale briefly."
}

interface Message {
  role: 'system' | 'user' | 'assistant'
  content: string
}

export default function ChatGPTPanel() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [contextLength, setContextLength] = useState(0)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const initialized = useRef(false)

  // Initialize with system message on first render
  useEffect(() => {
    if (!initialized.current && messages.length === 0) {
      setMessages([SYSTEM_MESSAGE])
      initialized.current = true
    }
  }, [])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage: Message = { role: 'user', content: input.trim() }
    
    // Add user message to UI
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)
    setError('')

    try {
      // Determine which messages to send to proxy
      // If this is the first user message, send system + user
      // Otherwise just send the new user message
      const isFirstMessage = messages.length === 1 && messages[0].role === 'system'
      const messagesToSend = isFirstMessage 
        ? [SYSTEM_MESSAGE, userMessage]
        : [userMessage]

      const res = await fetch(`${PROXY_URL}/gpt/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session: SESSION_ID,
          messages: messagesToSend,
          model: 'gpt-4o-mini',
          temperature: 0.7,
          max_tokens: 2000,
        }),
      })

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail || `Proxy error: ${res.status}`)
      }

      const data = await res.json()
      
      if (data.reply) {
        const assistantMessage: Message = { role: 'assistant', content: data.reply }
        setMessages(prev => [...prev, assistantMessage])
        setContextLength(data.context_length || 0)
      } else {
        throw new Error('No reply from proxy')
      }
    } catch (err: any) {
      setError(err.message || 'Failed to send message')
      console.error('Chat error:', err)
    } finally {
      setLoading(false)
    }
  }

  const resetSession = async () => {
    if (!confirm('Reset conversation? This will clear all chat history.')) return

    try {
      const res = await fetch(`${PROXY_URL}/gpt/session/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session: SESSION_ID }),
      })

      if (res.ok) {
        setMessages([SYSTEM_MESSAGE])
        setContextLength(0)
        setError('')
      } else {
        throw new Error('Failed to reset session')
      }
    } catch (err: any) {
      setError(err.message || 'Failed to reset session')
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      padding: '16px',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '16px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <h2 style={{ margin: 0, fontSize: '18px' }}>ChatGPT</h2>
          {contextLength > 0 && (
            <span style={{ fontSize: '12px', color: '#666' }}>
              ({contextLength} messages)
            </span>
          )}
        </div>
        <button
          onClick={resetSession}
          disabled={loading}
          style={{
            padding: '6px 12px',
            backgroundColor: '#dc3545',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: '12px',
            fontWeight: 'bold',
          }}
        >
          Reset
        </button>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        backgroundColor: '#f9f9f9',
        borderRadius: '4px',
        padding: '12px',
        marginBottom: '12px',
        overflowY: 'auto',
      }}>
        {messages.filter(m => m.role !== 'system').map((msg, i) => (
          <div
            key={i}
            style={{
              marginBottom: '12px',
              padding: '8px 12px',
              borderRadius: '8px',
              backgroundColor: msg.role === 'user' ? '#e3f2fd' : '#f1f8e9',
              maxWidth: '80%',
              marginLeft: msg.role === 'user' ? 'auto' : '0',
              marginRight: msg.role === 'user' ? '0' : 'auto',
            }}
          >
            <div style={{ fontSize: '11px', fontWeight: 'bold', marginBottom: '4px', color: '#666' }}>
              {msg.role === 'user' ? 'You' : 'GPT'}
            </div>
            <div style={{ fontSize: '14px', whiteSpace: 'pre-wrap' }}>
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ color: '#888', fontSize: '14px', fontStyle: 'italic' }}>
            ChatGPT is typing...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Error */}
      {error && (
        <div style={{
          padding: '8px 12px',
          backgroundColor: '#ffebee',
          color: '#c62828',
          borderRadius: '4px',
          marginBottom: '12px',
          fontSize: '13px',
        }}>
          Error: {error}
        </div>
      )}

      {/* Input */}
      <div style={{ marginBottom: '12px' }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Message ChatGPT... (Shift+Enter for new line)"
          disabled={loading}
          style={{
            width: '100%',
            height: '60px',
            padding: '8px',
            borderRadius: '4px',
            border: '1px solid #ddd',
            resize: 'none',
            fontFamily: 'inherit',
          }}
        />
      </div>

      <button
        onClick={sendMessage}
        disabled={loading || !input.trim()}
        style={{
          padding: '10px 20px',
          backgroundColor: loading || !input.trim() ? '#ccc' : '#2196F3',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
          fontWeight: 'bold',
        }}
      >
        {loading ? 'Sending...' : 'Send'}
      </button>
    </div>
  )
}
