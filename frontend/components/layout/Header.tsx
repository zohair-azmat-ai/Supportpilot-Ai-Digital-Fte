'use client'

import React from 'react'
import { Menu, Bell, LogOut } from 'lucide-react'
import { cn } from '../../lib/utils'
import { getInitials } from '../../lib/utils'
import { User } from '../../types'

interface HeaderProps {
  title?: string
  user: User | null
  onMenuClick: () => void
  onLogout: () => void
  isAdmin?: boolean
}

export function Header({ title, user, onMenuClick, onLogout, isAdmin = false }: HeaderProps) {
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
