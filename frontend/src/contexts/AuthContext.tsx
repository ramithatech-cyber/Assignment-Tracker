import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { api, tokenStore } from '../api/client'
import type { Role, User } from '../types'

interface AuthValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<User>
  register: (payload: {
    email: string
    password: string
    full_name: string
    role: Role
    signup_code?: string
  }) => Promise<User>
  logout: () => void
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // Restore the session on boot: the token lives in localStorage, but only the
  // server can say whether it is still valid.
  useEffect(() => {
    if (!tokenStore.get()) {
      setLoading(false)
      return
    }
    api
      .me()
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const token = await api.login(email, password)
    tokenStore.set(token.access_token)
    setUser(token.user)
    return token.user
  }, [])

  const register = useCallback(
    async (payload: {
      email: string
      password: string
      full_name: string
      role: Role
      signup_code?: string
    }) => {
      const token = await api.register(payload)
      tokenStore.set(token.access_token)
      setUser(token.user)
      return token.user
    },
    [],
  )

  const logout = useCallback(() => {
    tokenStore.clear()
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}
