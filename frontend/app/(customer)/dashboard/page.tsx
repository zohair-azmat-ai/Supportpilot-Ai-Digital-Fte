'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  AlertCircle,
  ArrowRight,
  CheckCircle,
  HeadphonesIcon,
  MessageCircle,
  MessageSquarePlus,
  Ticket,
} from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { useTickets } from '@/hooks/useTickets'
import { useConversations } from '@/hooks/useConversations'
import { useToast } from '@/context/ToastContext'
import { StatsCard } from '@/components/dashboard/StatsCard'
import { RecentTickets } from '@/components/dashboard/RecentTickets'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { ChannelBadge, ConversationStatusBadge } from '@/components/ui/Badge'
import { formatRelativeDate } from '@/lib/utils'
import { Conversation } from '@/types'

export default function DashboardPage() {
  const { user } = useAuth()
  const { tickets, loading: ticketsLoading } = useTickets()
  const { conversations, loading: convsLoading, createConversation } = useConversations()
  const router = useRouter()
  const toast = useToast()
  const [creatingChat, setCreatingChat] = useState(false)

  const openTickets = tickets.filter((ticket) => ticket.status === 'open').length
  const resolvedTickets = tickets.filter((ticket) => ticket.status === 'resolved').length

  const handleNewChat = async () => {
    setCreatingChat(true)
    try {
      const conv = await createConversation()
      router.push(`/chat/${conv.id}`)
    } catch {
      setCreatingChat(false)
      toast.error('Failed to start conversation. Please try again.')
    }
  }

  const greeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good morning'
    if (hour < 17) return 'Good afternoon'
    return 'Good evening'
  }

  return (
    <div className="max-w-6xl space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">
            {greeting()}, {user?.name?.split(' ')[0]}
          </h1>
          <p className="mt-0.5 text-sm text-slate-500">Here&apos;s a summary of your support activity</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" size="sm" icon={HeadphonesIcon} onClick={() => router.push('/support')}>
            Submit Request
          </Button>
          <Button
            variant="primary"
            size="sm"
            icon={MessageSquarePlus}
            loading={creatingChat}
            onClick={handleNewChat}
          >
            New Chat
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatsCard label="Total Tickets" value={ticketsLoading ? '-' : tickets.length} icon={Ticket} color="indigo" />
        <StatsCard label="Open Tickets" value={ticketsLoading ? '-' : openTickets} icon={AlertCircle} color="amber" />
        <StatsCard
          label="Conversations"
          value={convsLoading ? '-' : conversations.length}
          icon={MessageCircle}
          color="blue"
        />
        <StatsCard
          label="Resolved"
          value={ticketsLoading ? '-' : resolvedTickets}
          icon={CheckCircle}
          color="emerald"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <Card
          title="Recent Tickets"
          description="Your latest support tickets"
          action={
            <Link href="/tickets">
              <Button variant="ghost" size="sm" icon={ArrowRight} iconPosition="right">
                View all
              </Button>
            </Link>
          }
          className="lg:col-span-3"
          noPadding
        >
          <div className="p-4">
            <RecentTickets tickets={tickets.slice(0, 5)} viewAllHref="/tickets" />
          </div>
        </Card>

        <Card
          title="Recent Conversations"
          description="Your latest chats"
          action={
            <Link href="/chat">
              <Button variant="ghost" size="sm" icon={ArrowRight} iconPosition="right">
                View all
              </Button>
            </Link>
          }
          className="lg:col-span-2"
          noPadding
        >
          <div className="space-y-2 p-4">
            {convsLoading ? (
              <div className="py-8 text-center text-sm text-slate-500">Loading...</div>
            ) : conversations.length === 0 ? (
              <div className="py-8 text-center">
                <MessageCircle className="mx-auto mb-2 h-8 w-8 text-slate-600" />
                <p className="text-sm text-slate-500">No conversations yet</p>
              </div>
            ) : (
              conversations.slice(0, 3).map((conv: Conversation) => (
                <Link
                  key={conv.id}
                  href={`/chat/${conv.id}`}
                  className="flex flex-col gap-1.5 rounded-lg border border-border/50 bg-background/50 px-3 py-3 transition-all hover:border-border hover:bg-background-elevated/30"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm font-medium text-slate-200">
                      {conv.subject || 'Untitled Conversation'}
                    </span>
                    <ConversationStatusBadge status={conv.status} />
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <ChannelBadge channel={conv.channel} />
                    {conv.status === 'escalated' && (
                      <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-red-400">
                        Human review
                      </span>
                    )}
                    <span className="text-[10px] text-slate-600">{formatRelativeDate(conv.created_at)}</span>
                  </div>
                </Link>
              ))
            )}
            <button
              onClick={handleNewChat}
              disabled={creatingChat}
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-border py-2.5 text-sm text-slate-500 transition-all hover:border-accent/40 hover:text-accent disabled:opacity-50"
            >
              <MessageSquarePlus size={14} />
              Start new conversation
            </button>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="flex items-center justify-between rounded-xl border border-indigo-500/20 bg-gradient-to-br from-indigo-500/10 to-transparent p-5">
          <div>
            <h3 className="mb-1 text-sm font-semibold text-slate-200">Start a New Chat</h3>
            <p className="text-xs text-slate-500">Get instant AI-powered support</p>
          </div>
          <Button
            variant="primary"
            size="sm"
            icon={MessageSquarePlus}
            loading={creatingChat}
            onClick={handleNewChat}
          >
            Chat Now
          </Button>
        </div>

        <div className="flex items-center justify-between rounded-xl border border-purple-500/20 bg-gradient-to-br from-purple-500/10 to-transparent p-5">
          <div>
            <h3 className="mb-1 text-sm font-semibold text-slate-200">Submit a Request</h3>
            <p className="text-xs text-slate-500">Create a detailed support ticket</p>
          </div>
          <Link href="/support">
            <Button variant="secondary" size="sm" icon={HeadphonesIcon}>
              Submit
            </Button>
          </Link>
        </div>
      </div>
    </div>
  )
}
