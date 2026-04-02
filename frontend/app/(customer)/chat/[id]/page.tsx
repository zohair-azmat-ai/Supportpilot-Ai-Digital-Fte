'use client'

import React, { useCallback, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import {
  AlertTriangle, ArrowLeft, ArrowUpRight, Bot, Brain,
  Cpu, Headphones, Layers3, Send, Tag,
} from 'lucide-react'
import { useConversationDetail } from '../../../../hooks/useConversations'
import { adminApi, messagesApi, aiApi } from '../../../../lib/api'
import { useAuth } from '../../../../hooks/useAuth'
import { ConversationInsight, Message } from '../../../../types'
import { ChatWindow } from '../../../../components/chat/ChatWindow'
import { ChatInput } from '../../../../components/chat/ChatInput'
import { ChannelBadge, ConversationStatusBadge, EscalationFlag } from '../../../../components/ui/Badge'
import { LoadingSpinner } from '../../../../components/ui/LoadingSpinner'
import { useToast } from '../../../../context/ToastContext'
import { cn, formatPercent, formatMs } from '../../../../lib/utils'

// ── AI Insight Panel (admin-only) ────────────────────────────────────────────

const AGENT_STYLE: Record<string, { label: string; cls: string; dot: string }> = {
  billing:   { label: 'Billing',   cls: 'text-indigo-300 bg-indigo-500/15 border-indigo-500/25', dot: 'bg-indigo-400' },
  technical: { label: 'Technical', cls: 'text-amber-300  bg-amber-500/15  border-amber-500/25',  dot: 'bg-amber-400' },
  account:   { label: 'Account',   cls: 'text-purple-300 bg-purple-500/15 border-purple-500/25', dot: 'bg-purple-400' },
  general:   { label: 'General',   cls: 'text-slate-400  bg-slate-700/40  border-slate-700/40',  dot: 'bg-slate-500' },
}

const URGENCY_CLS: Record<string, string> = {
  critical: 'text-red-400',
  high:     'text-orange-400',
  medium:   'text-amber-400',
  low:      'text-emerald-400',
}

const SENTIMENT_CLS: Record<string, string> = {
  positive:   'text-emerald-400',
  neutral:    'text-slate-400',
  negative:   'text-red-400',
  frustrated: 'text-red-400',
}

function InsightField({ label, value, valueClass }: {
  label: string
  value: React.ReactNode
  valueClass?: string
}) {
  return (
    <div className="space-y-0.5">
      <p className="text-[10px] uppercase tracking-wider text-slate-600">{label}</p>
      <p className={cn('text-xs font-semibold truncate', valueClass ?? 'text-slate-200')}>{value}</p>
    </div>
  )
}

function AIInsightPanel({ insight }: { insight: ConversationInsight }) {
  const agentMeta = AGENT_STYLE[insight.routed_agent ?? 'general'] ?? AGENT_STYLE.general
  const confPct = insight.confidence != null ? Math.round(insight.confidence * 100) : null
  const confColor = confPct == null ? 'text-slate-500' : confPct >= 80 ? 'text-emerald-400' : confPct >= 60 ? 'text-amber-400' : 'text-red-400'

  return (
    <div className="border-t border-border/50 bg-background-elevated/30 px-4 py-3">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-indigo-500/15 border border-indigo-500/20">
          <Cpu size={12} className="text-indigo-400" />
        </div>
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          AI Insight · Latest turn
        </span>
      </div>

      {/* Fields grid */}
      <div className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-8">
        {/* Routed agent */}
        <div className="space-y-0.5">
          <p className="text-[10px] uppercase tracking-wider text-slate-600">Routed Agent</p>
          <span className={cn(
            'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold',
            agentMeta.cls,
          )}>
            <span className={cn('h-1.5 w-1.5 rounded-full', agentMeta.dot)} />
            {agentMeta.label}
          </span>
        </div>

        {/* Intent */}
        <InsightField
          label="Intent"
          value={insight.intent ? insight.intent.replace(/_/g, ' ') : '—'}
          valueClass="text-slate-200 capitalize"
        />

        {/* Confidence */}
        <div className="space-y-0.5">
          <p className="text-[10px] uppercase tracking-wider text-slate-600">Confidence</p>
          {confPct != null ? (
            <div className="flex items-center gap-1.5">
              <div className="h-1 w-12 overflow-hidden rounded-full bg-white/10">
                <div
                  className={cn('h-full rounded-full', confPct >= 80 ? 'bg-emerald-400' : confPct >= 60 ? 'bg-amber-400' : 'bg-red-400')}
                  style={{ width: `${confPct}%` }}
                />
              </div>
              <span className={cn('text-xs font-semibold tabular-nums', confColor)}>{confPct}%</span>
            </div>
          ) : (
            <span className="text-xs text-slate-500">—</span>
          )}
        </div>

        {/* Urgency */}
        <InsightField
          label="Urgency"
          value={insight.urgency ?? '—'}
          valueClass={cn('capitalize', insight.urgency ? URGENCY_CLS[insight.urgency] ?? 'text-slate-400' : 'text-slate-500')}
        />

        {/* Sentiment */}
        <InsightField
          label="Sentiment"
          value={insight.sentiment ?? '—'}
          valueClass={cn('capitalize', insight.sentiment ? SENTIMENT_CLS[insight.sentiment] ?? 'text-slate-400' : 'text-slate-500')}
        />

        {/* Response time */}
        {insight.response_time_ms != null && (
          <InsightField
            label="Response time"
            value={formatMs(insight.response_time_ms)}
            valueClass="text-sky-300"
          />
        )}

        {/* Category (from ticket) */}
        {insight.category && (
          <InsightField
            label="Category"
            value={insight.category.replace(/_/g, ' ')}
            valueClass="text-slate-200 capitalize"
          />
        )}

        {/* Priority (from ticket) */}
        {insight.priority && (
          <InsightField
            label="Priority"
            value={insight.priority}
            valueClass={cn('capitalize', insight.priority === 'urgent' ? 'text-red-400' : insight.priority === 'high' ? 'text-orange-400' : insight.priority === 'medium' ? 'text-amber-400' : 'text-slate-400')}
          />
        )}
      </div>

      {/* Escalation detail row */}
      {insight.escalated && (
        <div className="mt-3 flex flex-wrap items-start gap-x-6 gap-y-1.5 rounded-lg border border-red-500/20 bg-red-500/8 px-3 py-2">
          <div className="flex items-center gap-1.5">
            <AlertTriangle size={11} className="text-red-400 shrink-0" />
            <span className="text-[11px] font-semibold text-red-300">Escalated</span>
            {insight.escalation_level && (
              <span className="text-[10px] text-red-400/70">· {insight.escalation_level}</span>
            )}
          </div>
          {insight.escalation_cause && (
            <span className="text-[11px] text-slate-400">
              Cause: <span className="text-slate-300">{insight.escalation_cause.replace(/_/g, ' ')}</span>
            </span>
          )}
          {insight.escalation_reason && (
            <span className="text-[11px] text-slate-400 truncate max-w-xs">
              Reason: <span className="text-slate-300 italic">{insight.escalation_reason}</span>
            </span>
          )}
        </div>
      )}
    </div>
  )
}

export default function ChatDetailPage() {
  const params = useParams()
  const id = params.id as string
  const { conversation, loading, error, addMessages, addUserMessage, addAiMessage } = useConversationDetail(id)
  const [aiLoading, setAiLoading] = useState(false)
  const [streamingContent, setStreamingContent] = useState<string | null>(null)
  const [insight, setInsight] = useState<ConversationInsight | null>(null)
  const [handoffMode, setHandoffMode] = useState<'ai' | 'human'>('ai')
  const [handoffLoading, setHandoffLoading] = useState(false)
  const [adminReply, setAdminReply] = useState('')
  const [adminSending, setAdminSending] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [suggestionsLoading, setSuggestionsLoading] = useState(false)
  const pendingUserMsg = useRef<Message | null>(null)
  const toast = useToast()
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  // Sync handoff_mode from conversation data
  useEffect(() => {
    if (conversation) {
      setHandoffMode((conversation.handoff_mode ?? 'ai') as 'ai' | 'human')
    }
  }, [conversation?.handoff_mode])

  // Fetch AI insight for admins (non-blocking — failure silently ignored)
  useEffect(() => {
    if (!isAdmin || !id) return
    adminApi.getConversationInsight(id)
      .then((data) => setInsight(data))
      .catch(() => {/* no insight yet — new conversation or no metrics */})
  }, [id, isAdmin])

  const handleHandoff = useCallback(async (mode: 'ai' | 'human') => {
    setHandoffLoading(true)
    try {
      await adminApi.setHandoffMode(id, mode)
      setHandoffMode(mode)
      toast.success(mode === 'human' ? 'You are now handling this conversation.' : 'AI has resumed handling this conversation.')
    } catch {
      toast.error('Failed to update handoff mode.')
    } finally {
      setHandoffLoading(false)
    }
  }, [id, toast])

  const handleAdminSend = useCallback(async () => {
    const content = adminReply.trim()
    if (!content) return
    setAdminSending(true)
    try {
      const msg = await adminApi.sendMessage(id, content) as Message
      addAiMessage(msg)  // addAiMessage appends to messages list
      setAdminReply('')
    } catch {
      toast.error('Failed to send message.')
    } finally {
      setAdminSending(false)
    }
  }, [adminReply, id, addAiMessage, toast])

  const handleSend = async (content: string) => {
    if (!conversation) return
    setAiLoading(true)
    setStreamingContent(null)
    setSuggestions([])
    pendingUserMsg.current = null

    console.log('[stream] starting for conversation', id)

    try {
      await messagesApi.stream(id, content, {
        onUserMessage: (userMsg) => {
          console.log('[stream] user_message received', userMsg.id)
          pendingUserMsg.current = userMsg
          addUserMessage(userMsg)
        },
        onToken: (token) => {
          // First token: switch from typing dots to live streaming text
          setAiLoading(false)
          setStreamingContent((prev) => {
            if (prev === null) console.log('[stream] first token received')
            return (prev ?? '') + token
          })
        },
        onDone: (aiMsg) => {
          console.log('[stream] done — ai_message id:', aiMsg.id, 'intent:', aiMsg.intent)
          setStreamingContent(null)
          setAiLoading(false)
          addAiMessage(aiMsg)
          // Fetch smart reply suggestions based on the user's message (non-blocking)
          setSuggestionsLoading(true)
          aiApi.getSuggestions(content)
            .then((res) => setSuggestions(res.suggestions.slice(0, 3)))
            .catch(() => {/* suggestions are non-critical — fail silently */})
            .finally(() => setSuggestionsLoading(false))
        },
        onError: (errMsg) => {
          console.error('[stream] error event:', errMsg)
          setStreamingContent(null)
          setAiLoading(false)
          toast.error(errMsg)
        },
      })
    } catch (err) {
      console.error('[stream] fetch-level error:', err)
      setStreamingContent(null)
      setAiLoading(false)
      toast.error('Streaming failed. Please try again.')
    }
  }

  const handleSuggestionClick = (text: string) => {
    setSuggestions([])
    handleSend(text)
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoadingSpinner center size="lg" label="Loading conversation..." />
      </div>
    )
  }

  if (error || !conversation) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4">
        <p className="text-sm text-red-400">{error || 'Conversation not found'}</p>
        <Link href="/chat" className="text-sm text-accent transition-colors hover:text-accent-light">
          Back to conversations
        </Link>
      </div>
    )
  }

  const aiMessages = conversation.messages.filter((message) => message.sender_type === 'ai')
  const confidenceValues = aiMessages
    .map((message) => message.ai_confidence)
    .filter((value): value is number => value !== null && value !== undefined)
  const averageConfidence =
    confidenceValues.length > 0
      ? confidenceValues.reduce((sum, value) => sum + value, 0) / confidenceValues.length
      : null
  const isEscalated = conversation.status === 'escalated'
  const lastAiMessage = aiMessages[aiMessages.length - 1]
  const lastIntent = lastAiMessage?.intent ?? null
  const isHardBlocked = lastAiMessage?.intent === 'billing_limit'

  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-4xl flex-col overflow-hidden rounded-2xl border border-border bg-background-surface">
      <div className="border-b border-border bg-background-surface/80 px-4 py-4 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <Link
            href="/chat"
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-white/5 hover:text-slate-300"
          >
            <ArrowLeft size={18} />
          </Link>
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-sm font-semibold text-slate-200">
              {conversation.subject || 'Untitled Conversation'}
            </h2>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <ChannelBadge channel={conversation.channel} />
              <ConversationStatusBadge status={conversation.status} />
              <EscalationFlag escalated={isEscalated} />
            </div>
          </div>
          <div className="shrink-0 text-xs text-slate-600">{conversation.messages.length} messages</div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-border/70 bg-background px-3 py-3">
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-slate-500">
              <Layers3 size={14} />
              Unified History
            </div>
            <p className="mt-2 text-sm text-slate-300">
              This thread stays part of your shared support timeline across web, email, and WhatsApp.
            </p>
          </div>

          <div className="rounded-xl border border-border/70 bg-background px-3 py-3">
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-slate-500">
              <Brain size={14} />
              AI Confidence
            </div>
            <p className="mt-2 text-lg font-semibold text-slate-100">
              {averageConfidence === null ? 'Pending' : formatPercent(averageConfidence)}
            </p>
            <p className="text-xs text-slate-500">Average across AI replies in this conversation</p>
          </div>

          <div className="rounded-xl border border-border/70 bg-background px-3 py-3">
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-slate-500">
              <Tag size={14} />
              Last Intent
            </div>
            <p className="mt-2 text-sm font-semibold text-slate-100">
              {lastIntent ? lastIntent.replace(/_/g, ' ') : 'None detected'}
            </p>
            <p className="text-xs text-slate-500">Most recent AI-detected intent</p>
          </div>

          <div className={cn(
            'rounded-xl border px-3 py-3',
            isEscalated ? 'border-red-500/30 bg-red-500/10' : 'border-border/70 bg-background'
          )}>
            <div className={cn(
              'flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em]',
              isEscalated ? 'text-red-400' : 'text-slate-500'
            )}>
              <AlertTriangle size={14} />
              Escalation
            </div>
            <p className="mt-2 text-lg font-semibold text-slate-100">
              {isEscalated ? 'Human follow-up required' : 'AI handling actively'}
            </p>
            <p className={cn('text-xs', isEscalated ? 'text-red-300/70' : 'text-slate-500')}>
              {isEscalated ? 'Flagged for human review' : 'No escalation flag on this conversation'}
            </p>
          </div>
        </div>
      </div>

      {/* AI Insight panel — admin only, shown when metrics are available */}
      {isAdmin && insight && <AIInsightPanel insight={insight} />}

      {/* Human Handoff panel — admin only, shown on escalated conversations */}
      {isAdmin && isEscalated && (
        <div className={cn(
          'border-t px-4 py-3 flex items-center gap-3',
          handoffMode === 'human'
            ? 'border-emerald-500/20 bg-emerald-500/5'
            : 'border-red-500/20 bg-red-500/5'
        )}>
          <div className={cn(
            'flex h-7 w-7 shrink-0 items-center justify-center rounded-full',
            handoffMode === 'human' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
          )}>
            <Headphones size={13} />
          </div>
          <div className="flex-1 min-w-0">
            <p className={cn('text-xs font-semibold', handoffMode === 'human' ? 'text-emerald-300' : 'text-red-300')}>
              {handoffMode === 'human' ? 'Human Active — AI paused' : 'Escalated — awaiting handoff'}
            </p>
            <p className="text-[10px] text-slate-500">
              {handoffMode === 'human'
                ? 'You are replying directly. Click "Return to AI" to resume automation.'
                : 'Click "Take Over" to handle this conversation manually.'}
            </p>
          </div>
          {handoffMode === 'ai' ? (
            <button
              onClick={() => handleHandoff('human')}
              disabled={handoffLoading}
              className="shrink-0 flex items-center gap-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 px-3 py-1.5 text-xs font-semibold text-white transition-colors disabled:opacity-50"
            >
              <Headphones size={12} />
              Take Over
            </button>
          ) : (
            <button
              onClick={() => handleHandoff('ai')}
              disabled={handoffLoading}
              className="shrink-0 flex items-center gap-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 px-3 py-1.5 text-xs font-semibold text-slate-200 transition-colors disabled:opacity-50"
            >
              <Bot size={12} />
              Return to AI
            </button>
          )}
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        <ChatWindow
          messages={conversation.messages}
          channel={conversation.channel}
          escalated={isEscalated}
          isLoading={aiLoading}
          streamingContent={streamingContent}
        />
      </div>

      {/* Bottom input area */}
      {isHardBlocked ? (
        <div className="border-t border-red-500/20 bg-red-500/5 px-4 py-4">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm text-red-300">
              Monthly limit reached — upgrade to continue this conversation.
            </p>
            <Link href="/admin/billing">
              <button className="shrink-0 flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 px-4 py-2 text-sm font-semibold text-white hover:from-indigo-500 hover:to-purple-500 transition-all">
                <ArrowUpRight size={14} />
                Upgrade
              </button>
            </Link>
          </div>
        </div>
      ) : isAdmin && handoffMode === 'human' ? (
        /* Admin reply input when in human handoff mode */
        <div className="border-t border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
          <div className="flex items-end gap-3">
            <textarea
              value={adminReply}
              onChange={(e) => setAdminReply(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleAdminSend()
                }
              }}
              placeholder="Reply as human agent… (Enter to send, Shift+Enter for newline)"
              rows={2}
              className="flex-1 resize-none rounded-xl border border-emerald-500/25 bg-background px-3 py-2.5 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-emerald-500/50 transition-colors"
            />
            <button
              onClick={handleAdminSend}
              disabled={adminSending || !adminReply.trim()}
              className="shrink-0 flex items-center gap-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-white transition-colors disabled:opacity-40"
            >
              <Send size={13} />
              Send
            </button>
          </div>
        </div>
      ) : (
        <>
          <ChatInput
            onSend={handleSend}
            disabled={aiLoading || streamingContent !== null || conversation.status === 'closed'}
            placeholder={conversation.status === 'closed' ? 'This conversation is closed' : 'Type your message...'}
          />
          {/* Smart reply suggestions */}
          {(suggestionsLoading || suggestions.length > 0) && conversation.status !== 'closed' && (
            <div className="flex flex-wrap gap-2 px-4 pb-3 pt-1">
              {suggestionsLoading ? (
                [110, 140, 118].map((w, i) => (
                  <div
                    key={i}
                    className="h-7 animate-pulse rounded-full bg-white/5"
                    style={{ width: w }}
                  />
                ))
              ) : (
                suggestions.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => handleSuggestionClick(s)}
                    className="rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-xs font-medium text-indigo-300 transition-colors hover:border-indigo-500/60 hover:bg-indigo-500/20 hover:text-indigo-200 active:scale-95"
                  >
                    {s}
                  </button>
                ))
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
