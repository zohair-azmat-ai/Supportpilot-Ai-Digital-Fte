'use client'

import React, { useEffect, useRef } from 'react'
import { Bot, MessageCircle } from 'lucide-react'
import { Channel, Message } from '../../types'
import { MessageBubble } from './MessageBubble'

interface ChatWindowProps {
  messages: Message[]
  channel: Channel
  escalated?: boolean
  isLoading?: boolean
  streamingContent?: string | null
}

function TypingIndicator() {
  return (
    <div className="flex gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-background-elevated border border-border text-slate-400">
        <Bot size={14} />
      </div>
      <div className="rounded-2xl rounded-tl-sm bg-background-surface border border-border px-4 py-3">
        <div className="flex items-center gap-1.5">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-2 w-2 rounded-full bg-slate-500 animate-bounce"
              style={{ animationDelay: `${i * 0.15}s`, animationDuration: '0.8s' }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

export function ChatWindow({
  messages,
  channel,
  escalated = false,
  isLoading = false,
  streamingContent = null,
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading, streamingContent])

  const streamingMessage: Message | null = streamingContent != null
    ? {
        id: '__streaming__',
        conversation_id: '',
        sender_type: 'ai',
        content: streamingContent,
        intent: null,
        ai_confidence: null,
        sentiment: null,
        urgency: null,
        escalate: null,
        created_at: new Date().toISOString(),
      }
    : null

  if (messages.length === 0 && !isLoading && streamingContent == null) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-center px-4">
        <div className="rounded-2xl bg-background-surface border border-border p-5">
          <MessageCircle className="h-10 w-10 text-slate-500 mx-auto" />
        </div>
        <div>
          <h3 className="text-base font-semibold text-slate-200 mb-1">Start the conversation</h3>
          <p className="text-sm text-slate-500 max-w-xs">
            Send a message below and our AI assistant will respond instantly.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-5 p-4 lg:p-6">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} channel={channel} escalated={escalated} />
      ))}
      {streamingMessage && (
        <MessageBubble
          message={streamingMessage}
          channel={channel}
          escalated={escalated}
          isStreaming
        />
      )}
      {isLoading && streamingContent == null && <TypingIndicator />}
      <div ref={bottomRef} />
    </div>
  )
}
