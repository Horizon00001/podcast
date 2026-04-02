import { Link, Outlet } from 'react-router-dom'

function App() {
  return (
    <>
      <header style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <Link to="/">播客列表</Link>
        <Link to="/generate">手动生成</Link>
      </header>
      <Outlet />
    </>
  )
}

export default App
