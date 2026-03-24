'use client'

import React, { useEffect } from 'react'
import { X } from 'lucide-react'
import { cn } from '../../lib/utils'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  description?: string
  children: React.ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
}

const sizeMap = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-2xl',
}

export function Modal({ isOpen, onClose, title, description, children, size = 'md', className }: ModalProps) {
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) {
      document.addEventListener('keydown', handleKey)
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.removeEventListener('keydown', handleKey)
      document.body.style.overflow = ''
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Panel */}
      <div
        className={cn(
          'relative w-full rounded-2xl bg-background-surface border border-border shadow-2xl shadow-black/50 animate-slide-up',
          sizeMap[size],
          className
        )}
      >
        {(title || description) && (
          <div className="flex items-start justify-between px-6 py-4 border-b border-border">
            <div>
              {title && <h2 className="text-base font-semibold text-slate-100">{title}</h2>}
              {description && <p className="text-sm text-slate-500 mt-0.5">{description}</p>}
            </div>
            <button
              onClick={onClose}
              className="ml-4 p-1 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-white/5 transition-colors"
              aria-label="Close modal"
            >
              <X size={18} />
            </button>
          </div>
        )}
        {!title && !description && (
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-1 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-white/5 transition-colors z-10"
            aria-label="Close modal"
          >
            <X size={18} />
          </button>
        )}
        <div className="p-6">{children}</div>
      </div>
    </div>
  )
}
