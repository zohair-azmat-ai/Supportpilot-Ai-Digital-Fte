'use client'

import React, { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import {
  ArrowUpCircle, Bot, Clock, Cpu, ExternalLink,
  Headphones, Hourglass, Loader2, RefreshCw,
  ShieldAlert, Inbox, Zap, Users, CheckSquare, Square,
} from 'lucide-react'
import { adminApi } from '../../../../lib/api'
import { QueueItem } from '../../../../types'
import { ChannelBadge } from '../../../../components/ui/Badge'
import { Button } from '../../../../components/ui/Button'
import { LoadingSpinner } from '../../../../components/ui/LoadingSpinner'
import { EmptyState } from '../../../../components/ui/EmptyState'
import { useToast } from '../../../../context/ToastContext'
import { cn, formatRelativeDate } from '../../../../lib/utils'

// ── SLA ───────────────────────────────────────────────────────────────────────
const SLA_MINUTES: Record<string, number> = {
  urgent: 30, high: 120, medium: 480, low: 1440,
}

type SlaState = 'on_time' | 'nearing' | 'overdue'

function getSlaState(item: QueueItem): SlaState {
  const tier = item.ticket_priority ?? item.urgency ?? 'medium'
  const slaMs = (SLA_MINUTES[tier] ?? SLA_MINUTES.medium) * 60_000
  const elapsed = Date.now() - new Date(item.updated_at).getTime()
  if (elapsed >= slaMs) return 'overdue'
  if (elapsed >= slaMs * 0.75) return 'nearing'
  return 'on_time'
}

function timeUntilSla(item: QueueItem): string {
  const tier = item.ticket_priority ?? item.urgency ?? 'medium'
  const slaMs = (SLA_MINUTES[tier] ?? SLA_MINUTES.medium) * 60_000
  const remaining = slaMs - (Date.now() - new Date(item.updated_at).getTime())
  if (remaining <= 0) {
    const over = Math.round(-remaining / 60_000)
    return over < 60 ? `${over}m overdue` : `${Math.round(over / 60)}h overdue`
  }
  const mins = Math.round(remaining / 60_000)
  return mins < 60 ? `${mins}m left` : `${Math.round(mins / 60)}h left`
}

const SLA_CFG: Record<SlaState, { cls: string; dot: string }> = {
  on_time: { cls: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/8', dot: 'bg-emerald-400' },
  nearing: { cls: 'text-amber-400  border-amber-500/20  bg-amber-500/8',    dot: 'bg-amber-400'  },
  overdue: { cls: 'text-red-400    border-red-500/20    bg-red-500/8',      dot: 'bg-red-400'    },
}

function SlaBadge({ item }: { item: QueueItem }) {
  const cfg = SLA_CFG[getSlaState(item)]
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold', cfg.cls)}>
      <span className={cn('h-1.5 w-1.5 rounded-full', cfg.dot)} />
      {timeUntilSla(item)}
    </span>
  )
}

// ── Badges ────────────────────────────────────────────────────────────────────
const AGENT_BADGE: Record<string, { label: string; cls: string }> = {
  billing:   { label: 'Billing',   cls: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/25' },
  technical: { label: 'Technical', cls: 'bg-amber-500/15  text-amber-300  border-amber-500/25' },
  account:   { label: 'Account',   cls: 'bg-purple-500/15 text-purple-300 border-purple-500/25' },
  general:   { label: 'General',   cls: 'bg-slate-700/40  text-slate-400  border-slate-700/40'  },
}
function AgentBadge({ agent }: { agent: string | null }) {
  if (!agent) return <span className="text-slate-600 text-xs">—</span>
  const m = AGENT_BADGE[agent] ?? { label: agent, cls: 'bg-slate-700/40 text-slate-400 border-slate-700/40' }
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold', m.cls)}>
      <Cpu size={9} />{m.label}
    </span>
  )
}

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

function HandoffBadge({ mode }: { mode: 'ai' | 'human' }) {
  return mode === 'human' ? (
    <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">
      <Headphones size={9} />Human
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 rounded-full border border-slate-700/40 bg-slate-700/20 px-2 py-0.5 text-[10px] font-semibold text-slate-400">
      <Bot size={9} />AI
    </span>
  )
}

// ── Per-row action button ─────────────────────────────────────────────────────
function ActionBtn({ onClick, disabled, icon: Icon, label, cls }: {
  onClick: () => void; disabled: boolean
  icon: React.ElementType; label: string; cls: string
}) {
  return (
    <button onClick={onClick} disabled={disabled} title={label}
      className={cn('inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed', cls)}>
      {disabled ? <Loader2 size={9} className="animate-spin" /> : <Icon size={9} />}
      {label}
    </button>
  )
}

const PRIORITY_NEXT: Record<string, string> = { low: 'medium', medium: 'high', high: 'urgent' }

// ── Queue row ─────────────────────────────────────────────────────────────────
function QueueRow({
  item, selected, onToggle, onPatch, onRefresh,
}: {
  item: QueueItem
  selected: boolean
  onToggle: (id: string) => void
  onPatch: (id: string, patch: Partial<QueueItem>) => void
  onRefresh: () => void
}) {
  const [busy, setBusy] = useState(false)
  const toast = useToast()

  const run = useCallback(async (
    label: string,
    fn: () => Promise<unknown>,
    patch?: Partial<QueueItem>,
  ) => {
    setBusy(true)
    try {
      await fn()
      if (patch) onPatch(item.conversation_id, patch)
      else onRefresh()
    } catch {
      toast.error(`Failed: ${label}`)
    } finally {
      setBusy(false)
    }
  }, [item.conversation_id, onPatch, onRefresh, toast])

  const handleTakeOver = () => run(
    'Take Over',
    () => adminApi.setHandoffMode(item.conversation_id, 'human').then(() => toast.success('You are now handling this conversation.')),
    { handoff_mode: 'human' },
  )
  const handleReturnToAI = () => run(
    'Return to AI',
    () => adminApi.setHandoffMode(item.conversation_id, 'ai').then(() => toast.success('AI resumed.')),
    { handoff_mode: 'ai' },
  )
  const handleRaisePriority = () => {
    const next = PRIORITY_NEXT[item.ticket_priority ?? '']
    if (!next || !item.ticket_id) return
    run(
      `Raise to ${next}`,
      () => adminApi.updateTicket(item.ticket_id!, { priority: next as never }).then(() => toast.success(`Priority → ${next}.`)),
      { ticket_priority: next },
    )
  }
  const handleMarkWaiting = () => run(
    'Mark Waiting',
    () => adminApi.updateTicket(item.ticket_id!, { status: 'in_progress' as never }).then(() => toast.success('Marked waiting for customer.')),
    { ticket_status: 'in_progress' },
  )

  const canTakeOver      = item.handoff_mode === 'ai'
  const canReturnToAI    = item.handoff_mode === 'human'
  const canRaisePriority = !!item.ticket_id && !!PRIORITY_NEXT[item.ticket_priority ?? '']
  const canMarkWaiting   = item.status === 'active' && !!item.ticket_id && item.ticket_status !== 'in_progress'

  return (
    <tr className={cn('transition-colors', selected ? 'bg-indigo-500/8' : 'bg-background-surface hover:bg-background-elevated')}>
      {/* Checkbox */}
      <td className="pl-4 pr-2 py-3 w-8">
        <button onClick={() => onToggle(item.conversation_id)} className="text-slate-500 hover:text-indigo-400 transition-colors">
          {selected ? <CheckSquare size={15} className="text-indigo-400" /> : <Square size={15} />}
        </button>
      </td>
      {/* Conversation */}
      <td className="px-3 py-3">
        <p className="text-sm font-medium text-slate-200 truncate max-w-[160px]">{item.subject || 'Untitled'}</p>
        <p className="text-[10px] font-mono text-slate-600 mt-0.5">#{item.conversation_id.slice(0, 8)}</p>
      </td>
      <td className="px-3 py-3"><ChannelBadge channel={item.channel} /></td>
      <td className="px-3 py-3"><AgentBadge agent={item.routed_agent} /></td>
      <td className="px-3 py-3"><HandoffBadge mode={item.handoff_mode} /></td>
      <td className="px-3 py-3"><PriorityBadge priority={item.ticket_priority} /></td>
      <td className="px-3 py-3">
        <span className={cn('text-xs font-semibold capitalize',
          item.urgency === 'critical' ? 'text-red-400' : item.urgency === 'high' ? 'text-orange-400' :
          item.urgency === 'medium' ? 'text-amber-400' : item.urgency === 'low' ? 'text-emerald-400' : 'text-slate-600',
        )}>{item.urgency ?? '—'}</span>
      </td>
      <td className="px-3 py-3"><SlaBadge item={item} /></td>
      <td className="px-3 py-3">
        <div className="flex items-center gap-1 text-xs text-slate-500">
          <Clock size={11} />{formatRelativeDate(item.updated_at)}
        </div>
      </td>
      {/* Actions */}
      <td className="px-3 py-3">
        <div className="flex flex-wrap items-center gap-1.5">
          <Link href={`/chat/${item.conversation_id}`}
            className="inline-flex items-center gap-1 rounded-md border border-slate-700/50 bg-slate-700/20 px-2 py-1 text-[10px] font-semibold text-slate-300 hover:bg-slate-700/40 transition-colors">
            <ExternalLink size={9} />Open
          </Link>
          {canTakeOver && (
            <ActionBtn onClick={handleTakeOver} disabled={busy} icon={Headphones} label="Take Over"
              cls="border-emerald-500/30 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20" />
          )}
          {canReturnToAI && (
            <ActionBtn onClick={handleReturnToAI} disabled={busy} icon={Bot} label="Return to AI"
              cls="border-slate-600/50 bg-slate-700/30 text-slate-300 hover:bg-slate-700/50" />
          )}
          {canRaisePriority && (
            <ActionBtn onClick={handleRaisePriority} disabled={busy} icon={ArrowUpCircle}
              label={`↑ ${PRIORITY_NEXT[item.ticket_priority ?? 'low']}`}
              cls="border-orange-500/30 bg-orange-500/10 text-orange-300 hover:bg-orange-500/20" />
          )}
          {canMarkWaiting && (
            <ActionBtn onClick={handleMarkWaiting} disabled={busy} icon={Hourglass} label="Waiting"
              cls="border-sky-500/30 bg-sky-500/10 text-sky-300 hover:bg-sky-500/20" />
          )}
        </div>
      </td>
    </tr>
  )
}

// ── Group definitions ─────────────────────────────────────────────────────────
type QueueGroup = {
  id: string; label: string; icon: React.ElementType
  iconCls: string; headerCls: string
  filter: (i: QueueItem) => boolean
}

const QUEUE_GROUPS: QueueGroup[] = [
  { id: 'escalated',   label: 'Escalated',             icon: ShieldAlert, iconCls: 'text-red-400',     headerCls: 'border-red-500/20 bg-red-500/5',
    filter: (i) => i.status === 'escalated' && i.handoff_mode === 'ai' },
  { id: 'human_active', label: 'Human Active',          icon: Headphones, iconCls: 'text-emerald-400', headerCls: 'border-emerald-500/20 bg-emerald-500/5',
    filter: (i) => i.handoff_mode === 'human' },
  { id: 'urgent_high', label: 'Urgent / High Priority', icon: Zap,        iconCls: 'text-orange-400', headerCls: 'border-orange-500/20 bg-orange-500/5',
    filter: (i) => (i.ticket_priority === 'urgent' || i.ticket_priority === 'high' || i.urgency === 'critical' || i.urgency === 'high') && i.status !== 'escalated' && i.handoff_mode !== 'human' },
  { id: 'ai_active',   label: 'AI Active',              icon: Bot,        iconCls: 'text-indigo-400', headerCls: 'border-indigo-500/20 bg-indigo-500/5',
    filter: (i) => i.status === 'active' && i.handoff_mode === 'ai' && i.ticket_priority !== 'urgent' && i.ticket_priority !== 'high' && i.urgency !== 'critical' && i.urgency !== 'high' },
  { id: 'waiting',     label: 'Waiting for Customer',   icon: Users,      iconCls: 'text-sky-400',    headerCls: 'border-sky-500/20 bg-sky-500/5',
    filter: (i) => (i.ticket_status === 'in_progress' || i.ticket_status === 'resolved') && i.status !== 'closed' },
]

// ── Group section ─────────────────────────────────────────────────────────────
const SLA_ORDER: Record<SlaState, number> = { overdue: 0, nearing: 1, on_time: 2 }

function QueueGroupSection({ group, items, selected, onToggle, onToggleAll, onPatch, onRefresh }: {
  group: QueueGroup; items: QueueItem[]
  selected: Set<string>; onToggle: (id: string) => void
  onToggleAll: (ids: string[], checked: boolean) => void
  onPatch: (id: string, patch: Partial<QueueItem>) => void
  onRefresh: () => void
}) {
  const Icon = group.icon
  if (items.length === 0) return null
  const sorted = [...items].sort((a, b) => SLA_ORDER[getSlaState(a)] - SLA_ORDER[getSlaState(b)])
  const ids = sorted.map((i) => i.conversation_id)
  const allChecked = ids.every((id) => selected.has(id))

  return (
    <div className="rounded-xl border border-border overflow-hidden">
      <div className={cn('flex items-center gap-2 border-b border-border px-4 py-2.5', group.headerCls)}>
        <Icon size={14} className={group.iconCls} />
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">{group.label}</span>
        <span className="ml-auto rounded-full bg-white/10 px-2 py-0.5 text-[10px] font-bold text-slate-400">{items.length}</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border/50 bg-background-elevated/30">
              <th className="pl-4 pr-2 py-2 w-8">
                <button onClick={() => onToggleAll(ids, !allChecked)} className="text-slate-500 hover:text-indigo-400 transition-colors">
                  {allChecked ? <CheckSquare size={13} className="text-indigo-400" /> : <Square size={13} />}
                </button>
              </th>
              {['Conversation', 'Channel', 'Agent', 'Mode', 'Priority', 'Urgency', 'SLA', 'Updated', 'Actions'].map((h) => (
                <th key={h} className="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-600">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border/50">
            {sorted.map((item) => (
              <QueueRow key={item.conversation_id} item={item}
                selected={selected.has(item.conversation_id)}
                onToggle={onToggle} onPatch={onPatch} onRefresh={onRefresh} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Stat card ─────────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, cls }: { label: string; value: number; sub?: string; cls?: string }) {
  return (
    <div className="rounded-2xl border border-border bg-background-surface p-5">
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className={cn('mt-3 text-3xl font-bold', cls ?? 'text-slate-100')}>{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-600">{sub}</p>}
    </div>
  )
}

// ── Filter pill ───────────────────────────────────────────────────────────────
function FilterPill({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={cn(
      'rounded-full border px-3 py-1 text-[11px] font-semibold transition-all',
      active
        ? 'border-indigo-500/60 bg-indigo-500/20 text-indigo-300'
        : 'border-slate-700/50 bg-slate-800/40 text-slate-500 hover:border-slate-600 hover:text-slate-300',
    )}>
      {label}
    </button>
  )
}

// ── Filter types ──────────────────────────────────────────────────────────────
type StatusFilter   = 'all' | 'escalated' | 'human_active' | 'ai_active' | 'waiting'
type PriorityFilter = 'all' | 'urgent' | 'high' | 'medium' | 'low'
type SlaFilter      = 'all' | 'on_time' | 'nearing' | 'overdue'

function matchesFilters(
  item: QueueItem,
  status: StatusFilter,
  priority: PriorityFilter,
  sla: SlaFilter,
): boolean {
  if (status !== 'all') {
    if (status === 'escalated'    && !(item.status === 'escalated' && item.handoff_mode === 'ai')) return false
    if (status === 'human_active' && item.handoff_mode !== 'human') return false
    if (status === 'ai_active'    && !(item.status === 'active' && item.handoff_mode === 'ai'))    return false
    if (status === 'waiting'      && !((item.ticket_status === 'in_progress' || item.ticket_status === 'resolved') && item.status !== 'closed')) return false
  }
  if (priority !== 'all') {
    const p = item.ticket_priority ?? item.urgency
    if (p !== priority) return false
  }
  if (sla !== 'all' && getSlaState(item) !== sla) return false
  return true
}

// ── Bulk action bar ───────────────────────────────────────────────────────────
function BulkActionBar({ count, items, selected, onPatch, onRefresh, onClear }: {
  count: number
  items: QueueItem[]
  selected: Set<string>
  onPatch: (id: string, patch: Partial<QueueItem>) => void
  onRefresh: () => void
  onClear: () => void
}) {
  const [busy, setBusy] = useState(false)
  const toast = useToast()

  const selectedItems = items.filter((i) => selected.has(i.conversation_id))

  const runBulk = useCallback(async (
    label: string,
    actions: Array<{ id: string; fn: () => Promise<unknown>; patch: Partial<QueueItem> }>,
  ) => {
    if (actions.length === 0) { toast.error(`No eligible items for: ${label}`); return }
    setBusy(true)
    let failed = 0
    for (const { id, fn, patch } of actions) {
      try { await fn(); onPatch(id, patch) }
      catch { failed++ }
    }
    setBusy(false)
    if (failed === 0) toast.success(`${label}: applied to ${actions.length} item${actions.length > 1 ? 's' : ''}.`)
    else toast.error(`${label}: ${failed} item${failed > 1 ? 's' : ''} failed.`)
    onClear()
  }, [onPatch, onClear, toast])

  const bulkTakeOver = () => runBulk('Take Over', selectedItems
    .filter((i) => i.handoff_mode === 'ai')
    .map((i) => ({ id: i.conversation_id, fn: () => adminApi.setHandoffMode(i.conversation_id, 'human'), patch: { handoff_mode: 'human' as const } })))

  const bulkReturnToAI = () => runBulk('Return to AI', selectedItems
    .filter((i) => i.handoff_mode === 'human')
    .map((i) => ({ id: i.conversation_id, fn: () => adminApi.setHandoffMode(i.conversation_id, 'ai'), patch: { handoff_mode: 'ai' as const } })))

  const bulkMarkWaiting = () => runBulk('Mark Waiting', selectedItems
    .filter((i) => i.status === 'active' && !!i.ticket_id && i.ticket_status !== 'in_progress')
    .map((i) => ({ id: i.conversation_id, fn: () => adminApi.updateTicket(i.ticket_id!, { status: 'in_progress' as never }), patch: { ticket_status: 'in_progress' } })))

  const bulkRaisePriority = () => runBulk('Raise Priority', selectedItems
    .filter((i) => !!i.ticket_id && !!PRIORITY_NEXT[i.ticket_priority ?? ''])
    .map((i) => {
      const next = PRIORITY_NEXT[i.ticket_priority!]
      return { id: i.conversation_id, fn: () => adminApi.updateTicket(i.ticket_id!, { priority: next as never }), patch: { ticket_priority: next } }
    }))

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-indigo-500/25 bg-indigo-500/8 px-4 py-3">
      <span className="text-xs font-semibold text-indigo-300">
        {count} selected
      </span>
      <div className="h-3 w-px bg-indigo-500/30" />
      {[
        { label: 'Take Over',       icon: Headphones,    fn: bulkTakeOver,      cls: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20' },
        { label: 'Return to AI',    icon: Bot,           fn: bulkReturnToAI,    cls: 'border-slate-600/50 bg-slate-700/30 text-slate-300 hover:bg-slate-700/50' },
        { label: '↑ Priority',      icon: ArrowUpCircle, fn: bulkRaisePriority, cls: 'border-orange-500/30 bg-orange-500/10 text-orange-300 hover:bg-orange-500/20' },
        { label: 'Mark Waiting',    icon: Hourglass,     fn: bulkMarkWaiting,   cls: 'border-sky-500/30 bg-sky-500/10 text-sky-300 hover:bg-sky-500/20' },
      ].map(({ label, icon: Icon, fn, cls }) => (
        <button key={label} onClick={fn} disabled={busy}
          className={cn('inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed', cls)}>
          {busy ? <Loader2 size={11} className="animate-spin" /> : <Icon size={11} />}
          {label}
        </button>
      ))}
      <button onClick={onClear} disabled={busy}
        className="ml-auto text-[10px] text-slate-600 hover:text-slate-400 transition-colors disabled:opacity-40">
        Clear
      </button>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function SupportQueuePage() {
  const [items, setItems] = useState<QueueItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastFetch, setLastFetch] = useState<Date | null>(null)
  const [selected, setSelected] = useState<Set<string>>(new Set())

  // Filters
  const [fStatus,   setFStatus]   = useState<StatusFilter>('all')
  const [fPriority, setFPriority] = useState<PriorityFilter>('all')
  const [fSla,      setFSla]      = useState<SlaFilter>('all')

  const fetchQueue = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const data = await adminApi.getQueue()
      setItems(data); setLastFetch(new Date())
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load queue')
    } finally { setLoading(false) }
  }, [])

  const silentRefresh = useCallback(async () => {
    try { const data = await adminApi.getQueue(); setItems(data); setLastFetch(new Date()) }
    catch { /* non-fatal */ }
  }, [])

  useEffect(() => {
    fetchQueue()
    const t = setInterval(silentRefresh, 60_000)
    return () => clearInterval(t)
  }, [fetchQueue, silentRefresh])

  // Optimistic local patch — avoids refetch for single-row actions
  const patchItem = useCallback((id: string, patch: Partial<QueueItem>) => {
    setItems((prev) => prev.map((i) => i.conversation_id === id ? { ...i, ...patch } : i))
  }, [])

  const toggleSelect = useCallback((id: string) => {
    setSelected((prev) => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n })
  }, [])

  const toggleAll = useCallback((ids: string[], checked: boolean) => {
    setSelected((prev) => {
      const n = new Set(prev)
      ids.forEach((id) => checked ? n.add(id) : n.delete(id))
      return n
    })
  }, [])

  const clearSelection = useCallback(() => setSelected(new Set()), [])

  // Filtered view (client-side, zero API calls)
  const filteredItems = useMemo(
    () => items.filter((i) => matchesFilters(i, fStatus, fPriority, fSla)),
    [items, fStatus, fPriority, fSla],
  )

  // Summary counts (from full unfiltered list)
  const escalated   = items.filter((i) => i.status === 'escalated')
  const humanActive = items.filter((i) => i.handoff_mode === 'human')
  const overdue     = items.filter((i) => getSlaState(i) === 'overdue')
  const nearing     = items.filter((i) => getSlaState(i) === 'nearing')

  const hasFilters = fStatus !== 'all' || fPriority !== 'all' || fSla !== 'all'
  const selectedCount = selected.size

  return (
    <div className="space-y-5 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Support Queue</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {filteredItems.length !== items.length
              ? `${filteredItems.length} of ${items.length} conversations`
              : `${items.length} active conversation${items.length !== 1 ? 's' : ''}`}
            {lastFetch && <span className="ml-2 text-slate-600">· {formatRelativeDate(lastFetch.toISOString())}</span>}
          </p>
        </div>
        <Button variant="outline" size="sm" icon={RefreshCw} onClick={fetchQueue}>Refresh</Button>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Escalated"    value={escalated.length}   cls="text-red-300"     sub="awaiting handoff" />
        <StatCard label="Human Active" value={humanActive.length} cls="text-emerald-300" sub="admin in control" />
        <StatCard label="Overdue"      value={overdue.length}     cls="text-red-300"     sub="past SLA deadline" />
        <StatCard label="Nearing SLA"  value={nearing.length}     cls="text-amber-300"   sub="within 75% of limit" />
      </div>

      {/* Filter bar */}
      <div className="rounded-xl border border-border bg-background-surface px-4 py-3 space-y-3">
        {/* Status row */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-14 text-[10px] font-semibold uppercase tracking-wider text-slate-600">Status</span>
          {([
            ['all', 'All'], ['escalated', 'Escalated'], ['human_active', 'Human Active'],
            ['ai_active', 'AI Active'], ['waiting', 'Waiting'],
          ] as [StatusFilter, string][]).map(([v, l]) => (
            <FilterPill key={v} label={l} active={fStatus === v} onClick={() => setFStatus(v)} />
          ))}
        </div>
        {/* Priority row */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-14 text-[10px] font-semibold uppercase tracking-wider text-slate-600">Priority</span>
          {([['all', 'All'], ['urgent', 'Urgent'], ['high', 'High'], ['medium', 'Medium'], ['low', 'Low']] as [PriorityFilter, string][]).map(([v, l]) => (
            <FilterPill key={v} label={l} active={fPriority === v} onClick={() => setFPriority(v)} />
          ))}
        </div>
        {/* SLA row */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-14 text-[10px] font-semibold uppercase tracking-wider text-slate-600">SLA</span>
          {([['all', 'All'], ['on_time', 'On Time'], ['nearing', 'Nearing'], ['overdue', 'Overdue']] as [SlaFilter, string][]).map(([v, l]) => (
            <FilterPill key={v} label={l} active={fSla === v} onClick={() => setFSla(v)} />
          ))}
          {hasFilters && (
            <button onClick={() => { setFStatus('all'); setFPriority('all'); setFSla('all') }}
              className="ml-2 text-[10px] text-slate-600 hover:text-slate-400 transition-colors">
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Bulk action bar — only when items selected */}
      {selectedCount > 0 && (
        <BulkActionBar
          count={selectedCount}
          items={items}
          selected={selected}
          onPatch={patchItem}
          onRefresh={silentRefresh}
          onClear={clearSelection}
        />
      )}

      {/* SLA legend */}
      <div className="flex flex-wrap items-center gap-4 rounded-xl border border-border bg-background-surface px-4 py-3">
        <span className="text-xs font-medium uppercase tracking-wider text-slate-500">SLA thresholds:</span>
        {Object.entries(SLA_MINUTES).map(([tier, mins]) => (
          <span key={tier} className="text-xs text-slate-400">
            <span className="font-semibold capitalize text-slate-300">{tier}</span>
            {' '}· {mins < 60 ? `${mins}m` : `${mins / 60}h`}
          </span>
        ))}
        <span className="ml-auto text-[10px] text-slate-600">ticket priority → urgency fallback</span>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      {loading ? (
        <LoadingSpinner center size="lg" label="Loading queue..." />
      ) : filteredItems.length === 0 ? (
        <EmptyState icon={Inbox} title={hasFilters ? 'No matches' : 'Queue is empty'}
          description={hasFilters ? 'Try adjusting the filters above.' : 'No active or escalated conversations right now.'} />
      ) : (
        <div className="space-y-5">
          {QUEUE_GROUPS.map((group) => (
            <QueueGroupSection key={group.id} group={group}
              items={filteredItems.filter(group.filter)}
              selected={selected}
              onToggle={toggleSelect}
              onToggleAll={toggleAll}
              onPatch={patchItem}
              onRefresh={silentRefresh}
            />
          ))}
        </div>
      )}
    </div>
  )
}
