'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { AlertTriangle, ArrowLeft, Brain, Layers3 } from 'lucide-react'
import { useConversationDetail } from '@/hooks/useConversations'
import { messagesApi } from '@/lib/api'
import { ChatWindow } from '@/components/chat/ChatWindow'
import { ChatInput } from '@/components/chat/ChatInput'
import { ChannelBadge, ConversationStatusBadge, EscalationFlag } from '@/components/ui/Badge'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useToast } from '@/context/ToastContext'
import { formatPercent } from '@/lib/utils'

export default function ChatDetailPage() {
  const params = useParams()
  const id = params.id as string
  const { conversation, loading, error, addMessages } = useConversationDetail(id)
  const [aiLoading, setAiLoading] = useState(false)
  const toast = useToast()

  const handleSend = async (content: string) => {
    if (!conversation) return
    setAiLoading(true)
    try {
      const { user_message, ai_message } = await messagesApi.send(id, content)
      addMessages(user_message, ai_message)
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to send message'
          : 'Failed to send message. Please try again.'
      toast.error(msg)
    } finally {
      setAiLoading(false)
    }
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

        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
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
              <AlertTriangle size={14} />
              Escalation
            </div>
            <p className="mt-2 text-lg font-semibold text-slate-100">
              {isEscalated ? 'Human follow-up required' : 'AI handling actively'}
            </p>
            <p className="text-xs text-slate-500">
              {isEscalated ? 'Flagged for human review' : 'No escalation flag on this conversation'}
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <ChatWindow
          messages={conversation.messages}
          channel={conversation.channel}
          escalated={isEscalated}
          isLoading={aiLoading}
        />
      </div>

      <ChatInput
        onSend={handleSend}
        disabled={aiLoading || conversation.status === 'closed'}
        placeholder={conversation.status === 'closed' ? 'This conversation is closed' : 'Type your message...'}
      />
    </div>
  )
}
