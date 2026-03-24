import React from 'react'
import { Bot, User as UserIcon } from 'lucide-react'
import { Channel, Message } from '../../types'
import { formatRelativeDate, capitalize, cn } from '../../lib/utils'
import { ChannelBadge, EscalationFlag, SentimentBadge } from '../ui/Badge'

interface MessageBubbleProps {
  message: Message
  channel: Channel
  escalated?: boolean
  isStreaming?: boolean
}

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

export function MessageBubble({ message, channel, escalated = false, isStreaming = false }: MessageBubbleProps) {
  const isUser = message.sender_type === 'user'
  const isAI = message.sender_type === 'ai'

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
        <div
          className={cn(
            'rounded-2xl px-4 py-3 text-sm leading-relaxed',
            isUser
              ? 'bg-gradient-to-br from-indigo-600 to-purple-600 text-white rounded-tr-sm'
              : 'bg-background-surface border border-border text-slate-200 rounded-tl-sm'
          )}
        >
          {message.content.split('\n').map((line, i) => (
            <React.Fragment key={i}>
              {i > 0 && <br />}
              {line}
            </React.Fragment>
          ))}
          {isStreaming && (
            <span className="ml-0.5 inline-block h-[1em] w-0.5 translate-y-[1px] animate-pulse rounded-sm bg-current opacity-70" />
          )}
        </div>

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
