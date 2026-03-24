'use client'

import React, { useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ChevronRight, Layers3, MessageCircle, MessageSquarePlus, Route } from 'lucide-react'
import { useConversations } from '../../../hooks/useConversations'
import { Button } from '../../../components/ui/Button'
import { ChannelBadge, ConversationStatusBadge, EscalationFlag } from '../../../components/ui/Badge'
import { LoadingSpinner } from '../../../components/ui/LoadingSpinner'
import { EmptyState } from '../../../components/ui/EmptyState'
import { formatRelativeDate } from '../../../lib/utils'
import { useToast } from '../../../context/ToastContext'

export default function ConversationsPage() {
  const { conversations, loading, error, createConversation } = useConversations()
  const router = useRouter()
  const [creating, setCreating] = useState(false)
  const toast = useToast()

  const handleNew = async () => {
    setCreating(true)
    try {
      const conv = await createConversation()
      router.push(`/chat/${conv.id}`)
    } catch {
      setCreating(false)
      toast.error('Failed to start conversation. Please try again.')
    }
  }

  const channelBreakdown = useMemo(() => {
    return [
      { label: 'Web', value: conversations.filter((conv) => conv.channel === 'web').length, channel: 'web' as const },
      { label: 'Email', value: conversations.filter((conv) => conv.channel === 'email').length, channel: 'email' as const },
      { label: 'WhatsApp', value: conversations.filter((conv) => conv.channel === 'whatsapp').length, channel: 'whatsapp' as const },
    ]
  }, [conversations])

  const escalatedCount = conversations.filter((conv) => conv.status === 'escalated').length

  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Conversations</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Unified history across your web, email, and WhatsApp support channels
          </p>
        </div>
        <Button variant="primary" icon={MessageSquarePlus} loading={creating} onClick={handleNew}>
          New Conversation
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-[1.4fr_repeat(3,minmax(0,1fr))]">
        <div className="rounded-2xl border border-border bg-gradient-to-br from-sky-500/12 via-transparent to-emerald-500/10 p-5">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.2em] text-slate-400">
            <Layers3 size={14} />
            Unified History
          </div>
          <h2 className="mt-3 text-lg font-semibold text-slate-100">Every support touchpoint in one timeline</h2>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            Keep channel context visible, track escalations, and jump back into the right conversation without losing history.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {channelBreakdown.map((item) => (
              <div key={item.channel} className="rounded-xl border border-border/70 bg-background/70 px-3 py-2">
                <ChannelBadge channel={item.channel} />
                <p className="mt-2 text-xl font-semibold text-slate-100">{item.value}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-background-surface p-5">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.2em] text-slate-500">
            <MessageCircle size={14} />
            Total
          </div>
          <p className="mt-3 text-3xl font-bold text-slate-100">{conversations.length}</p>
          <p className="mt-1 text-xs text-slate-500">All conversations across channels</p>
        </div>

        <div className="rounded-2xl border border-border bg-background-surface p-5">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.2em] text-slate-500">
            <Route size={14} />
            Active
          </div>
          <p className="mt-3 text-3xl font-bold text-emerald-300">
            {conversations.filter((conv) => conv.status === 'active').length}
          </p>
          <p className="mt-1 text-xs text-slate-500">Currently open AI conversations</p>
        </div>

        <div className="rounded-2xl border border-border bg-background-surface p-5">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.2em] text-slate-500">
            <Route size={14} />
            Escalated
          </div>
          <p className="mt-3 text-3xl font-bold text-rose-300">{escalatedCount}</p>
          <p className="mt-1 text-xs text-slate-500">Threads flagged for human review</p>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          Failed to load conversations: {error}
        </div>
      )}

      {loading && <LoadingSpinner center size="lg" label="Loading conversations..." />}

      {!loading && !error && conversations.length === 0 && (
        <EmptyState
          icon={MessageCircle}
          title="No conversations yet"
          description="Start a new conversation to get instant AI-powered support."
          action={{
            label: 'Start New Conversation',
            onClick: handleNew,
            icon: MessageSquarePlus,
          }}
        />
      )}

      {!loading && conversations.length > 0 && (
        <div className="space-y-3">
          {conversations.map((conv) => {
            const isEscalated = conv.status === 'escalated'

            return (
              <Link
                key={conv.id}
                href={`/chat/${conv.id}`}
                className="group flex items-center justify-between rounded-2xl border border-border bg-background-surface px-5 py-4 transition-all duration-150 hover:border-accent/30 hover:bg-background-elevated"
              >
                <div className="min-w-0 flex-1">
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <span className="truncate text-sm font-semibold text-slate-200">
                      {conv.subject || 'Untitled Conversation'}
                    </span>
                    <ConversationStatusBadge status={conv.status} />
                    <EscalationFlag escalated={isEscalated} />
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <ChannelBadge channel={conv.channel} />
                    <span className="text-xs text-slate-600">{formatRelativeDate(conv.created_at)}</span>
                    <span className="text-xs text-slate-500">
                      {isEscalated ? 'Human handoff visible in unified history' : 'Tracked in unified history'}
                    </span>
                  </div>
                </div>
                <ChevronRight
                  size={18}
                  className="ml-3 shrink-0 text-slate-600 transition-colors group-hover:text-accent"
                />
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
