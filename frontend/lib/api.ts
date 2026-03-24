import axios from 'axios'
import { getToken, clearAuth } from './auth'
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
}

export default api
