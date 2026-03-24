'use client'

import React, { useState } from 'react'
import { Plus, Ticket as TicketIcon } from 'lucide-react'
import { useTickets } from '../../../hooks/useTickets'
import { TicketCard } from '../../../components/tickets/TicketCard'
import { Button } from '../../../components/ui/Button'
import { Modal } from '../../../components/ui/Modal'
import { LoadingSpinner } from '../../../components/ui/LoadingSpinner'
import { EmptyState } from '../../../components/ui/EmptyState'
import { Input } from '../../../components/ui/Input'
import { Textarea } from '../../../components/ui/Textarea'
import { Select } from '../../../components/ui/Select'
import { Ticket, TicketStatus, TicketPriority } from '../../../types'
import { cn } from '../../../lib/utils'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useToast } from '../../../context/ToastContext'

const filterTabs: { label: string; value: TicketStatus | 'all' }[] = [
  { label: 'All', value: 'all' },
  { label: 'Open', value: 'open' },
  { label: 'In Progress', value: 'in_progress' },
  { label: 'Resolved', value: 'resolved' },
  { label: 'Closed', value: 'closed' },
]

const schema = z.object({
  title: z.string().min(5, 'Title must be at least 5 characters'),
  description: z.string().min(20, 'Description must be at least 20 characters'),
  category: z.string().min(1, 'Please select a category'),
  priority: z.enum(['low', 'medium', 'high', 'urgent'] as const),
})

type CreateForm = z.infer<typeof schema>

const CATEGORY_OPTIONS = [
  { value: 'Technical', label: 'Technical Issue' },
  { value: 'Billing', label: 'Billing' },
  { value: 'General', label: 'General Inquiry' },
  { value: 'Feature Request', label: 'Feature Request' },
  { value: 'Bug Report', label: 'Bug Report' },
]

const PRIORITY_OPTIONS = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'urgent', label: 'Urgent' },
]

export default function TicketsPage() {
  const { tickets, loading, error, createTicket } = useTickets()
  const [activeFilter, setActiveFilter] = useState<TicketStatus | 'all'>('all')
  const [showModal, setShowModal] = useState(false)
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null)
  const [apiError, setApiError] = useState<string | null>(null)
  const toast = useToast()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CreateForm>({
    resolver: zodResolver(schema),
    defaultValues: { priority: 'medium' },
  })

  const filtered = tickets.filter((t) => activeFilter === 'all' || t.status === activeFilter)

  const handleCreate = async (data: CreateForm) => {
    setApiError(null)
    try {
      await createTicket({
        title: data.title,
        description: data.description,
        category: data.category,
        priority: data.priority as TicketPriority,
      })
      reset()
      setShowModal(false)
      toast.success('Ticket created successfully!')
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to create ticket'
          : 'Failed to create ticket'
      setApiError(msg)
      toast.error(msg)
    }
  }

  return (
    <div className="max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">My Tickets</h1>
          <p className="text-sm text-slate-500 mt-0.5">Manage your support tickets</p>
        </div>
        <Button variant="primary" icon={Plus} onClick={() => setShowModal(true)}>
          Create Ticket
        </Button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex gap-1 rounded-xl bg-background-surface border border-border p-1 w-fit">
        {filterTabs.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setActiveFilter(tab.value)}
            className={cn(
              'rounded-lg px-4 py-1.5 text-xs font-medium transition-all',
              activeFilter === tab.value
                ? 'bg-accent text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            )}
          >
            {tab.label}
            {tab.value !== 'all' && (
              <span className="ml-1.5 tabular-nums opacity-60">
                {tickets.filter((t) => t.status === tab.value).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Loading */}
      {loading && <LoadingSpinner center size="lg" label="Loading tickets..." />}

      {/* Empty */}
      {!loading && filtered.length === 0 && (
        <EmptyState
          icon={TicketIcon}
          title={activeFilter === 'all' ? 'No tickets yet' : `No ${activeFilter.replace('_', ' ')} tickets`}
          description={
            activeFilter === 'all'
              ? 'Create a ticket to get support from our team.'
              : `You don't have any ${activeFilter.replace('_', ' ')} tickets.`
          }
          action={
            activeFilter === 'all'
              ? { label: 'Create Ticket', onClick: () => setShowModal(true), icon: Plus }
              : undefined
          }
        />
      )}

      {/* Grid */}
      {!loading && filtered.length > 0 && (
        <div className="grid grid-cols-1 gap-3">
          {filtered.map((ticket) => (
            <TicketCard
              key={ticket.id}
              ticket={ticket}
              onClick={() => setSelectedTicket(ticket)}
            />
          ))}
        </div>
      )}

      {/* Create Ticket Modal */}
      <Modal
        isOpen={showModal}
        onClose={() => { setShowModal(false); reset(); setApiError(null) }}
        title="Create Support Ticket"
        description="Describe your issue and we'll get back to you"
        size="lg"
      >
        <form onSubmit={handleSubmit(handleCreate)} className="space-y-4">
          {apiError && (
            <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-400">
              {apiError}
            </div>
          )}
          <Input
            label="Title"
            placeholder="Brief description of the issue"
            error={errors.title?.message}
            {...register('title')}
          />
          <div className="grid grid-cols-2 gap-3">
            <Select
              label="Category"
              options={CATEGORY_OPTIONS}
              placeholder="Select category"
              error={errors.category?.message}
              {...register('category')}
            />
            <Select
              label="Priority"
              options={PRIORITY_OPTIONS}
              error={errors.priority?.message}
              {...register('priority')}
            />
          </div>
          <Textarea
            label="Description"
            placeholder="Detailed description of your issue..."
            rows={4}
            error={errors.description?.message}
            {...register('description')}
          />
          <div className="flex gap-3 pt-2">
            <Button
              type="button"
              variant="outline"
              fullWidth
              onClick={() => { setShowModal(false); reset(); setApiError(null) }}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" fullWidth loading={isSubmitting}>
              {isSubmitting ? 'Creating...' : 'Create Ticket'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Ticket Detail Modal */}
      <Modal
        isOpen={!!selectedTicket}
        onClose={() => setSelectedTicket(null)}
        title={selectedTicket?.title}
        size="lg"
      >
        {selectedTicket && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Status</p>
                <span className="text-sm text-slate-300 capitalize">{selectedTicket.status.replace('_', ' ')}</span>
              </div>
              <div>
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Priority</p>
                <span className="text-sm text-slate-300 capitalize">{selectedTicket.priority}</span>
              </div>
              <div>
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Category</p>
                <span className="text-sm text-slate-300">{selectedTicket.category}</span>
              </div>
              <div>
                <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Ticket ID</p>
                <span className="text-xs font-mono text-slate-400">#{selectedTicket.id.slice(0, 12)}</span>
              </div>
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">Description</p>
              <p className="text-sm text-slate-300 leading-relaxed">{selectedTicket.description}</p>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
