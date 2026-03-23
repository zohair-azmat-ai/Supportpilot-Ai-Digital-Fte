'use client'

import React from 'react'
import { Ticket, TicketStatus } from '@/types'
import { StatusBadge, PriorityBadge, Badge } from '@/components/ui/Badge'
import { formatDate, truncate } from '@/lib/utils'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { Ticket as TicketIcon } from 'lucide-react'

interface TicketTableProps {
  tickets: Ticket[]
  loading?: boolean
  onStatusChange?: (id: string, status: TicketStatus) => void
  showUserColumn?: boolean
}

const STATUS_OPTIONS: { value: TicketStatus; label: string }[] = [
  { value: 'open', label: 'Open' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'closed', label: 'Closed' },
]

export function TicketTable({ tickets, loading, onStatusChange, showUserColumn = false }: TicketTableProps) {
  if (loading) {
    return <LoadingSpinner center size="lg" label="Loading tickets..." />
  }

  if (tickets.length === 0) {
    return (
      <EmptyState
        icon={TicketIcon}
        title="No tickets found"
        description="No tickets match your current filters."
      />
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-background-elevated/50">
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
              Ticket
            </th>
            {showUserColumn && (
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                User
              </th>
            )}
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
              Category
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
              Priority
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
              Status
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
              Created
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/50">
          {tickets.map((ticket) => (
            <tr
              key={ticket.id}
              className="bg-background-surface hover:bg-background-elevated transition-colors"
            >
              <td className="px-4 py-3">
                <div>
                  <p className="font-medium text-slate-200 text-sm">{truncate(ticket.title, 40)}</p>
                  <p className="text-xs text-slate-500 font-mono mt-0.5">#{ticket.id.slice(0, 8)}</p>
                </div>
              </td>
              {showUserColumn && (
                <td className="px-4 py-3 text-xs text-slate-400 font-mono">
                  {ticket.user_id.slice(0, 8)}
                </td>
              )}
              <td className="px-4 py-3">
                <Badge variant="gray" size="sm">{ticket.category}</Badge>
              </td>
              <td className="px-4 py-3">
                <PriorityBadge priority={ticket.priority} />
              </td>
              <td className="px-4 py-3">
                {onStatusChange ? (
                  <select
                    value={ticket.status}
                    onChange={(e) => onStatusChange(ticket.id, e.target.value as TicketStatus)}
                    className="rounded-md bg-background border border-border text-xs px-2 py-1 text-slate-300 focus:outline-none focus:ring-1 focus:ring-accent/50 cursor-pointer"
                  >
                    {STATUS_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value} className="bg-background-surface">
                        {opt.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <StatusBadge status={ticket.status} />
                )}
              </td>
              <td className="px-4 py-3 text-xs text-slate-500">{formatDate(ticket.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
