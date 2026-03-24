import React from 'react'
import { cn } from '../../lib/utils'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helperText?: string
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, className, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-')

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={inputId}
            className="text-sm font-medium text-slate-300"
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={cn(
            'w-full rounded-lg bg-background-surface border px-3 py-2.5 text-sm text-slate-100 placeholder:text-slate-500',
            'transition-all duration-200',
            'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent',
            error
              ? 'border-red-500/50 focus:ring-red-500/30 focus:border-red-500'
              : 'border-border hover:border-border-subtle',
            className
          )}
          {...props}
        />
        {error && (
          <p className="text-xs text-red-400 flex items-center gap-1">{error}</p>
        )}
        {helperText && !error && (
          <p className="text-xs text-slate-500">{helperText}</p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'
