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
  CreditCard,
  MessageSquare,
  XCircle,
  AlertTriangle,
  Zap,
} from 'lucide-react'
import { adminApi, billingApi } from '../../../lib/api'
import { AdminStats, Ticket as TicketType, Conversation, BillingSummary, UsageCounter } from '../../../types'
import { StatsCard } from '../../../components/dashboard/StatsCard'
import { Card } from '../../../components/ui/Card'
import { Button } from '../../../components/ui/Button'
import { StatusBadge, PriorityBadge, ConversationStatusBadge, ChannelBadge } from '../../../components/ui/Badge'
import { LoadingSpinner } from '../../../components/ui/LoadingSpinner'
import { formatDate, truncate, formatRelativeDate } from '../../../lib/utils'
import { useToast } from '../../../context/ToastContext'
import { cn } from '../../../lib/utils'

// ── Billing status banner ────────────────────────────────────────────────────

const TIER_STYLES: Record<string, { badge: string; dot: string }> = {
  free:  { badge: 'bg-slate-700/50 text-slate-400 border-slate-600/50',          dot: 'bg-slate-400' },
  pro:   { badge: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/25',        dot: 'bg-indigo-400' },
  team:  { badge: 'bg-purple-500/15 text-purple-300 border-purple-500/25',        dot: 'bg-purple-400' },
}

function MiniUsageBar({ counter, label, icon: Icon }: {
  counter: UsageCounter
  label: string
  icon: React.ElementType
}) {
  const pct = counter.unlimited ? 0 : Math.min(counter.pct, 100)
  const barColor = counter.hard_blocked ? 'bg-red-500' : counter.soft_warning ? 'bg-amber-500' : 'bg-emerald-500'
  const textColor = counter.hard_blocked ? 'text-red-400' : counter.soft_warning ? 'text-amber-400' : 'text-slate-400'

  return (
    <div className="space-y-1.5 min-w-0">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <Icon size={11} className="shrink-0 text-slate-500" />
          <span className="text-[11px] text-slate-500 truncate">{label}</span>
        </div>
        <span className={cn('text-[11px] font-semibold tabular-nums shrink-0', textColor)}>
          {counter.unlimited
            ? <span className="text-slate-500">∞</span>
            : `${counter.used.toLocaleString()} / ${counter.limit.toLocaleString()}`}
        </span>
      </div>
      {!counter.unlimited && (
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-background-elevated">
          <div className={cn('h-full rounded-full transition-all duration-500', barColor)} style={{ width: `${pct}%` }} />
        </div>
      )}
    </div>
  )
}

function BillingStatusBanner({ summary }: { summary: BillingSummary }) {
  const { current_plan, current_plan_display, usage } = summary
  const style = TIER_STYLES[current_plan] ?? TIER_STYLES.free
  const hardBlocked = usage.messages.hard_blocked || usage.tickets.hard_blocked
  const softWarning = !hardBlocked && (usage.messages.soft_warning || usage.tickets.soft_warning)

  return (
    <div className={cn(
      'flex flex-wrap items-center gap-x-6 gap-y-3 rounded-xl border px-5 py-4 transition-colors',
      hardBlocked
        ? 'border-red-500/25 bg-red-500/8'
        : softWarning
        ? 'border-amber-500/25 bg-amber-500/8'
        : 'border-border bg-background-surface',
    )}>
      {/* Plan badge */}
      <div className="flex items-center gap-2.5 shrink-0">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-600/40 to-purple-600/40 border border-indigo-500/20">
          <CreditCard size={14} className="text-indigo-400" />
        </div>
        <div>
          <p className="text-[10px] text-slate-600 uppercase tracking-wider">Active Plan</p>
          <span className={cn(
            'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold',
            style.badge,
          )}>
            <span className={cn('h-1.5 w-1.5 rounded-full', style.dot)} />
            {current_plan_display}
          </span>
        </div>
      </div>

      {/* Divider */}
      <div className="hidden sm:block h-8 w-px bg-border/60 shrink-0" />

      {/* Usage bars */}
      <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 min-w-[200px]">
        <MiniUsageBar counter={usage.messages} label="AI Messages" icon={MessageSquare} />
        <MiniUsageBar counter={usage.tickets}  label="Tickets"     icon={Ticket} />
      </div>

      {/* Divider */}
      <div className="hidden sm:block h-8 w-px bg-border/60 shrink-0" />

      {/* State badge + link */}
      <div className="flex items-center gap-3 shrink-0">
        {hardBlocked ? (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-red-500/15 border border-red-500/25 px-2.5 py-1 text-[11px] font-semibold text-red-400">
            <XCircle size={11} /> Limit reached
          </span>
        ) : softWarning ? (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/15 border border-amber-500/25 px-2.5 py-1 text-[11px] font-semibold text-amber-400">
            <AlertTriangle size={11} /> Near limit
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 border border-emerald-500/25 px-2.5 py-1 text-[11px] font-semibold text-emerald-400">
            <Zap size={11} /> All good
          </span>
        )}
        <Link href="/admin/billing">
          <button className="flex items-center gap-1.5 text-[11px] font-medium text-slate-500 hover:text-accent transition-colors">
            View Billing <ArrowRight size={11} />
          </button>
        </Link>
      </div>
    </div>
  )
}

export default function AdminOverviewPage() {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [tickets, setTickets] = useState<TicketType[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [billing, setBilling] = useState<BillingSummary | null>(null)
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

    // Billing is fetched separately — a failure here must not break the dashboard
    billingApi.getSummary().then(setBilling).catch(() => {/* non-fatal */})
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

      {/* Billing status */}
      {billing && <BillingStatusBanner summary={billing} />}

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
