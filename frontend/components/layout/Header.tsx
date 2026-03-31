'use client'

import React, { useEffect, useState } from 'react'
import { Menu, Bell, LogOut } from 'lucide-react'
import { cn } from '../../lib/utils'
import { getInitials } from '../../lib/utils'
import { User } from '../../types'

type BuildStatus = 'live' | 'building' | 'offline'

function useBuildStatus(): BuildStatus {
  const [status, setStatus] = useState<BuildStatus>('building')

  useEffect(() => {
    const check = async () => {
      try {
        // NEXT_PUBLIC_API_URL points to the /api/v1 prefix (e.g. https://host/api/v1).
        // The /health endpoint lives at the root — not under /api/v1 — so strip
        // the suffix before appending it.
        const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
        const rootUrl = apiBase.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '')
        const res = await fetch(`${rootUrl}/health`, { cache: 'no-store' })
        // Treat any 2xx response as live — no strict body parsing needed.
        setStatus(res.ok ? 'live' : 'offline')
      } catch {
        setStatus('offline')
      }
    }

    check()
    const id = setInterval(check, 10_000)
    return () => clearInterval(id)
  }, [])

  return status
}

const STATUS_CONFIG: Record<BuildStatus, { dot: string; label: string }> = {
  live:     { dot: 'bg-emerald-400', label: 'Live' },
  building: { dot: 'bg-yellow-400 animate-pulse', label: 'Rebuilding...' },
  offline:  { dot: 'bg-red-500', label: 'Offline' },
}

interface HeaderProps {
  title?: string
  user: User | null
  onMenuClick: () => void
  onLogout: () => void
  isAdmin?: boolean
}

export function Header({ title, user, onMenuClick, onLogout, isAdmin = false }: HeaderProps) {
  const buildStatus = useBuildStatus()
  const { dot, label } = STATUS_CONFIG[buildStatus]

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-background/80 backdrop-blur-md px-4 lg:px-6">
      {/* Left: menu + title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="lg:hidden p-2 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-white/5 transition-colors"
          aria-label="Open menu"
        >
          <Menu size={20} />
        </button>
        {title && (
          <h1 className="text-base font-semibold text-slate-100 hidden sm:block">{title}</h1>
        )}
      </div>

      {/* Centre: system status badge */}
      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-background-surface border border-border text-xs text-slate-400">
        <span className={cn('h-2 w-2 rounded-full shrink-0', dot)} />
        <span>System Status: {label}</span>
      </div>

      {/* Right: notifications + user */}
      <div className="flex items-center gap-2">
        <button className="relative p-2 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-white/5 transition-colors">
          <Bell size={18} />
          <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-accent" />
        </button>

        <div className="flex items-center gap-2 ml-1">
          {user && (
            <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-background-surface border border-border">
              <div className={cn(
                'flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold text-white shrink-0',
                isAdmin
                  ? 'bg-gradient-to-br from-purple-500 to-pink-500'
                  : 'bg-gradient-to-br from-indigo-500 to-purple-500'
              )}>
                {getInitials(user.name)}
              </div>
              <div className="hidden sm:block">
                <p className="text-xs font-medium text-slate-200 leading-tight">{user.name}</p>
                <p className="text-[10px] text-slate-500 capitalize leading-tight">{user.role}</p>
              </div>
            </div>
          )}
          <button
            onClick={onLogout}
            className="p-2 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
            title="Logout"
          >
            <LogOut size={17} />
          </button>
        </div>
      </div>
    </header>
  )
}
