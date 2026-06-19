import { useState, useEffect } from 'react'

export function useAuth() {
  const [user,    setUser]    = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/v1/auth/me', { credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
      .then(data => { setUser(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  function login() {
    window.location.href = '/api/v1/auth/github'
  }

  async function logout() {
    await fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'include' })
    setUser(null)
  }

  return { user, loading, login, logout }
}
