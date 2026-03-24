import React from 'react'
import { Bot, User as UserIcon } from 'lucide-react'
import { Channel, Message } from '@/types'
import { formatRelativeDate, capitalize } from '../../lib/utils'
import { cn } from '../../lib/utils'
import { ChannelBadge, EscalationFlag } from '@/components/ui/Badge'

interface MessageBubbleProps {
  message: Message
  channel: Channel
  escalated?: boolean
}

export function MessageBubble({ message, channel, escalated = false }: MessageBubbleProps) {
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
      <div className={cn('flex flex-col gap-1 max-w-[75%]', isUser && 'items-end')}>
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
        </div>

        <div className={cn('flex flex-wrap items-center gap-2', isUser && 'flex-row-reverse')}>
          <ChannelBadge channel={channel} />
          {isAI && message.intent && (
            <span className="inline-flex items-center rounded-full bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 text-[10px] font-medium text-indigo-400">
              {capitalize(message.intent.replace(/_/g, ' '))}
            </span>
          )}
          {isAI && message.ai_confidence !== null && message.ai_confidence !== undefined && (
            <span className="text-[10px] text-slate-600">
              {Math.round(message.ai_confidence * 100)}% confidence
            </span>
          )}
          <span className="text-[10px] text-slate-600">
            {formatRelativeDate(message.created_at)}
          </span>
          {isAI && <EscalationFlag escalated={escalated} />}
        </div>
      </div>
    </div>
  )
}
