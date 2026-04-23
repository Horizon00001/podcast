import { Link, Outlet } from 'react-router-dom'
import { PlayerProvider } from './context/PlayerContext'
import { UserProvider, useUser } from './context/UserContext'
import { FavoritesProvider } from './context/FavoritesContext'
import { GlobalPlayer } from './components/GlobalPlayer'

function Header() {
  const { user, loading, error, usernameDraft, setUsernameDraft, saveUsername } = useUser()
  const linkStyle = { textDecoration: 'none', color: 'var(--text-h)', fontWeight: 500 }

  return (
    <header style={{
      display: 'flex',
      justifyContent: 'space-between',
      gap: '12px',
      padding: '12px 16px',
      borderBottom: '1px solid var(--border)',
      background: 'var(--bg)',
      position: 'sticky',
      top: 0,
      zIndex: 100,
      flexWrap: 'wrap'
    }}>
      <div style={{ display: 'flex', gap: 'clamp(16px, 4vw, 28px)', alignItems: 'center', flexWrap: 'wrap' }}>
        <Link to="/" style={linkStyle}>📻 播客库</Link>
        <Link to="/generate" style={linkStyle}>✨ 生成</Link>
        <Link to="/subscriptions" style={linkStyle}>📋 订阅</Link>
        <Link to="/favorites" style={linkStyle}>❤️ 收藏</Link>   {/* 新增 */}
        <Link to="/settings" style={linkStyle}>⚙️ 设置</Link>
      </div>
      <div style={{ display: 'flex', gap: 'clamp(16px, 4vw, 28px)', alignItems: 'center', flexWrap: 'wrap' }}>
        <Link to="/" style={linkStyle}>📻 播客库</Link>
        <Link to="/generate" style={linkStyle}>✨ 生成</Link>
        <Link to="/subscriptions" style={linkStyle}>📋 订阅</Link>
        <Link to="/settings" style={linkStyle}>⚙️ 设置</Link>
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          void saveUsername()
        }}
        style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
      >
        <input
          value={usernameDraft}
          onChange={(e) => setUsernameDraft(e.target.value)}
          placeholder="用户名"
          style={{
            padding: '6px 10px',
            borderRadius: '999px',
            border: '1px solid var(--border)',
            background: 'var(--bg)',
            minWidth: '120px',
          }}
        />
        <button
          type="submit"
          disabled={loading}
          style={{
            border: '1px solid var(--accent)',
            color: 'var(--accent)',
            borderRadius: '999px',
            background: 'transparent',
            padding: '6px 12px',
            cursor: 'pointer',
          }}
        >
          {loading ? '同步中' : '切换'}
        </button>
        <span style={{ fontSize: '12px', color: error ? 'red' : 'var(--text)' }}>
          {error ? `用户错误: ${error}` : `当前用户: ${user?.username ?? '未登录'}`}
        </span>
      </form>
    </header>
  )
}

function App() {
  return (
    <UserProvider>
      <PlayerProvider>
        <FavoritesProvider>   {/* ✅ 包裹收藏功能 */}
          <div style={{ paddingBottom: '100px', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
            <Header />
            <div style={{ flexGrow: 1 }}>
              <Outlet />
            </div>
            <GlobalPlayer />
          </div>
        </FavoritesProvider>
      </PlayerProvider>
    </UserProvider>
  )
}

export default App
