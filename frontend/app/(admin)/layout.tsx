'use client'

import React, { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  LayoutDashboard,
  Ticket,
  MessageCircle,
  Users,
  BarChart3,
  CreditCard,
  ListChecks,
} from 'lucide-react'
import { DashboardLayout } from '../../components/layout/DashboardLayout'
import { useAuth } from '../../hooks/useAuth'
import { PageLoader } from '../../components/ui/LoadingSpinner'

const navItems = [
  { label: 'Overview', href: '/admin', icon: LayoutDashboard },
  { label: 'Queue', href: '/admin/queue', icon: ListChecks },
  { label: 'Tickets', href: '/admin/tickets', icon: Ticket },
  { label: 'Conversations', href: '/admin/conversations', icon: MessageCircle },
  { label: 'Users', href: '/admin/users', icon: Users },
  { label: 'Analytics', href: '/admin/analytics', icon: BarChart3 },
  { label: 'Plans & Billing', href: '/admin/billing', icon: CreditCard },
]

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading, isAuthenticated } = useAuth()
  const router = useRouter()
  const { logout } = useAuth()

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.replace('/login')
      } else if (user && user.role !== 'admin') {
        router.replace('/dashboard')
      }
    }
  }, [isLoading, isAuthenticated, user, router])

  if (isLoading) return <PageLoader label="Loading admin panel..." />
  if (!isAuthenticated || !user || user.role !== 'admin') return null

  return (
    <DashboardLayout
      navItems={navItems}
      user={user}
      onLogout={logout}
      isAdmin={true}
    >
      {children}
    </DashboardLayout>
  )
}
