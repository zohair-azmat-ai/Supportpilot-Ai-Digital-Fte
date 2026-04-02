'use client'

import React, { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  LayoutDashboard,
  MessageSquarePlus,
  MessageCircle,
  Ticket,
  HeadphonesIcon,
  Settings,
  CreditCard,
} from 'lucide-react'
import { DashboardLayout } from '../../components/layout/DashboardLayout'
import { useAuth } from '../../hooks/useAuth'
import { PageLoader } from '../../components/ui/LoadingSpinner'

const navItems = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { label: 'New Chat', href: '/chat/new', icon: MessageSquarePlus },
  { label: 'Conversations', href: '/chat', icon: MessageCircle },
  { label: 'My Tickets', href: '/tickets', icon: Ticket },
  { label: 'Submit Request', href: '/support', icon: HeadphonesIcon },
  { label: 'Subscription', href: '/billing', icon: CreditCard },
  { label: 'Settings', href: '/settings', icon: Settings },
]

export default function CustomerLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading, isAuthenticated, logout } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.replace('/login')
      } else if (user?.role === 'admin') {
        router.replace('/admin')
      }
    }
  }, [isLoading, isAuthenticated, user, router])

  if (isLoading) return <PageLoader label="Loading dashboard..." />
  if (!isAuthenticated || !user || user.role === 'admin') return null

  return (
    <DashboardLayout
      navItems={navItems}
      user={user}
      onLogout={logout}
      isAdmin={false}
    >
      {children}
    </DashboardLayout>
  )
}
