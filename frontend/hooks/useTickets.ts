'use client'

import { useState, useCallback, useEffect } from 'react'
import { Ticket, TicketPriority, TicketStatus } from '@/types'
import { ticketsApi } from '@/lib/api'

export function useTickets() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchTickets = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await ticketsApi.list()
      setTickets(data)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load tickets'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchTickets()
  }, [fetchTickets])

  const createTicket = useCallback(
    async (data: {
      title: string
      description: string
      category: string
      priority: TicketPriority
    }): Promise<Ticket> => {
      const ticket = await ticketsApi.create(data)
      setTickets((prev) => [ticket, ...prev])
      return ticket
    },
    []
  )

  const updateTicket = useCallback(
    async (
      id: string,
      data: Partial<{ status: TicketStatus; priority: TicketPriority; assigned_to: string }>
    ): Promise<Ticket> => {
      const updated = await ticketsApi.update(id, data)
      setTickets((prev) => prev.map((t) => (t.id === id ? updated : t)))
      return updated
    },
    []
  )

  return { tickets, loading, error, fetchTickets, createTicket, updateTicket }
}
