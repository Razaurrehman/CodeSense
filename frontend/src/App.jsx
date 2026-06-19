import { useAuth } from './hooks/useAuth'
import LoginPage   from './pages/LoginPage'
import Dashboard   from './pages/Dashboard'

export default function App() {
  const { user, loading, login, logout } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="flex items-center gap-3 text-slate-400">
          <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="30 60" />
          </svg>
          <span className="text-sm">Loading…</span>
        </div>
      </div>
    )
  }

  if (!user) return <LoginPage onLogin={login} />

  return <Dashboard user={user} onLogout={logout} />
}
