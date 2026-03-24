'use client'

import React, { useEffect, useState, useCallback } from 'react'
import { RefreshCw, Filter } from 'lucide-react'
import { adminApi } from '../../../../lib/api'
import { Ticket, TicketStatus, TicketPriority } from '@/types'
import { TicketTable } from '@/components/tickets/TicketTable'
import { Button } from '@/components/ui/Button'
import { cn } from '../../../../lib/utils'

const STATUS_FILTERS: { label: string; value: TicketStatus | 'all' }[] = [
  { label: 'All', value: 'all' },
  { label: 'Open', value: 'open' },
  { label: 'In Progress', value: 'in_progress' },
  { label: 'Resolved', value: 'resolved' },
  { label: 'Closed', value: 'closed' },
]

const PRIORITY_FILTERS: { label: string; value: TicketPriority | 'all' }[] = [
  { label: 'All', value: 'all' },
  { label: 'Urgent', value: 'urgent' },
  { label: 'High', value: 'high' },
  { label: 'Medium', value: 'medium' },
  { label: 'Low', value: 'low' },
]

const PAGE_SIZE = 10

export default function AdminTicketsPage() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<TicketStatus | 'all'>('all')
  const [priorityFilter, setPriorityFilter] = useState<TicketPriority | 'all'>('all')
  const [page, setPage] = useState(1)
  const [sortField, setSortField] = useState<'created_at' | 'priority'>('created_at')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')

  const fetchTickets = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await adminApi.getTickets()
      setTickets(data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load tickets'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchTickets()
  }, [fetchTickets])

  const handleStatusChange = async (id: string, status: TicketStatus) => {
    try {
      const updated = await adminApi.updateTicket(id, { status })
      setTickets((prev) => prev.map((t) => (t.id === id ? updated : t)))
    } catch {
      // silently fail
    }
  }

  const filtered = tickets
    .filter((t) => statusFilter === 'all' || t.status === statusFilter)
    .filter((t) => priorityFilter === 'all' || t.priority === priorityFilter)
    .sort((a, b) => {
      if (sortField === 'created_at') {
        return sortDir === 'desc'
          ? new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          : new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      }
      const pOrder = { urgent: 0, high: 1, medium: 2, low: 3 }
      const pa = pOrder[a.priority]
      const pb = pOrder[b.priority]
      return sortDir === 'asc' ? pa - pb : pb - pa
    })

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const handleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortDir('desc')
    }
  }

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">All Tickets</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {filtered.length} ticket{filtered.length !== 1 ? 's' : ''} total
          </p>
        </div>
        <Button variant="outline" size="sm" icon={RefreshCw} onClick={fetchTickets}>
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex items-center gap-2">
          <Filter size={14} className="text-slate-500" />
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Status:</span>
          <div className="flex gap-1 rounded-lg bg-background-surface border border-border p-1">
            {STATUS_FILTERS.map((f) => (
              <button
                key={f.value}
                onClick={() => { setStatusFilter(f.value); setPage(1) }}
                className={cn(
                  'rounded-md px-3 py-1 text-xs font-medium transition-all',
                  statusFilter === f.value
                    ? 'bg-purple-500 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Priority:</span>
          <div className="flex gap-1 rounded-lg bg-background-surface border border-border p-1">
            {PRIORITY_FILTERS.map((f) => (
              <button
                key={f.value}
                onClick={() => { setPriorityFilter(f.value); setPage(1) }}
                className={cn(
                  'rounded-md px-3 py-1 text-xs font-medium transition-all',
                  priorityFilter === f.value
                    ? 'bg-purple-500 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2 ml-auto">
          <span className="text-xs text-slate-500">Sort:</span>
          <button
            onClick={() => handleSort('created_at')}
            className={cn(
              'text-xs px-2 py-1 rounded-md border transition-all',
              sortField === 'created_at'
                ? 'border-purple-500/40 text-purple-400 bg-purple-500/10'
                : 'border-border text-slate-500 hover:text-slate-300'
            )}
          >
            Date {sortField === 'created_at' && (sortDir === 'desc' ? '↓' : '↑')}
          </button>
          <button
            onClick={() => handleSort('priority')}
            className={cn(
              'text-xs px-2 py-1 rounded-md border transition-all',
              sortField === 'priority'
                ? 'border-purple-500/40 text-purple-400 bg-purple-500/10'
                : 'border-border text-slate-500 hover:text-slate-300'
            )}
          >
            Priority {sortField === 'priority' && (sortDir === 'desc' ? '↓' : '↑')}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Table */}
      <TicketTable
        tickets={paginated}
        loading={loading}
        onStatusChange={handleStatusChange}
        showUserColumn={true}
      />

      {/* Pagination */}
      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-500">
            Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length}
          </p>
          <div className="flex gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded-lg border border-border px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 disabled:opacity-40 hover:bg-background-elevated transition-all"
            >
              Previous
            </button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
              <button
                key={p}
                onClick={() => setPage(p)}
                className={cn(
                  'rounded-lg border px-3 py-1.5 text-xs transition-all',
                  page === p
                    ? 'border-purple-500/40 bg-purple-500/10 text-purple-400'
                    : 'border-border text-slate-400 hover:text-slate-200 hover:bg-background-elevated'
                )}
              >
                {p}
              </button>
            ))}
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="rounded-lg border border-border px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 disabled:opacity-40 hover:bg-background-elevated transition-all"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
