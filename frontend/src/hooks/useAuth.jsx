import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import apiClient from '../api/client'

const AuthContext = createContext(null)
export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem('viva_user') || 'null'))
  const [loading, setLoading] = useState(Boolean(localStorage.getItem('viva_access_token')))
  const logout = () => { localStorage.removeItem('viva_access_token'); localStorage.removeItem('viva_user'); setUser(null); setLoading(false) }
  useEffect(() => {
    const unauthorized = () => logout()
    window.addEventListener('viva:unauthorized', unauthorized)
    const token = localStorage.getItem('viva_access_token')
    if (token) apiClient.get('/api/auth/me').then(({ data }) => { setUser(data); localStorage.setItem('viva_user', JSON.stringify(data)) }).catch(logout).finally(() => setLoading(false))
    return () => window.removeEventListener('viva:unauthorized', unauthorized)
  }, [])
  const login = async (email, password) => { const { data } = await apiClient.post('/api/auth/login', { email, password }); localStorage.setItem('viva_access_token', data.access_token); localStorage.setItem('viva_user', JSON.stringify(data.user)); setUser(data.user); return data.user }
  const register = async ({ full_name, email, password }) => { const { data } = await apiClient.post('/api/auth/register', { full_name, email, password, role: 'student' }); localStorage.setItem('viva_access_token', data.access_token); localStorage.setItem('viva_user', JSON.stringify(data.user)); setUser(data.user); return data.user }
  const value = useMemo(() => ({ user, isAuthenticated: Boolean(user), login, register, logout, loading }), [user, loading])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
export function useAuth() { return useContext(AuthContext) }
