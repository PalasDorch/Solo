import { useState } from 'react'

const PROXY_URL = import.meta.env.VITE_PROXY_URL || 'http://127.0.0.1:8601'

interface Message {
  role: 'system' | 'user' | 'assistant'
  content: string
}

export default function ChatGPTPanel() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'system', content: 'You are ChatGPT, a helpful AI assistant.' },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage: Message = { role: 'user', content: input }
    const newMessages = [...messages, userMessage]
    setMessages(newMessages)
    setInput('')
    setLoading(true)
    setError('')

    try {
      const res = await fetch(`${PROXY_URL}/gpt/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: newMessages,
          max_tokens: 1000,
        }),
      })

      if (!res.ok) {
        throw new Error(`Proxy error: ${res.status}`)
      }

      const data = await res.json()
      
      if (data.reply) {
        setMessages([...newMessages, { role: 'assistant', content: data.reply }])
      } else {
        throw new Error('No reply from proxy')
      }
    } catch (err: any) {
      setError(err.message || 'Failed to send message')
    } finally {
      setLoading(false)
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
      <h2 style={{ margin: '0 0 16px 0', fontSize: '18px' }}>ChatGPT</h2>

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
              {msg.role === 'user' ? 'You' : 'ChatGPT'}
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
      </div>

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

      <div style={{ marginBottom: '12px' }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message... (Shift+Enter for new line)"
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

