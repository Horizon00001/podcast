import { Link, Outlet } from 'react-router-dom'
import { PlayerProvider } from './context/PlayerContext'
import { GlobalPlayer } from './components/GlobalPlayer'

function App() {
  const linkStyle = { textDecoration: 'none', color: 'var(--text-h)', fontWeight: 500 }

  return (
    <PlayerProvider>
      <div style={{ paddingBottom: '100px', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <header style={{
          display: 'flex',
          justifyContent: 'center',
          gap: 'clamp(16px, 5vw, 32px)',
          padding: '12px 16px',
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg)',
          position: 'sticky',
          top: 0,
          zIndex: 100,
          flexWrap: 'wrap'
        }}>
          <Link to="/" style={linkStyle}>📻 播客库</Link>
          <Link to="/generate" style={linkStyle}>✨ 生成</Link>
          <Link to="/subscriptions" style={linkStyle}>📋 订阅</Link>
          <Link to="/settings" style={linkStyle}>⚙️ 设置</Link>
        </header>
        <div style={{ flexGrow: 1 }}>
          <Outlet />
        </div>
        <GlobalPlayer />
      </div>
    </PlayerProvider>
  )
}

export default App