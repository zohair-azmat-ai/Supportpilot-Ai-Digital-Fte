import React from 'react'
import { Ticket } from '../../types'
import { StatusBadge, PriorityBadge, Badge } from '../ui/Badge'
import { formatRelativeDate, truncate } from '../../lib/utils'
import { cn } from '../../lib/utils'
import { Clock } from 'lucide-react'

interface TicketCardProps {
  ticket: Ticket
  onClick?: () => void
  className?: string
}

export function TicketCard({ ticket, onClick, className }: TicketCardProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        'rounded-xl bg-background-surface border border-border p-4 transition-all duration-200',
        onClick && 'cursor-pointer hover:border-accent/40 hover:bg-background-elevated',
        className
      )}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-slate-200 truncate">{ticket.title}</h3>
          <p className="mt-0.5 text-xs text-slate-500 line-clamp-2">
            {truncate(ticket.description, 100)}
          </p>
        </div>
        <StatusBadge status={ticket.status} />
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <Badge variant="gray" size="sm">{ticket.category}</Badge>
        <PriorityBadge priority={ticket.priority} />
        <div className="ml-auto flex items-center gap-1 text-[10px] text-slate-600">
          <Clock size={10} />
          <span>{formatRelativeDate(ticket.created_at)}</span>
        </div>
      </div>
    </div>
  )
}
