'use client'

import React, { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import {
  AlertTriangle, ArrowUpCircle, Bot, Clock, Cpu, ExternalLink,
  Headphones, Hourglass, Loader2, RefreshCw, ShieldAlert, Inbox, Zap, Users,
} from 'lucide-react'
import { adminApi } from '../../../../lib/api'
import { QueueItem } from '../../../../types'
import { ChannelBadge } from '../../../../components/ui/Badge'
import { Button } from '../../../../components/ui/Button'
import { LoadingSpinner } from '../../../../components/ui/LoadingSpinner'
import { EmptyState } from '../../../../components/ui/EmptyState'
import { useToast } from '../../../../context/ToastContext'
import { cn, formatRelativeDate } from '../../../../lib/utils'

// ── SLA config ────────────────────────────────────────────────────────────────
const SLA_MINUTES: Record<string, number> = {
  urgent:  30,
  high:    120,
  medium:  480,
  low:     1440,
}

type SlaState = 'on_time' | 'nearing' | 'overdue'

function getSlaState(item: QueueItem): SlaState {
  const tier = item.ticket_priority ?? item.urgency ?? 'medium'
  const slaMs = (SLA_MINUTES[tier] ?? SLA_MINUTES.medium) * 60_000
  const nearingMs = slaMs * 0.75
  const elapsedMs = Date.now() - new Date(item.updated_at).getTime()
  if (elapsedMs >= slaMs) return 'overdue'
  if (elapsedMs >= nearingMs) return 'nearing'
  return 'on_time'
}

function timeUntilSla(item: QueueItem): string {
  const tier = item.ticket_priority ?? item.urgency ?? 'medium'
  const slaMs = (SLA_MINUTES[tier] ?? SLA_MINUTES.medium) * 60_000
  const elapsedMs = Date.now() - new Date(item.updated_at).getTime()
  const remaining = slaMs - elapsedMs
  if (remaining <= 0) {
    const over = Math.round(-remaining / 60_000)
    return over < 60 ? `${over}m overdue` : `${Math.round(over / 60)}h overdue`
  }
  const mins = Math.round(remaining / 60_000)
  return mins < 60 ? `${mins}m left` : `${Math.round(mins / 60)}h left`
}

const SLA_CONFIG: Record<SlaState, { cls: string; dot: string }> = {
  on_time: { cls: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/8', dot: 'bg-emerald-400' },
  nearing: { cls: 'text-amber-400  border-amber-500/20  bg-amber-500/8',    dot: 'bg-amber-400'  },
  overdue: { cls: 'text-red-400    border-red-500/20    bg-red-500/8',      dot: 'bg-red-400'    },
}

function SlaBadge({ item }: { item: QueueItem }) {
  const state = getSlaState(item)
  const cfg = SLA_CONFIG[state]
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold', cfg.cls)}>
      <span className={cn('h-1.5 w-1.5 rounded-full', cfg.dot)} />
      {timeUntilSla(item)}
    </span>
  )
}

// ── Agent badge ───────────────────────────────────────────────────────────────
const AGENT_BADGE: Record<string, { label: string; cls: string }> = {
  billing:   { label: 'Billing',   cls: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/25' },
  technical: { label: 'Technical', cls: 'bg-amber-500/15  text-amber-300  border-amber-500/25' },
  account:   { label: 'Account',   cls: 'bg-purple-500/15 text-purple-300 border-purple-500/25' },
  general:   { label: 'General',   cls: 'bg-slate-700/40  text-slate-400  border-slate-700/40'  },
}
function AgentBadge({ agent }: { agent: string | null }) {
  if (!agent) return <span className="text-slate-600 text-xs">—</span>
  const meta = AGENT_BADGE[agent] ?? { label: agent, cls: 'bg-slate-700/40 text-slate-400 border-slate-700/40' }
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold', meta.cls)}>
      <Cpu size={9} />
      {meta.label}
    </span>
  )
}

// ── Priority badge ────────────────────────────────────────────────────────────
const PRIORITY_CLS: Record<string, string> = {
  urgent: 'text-red-400 border-red-500/25 bg-red-500/10',
  high:   'text-orange-400 border-orange-500/25 bg-orange-500/10',
  medium: 'text-amber-400 border-amber-500/25 bg-amber-500/10',
  low:    'text-slate-400 border-slate-700/40 bg-slate-700/20',
}
function PriorityBadge({ priority }: { priority: string | null }) {
  if (!priority) return <span className="text-slate-600 text-xs">—</span>
  return (
    <span className={cn('inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold capitalize', PRIORITY_CLS[priority] ?? PRIORITY_CLS.low)}>
      {priority}
    </span>
  )
}

// ── Handoff badge ─────────────────────────────────────────────────────────────
function HandoffBadge({ mode }: { mode: 'ai' | 'human' }) {
  return mode === 'human' ? (
    <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">
      <Headphones size={9} />
      Human
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 rounded-full border border-slate-700/40 bg-slate-700/20 px-2 py-0.5 text-[10px] font-semibold text-slate-400">
      <Bot size={9} />
      AI
    </span>
  )
}

// ── Action button ─────────────────────────────────────────────────────────────
function ActionBtn({
  onClick, disabled, icon: Icon, label, cls,
}: {
  onClick: () => void
  disabled: boolean
  icon: React.ElementType
  label: string
  cls: string
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={label}
      className={cn(
        'inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed',
        cls,
      )}
    >
      {disabled ? <Loader2 size={9} className="animate-spin" /> : <Icon size={9} />}
      {label}
    </button>
  )
}

// ── Priority bump map ─────────────────────────────────────────────────────────
const PRIORITY_NEXT: Record<string, string> = { low: 'medium', medium: 'high', high: 'urgent' }

// ── Queue row ─────────────────────────────────────────────────────────────────
function QueueRow({ item, onRefresh }: { item: QueueItem; onRefresh: () => void }) {
  const [busy, setBusy] = useState(false)
  const toast = useToast()

  const run = useCallback(async (label: string, fn: () => Promise<unknown>) => {
    setBusy(true)
    try {
      await fn()
      onRefresh()
    } catch {
      toast.error(`Failed: ${label}`)
    } finally {
      setBusy(false)
    }
  }, [onRefresh, toast])

  const handleTakeOver = () =>
    run('Take Over', () => adminApi.setHandoffMode(item.conversation_id, 'human').then(() => toast.success('You are now handling this conversation.')))

  const handleReturnToAI = () =>
    run('Return to AI', () => adminApi.setHandoffMode(item.conversation_id, 'ai').then(() => toast.success('AI resumed for this conversation.')))

  const handleRaisePriority = () => {
    const next = PRIORITY_NEXT[item.ticket_priority ?? 'low']
    if (!next || !item.ticket_id) return
    run(`Raise to ${next}`, () =>
      adminApi.updateTicket(item.ticket_id!, { priority: next as 'low' | 'medium' | 'high' | 'urgent' })
        .then(() => toast.success(`Priority raised to ${next}.`))
    )
  }

  const handleMarkWaiting = () =>
    run('Mark Waiting', () =>
      adminApi.updateTicket(item.ticket_id!, { status: 'in_progress' })
        .then(() => toast.success('Marked as waiting for customer.'))
    )

  // Visibility rules
  const canTakeOver      = item.handoff_mode === 'ai'
  const canReturnToAI    = item.handoff_mode === 'human'
  const canRaisePriority = !!item.ticket_id && !!PRIORITY_NEXT[item.ticket_priority ?? '']
  const canMarkWaiting   = item.status === 'active' && !!item.ticket_id && item.ticket_status !== 'in_progress'

  return (
    <tr className="bg-background-surface hover:bg-background-elevated transition-colors">
      {/* Conversation */}
      <td className="px-4 py-3">
        <div>
          <p className="text-sm font-medium text-slate-200 truncate max-w-[160px]">
            {item.subject || 'Untitled'}
          </p>
          <p className="text-[10px] font-mono text-slate-600 mt-0.5">#{item.conversation_id.slice(0, 8)}</p>
        </div>
      </td>
      {/* Channel */}
      <td className="px-4 py-3">
        <ChannelBadge channel={item.channel} />
      </td>
      {/* Agent */}
      <td className="px-4 py-3">
        <AgentBadge agent={item.routed_agent} />
      </td>
      {/* Handoff */}
      <td className="px-4 py-3">
        <HandoffBadge mode={item.handoff_mode} />
      </td>
      {/* Priority */}
      <td className="px-4 py-3">
        <PriorityBadge priority={item.ticket_priority} />
      </td>
      {/* Urgency */}
      <td className="px-4 py-3">
        <span className={cn(
          'text-xs font-semibold capitalize',
          item.urgency === 'critical' ? 'text-red-400' :
          item.urgency === 'high'     ? 'text-orange-400' :
          item.urgency === 'medium'   ? 'text-amber-400' :
          item.urgency === 'low'      ? 'text-emerald-400' : 'text-slate-600',
        )}>
          {item.urgency ?? '—'}
        </span>
      </td>
      {/* SLA */}
      <td className="px-4 py-3">
        <SlaBadge item={item} />
      </td>
      {/* Updated */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-1 text-xs text-slate-500">
          <Clock size={11} className="shrink-0" />
          {formatRelativeDate(item.updated_at)}
        </div>
      </td>
      {/* Actions */}
      <td className="px-4 py-3">
        <div className="flex flex-wrap items-center gap-1.5">
          {/* Always: Open conversation */}
          <Link
            href={`/chat/${item.conversation_id}`}
            className="inline-flex items-center gap-1 rounded-md border border-slate-700/50 bg-slate-700/20 px-2 py-1 text-[10px] font-semibold text-slate-300 hover:bg-slate-700/40 transition-colors"
          >
            <ExternalLink size={9} />
            Open
          </Link>

          {/* Take Over — only when AI mode */}
          {canTakeOver && (
            <ActionBtn
              onClick={handleTakeOver}
              disabled={busy}
              icon={Headphones}
              label="Take Over"
              cls="border-emerald-500/30 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20"
            />
          )}

          {/* Return to AI — only when human mode */}
          {canReturnToAI && (
            <ActionBtn
              onClick={handleReturnToAI}
              disabled={busy}
              icon={Bot}
              label="Return to AI"
              cls="border-slate-600/50 bg-slate-700/30 text-slate-300 hover:bg-slate-700/50"
            />
          )}

          {/* Raise Priority — only when ticket exists and not already urgent */}
          {canRaisePriority && (
            <ActionBtn
              onClick={handleRaisePriority}
              disabled={busy}
              icon={ArrowUpCircle}
              label={`↑ ${PRIORITY_NEXT[item.ticket_priority ?? 'low']}`}
              cls="border-orange-500/30 bg-orange-500/10 text-orange-300 hover:bg-orange-500/20"
            />
          )}

          {/* Mark Waiting for Customer — only when active + ticket exists + not already waiting */}
          {canMarkWaiting && (
            <ActionBtn
              onClick={handleMarkWaiting}
              disabled={busy}
              icon={Hourglass}
              label="Waiting"
              cls="border-sky-500/30 bg-sky-500/10 text-sky-300 hover:bg-sky-500/20"
            />
          )}
        </div>
      </td>
    </tr>
  )
}

// ── Queue group definitions ───────────────────────────────────────────────────
type QueueGroup = {
  id: string
  label: string
  icon: React.ElementType
  iconCls: string
  headerCls: string
  filter: (item: QueueItem) => boolean
}

const QUEUE_GROUPS: QueueGroup[] = [
  {
    id: 'escalated',
    label: 'Escalated',
    icon: ShieldAlert,
    iconCls: 'text-red-400',
    headerCls: 'border-red-500/20 bg-red-500/5',
    filter: (i) => i.status === 'escalated' && i.handoff_mode === 'ai',
  },
  {
    id: 'human_active',
    label: 'Human Active',
    icon: Headphones,
    iconCls: 'text-emerald-400',
    headerCls: 'border-emerald-500/20 bg-emerald-500/5',
    filter: (i) => i.handoff_mode === 'human',
  },
  {
    id: 'urgent_high',
    label: 'Urgent / High Priority',
    icon: Zap,
    iconCls: 'text-orange-400',
    headerCls: 'border-orange-500/20 bg-orange-500/5',
    filter: (i) =>
      (i.ticket_priority === 'urgent' || i.ticket_priority === 'high' || i.urgency === 'critical' || i.urgency === 'high') &&
      i.status !== 'escalated' &&
      i.handoff_mode !== 'human',
  },
  {
    id: 'ai_active',
    label: 'AI Active',
    icon: Bot,
    iconCls: 'text-indigo-400',
    headerCls: 'border-indigo-500/20 bg-indigo-500/5',
    filter: (i) =>
      i.status === 'active' &&
      i.handoff_mode === 'ai' &&
      i.ticket_priority !== 'urgent' &&
      i.ticket_priority !== 'high' &&
      i.urgency !== 'critical' &&
      i.urgency !== 'high',
  },
  {
    id: 'waiting',
    label: 'Waiting for Customer',
    icon: Users,
    iconCls: 'text-sky-400',
    headerCls: 'border-sky-500/20 bg-sky-500/5',
    filter: (i) =>
      (i.ticket_status === 'in_progress' || i.ticket_status === 'resolved') &&
      i.status !== 'closed',
  },
]

// ── Group section ─────────────────────────────────────────────────────────────
function QueueGroupSection({
  group, items, onRefresh,
}: {
  group: QueueGroup
  items: QueueItem[]
  onRefresh: () => void
}) {
  const Icon = group.icon
  if (items.length === 0) return null

  const ORDER: Record<SlaState, number> = { overdue: 0, nearing: 1, on_time: 2 }
  const sorted = [...items].sort((a, b) => ORDER[getSlaState(a)] - ORDER[getSlaState(b)])

  return (
    <div className="rounded-xl border border-border overflow-hidden">
      <div className={cn('flex items-center gap-2 border-b border-border px-4 py-2.5', group.headerCls)}>
        <Icon size={14} className={group.iconCls} />
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
          {group.label}
        </span>
        <span className="ml-auto rounded-full bg-white/10 px-2 py-0.5 text-[10px] font-bold text-slate-400">
          {items.length}
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border/50 bg-background-elevated/30">
              {['Conversation', 'Channel', 'Agent', 'Mode', 'Priority', 'Urgency', 'SLA', 'Updated', 'Actions'].map((h) => (
                <th key={h} className="px-4 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-600">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {sorted.map((item) => (
              <QueueRow key={item.conversation_id} item={item} onRefresh={onRefresh} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Summary stat card ─────────────────────────────────────────────────────────
function StatCard({ label, value, sub, cls }: { label: string; value: number; sub?: string; cls?: string }) {
  return (
    <div className="rounded-2xl border border-border bg-background-surface p-5">
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className={cn('mt-3 text-3xl font-bold', cls ?? 'text-slate-100')}>{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-600">{sub}</p>}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function SupportQueuePage() {
  const [items, setItems] = useState<QueueItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastFetch, setLastFetch] = useState<Date | null>(null)

  const fetchQueue = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await adminApi.getQueue()
      setItems(data)
      setLastFetch(new Date())
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load queue')
    } finally {
      setLoading(false)
    }
  }, [])

  // Lightweight re-fetch without showing full-page spinner (used by row actions)
  const silentRefresh = useCallback(async () => {
    try {
      const data = await adminApi.getQueue()
      setItems(data)
      setLastFetch(new Date())
    } catch {
      // non-fatal — stale data is acceptable after a successful action
    }
  }, [])

  useEffect(() => {
    fetchQueue()
    const timer = setInterval(silentRefresh, 60_000)
    return () => clearInterval(timer)
  }, [fetchQueue, silentRefresh])

  const escalated   = items.filter((i) => i.status === 'escalated')
  const humanActive = items.filter((i) => i.handoff_mode === 'human')
  const overdue     = items.filter((i) => getSlaState(i) === 'overdue')
  const nearing     = items.filter((i) => getSlaState(i) === 'nearing')

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Support Queue</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {items.length} active conversation{items.length !== 1 ? 's' : ''}
            {lastFetch && (
              <span className="ml-2 text-slate-600">· refreshed {formatRelativeDate(lastFetch.toISOString())}</span>
            )}
          </p>
        </div>
        <Button variant="outline" size="sm" icon={RefreshCw} onClick={fetchQueue}>
          Refresh
        </Button>
      </div>

      {/* Summary row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Escalated"    value={escalated.length}   cls="text-red-300"     sub="awaiting handoff" />
        <StatCard label="Human Active" value={humanActive.length} cls="text-emerald-300" sub="admin in control" />
        <StatCard label="Overdue"      value={overdue.length}     cls="text-red-300"     sub="past SLA deadline" />
        <StatCard label="Nearing SLA"  value={nearing.length}     cls="text-amber-300"   sub="within 75% of limit" />
      </div>

      {/* SLA legend */}
      <div className="flex flex-wrap items-center gap-4 rounded-xl border border-border bg-background-surface px-4 py-3">
        <span className="text-xs font-medium uppercase tracking-wider text-slate-500">SLA thresholds:</span>
        {Object.entries(SLA_MINUTES).map(([tier, mins]) => (
          <span key={tier} className="text-xs text-slate-400">
            <span className="font-semibold capitalize text-slate-300">{tier}</span>
            {' '}· {mins < 60 ? `${mins}m` : `${mins / 60}h`}
          </span>
        ))}
        <span className="ml-auto text-[10px] text-slate-600">based on ticket priority → AI urgency fallback</span>
      </div>

      {/* Action legend */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-background-surface px-4 py-3">
        <span className="text-xs font-medium uppercase tracking-wider text-slate-500">Actions:</span>
        <span className="inline-flex items-center gap-1 text-[10px] text-slate-400"><Headphones size={10} className="text-emerald-400" /> Take Over — pauses AI, admin replies</span>
        <span className="inline-flex items-center gap-1 text-[10px] text-slate-400"><Bot size={10} className="text-slate-400" /> Return to AI — resumes automation</span>
        <span className="inline-flex items-center gap-1 text-[10px] text-slate-400"><ArrowUpCircle size={10} className="text-orange-400" /> ↑ Priority — bumps ticket one level</span>
        <span className="inline-flex items-center gap-1 text-[10px] text-slate-400"><Hourglass size={10} className="text-sky-400" /> Waiting — marks ticket in-progress</span>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Content */}
      {loading ? (
        <LoadingSpinner center size="lg" label="Loading queue..." />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Inbox}
          title="Queue is empty"
          description="No active or escalated conversations right now."
        />
      ) : (
        <div className="space-y-5">
          {QUEUE_GROUPS.map((group) => (
            <QueueGroupSection
              key={group.id}
              group={group}
              items={items.filter(group.filter)}
              onRefresh={silentRefresh}
            />
          ))}
        </div>
      )}
    </div>
  )
}
