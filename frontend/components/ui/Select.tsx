import React from 'react'
import { cn } from '../../lib/utils'

interface SelectOption {
  value: string
  label: string
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
  helperText?: string
  options: SelectOption[]
  placeholder?: string
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, helperText, options, placeholder, className, id, ...props }, ref) => {
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
        <select
          ref={ref}
          id={inputId}
          className={cn(
            'w-full rounded-lg bg-background-surface border px-3 py-2.5 text-sm text-slate-100',
            'transition-all duration-200 appearance-none cursor-pointer',
            'focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent',
            error
              ? 'border-red-500/50 focus:ring-red-500/30 focus:border-red-500'
              : 'border-border hover:border-border-subtle',
            className
          )}
          {...props}
        >
          {placeholder && (
            <option value="" className="bg-background-surface text-slate-500">
              {placeholder}
            </option>
          )}
          {options.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-background-surface text-slate-100">
              {opt.label}
            </option>
          ))}
        </select>
        {error && (
          <p className="text-xs text-red-400">{error}</p>
        )}
        {helperText && !error && (
          <p className="text-xs text-slate-500">{helperText}</p>
        )}
      </div>
    )
  }
)

Select.displayName = 'Select'
