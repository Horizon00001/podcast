import { useState } from 'react'
import { NavLink, Outlet, useLocation, matchPath } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { PlayerProvider } from './context/PlayerContext'
import { UserProvider, useUser } from './context/UserContext'
import { FavoritesProvider } from './context/FavoritesContext'
import { GlobalPlayer } from './components/GlobalPlayer'

const navIcons: Record<string, React.ReactNode> = {
  '/': (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="8" height="8" rx="2" />
      <rect x="14" y="3" width="8" height="8" rx="2" />
      <rect x="2" y="13" width="8" height="8" rx="2" />
      <rect x="14" y="13" width="8" height="8" rx="2" />
    </svg>
  ),
  '/generate': (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3l2.4 7.2L22 12l-7.6 1.8L12 21l-2.4-7.2L2 12l7.6-1.8z" />
    </svg>
  ),
  '/subscriptions': (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" />
    </svg>
  ),
  '/favorites': (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z" />
    </svg>
  ),
  '/settings': (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
    </svg>
  ),
}

const navItems = [
  { to: '/', label: '播客库' },
  { to: '/generate', label: '生成' },
  { to: '/subscriptions', label: '订阅' },
  { to: '/favorites', label: '收藏' },
  { to: '/settings', label: '设置' },
]

const navGroups = [
  {
    title: '浏览',
    items: navItems.slice(0, 3),
  },
  {
    title: '资料库',
    items: navItems.slice(3),
  },
]

const SIDEBAR_WIDTH = 228
const DESKTOP_UI_SCALE = 0.92

function AccountPanel({ compact = false }: { compact?: boolean }) {
  const { user, loading, error, usernameDraft, setUsernameDraft, saveUsername } = useUser()

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        void saveUsername()
      }}
      style={{ display: 'grid', gap: '8px', minWidth: compact ? '220px' : '240px' }}
    >
      <div style={{ fontSize: '12px', letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text)', fontWeight: 700 }}>
        账户
      </div>
      <div style={{ fontSize: '13px', color: '#3d3845', lineHeight: 1.5 }}>
        {user ? `当前使用 ${user.username} 浏览和保存内容。` : '登录后可同步收藏与个性化推荐。'}
      </div>
      <input
        value={usernameDraft}
        onChange={(e) => setUsernameDraft(e.target.value)}
        placeholder="用户名"
        style={{
          padding: '9px 11px',
          borderRadius: '12px',
          border: '1px solid rgba(8, 6, 13, 0.12)',
          background: '#ffffff',
          minWidth: '120px',
          color: 'var(--text-h)',
        }}
      />
       <button
         type="submit"
         disabled={loading}
         style={{
           border: '1px solid rgba(8, 6, 13, 0.12)',
           color: 'var(--text-h)',
           borderRadius: '999px',
           background: '#ffffff',
           padding: '8px 12px',
           cursor: 'pointer',
           fontWeight: 600,
           fontSize: '13px',
         }}
       >
         {loading ? '同步中' : '切换用户'}
       </button>
      <span style={{ fontSize: '12px', color: error ? 'red' : 'var(--text)', lineHeight: 1.5 }}>
        {error ? `用户错误: ${error}` : `当前用户: ${user?.username ?? '未登录'}`}
      </span>
    </form>
  )
}

