import React from 'react'
import { LucideIcon, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

type Variant = 'primary' | 'secondary' | 'danger' | 'outline' | 'ghost'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  fullWidth?: boolean
  icon?: LucideIcon
  iconPosition?: 'left' | 'right'
  children?: React.ReactNode
}

const variantStyles: Record<Variant, string> = {
  primary:
    'bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:from-indigo-500 hover:to-purple-500 shadow-lg shadow-indigo-500/25',
  secondary:
    'bg-background-surface text-slate-300 hover:bg-background-elevated hover:text-white border border-border',
  danger:
    'bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/30',
  outline:
    'bg-transparent text-slate-300 hover:bg-white/5 border border-border hover:border-accent',
  ghost:
    'bg-transparent text-slate-400 hover:bg-white/5 hover:text-white',
}

const sizeStyles: Record<Size, string> = {
  sm: 'px-3 py-1.5 text-xs gap-1.5',
  md: 'px-4 py-2 text-sm gap-2',
  lg: 'px-6 py-3 text-base gap-2.5',
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  fullWidth = false,
  icon: Icon,
  iconPosition = 'left',
  children,
  className,
  disabled,
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading

  return (
    <button
      className={cn(
        'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:ring-offset-2 focus:ring-offset-background active:scale-[0.98] select-none',
        variantStyles[variant],
        sizeStyles[size],
        fullWidth && 'w-full',
        isDisabled && 'opacity-50 cursor-not-allowed pointer-events-none',
        className
      )}
      disabled={isDisabled}
      {...props}
    >
      {loading ? (
        <Loader2 className="animate-spin shrink-0" size={size === 'sm' ? 14 : size === 'lg' ? 18 : 16} />
      ) : (
        Icon && iconPosition === 'left' && (
          <Icon className="shrink-0" size={size === 'sm' ? 14 : size === 'lg' ? 18 : 16} />
        )
      )}
      {children}
      {!loading && Icon && iconPosition === 'right' && (
        <Icon className="shrink-0" size={size === 'sm' ? 14 : size === 'lg' ? 18 : 16} />
      )}
    </button>
  )
}
