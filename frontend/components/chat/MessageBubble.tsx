import React from 'react'
import Link from 'next/link'
import { Bot, User as UserIcon, Lock, ArrowRight, AlertTriangle } from 'lucide-react'
import { Channel, Message } from '../../types'
import { formatRelativeDate, capitalize, cn } from '../../lib/utils'
import { ChannelBadge, EscalationFlag, SentimentBadge } from '../ui/Badge'

interface MessageBubbleProps {
  message: Message
  channel: Channel
  escalated?: boolean
  isStreaming?: boolean
}

// Marker injected by channel_pipeline and message_service for soft warnings
const SOFT_WARN_MARKER = '\n\n---\n_Note:'

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color =
    pct >= 80 ? 'bg-emerald-400' : pct >= 60 ? 'bg-amber-400' : 'bg-red-400'
  const textColor =
    pct >= 80 ? 'text-emerald-400' : pct >= 60 ? 'text-amber-400' : 'text-red-400'

  return (
    <div className="flex items-center gap-2">
      <div className="h-1 w-16 overflow-hidden rounded-full bg-white/10">
        <div
          className={cn('h-full rounded-full transition-all', color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={cn('text-[10px] font-medium tabular-nums', textColor)}>
        {pct}%
      </span>
    </div>
  )
}

// Hard-block card — replaces the normal AI bubble when intent=billing_limit
function BillingLimitCard({ channel }: { channel: Channel }) {
  return (
    <div className="flex gap-3 animate-slide-up">
      {/* Bot avatar */}
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-background-elevated border border-red-500/30 text-red-400">
        <Lock size={14} />
      </div>

      {/* Card */}
      <div className="max-w-[75%] space-y-0">
        <div className="rounded-2xl rounded-tl-sm border border-red-500/25 bg-red-500/8 px-4 py-4">
          <p className="text-sm font-semibold text-red-300 mb-1">
            Monthly limit reached
          </p>
          <p className="text-sm text-slate-400 leading-relaxed mb-4">
            You've used all your AI messages for this month on your current plan.
            Upgrade to continue the conversation.
          </p>
          <Link href="/admin/billing">
            <button className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 px-4 py-2 text-sm font-semibold text-white hover:from-indigo-500 hover:to-purple-500 transition-all">
              <ArrowRight size={14} />
              Upgrade Plan
            </button>
          </Link>
        </div>
        <div className="flex items-center gap-2 pt-1.5 pl-1">
          <ChannelBadge channel={channel} />
          <span className="inline-flex items-center rounded-full bg-red-500/10 border border-red-500/20 px-2 py-0.5 text-[10px] font-medium text-red-400">
            billing_limit
          </span>
        </div>
      </div>
    </div>
  )
}

export function MessageBubble({ message, channel, escalated = false, isStreaming = false }: MessageBubbleProps) {
  const isUser = message.sender_type === 'user'
  const isAI = message.sender_type === 'ai'

  // Hard-block: replace entire bubble with upgrade prompt
  if (isAI && message.intent === 'billing_limit') {
    return <BillingLimitCard channel={channel} />
  }

  // Soft-warning: detect the appended note and split it out
  const hasSoftWarn = isAI && !isStreaming && message.content.includes(SOFT_WARN_MARKER)
  const mainContent = hasSoftWarn
    ? message.content.split(SOFT_WARN_MARKER)[0]
    : message.content
  // Extract the note text: strip leading space and trailing _ from markdown italic
  const warnNote = hasSoftWarn
    ? (message.content.split(SOFT_WARN_MARKER)[1] ?? '').replace(/^[\s_]+|[_\s]+$/g, '').trim()
    : null

  return (
    <div
      className={cn(
        'flex gap-3 animate-slide-up',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      {/* Avatar */}
      <div className={cn(
        'flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold',
        isUser
          ? 'bg-gradient-to-br from-indigo-500 to-purple-500 text-white'
          : 'bg-background-elevated border border-border text-slate-400'
      )}>
        {isUser ? <UserIcon size={14} /> : <Bot size={14} />}
      </div>

      {/* Content */}
      <div className={cn('flex flex-col gap-1.5 max-w-[75%]', isUser && 'items-end')}>
        {/* Main bubble */}
        <div
          className={cn(
            'rounded-2xl px-4 py-3 text-sm leading-relaxed',
            isUser
              ? 'bg-gradient-to-br from-indigo-600 to-purple-600 text-white rounded-tr-sm'
              : 'bg-background-surface border border-border text-slate-200 rounded-tl-sm'
          )}
        >
          {mainContent.split('\n').map((line, i) => (
            <React.Fragment key={i}>
              {i > 0 && <br />}
              {line}
            </React.Fragment>
          ))}
          {isStreaming && (
            <span className="ml-0.5 inline-block h-[1em] w-0.5 translate-y-[1px] animate-pulse rounded-sm bg-current opacity-70" />
          )}
        </div>

        {/* Soft-warning note */}
        {warnNote && (
          <div className="flex items-start gap-2 rounded-xl border border-amber-500/20 bg-amber-500/8 px-3 py-2 max-w-full">
            <AlertTriangle size={12} className="shrink-0 mt-0.5 text-amber-400" />
            <p className="text-[11px] text-amber-300 leading-relaxed">
              {warnNote}
              {' '}
              <Link href="/admin/billing" className="underline hover:text-amber-200 transition-colors">
                View plan
              </Link>
            </p>
          </div>
        )}

        {/* AI signal row */}
        {isAI && (
          <div className={cn('flex flex-wrap items-center gap-2', isUser && 'flex-row-reverse')}>
            <ChannelBadge channel={channel} />

            {message.intent && (
              <span className="inline-flex items-center rounded-full bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 text-[10px] font-medium text-indigo-400">
                {capitalize(message.intent.replace(/_/g, ' '))}
              </span>
            )}

            {message.sentiment && (
              <SentimentBadge sentiment={message.sentiment} />
            )}

            {message.ai_confidence !== null && message.ai_confidence !== undefined && (
              <ConfidenceBar value={message.ai_confidence} />
            )}

            <span className="text-[10px] text-slate-600">
              {formatRelativeDate(message.created_at)}
            </span>

            <EscalationFlag escalated={escalated} />
          </div>
        )}

        {/* User message timestamp */}
        {isUser && (
          <span className="text-[10px] text-slate-600">
            {formatRelativeDate(message.created_at)}
          </span>
        )}
      </div>
    </div>
  )
}
