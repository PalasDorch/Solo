import { useState, useEffect } from 'react'
import { bridgeHealth } from '../lib/bridge'

const PROXY_URL = import.meta.env.VITE_PROXY_URL || 'http://127.0.0.1:8601'

export default function StatusBar() {
  const [bridgeOk, setBridgeOk] = useState<boolean | null>(null)
  const [proxyOk, setProxyOk] = useState<boolean | null>(null)

  const checkBridge = async () => {
    try {
      const data = await bridgeHealth()
      setBridgeOk(data.ok === true)
    } catch {
      setBridgeOk(false)
    }
  }

  const checkProxy = async () => {
    try {
      const res = await fetch(`${PROXY_URL}/gpt/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: 'ping' }],
          max_tokens: 5,
        }),
      })
      const data = await res.json()
      setProxyOk(!!data.reply)
    } catch {
      setProxyOk(false)
    }
  }

  useEffect(() => {
    checkBridge()
    checkProxy()
    const interval = setInterval(() => {
      checkBridge()
      checkProxy()
    }, 10000) // Check every 10 seconds
    return () => clearInterval(interval)
  }, [])

  const pill = (label: string, ok: boolean | null) => (
    <div style={{
      display: 'inline-block',
      padding: '4px 12px',
      borderRadius: '12px',
      backgroundColor: ok === null ? '#888' : ok ? '#4CAF50' : '#f44336',
      color: 'white',
      fontSize: '12px',
      fontWeight: 'bold',
      marginRight: '8px',
    }}>
      {label}: {ok === null ? '...' : ok ? 'OK' : 'FAIL'}
    </div>
  )

  return (
    <div style={{
      padding: '8px 16px',
      backgroundColor: '#f5f5f5',
      borderBottom: '1px solid #ddd',
      display: 'flex',
      alignItems: 'center',
    }}>
      {pill('Bridge', bridgeOk)}
      {pill('Proxy', proxyOk)}
    </div>
  )
}