function AccountEntry() {
  const { user, loading } = useUser()
  const [open, setOpen] = useState(false)
  const initial = (user?.username?.[0] ?? '登').toUpperCase()

  return (
    <div style={{ position: 'relative' }}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        style={{
          border: `1px solid ${open ? 'rgba(170, 59, 255, 0.28)' : 'rgba(8, 6, 13, 0.08)'}`,
          background: open ? 'rgba(255, 255, 255, 0.96)' : 'rgba(255, 255, 255, 0.72)',
          borderRadius: '999px',
          padding: user ? '7px 12px 7px 7px' : '8px 13px',
          display: 'flex',
          alignItems: 'center',
          gap: user ? '9px' : '7px',
          cursor: 'pointer',
          color: 'var(--text-h)',
          boxShadow: open ? '0 14px 30px rgba(8, 6, 13, 0.12)' : '0 8px 22px rgba(8, 6, 13, 0.06)',
          backdropFilter: 'blur(16px)',
          transition: 'border-color 0.18s, background 0.18s, box-shadow 0.18s, transform 0.18s',
        }}
      >
        <span
          style={{
            width: user ? '28px' : '24px',
            height: user ? '28px' : '24px',
            borderRadius: '50%',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: user
              ? '#111111'
              : 'rgba(8, 6, 13, 0.06)',
            color: user ? '#ffffff' : '#3d3845',
            fontSize: '12px',
            fontWeight: 700,
            boxShadow: user ? '0 6px 14px rgba(8, 6, 13, 0.16)' : 'none',
          }}
        >
          {user ? initial : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4" />
              <path d="M10 17l5-5-5-5" />
              <path d="M15 12H3" />
            </svg>
          )}
        </span>
        <span style={{ color: '#111111', fontSize: '13px', fontWeight: 700, letterSpacing: '-0.01em', lineHeight: 1 }}>
          {loading ? '同步中...' : user?.username ?? '登录'}
        </span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.18 }}
            style={{
              position: 'absolute',
              top: 'calc(100% + 10px)',
              right: 0,
              zIndex: 120,
              background: 'rgba(255,255,255,0.96)',
              border: '1px solid rgba(8, 6, 13, 0.08)',
              borderRadius: '18px',
              padding: '14px',
              boxShadow: '0 18px 40px rgba(8, 6, 13, 0.12)',
              backdropFilter: 'blur(12px)',
            }}
          >
            <AccountPanel compact />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function NavigationRail() {
  return (
    <>
      <aside
        style={{
          width: `${SIDEBAR_WIDTH}px`,
          background: '#f3f3f5',
          padding: '20px 14px 20px 16px',
          boxSizing: 'border-box',
          display: 'flex',
          flexDirection: 'column',
          gap: '20px',
          position: 'sticky',
          top: 0,
          alignSelf: 'flex-start',
          height: '100vh',
        }}
        className="desktop-sidebar"
      >
        <div style={{ fontSize: '24px', lineHeight: 1.04, letterSpacing: '-0.05em', color: '#111111', fontWeight: 700, marginBottom: '18px' }}>
          Podcasts
        </div>
        <div style={{ display: 'grid', gap: '18px' }}>
          {navGroups.map((group) => (
            <div key={group.title}>
              <div style={{ fontSize: '11px', color: '#6b6375', marginBottom: '6px', paddingLeft: '10px', fontWeight: 600 }}>
                {group.title}
              </div>
              <nav style={{ display: 'grid', gap: '2px' }}>
                {group.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === '/'}
                    style={({ isActive }) => ({
                      textDecoration: 'none',
                      color: isActive ? '#111111' : '#3d3845',
                      background: isActive ? 'rgba(170, 59, 255, 0.14)' : 'transparent',
                      borderRadius: '10px',
                      padding: '8px 10px',
                      fontWeight: isActive ? 600 : 500,
                      fontSize: '14px',
                      transition: 'background 0.2s, color 0.2s, transform 0.2s',
                      boxShadow: isActive ? 'inset 0 0 0 1px rgba(170, 59, 255, 0.18)' : 'none',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                    })}
                  >
                    {navIcons[item.to]}
                    {item.label}
                  </NavLink>
                ))}
              </nav>
            </div>
          ))}
        </div>

      </aside>

      <header
          style={{
            display: 'none',
            padding: '12px 16px',
            borderBottom: '1px solid var(--border)',
            background: '#f5f5f7',
            position: 'sticky',
            top: 0,
            zIndex: 100,
          backdropFilter: 'blur(10px)',
        }}
        className="mobile-topbar"
      >
        <div style={{ display: 'flex', gap: '10px', overflowX: 'auto', paddingBottom: '6px' }}>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              style={({ isActive }) => ({
                textDecoration: 'none',
                color: isActive ? 'var(--text-h)' : 'var(--text)',
                background: isActive ? 'var(--accent-bg)' : 'transparent',
                border: `1px solid ${isActive ? 'var(--accent-border)' : 'var(--border)'}`,
                borderRadius: '999px',
                padding: '8px 14px',
                whiteSpace: 'nowrap',
                fontSize: '14px',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              })}
            >
              {navIcons[item.to]}
              {item.label}
            </NavLink>
          ))}
        </div>
      </header>
    </>
  )
}

function AnimatedOutlet() {
  const location = useLocation()
  const isPodcastDetailPage = Boolean(matchPath('/podcasts/:id', location.pathname))

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -12 }}
        transition={{ duration: 0.2 }}
        style={{ flexGrow: 1, position: 'relative' }}
      >
        {!isPodcastDetailPage && (
          <div style={{ position: 'absolute', top: '18px', right: '24px', zIndex: 20 }}>
            <AccountEntry />
          </div>
        )}
        <Outlet />
      </motion.div>
    </AnimatePresence>
  )
}

function App() {
  const location = useLocation()
  const isPodcastDetailPage = Boolean(matchPath('/podcasts/:id', location.pathname))

  return (
    <UserProvider>
      <PlayerProvider>
        <FavoritesProvider>
          <div style={{ minHeight: '100vh', display: 'flex', background: '#ffffff' }}>
            <NavigationRail />
            <div
              style={{
                flex: 1,
                minWidth: 0,
                paddingBottom: isPodcastDetailPage ? '0' : '100px',
                background: '#ffffff',
                overflowX: 'hidden',
              }}
            >
              <div className="desktop-ui-scale">
                <AnimatedOutlet />
              </div>
            </div>
            {!isPodcastDetailPage && <GlobalPlayer sidebarWidth={SIDEBAR_WIDTH} desktopScale={DESKTOP_UI_SCALE} />}
          </div>
          <style>{`
            .desktop-ui-scale {
              width: calc(100% / ${DESKTOP_UI_SCALE});
              min-height: calc(100vh / ${DESKTOP_UI_SCALE});
              transform: scale(${DESKTOP_UI_SCALE});
              transform-origin: top left;
            }

            @media (max-width: 900px) {
              .desktop-sidebar {
                display: none !important;
              }

              .mobile-topbar {
                display: block !important;
              }

              .desktop-ui-scale {
                width: 100%;
                min-height: auto;
                transform: none;
              }
            }
          `}</style>
        </FavoritesProvider>
      </PlayerProvider>
    </UserProvider>
  )
}

export default App
