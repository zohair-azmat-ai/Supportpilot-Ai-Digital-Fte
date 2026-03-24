import React from 'react'
import { cn } from '../../lib/utils'

type SpinnerSize = 'sm' | 'md' | 'lg' | 'xl'

interface LoadingSpinnerProps {
  size?: SpinnerSize
  center?: boolean
  className?: string
  label?: string
}

const sizeMap: Record<SpinnerSize, string> = {
  sm: 'h-4 w-4 border-2',
  md: 'h-6 w-6 border-2',
  lg: 'h-10 w-10 border-[3px]',
  xl: 'h-14 w-14 border-4',
}

export function LoadingSpinner({ size = 'md', center = false, className, label }: LoadingSpinnerProps) {
  const spinner = (
    <div
      className={cn(
        'rounded-full border-t-transparent border-accent animate-spin',
        sizeMap[size],
        className
      )}
      role="status"
      aria-label={label || 'Loading'}
    />
  )

  if (center) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 min-h-[120px]">
        {spinner}
        {label && <p className="text-sm text-slate-500">{label}</p>}
      </div>
    )
  }

  return spinner
}

export function PageLoader({ label = 'Loading...' }: { label?: string }) {
  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <div className="flex flex-col items-center gap-4">
        <div className="relative">
          <div className="h-12 w-12 rounded-full border-4 border-accent/20 border-t-accent animate-spin" />
          <div className="absolute inset-0 rounded-full bg-accent/5 blur-xl" />
        </div>
        <p className="text-sm text-slate-500 animate-pulse">{label}</p>
      </div>
    </div>
  )
}
