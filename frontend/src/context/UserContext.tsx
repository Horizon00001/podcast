import { createContext, useContext, useEffect, useMemo, useState } from 'react'

import { api } from '../services/api'

type AppUser = {
  id: number
  username: string
  email: string
}

type UserContextValue = {
  user: AppUser | null
  loading: boolean
  error: string
  usernameDraft: string
  setUsernameDraft: (value: string) => void
  saveUsername: () => Promise<void>
}

const USERNAME_KEY = 'currentUsername'

const UserContext = createContext<UserContextValue | undefined>(undefined)

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [usernameDraft, setUsernameDraft] = useState(() => localStorage.getItem(USERNAME_KEY) ?? 'demo')

  const syncUser = async (username: string) => {
    setLoading(true)
    setError('')
    try {
      const result = await api.ensureUser(username)
      setUser({ id: result.id, username: result.username, email: result.email })
      localStorage.setItem(USERNAME_KEY, result.username)
      setUsernameDraft(result.username)
    } catch (syncError) {
      setError((syncError as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void syncUser(usernameDraft)
  }, [])

  const saveUsername = async () => {
    await syncUser(usernameDraft)
  }

  const value = useMemo(
    () => ({ user, loading, error, usernameDraft, setUsernameDraft, saveUsername }),
    [user, loading, error, usernameDraft],
  )

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>
}

export function useUser() {
  const context = useContext(UserContext)
  if (!context) {
    throw new Error('useUser must be used within a UserProvider')
  }
  return context
}
