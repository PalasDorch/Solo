import { useState, useEffect } from 'react'
import { bridgeHealth } from '../lib/bridge'

export default function RWKVPanel() {
  const [input, setInput] = useState('')
  const [bridgeOk, setBridgeOk] = useState<boolean | null>(null)

  useEffect(() => {
    const checkBridge = async () => {
      try {
        const data = await bridgeHealth()
        setBridgeOk(data.ok === true)
      } catch {
        setBridgeOk(false)
      }
    }
    checkBridge()
    const interval = setInterval(checkBridge, 10000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      padding: '16px',
      borderRight: '1px solid #ddd',
    }}>
      <h2 style={{ margin: '0 0 16px 0', fontSize: '18px' }}>Solomon (RWKV)</h2>
      
      <div style={{
        flex: 1,
        backgroundColor: '#f9f9f9',
        borderRadius: '4px',
        padding: '12px',
        marginBottom: '12px',
        overflowY: 'auto',
      }}>
        <p style={{ color: '#888', fontSize: '14px' }}>
          Chat messages will appear here (Phase 2)
        </p>
      </div>

      <div style={{ marginBottom: '12px' }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          disabled
          style={{
            width: '100%',
            height: '60px',
            padding: '8px',
            borderRadius: '4px',
            border: '1px solid #ddd',
            resize: 'none',
            fontFamily: 'inherit',
            backgroundColor: '#f5f5f5',
          }}
        />
      </div>

      <button
        disabled
        style={{
          padding: '10px 20px',
          backgroundColor: '#ccc',
          color: '#666',
          border: 'none',
          borderRadius: '4px',
          cursor: 'not-allowed',
          fontWeight: 'bold',
        }}
        title="Send disabled until RWKV chat is wired (Phase 2)"
      >
        Send (Coming in Phase 2)
      </button>

      <div style={{
        marginTop: '12px',
        padding: '8px',
        backgroundColor: '#f5f5f5',
        borderRadius: '4px',
        fontSize: '12px',
        display: 'flex',
        alignItems: 'center',
      }}>
        <span style={{
          display: 'inline-block',
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          backgroundColor: bridgeOk === null ? '#888' : bridgeOk ? '#4CAF50' : '#f44336',
          marginRight: '8px',
        }} />
        Bridge health: {bridgeOk === null ? 'Checking...' : bridgeOk ? 'OK' : 'FAIL'}
      </div>
    </div>
  )
}

