'use client'

import React, { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { RefreshCw, MessageCircle, ExternalLink, AlertTriangle, Layers3 } from 'lucide-react'
import { adminApi } from '../../../../lib/api'
import { Conversation, ConversationStatus, Channel } from '../../../../types'
import { ConversationStatusBadge, ChannelBadge, EscalationFlag } from '../../../../components/ui/Badge'
import { Button } from '../../../../components/ui/Button'
import { LoadingSpinner } from '../../../../components/ui/LoadingSpinner'
import { EmptyState } from '../../../../components/ui/EmptyState'
import { formatDate, formatRelativeDate } from '../../../../lib/utils'
import { cn } from '../../../../lib/utils'

const STATUS_FILTERS: { label: string; value: ConversationStatus | 'all' }[] = [
  { label: 'All', value: 'all' },
  { label: 'Active', value: 'active' },
  { label: 'Closed', value: 'closed' },
  { label: 'Escalated', value: 'escalated' },
]

const CHANNEL_FILTERS: { label: string; value: Channel | 'all' }[] = [
  { label: 'All', value: 'all' },
  { label: 'Web', value: 'web' },
  { label: 'Email', value: 'email' },
  { label: 'WhatsApp', value: 'whatsapp' },
]

export default function AdminConversationsPage() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<ConversationStatus | 'all'>('all')
  const [channelFilter, setChannelFilter] = useState<Channel | 'all'>('all')

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await adminApi.getConversations()
      setConversations(data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load conversations'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const filtered = conversations
    .filter((c) => statusFilter === 'all' || c.status === statusFilter)
    .filter((c) => channelFilter === 'all' || c.channel === channelFilter)

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">All Conversations</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {filtered.length} conversation{filtered.length !== 1 ? 's' : ''}
          </p>
        </div>
        <Button variant="outline" size="sm" icon={RefreshCw} onClick={fetchData}>
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-border bg-gradient-to-br from-sky-500/12 via-transparent to-emerald-500/10 p-5">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-slate-400">
            <Layers3 size={14} />
            Unified History
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-400">
            Customer conversations stay visible here across all active channels for demo-ready multi-channel support.
          </p>
        </div>
        <div className="rounded-2xl border border-border bg-background-surface p-5">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-slate-500">
            <MessageCircle size={14} />
            Active
          </div>
          <p className="mt-3 text-3xl font-bold text-emerald-300">
            {filtered.filter((conv) => conv.status === 'active').length}
          </p>
        </div>
        <div className="rounded-2xl border border-border bg-background-surface p-5">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-slate-500">
            <AlertTriangle size={14} />
            Escalated
          </div>
          <p className="mt-3 text-3xl font-bold text-rose-300">
            {filtered.filter((conv) => conv.status === 'escalated').length}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Status:</span>
          <div className="flex gap-1 rounded-lg bg-background-surface border border-border p-1">
            {STATUS_FILTERS.map((f) => (
              <button
                key={f.value}
                onClick={() => setStatusFilter(f.value)}
                className={cn(
                  'rounded-md px-3 py-1 text-xs font-medium transition-all',
                  statusFilter === f.value
                    ? 'bg-purple-500 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Channel:</span>
          <div className="flex gap-1 rounded-lg bg-background-surface border border-border p-1">
            {CHANNEL_FILTERS.map((f) => (
              <button
                key={f.value}
                onClick={() => setChannelFilter(f.value)}
                className={cn(
                  'rounded-md px-3 py-1 text-xs font-medium transition-all',
                  channelFilter === f.value
                    ? 'bg-purple-500 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Content */}
      {loading ? (
        <LoadingSpinner center size="lg" label="Loading conversations..." />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={MessageCircle}
          title="No conversations found"
          description="No conversations match your current filters."
        />
      ) : (
        <div className="rounded-xl border border-border overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-background-elevated/50">
                {['ID', 'Subject', 'User', 'Channel', 'Status', 'Created', 'Actions'].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {filtered.map((conv) => (
                <tr key={conv.id} className="bg-background-surface hover:bg-background-elevated transition-colors">
                  <td className="px-4 py-3">
                    <span className="text-xs font-mono text-slate-500">#{conv.id.slice(0, 8)}</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-medium text-slate-200">
                        {conv.subject || 'Untitled'}
                      </span>
                      <EscalationFlag escalated={conv.status === 'escalated'} />
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs font-mono text-slate-500">{conv.user_id.slice(0, 8)}</span>
                  </td>
                  <td className="px-4 py-3">
                    <ChannelBadge channel={conv.channel} />
                  </td>
                  <td className="px-4 py-3">
                    <ConversationStatusBadge status={conv.status} />
                  </td>
                  <td className="px-4 py-3">
                    <div>
                      <p className="text-xs text-slate-400">{formatDate(conv.created_at)}</p>
                      <p className="text-[10px] text-slate-600">{formatRelativeDate(conv.created_at)}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/chat/${conv.id}`}
                      className="inline-flex items-center gap-1 text-xs text-accent hover:text-accent-light transition-colors"
                    >
                      <ExternalLink size={12} />
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
