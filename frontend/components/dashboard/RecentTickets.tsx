import React from 'react'
import Link from 'next/link'
import { Ticket } from '@/types'
import { StatusBadge, PriorityBadge } from '@/components/ui/Badge'
import { formatRelativeDate, truncate } from '@/lib/utils'
import { EmptyState } from '@/components/ui/EmptyState'
import { Ticket as TicketIcon, ArrowRight } from 'lucide-react'

interface RecentTicketsProps {
  tickets: Ticket[]
  viewAllHref?: string
}

export function RecentTickets({ tickets, viewAllHref }: RecentTicketsProps) {
  if (tickets.length === 0) {
    return (
      <EmptyState
        icon={TicketIcon}
        title="No tickets yet"
        description="Tickets will appear here once created."
      />
    )
  }

  return (
    <div className="space-y-2">
      {tickets.slice(0, 5).map((ticket) => (
        <div
          key={ticket.id}
          className="flex items-center justify-between rounded-lg bg-background/50 border border-border/50 px-4 py-3 hover:border-border hover:bg-background-elevated/30 transition-all duration-150"
        >
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-200 truncate">{truncate(ticket.title, 45)}</p>
            <div className="flex items-center gap-2 mt-1">
              <PriorityBadge priority={ticket.priority} />
              <span className="text-[10px] text-slate-600">{formatRelativeDate(ticket.created_at)}</span>
            </div>
          </div>
          <div className="ml-3 shrink-0">
            <StatusBadge status={ticket.status} />
          </div>
        </div>
      ))}
      {viewAllHref && (
        <Link
          href={viewAllHref}
          className="flex items-center justify-center gap-2 rounded-lg border border-dashed border-border py-2.5 text-sm text-slate-500 hover:text-accent hover:border-accent/40 transition-all"
        >
          View all tickets
          <ArrowRight size={14} />
        </Link>
      )}
    </div>
  )
}
