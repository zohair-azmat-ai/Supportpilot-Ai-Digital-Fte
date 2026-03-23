import React from 'react'
import { LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'

interface StatsCardProps {
  label: string
  value: number | string
  icon: LucideIcon
  change?: {
    value: number
    label?: string
  }
  color?: 'indigo' | 'purple' | 'emerald' | 'amber' | 'red' | 'blue'
  className?: string
}

const colorMap = {
  indigo: {
    icon: 'bg-indigo-500/15 text-indigo-400',
    glow: 'shadow-indigo-500/10',
    value: 'text-indigo-300',
  },
  purple: {
    icon: 'bg-purple-500/15 text-purple-400',
    glow: 'shadow-purple-500/10',
    value: 'text-purple-300',
  },
  emerald: {
    icon: 'bg-emerald-500/15 text-emerald-400',
    glow: 'shadow-emerald-500/10',
    value: 'text-emerald-300',
  },
  amber: {
    icon: 'bg-amber-500/15 text-amber-400',
    glow: 'shadow-amber-500/10',
    value: 'text-amber-300',
  },
  red: {
    icon: 'bg-red-500/15 text-red-400',
    glow: 'shadow-red-500/10',
    value: 'text-red-300',
  },
  blue: {
    icon: 'bg-blue-500/15 text-blue-400',
    glow: 'shadow-blue-500/10',
    value: 'text-blue-300',
  },
}

export function StatsCard({ label, value, icon: Icon, change, color = 'indigo', className }: StatsCardProps) {
  const colors = colorMap[color]
  const isPositive = change && change.value > 0
  const isNegative = change && change.value < 0
  const isNeutral = change && change.value === 0

  return (
    <div
      className={cn(
        'rounded-xl bg-background-surface border border-border p-5 transition-all duration-200 hover:border-border-subtle shadow-lg',
        colors.glow,
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500 mb-1">{label}</p>
          <p className={cn('text-3xl font-bold tabular-nums', colors.value)}>{value}</p>
          {change !== undefined && (
            <div className={cn(
              'flex items-center gap-1 mt-2 text-xs font-medium',
              isPositive ? 'text-emerald-400' : isNegative ? 'text-red-400' : 'text-slate-500'
            )}>
              {isPositive ? (
                <TrendingUp size={12} />
              ) : isNegative ? (
                <TrendingDown size={12} />
              ) : (
                <Minus size={12} />
              )}
              <span>
                {isPositive ? '+' : ''}{change.value}
                {change.label ? ` ${change.label}` : ''}
              </span>
            </div>
          )}
        </div>
        <div className={cn('rounded-xl p-3', colors.icon)}>
          <Icon size={20} />
        </div>
      </div>
    </div>
  )
}
