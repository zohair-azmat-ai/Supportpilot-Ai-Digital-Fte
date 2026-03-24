'use client'

import React, { useState } from 'react'
import { LucideIcon } from 'lucide-react'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { User } from '../../types'

interface NavItem {
  label: string
  href: string
  icon: LucideIcon
  badge?: string | number
}

interface DashboardLayoutProps {
  children: React.ReactNode
  navItems: NavItem[]
  user: User | null
  onLogout: () => void
  title?: string
  isAdmin?: boolean
}

export function DashboardLayout({
  children,
  navItems,
  user,
  onLogout,
  title,
  isAdmin = false,
}: DashboardLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <Sidebar
        navItems={navItems}
        user={user}
        onLogout={onLogout}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        isAdmin={isAdmin}
      />
      <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
        <Header
          title={title}
          user={user}
          onMenuClick={() => setSidebarOpen(true)}
          onLogout={onLogout}
          isAdmin={isAdmin}
        />
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
