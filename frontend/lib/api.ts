import axios from 'axios'
import { getToken, clearAuth, TOKEN_KEY } from './auth'
import {
  User,
  Conversation,
  ConversationDetail,
  Message,
  Ticket,
  AdminStats,
  MetricsOverview,
  ChannelMetricsResponse,
  TokenResponse,
  SupportSubmitResponse,
  TicketStatus,
  TicketPriority,
  Role,
  BillingSummary,
  BillingPlan,
} from '../types'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearAuth()
      if (typeof window !== 'undefined') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// Auth
export const authApi = {
  signup: async (data: {
    name: string
    email: string
    password: string
    role: Role
  }): Promise<TokenResponse> => {
    const res = await api.post('/auth/signup', data)
    return res.data
  },

  login: async (data: {
    email: string
    password: string
  }): Promise<TokenResponse> => {
    const res = await api.post('/auth/login', data)
    return res.data
  },

  getMe: async (): Promise<User> => {
    const res = await api.get('/auth/me')
    return res.data
  },
}

// Conversations
export const conversationsApi = {
  list: async (): Promise<Conversation[]> => {
    const res = await api.get('/conversations')
    return res.data
  },

  create: async (data: { subject?: string; channel?: string }): Promise<Conversation> => {
    const res = await api.post('/conversations', data)
    return res.data
  },

  getById: async (id: string): Promise<ConversationDetail> => {
    const res = await api.get(`/conversations/${id}`)
    return res.data
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/conversations/${id}`)
  },
}

// Messages
export const messagesApi = {
  send: async (
    conversationId: string,
    content: string
  ): Promise<{ user_message: Message; ai_message: Message }> => {
    const res = await api.post(`/conversations/${conversationId}/messages`, { content })
    return res.data
  },

  stream: async (
    conversationId: string,
    content: string,
    callbacks: {
      onUserMessage: (msg: Message) => void
      onToken: (token: string) => void
      onDone: (msg: Message) => void
      onError: (error: string) => void
    }
  ): Promise<void> => {
    const { onUserMessage, onToken, onDone, onError } = callbacks
    const token = typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
    const url = `${baseUrl}/conversations/${conversationId}/messages/stream`
    console.log('[stream] fetch →', url, 'auth:', !!token)

    const response = await fetch(
      url,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ content }),
      }
    )

    console.log('[stream] response status:', response.status)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) throw new Error('No response body')

    const decoder = new TextDecoder()
    let buffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue

          try {
            const event = JSON.parse(raw)
            if (event.type === 'user_message') onUserMessage(event.message as Message)
            else if (event.type === 'token') onToken(event.content as string)
            else if (event.type === 'done') onDone(event.message as Message)
            else if (event.type === 'error') onError(event.message as string)
          } catch {
            // Skip malformed SSE events
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  },
}

// Tickets
export const ticketsApi = {
  list: async (): Promise<Ticket[]> => {
    const res = await api.get('/tickets')
    return res.data
  },

  create: async (data: {
    title: string
    description: string
    category: string
    priority: TicketPriority
  }): Promise<Ticket> => {
    const res = await api.post('/tickets', data)
    return res.data
  },

  getById: async (id: string): Promise<Ticket> => {
    const res = await api.get(`/tickets/${id}`)
    return res.data
  },

  update: async (
    id: string,
    data: Partial<{ status: TicketStatus; priority: TicketPriority; assigned_to: string }>
  ): Promise<Ticket> => {
    const res = await api.patch(`/tickets/${id}`, data)
    return res.data
  },
}

// Support
export const supportApi = {
  submit: async (data: {
    name: string
    email: string
    subject: string
    category: string
    priority: TicketPriority
    message: string
  }): Promise<SupportSubmitResponse> => {
    const res = await api.post('/support/submit', data)
    return res.data
  },
}

// Admin
export const adminApi = {
  getStats: async (): Promise<AdminStats> => {
    const res = await api.get('/admin/stats')
    return res.data
  },

  getTickets: async (): Promise<Ticket[]> => {
    const res = await api.get('/admin/tickets')
    return res.data
  },

  getConversations: async (): Promise<Conversation[]> => {
    const res = await api.get('/admin/conversations')
    return res.data
  },

  getConversationInsight: async (conversationId: string) => {
    const res = await api.get(`/admin/conversations/${conversationId}/insight`)
    return res.data
  },

  getUsers: async (): Promise<User[]> => {
    const res = await api.get('/admin/users')
    return res.data
  },

  updateTicket: async (
    id: string,
    data: Partial<{ status: TicketStatus; priority: TicketPriority; assigned_to: string }>
  ): Promise<Ticket> => {
    const res = await api.patch(`/admin/tickets/${id}`, data)
    return res.data
  },
}

export const metricsApi = {
  getOverview: async (): Promise<MetricsOverview> => {
    const res = await api.get('/metrics/overview')
    return res.data
  },

  getChannels: async (): Promise<ChannelMetricsResponse> => {
    const res = await api.get('/metrics/channels')
    return res.data
  },

  getRouting: async (): Promise<{ routing: { conversation_id: string; routed_agent: string }[] }> => {
    const res = await api.get('/metrics/routing')
    return res.data
  },
}

export const billingApi = {
  getSummary: async (): Promise<BillingSummary> => {
    const res = await api.get('/admin/billing/summary')
    return res.data
  },

  getPlans: async (): Promise<{ plans: BillingPlan[]; current_plan: string }> => {
    const res = await api.get('/admin/billing/plans')
    return res.data
  },

  updatePlan: async (planTier: string): Promise<{ updated: boolean; plan_tier: string; plan_detail: BillingPlan }> => {
    const res = await api.patch('/admin/billing/plan', { plan_tier: planTier })
    return res.data
  },
}

export default api
