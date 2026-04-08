import { Link, Outlet } from 'react-router-dom'
import { PlayerProvider } from './context/PlayerContext'
import { GlobalPlayer } from './components/GlobalPlayer'

function App() {
  return (
    <PlayerProvider>
      <div style={{ paddingBottom: '100px', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <header style={{
          display: 'flex',
          justifyContent: 'center',
          gap: '32px',
          padding: '20px 0',
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg)',
          position: 'sticky',
          top: 0,
          zIndex: 100
        }}>
          <Link to="/" style={{ textDecoration: 'none', color: 'var(--text-h)', fontWeight: 500 }}>播客库</Link>
          <Link to="/generate" style={{ textDecoration: 'none', color: 'var(--text-h)', fontWeight: 500 }}>生成</Link>
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
