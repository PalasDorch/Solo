import StatusBar from './components/StatusBar'
import RWKVPanel from './components/RWKVPanel'
import ChatGPTPanel from './components/ChatGPTPanel'

function App() {
  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <StatusBar />
      
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <div style={{ flex: 1 }}>
          <RWKVPanel />
        </div>
        <div style={{ flex: 1 }}>
          <ChatGPTPanel />
        </div>
      </div>
    </div>
  )
}

export default App

