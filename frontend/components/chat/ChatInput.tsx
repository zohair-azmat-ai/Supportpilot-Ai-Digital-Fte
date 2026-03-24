'use client'

import React, { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { Send } from 'lucide-react'
import { cn } from '../../lib/utils'

interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
  placeholder?: string
}

export function ChatInput({ onSend, disabled = false, placeholder = 'Type your message...' }: ChatInputProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = 'auto'
    const newHeight = Math.min(textarea.scrollHeight, 120)
    textarea.style.height = `${newHeight}px`
  }, [value])

  const handleSend = () => {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="border-t border-border bg-background/80 backdrop-blur-md p-4">
      <div className="flex items-end gap-3 rounded-xl bg-background-surface border border-border focus-within:border-accent/50 focus-within:ring-1 focus-within:ring-accent/30 transition-all duration-200 px-4 py-3">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className={cn(
            'flex-1 resize-none bg-transparent text-sm text-slate-100 placeholder:text-slate-500',
            'focus:outline-none max-h-[120px] leading-relaxed',
            disabled && 'opacity-50 cursor-not-allowed'
          )}
        />
        <div className="flex items-center gap-2 shrink-0 pb-0.5">
          {value.length > 0 && (
            <span className="text-[10px] text-slate-600 tabular-nums">{value.length}</span>
          )}
          <button
            onClick={handleSend}
            disabled={!value.trim() || disabled}
            className={cn(
              'flex h-8 w-8 items-center justify-center rounded-lg transition-all duration-200',
              value.trim() && !disabled
                ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:from-indigo-500 hover:to-purple-500 shadow-lg shadow-indigo-500/25 active:scale-95'
                : 'bg-background-elevated text-slate-600 cursor-not-allowed'
            )}
            aria-label="Send message"
          >
            <Send size={14} />
          </button>
        </div>
      </div>
      <p className="mt-1.5 text-center text-[10px] text-slate-600">
        Press Enter to send · Shift+Enter for new line
      </p>
    </div>
  )
}
