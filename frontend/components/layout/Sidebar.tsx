'use client'

import React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LucideIcon, Zap, LogOut, X } from 'lucide-react'
import { cn } from '../../lib/utils'
import { getInitials } from '../../lib/utils'
import { User } from '@/types'

interface NavItem {
  label: string
  href: string
  icon: LucideIcon
  badge?: string | number
}

interface SidebarProps {
  navItems: NavItem[]
  user: User | null
  onLogout: () => void
  isOpen: boolean
  onClose: () => void
  isAdmin?: boolean
}

export function Sidebar({ navItems, user, onLogout, isOpen, onClose, isAdmin = false }: SidebarProps) {
  const pathname = usePathname()

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-0 z-50 flex h-full w-64 flex-col bg-background-surface border-r border-border transition-transform duration-300 ease-in-out',
          'lg:relative lg:translate-x-0',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Logo */}
        <div className="flex items-center justify-between px-5 py-5 border-b border-border">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className={cn(
              'flex h-8 w-8 items-center justify-center rounded-lg shadow-lg',
              isAdmin
                ? 'bg-gradient-to-br from-purple-600 to-pink-600 shadow-purple-500/25'
                : 'bg-gradient-to-br from-indigo-600 to-purple-600 shadow-indigo-500/25'
            )}>
              <Zap size={16} className="text-white" />
            </div>
            <div>
              <span className="text-sm font-bold text-slate-100 block leading-tight">SupportPilot</span>
              <span className="text-[10px] text-slate-500 uppercase tracking-wider leading-tight">
                {isAdmin ? 'Admin Panel' : 'AI Platform'}
              </span>
            </div>
          </Link>
          <button
            onClick={onClose}
            className="lg:hidden p-1 rounded-md text-slate-500 hover:text-slate-300"
          >
            <X size={18} />
          </button>
        </div>

        {isAdmin && (
          <div className="px-5 py-2">
            <span className="inline-flex items-center rounded-full bg-purple-500/20 border border-purple-500/30 px-2.5 py-0.5 text-xs font-semibold text-purple-400 uppercase tracking-wider">
              Admin
            </span>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
            const Icon = item.icon

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onClose}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150 group',
                  isActive
                    ? isAdmin
                      ? 'bg-purple-500/15 text-purple-300 border border-purple-500/20'
                      : 'bg-accent/15 text-accent-light border border-accent/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                )}
              >
                <Icon
                  size={17}
                  className={cn(
                    'shrink-0 transition-colors',
                    isActive
                      ? isAdmin ? 'text-purple-400' : 'text-accent-light'
                      : 'text-slate-500 group-hover:text-slate-300'
                  )}
                />
                <span className="flex-1">{item.label}</span>
                {item.badge !== undefined && (
                  <span className={cn(
                    'ml-auto inline-flex h-5 min-w-[20px] items-center justify-center rounded-full px-1.5 text-[10px] font-bold',
                    isAdmin ? 'bg-purple-500/20 text-purple-400' : 'bg-accent/20 text-accent-light'
                  )}>
                    {item.badge}
                  </span>
                )}
              </Link>
            )
          })}
        </nav>

        {/* User section */}
        {user && (
          <div className="border-t border-border p-4">
            <div className="flex items-center gap-3">
              <div className={cn(
                'flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold text-white shrink-0',
                isAdmin
                  ? 'bg-gradient-to-br from-purple-500 to-pink-500'
                  : 'bg-gradient-to-br from-indigo-500 to-purple-500'
              )}>
                {getInitials(user.name)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-200 truncate">{user.name}</p>
                <p className="text-xs text-slate-500 truncate">{user.email}</p>
              </div>
              <button
                onClick={onLogout}
                className="shrink-0 p-1.5 rounded-md text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-all"
                title="Logout"
              >
                <LogOut size={15} />
              </button>
            </div>
          </div>
        )}
      </aside>
    </>
  )
}
