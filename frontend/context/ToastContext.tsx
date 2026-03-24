'use client'

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react'
import { CheckCircle, XCircle, Info, X } from 'lucide-react'
import { cn } from '../lib/utils'

// ─── Types ───────────────────────────────────────────────────────────────────

type ToastType = 'success' | 'error' | 'info'

interface Toast {
  id: string
  type: ToastType
  message: string
  duration?: number
}

interface ToastContextValue {
  success: (message: string, duration?: number) => void
  error: (message: string, duration?: number) => void
  info: (message: string, duration?: number) => void
}

// ─── Context ─────────────────────────────────────────────────────────────────

const ToastContext = createContext<ToastContextValue | null>(null)

// ─── Single Toast Item ────────────────────────────────────────────────────────

const ICONS: Record<ToastType, React.ElementType> = {
  success: CheckCircle,
  error: XCircle,
  info: Info,
}

const STYLES: Record<ToastType, string> = {
  success: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  error: 'border-red-500/30 bg-red-500/10 text-red-300',
  info: 'border-indigo-500/30 bg-indigo-500/10 text-indigo-300',
}

const ICON_STYLES: Record<ToastType, string> = {
  success: 'text-emerald-400',
  error: 'text-red-400',
  info: 'text-indigo-400',
}

function ToastItem({
  toast,
  onDismiss,
}: {
  toast: Toast
  onDismiss: (id: string) => void
}) {
  const [visible, setVisible] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    // Slight delay so the enter animation plays
    const enterTimer = setTimeout(() => setVisible(true), 10)
    timerRef.current = setTimeout(() => {
      setVisible(false)
      setTimeout(() => onDismiss(toast.id), 300)
    }, toast.duration ?? 4000)

    return () => {
      clearTimeout(enterTimer)
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [toast.id, toast.duration, onDismiss])

  const Icon = ICONS[toast.type]

  return (
    <div
      className={cn(
        'flex items-start gap-3 rounded-xl border px-4 py-3 shadow-lg backdrop-blur-sm transition-all duration-300',
        STYLES[toast.type],
        visible
          ? 'translate-x-0 opacity-100'
          : 'translate-x-4 opacity-0'
      )}
      style={{ minWidth: '280px', maxWidth: '380px' }}
    >
      <Icon size={16} className={cn('mt-0.5 shrink-0', ICON_STYLES[toast.type])} />
      <p className="flex-1 text-sm leading-relaxed">{toast.message}</p>
      <button
        onClick={() => {
          setVisible(false)
          setTimeout(() => onDismiss(toast.id), 300)
        }}
        className="ml-1 shrink-0 opacity-60 hover:opacity-100 transition-opacity"
        aria-label="Dismiss"
      >
        <X size={14} />
      </button>
    </div>
  )
}

// ─── Provider ────────────────────────────────────────────────────────────────

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const add = useCallback((type: ToastType, message: string, duration?: number) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`
    setToasts((prev) => [...prev, { id, type, message, duration }])
  }, [])

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const value: ToastContextValue = {
    success: useCallback((msg, dur) => add('success', msg, dur), [add]),
    error: useCallback((msg, dur) => add('error', msg, dur), [add]),
    info: useCallback((msg, dur) => add('info', msg, dur), [add]),
  }

  return (
    <ToastContext.Provider value={value}>
      {children}
      {/* Toast portal — fixed top-right */}
      <div
        className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none"
        aria-live="polite"
        aria-atomic="false"
      >
        {toasts.map((toast) => (
          <div key={toast.id} className="pointer-events-auto">
            <ToastItem toast={toast} onDismiss={dismiss} />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within a ToastProvider')
  return ctx
}
