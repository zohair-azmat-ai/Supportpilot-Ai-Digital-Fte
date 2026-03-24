'use client'

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { User, Role } from '../types'
import { authApi } from '../lib/api'
import {
  getToken,
  setToken,
  setStoredUser,
  getStoredUser,
  clearAuth,
} from '../lib/auth'

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (name: string, email: string, password: string, role: Role) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    const token = getToken()
    if (!token) {
      setIsLoading(false)
      return
    }
    try {
      const me = await authApi.getMe()
      setUser(me)
      setStoredUser(me)
    } catch {
      clearAuth()
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    const stored = getStoredUser()
    if (stored) {
      setUser(stored)
    }
    refreshUser()
  }, [refreshUser])

  const login = async (email: string, password: string) => {
    const res = await authApi.login({ email, password })
    setToken(res.access_token)
    setStoredUser(res.user)
    setUser(res.user)
  }

  const signup = async (name: string, email: string, password: string, role: Role) => {
    const res = await authApi.signup({ name, email, password, role })
    setToken(res.access_token)
    setStoredUser(res.user)
    setUser(res.user)
  }

  const logout = () => {
    clearAuth()
    setUser(null)
    window.location.href = '/login'
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        signup,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuthContext(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuthContext must be used within AuthProvider')
  }
  return ctx
}
