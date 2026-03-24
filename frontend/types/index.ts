export type Role = 'customer' | 'admin'
export type TicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed'
export type TicketPriority = 'low' | 'medium' | 'high' | 'urgent'
export type ConversationStatus = 'active' | 'closed' | 'escalated'
export type Channel = 'web' | 'email' | 'whatsapp'
export type SenderType = 'user' | 'ai' | 'agent'

export interface User {
  id: string
  name: string
  email: string
  role: Role
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Conversation {
  id: string
  user_id: string
  channel: Channel
  status: ConversationStatus
  subject: string | null
  created_at: string
  updated_at: string
}

export interface ConversationDetail extends Conversation {
  messages: Message[]
}

export interface Message {
  id: string
  conversation_id: string
  sender_type: SenderType
  content: string
  intent: string | null
  ai_confidence: number | null
  sentiment: string | null
  urgency: string | null
  escalate: boolean | null
  created_at: string
}

export interface Ticket {
  id: string
  user_id: string
  conversation_id: string | null
  title: string
  description: string
  category: string
  priority: TicketPriority
  status: TicketStatus
  assigned_to: string | null
  created_at: string
  updated_at: string
}

export interface AdminStats {
  total_users: number
  total_tickets: number
  open_tickets: number
  total_conversations: number
  active_conversations: number
  resolved_today: number
}

export interface IntentCount {
  intent: string
  count: number
}

export interface SentimentCount {
  sentiment: string
  count: number
}

export interface UrgencyCount {
  urgency: string
  count: number
}

export interface EscalationCauseCount {
  cause: string
  count: number
}

export interface MetricsOverview {
  total_interactions: number
  avg_confidence: number
  avg_response_ms: number
  escalation_rate: number
  escalation_count: number
  ticket_creation_rate: number
  avg_tools_per_run: number
  avg_iterations: number
  top_intents: IntentCount[]
  sentiment_breakdown: SentimentCount[]
  urgency_distribution: UrgencyCount[]
  escalation_cause_breakdown: EscalationCauseCount[]
  similar_issue_count: number
  similar_issue_rate: number
}

export interface ChannelMetric {
  channel: string
  interaction_count: number
  avg_confidence: number
  avg_response_ms: number
  escalation_count: number
  escalation_rate: number
}

export interface ChannelMetricsResponse {
  channels: ChannelMetric[]
  total_interactions: number
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface SupportSubmitResponse {
  conversation_id: string
  ticket_id: string
  confirmation_message: string
  ai_response: string
}
