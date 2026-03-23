import React from 'react'
import { cn } from '@/lib/utils'

type CardVariant = 'default' | 'elevated' | 'bordered' | 'glass'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant
  title?: string
  description?: string
  action?: React.ReactNode
  footer?: React.ReactNode
  noPadding?: boolean
}

const variantStyles: Record<CardVariant, string> = {
  default: 'bg-background-surface border border-border',
  elevated: 'bg-background-elevated border border-border shadow-xl shadow-black/20',
  bordered: 'bg-background-surface border-2 border-border',
  glass: 'bg-white/5 backdrop-blur-md border border-white/10',
}

export function Card({
  variant = 'default',
  title,
  description,
  action,
  footer,
  noPadding = false,
  children,
  className,
  ...props
}: CardProps) {
  const hasHeader = title || description || action

  return (
    <div
      className={cn(
        'rounded-xl overflow-hidden',
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {hasHeader && (
        <div className="flex items-start justify-between px-6 py-4 border-b border-border">
          <div className="flex flex-col gap-0.5">
            {title && <h3 className="text-base font-semibold text-slate-100">{title}</h3>}
            {description && <p className="text-sm text-slate-500">{description}</p>}
          </div>
          {action && <div className="ml-4 shrink-0">{action}</div>}
        </div>
      )}
      <div className={cn(!noPadding && 'p-6')}>{children}</div>
      {footer && (
        <div className="px-6 py-4 border-t border-border bg-background/50">{footer}</div>
      )}
    </div>
  )
}
