import React from 'react'
import { Globe, Mail, MessageCircleMore, AlertTriangle, LucideIcon } from 'lucide-react'
import { cn } from '../../lib/utils'
import { TicketStatus, TicketPriority, ConversationStatus, Channel, Role } from '../../types'

type BadgeVariant =
  | 'default'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'purple'
  | 'gray'
  | 'indigo'

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
  success: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  warning: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  danger: 'bg-red-500/20 text-red-400 border-red-500/30',
  info: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  purple: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  gray: 'bg-slate-700/50 text-slate-400 border-slate-600/50',
  indigo: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
}

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
  size?: 'sm' | 'md'
}

export function Badge({ variant = 'default', size = 'md', children, className, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border font-medium',
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-0.5 text-xs',
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  )
}

export function StatusBadge({ status }: { status: TicketStatus }) {
  const map: Record<TicketStatus, { variant: BadgeVariant; label: string }> = {
    open: { variant: 'info', label: 'Open' },
    in_progress: { variant: 'warning', label: 'In Progress' },
    resolved: { variant: 'success', label: 'Resolved' },
    closed: { variant: 'gray', label: 'Closed' },
  }
  const { variant, label } = map[status] || { variant: 'default', label: status }
  return <Badge variant={variant}>{label}</Badge>
}

export function PriorityBadge({ priority }: { priority: TicketPriority }) {
  const map: Record<TicketPriority, { variant: BadgeVariant; label: string }> = {
    low: { variant: 'gray', label: 'Low' },
    medium: { variant: 'info', label: 'Medium' },
    high: { variant: 'warning', label: 'High' },
    urgent: { variant: 'danger', label: 'Urgent' },
  }
  const { variant, label } = map[priority] || { variant: 'default', label: priority }
  return <Badge variant={variant}>{label}</Badge>
}

export function ConversationStatusBadge({ status }: { status: ConversationStatus }) {
  const map: Record<ConversationStatus, { variant: BadgeVariant; label: string }> = {
    active: { variant: 'success', label: 'Active' },
    closed: { variant: 'gray', label: 'Closed' },
    escalated: { variant: 'danger', label: 'Escalated' },
  }
  const { variant, label } = map[status] || { variant: 'default', label: status }
  return <Badge variant={variant}>{label}</Badge>
}

export function getChannelMeta(channel: string): {
  variant: BadgeVariant
  label: string
  icon: LucideIcon
} {
  const map: Record<string, { variant: BadgeVariant; label: string; icon: LucideIcon }> = {
    web: { variant: 'info', label: 'Web', icon: Globe },
    email: { variant: 'warning', label: 'Email', icon: Mail },
    whatsapp: { variant: 'success', label: 'WhatsApp', icon: MessageCircleMore },
  }

  return map[channel] || { variant: 'default', label: channel, icon: Globe }
}

export function ChannelBadge({ channel }: { channel: Channel | string }) {
  const { variant, label, icon: Icon } = getChannelMeta(channel)

  return (
    <Badge variant={variant} className="gap-1.5">
      <Icon size={12} />
      <span>{label}</span>
    </Badge>
  )
}

export function EscalationFlag({ escalated }: { escalated: boolean }) {
  if (!escalated) return null

  return (
    <Badge variant="danger" className="gap-1.5">
      <AlertTriangle size={12} />
      <span>Escalation Flag</span>
    </Badge>
  )
}

export function RoleBadge({ role }: { role: Role }) {
  const map: Record<Role, { variant: BadgeVariant; label: string }> = {
    customer: { variant: 'indigo', label: 'Customer' },
    admin: { variant: 'purple', label: 'Admin' },
  }
  const { variant, label } = map[role] || { variant: 'default', label: role }
  return <Badge variant={variant}>{label}</Badge>
}
