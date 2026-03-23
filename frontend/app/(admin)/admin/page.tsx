'use client'

import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import {
  Users,
  Ticket,
  AlertCircle,
  MessageCircle,
  Activity,
  CheckCircle,
  ArrowRight,
  RefreshCw,
  BarChart3,
  TrendingUp,
} from 'lucide-react'
import { adminApi } from '@/lib/api'
import { AdminStats, Ticket as TicketType, Conversation } from '@/types'
import { StatsCard } from '@/components/dashboard/StatsCard'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { StatusBadge, PriorityBadge, ConversationStatusBadge, ChannelBadge } from '@/components/ui/Badge'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { formatDate, truncate, formatRelativeDate } from '@/lib/utils'
import { useToast } from '@/context/ToastContext'

export default function AdminOverviewPage() {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [tickets, setTickets] = useState<TicketType[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const toast = useToast()

  const fetchData = async (isRefresh = false) => {
    setLoading(true)
    setError(null)
    try {
      const [statsData, ticketsData, convsData] = await Promise.all([
        adminApi.getStats(),
        adminApi.getTickets(),
        adminApi.getConversations(),
      ])
      setStats(statsData)
      setTickets(ticketsData)
      setConversations(convsData)
      if (isRefresh) toast.success('Dashboard refreshed')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load data'
      setError(msg)
      if (isRefresh) toast.error('Failed to refresh dashboard')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  if (loading) return <LoadingSpinner center size="lg" label="Loading admin data..." />

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 min-h-[300px]">
        <p className="text-red-400 text-sm">{error}</p>
        <Button variant="outline" icon={RefreshCw} onClick={() => fetchData()}>
          Retry
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Admin Overview</h1>
          <p className="text-sm text-slate-500 mt-0.5">Platform health and activity summary</p>
        </div>
        <Button variant="outline" size="sm" icon={RefreshCw} onClick={() => fetchData(true)}>
          Refresh
        </Button>
      </div>

      {/* Stats grid */}
      {stats && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
            <StatsCard
              label="Total Users"
              value={stats.total_users}
              icon={Users}
              color="indigo"
            />
            <StatsCard
              label="Total Tickets"
              value={stats.total_tickets}
              icon={Ticket}
              color="purple"
            />
            <StatsCard
              label="Open Tickets"
              value={stats.open_tickets}
              icon={AlertCircle}
              color="amber"
            />
            <StatsCard
              label="Conversations"
              value={stats.total_conversations}
              icon={MessageCircle}
              color="blue"
            />
            <StatsCard
              label="Active Chats"
              value={stats.active_conversations}
              icon={Activity}
              color="emerald"
            />
            <StatsCard
              label="Resolved Today"
              value={stats.resolved_today}
              icon={CheckCircle}
              color="emerald"
            />
          </div>

          {/* Resolution rate banner */}
          {stats.total_tickets > 0 && (
            <div className="flex items-center gap-4 rounded-xl border border-emerald-500/20 bg-gradient-to-r from-emerald-500/10 to-transparent px-5 py-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-500/20">
                <TrendingUp size={18} className="text-emerald-400" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-semibold text-slate-100">
                  Resolution Rate:{' '}
                  <span className="text-emerald-400">
                    {Math.round(
                      ((stats.total_tickets - stats.open_tickets) / stats.total_tickets) * 100
                    )}%
                  </span>
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {stats.total_tickets - stats.open_tickets} of {stats.total_tickets} tickets resolved or closed
                </p>
              </div>
              <Link href="/admin/analytics">
                <button className="text-xs text-slate-500 hover:text-accent flex items-center gap-1 transition-colors">
                  <BarChart3 size={13} />
                  Analytics
                </button>
              </Link>
            </div>
          )}
        </>
      )}

      {/* Quick navigation */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Manage Tickets', href: '/admin/tickets', icon: Ticket, color: 'text-purple-400', bg: 'bg-purple-500/10 border-purple-500/20' },
          { label: 'Conversations', href: '/admin/conversations', icon: MessageCircle, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20' },
          { label: 'User Management', href: '/admin/users', icon: Users, color: 'text-indigo-400', bg: 'bg-indigo-500/10 border-indigo-500/20' },
          { label: 'Analytics', href: '/admin/analytics', icon: BarChart3, color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20' },
        ].map((item) => {
          const Icon = item.icon
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-xl border p-4 transition-all hover:scale-[1.02] ${item.bg}`}
            >
              <Icon size={16} className={item.color} />
              <span className="text-sm font-medium text-slate-300">{item.label}</span>
              <ArrowRight size={13} className="ml-auto text-slate-600" />
            </Link>
          )
        })}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Recent Tickets */}
        <Card
          title="Recent Tickets"
          description="Latest support tickets across all users"
          action={
            <Link href="/admin/tickets">
              <Button variant="ghost" size="sm" icon={ArrowRight} iconPosition="right">
                View all
              </Button>
            </Link>
          }
          noPadding
        >
          <div className="divide-y divide-border/50">
            {tickets.slice(0, 5).map((ticket) => (
              <div key={ticket.id} className="flex items-center justify-between px-5 py-3 hover:bg-background-elevated/30 transition-colors">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-200 truncate">{truncate(ticket.title, 40)}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <PriorityBadge priority={ticket.priority} />
                    <span className="text-[10px] text-slate-600">{formatDate(ticket.created_at)}</span>
                  </div>
                </div>
                <StatusBadge status={ticket.status} />
              </div>
            ))}
            {tickets.length === 0 && (
              <div className="py-8 text-center text-sm text-slate-500">No tickets yet</div>
            )}
          </div>
        </Card>

        {/* Recent Conversations */}
        <Card
          title="Recent Conversations"
          description="Latest support conversations"
          action={
            <Link href="/admin/conversations">
              <Button variant="ghost" size="sm" icon={ArrowRight} iconPosition="right">
                View all
              </Button>
            </Link>
          }
          noPadding
        >
          <div className="divide-y divide-border/50">
            {conversations.slice(0, 5).map((conv) => (
              <div key={conv.id} className="flex items-center justify-between px-5 py-3 hover:bg-background-elevated/30 transition-colors">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-200 truncate">
                    {conv.subject || 'Untitled Conversation'}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <ChannelBadge channel={conv.channel} />
                    <span className="text-[10px] text-slate-600">{formatRelativeDate(conv.created_at)}</span>
                  </div>
                </div>
                <ConversationStatusBadge status={conv.status} />
              </div>
            ))}
            {conversations.length === 0 && (
              <div className="py-8 text-center text-sm text-slate-500">No conversations yet</div>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}
