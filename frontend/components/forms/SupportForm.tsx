'use client'

import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { CheckCircle, MessageSquare, Ticket, ArrowRight, AlertCircle, RotateCcw } from 'lucide-react'
import Link from 'next/link'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { Select } from '@/components/ui/Select'
import { Button } from '@/components/ui/Button'
import { supportApi } from '../../lib/api'
import { SupportSubmitResponse, TicketPriority } from '@/types'

const schema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  subject: z.string().min(5, 'Subject must be at least 5 characters'),
  category: z.string().min(1, 'Please select a category'),
  priority: z.enum(['low', 'medium', 'high', 'urgent'] as const),
  message: z.string().min(20, 'Message must be at least 20 characters'),
})

type FormData = z.infer<typeof schema>

interface SupportFormProps {
  defaultName?: string
  defaultEmail?: string
}

const CATEGORY_OPTIONS = [
  { value: 'Technical', label: 'Technical Issue' },
  { value: 'Billing', label: 'Billing' },
  { value: 'General', label: 'General Inquiry' },
  { value: 'Feature Request', label: 'Feature Request' },
  { value: 'Bug Report', label: 'Bug Report' },
]

const PRIORITY_OPTIONS = [
  { value: 'low', label: 'Low - Not time sensitive' },
  { value: 'medium', label: 'Medium - Needs attention soon' },
  { value: 'high', label: 'High - Urgent issue' },
  { value: 'urgent', label: 'Urgent - Critical problem' },
]

export function SupportForm({ defaultName, defaultEmail }: SupportFormProps) {
  const [submitResult, setSubmitResult] = useState<SupportSubmitResponse | null>(null)
  const [apiError, setApiError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: defaultName || '',
      email: defaultEmail || '',
      priority: 'medium',
    },
  })

  const onSubmit = async (data: FormData) => {
    setApiError(null)
    try {
      const result = await supportApi.submit({
        name: data.name,
        email: data.email,
        subject: data.subject,
        category: data.category,
        priority: data.priority as TicketPriority,
        message: data.message,
      })
      setSubmitResult(result)
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to submit request. Please try again.'
          : 'Failed to submit request. Please try again.'
      setApiError(msg)
    }
  }

  if (submitResult) {
    return (
      <div className="flex flex-col items-center text-center py-6 gap-6 animate-fade-in">
        <div className="rounded-full bg-emerald-500/20 border border-emerald-500/30 p-5">
          <CheckCircle className="h-10 w-10 text-emerald-400" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-slate-100 mb-1">Request Submitted!</h2>
          <p className="text-slate-400 text-sm max-w-md">{submitResult.confirmation_message}</p>
        </div>

        <div className="w-full rounded-xl bg-background-elevated border border-border p-4 text-left space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Ticket ID</span>
            <span className="text-xs font-mono text-emerald-400">#{submitResult.ticket_id.slice(0, 12)}</span>
          </div>
          <div className="border-t border-border/50 pt-3">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">AI Response</p>
            <p className="text-sm text-slate-300 leading-relaxed">{submitResult.ai_response}</p>
          </div>
        </div>

        <div className="flex gap-3 w-full">
          <Link href="/tickets" className="flex-1">
            <Button variant="outline" fullWidth icon={Ticket}>
              View Tickets
            </Button>
          </Link>
          <Link href={`/chat/${submitResult.conversation_id}`} className="flex-1">
            <Button variant="primary" fullWidth icon={MessageSquare}>
              Open Chat
            </Button>
          </Link>
        </div>

        <button
          onClick={() => {
            setSubmitResult(null)
            setApiError(null)
            reset({ name: defaultName || '', email: defaultEmail || '', priority: 'medium' })
          }}
          className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors mx-auto"
        >
          <RotateCcw size={12} />
          Submit another request
        </button>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      {apiError && (
        <div className="flex items-center gap-2 rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-400">
          <AlertCircle size={16} className="shrink-0" />
          {apiError}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Input
          label="Full Name"
          placeholder="John Doe"
          error={errors.name?.message}
          {...register('name')}
        />
        <Input
          label="Email"
          type="email"
          placeholder="john@example.com"
          error={errors.email?.message}
          {...register('email')}
        />
      </div>

      <Input
        label="Subject"
        placeholder="Brief description of your issue"
        error={errors.subject?.message}
        {...register('subject')}
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Select
          label="Category"
          options={CATEGORY_OPTIONS}
          placeholder="Select a category"
          error={errors.category?.message}
          {...register('category')}
        />
        <Select
          label="Priority"
          options={PRIORITY_OPTIONS}
          error={errors.priority?.message}
          {...register('priority')}
        />
      </div>

      <Textarea
        label="Message"
        placeholder="Please describe your issue in detail (minimum 20 characters)..."
        rows={5}
        error={errors.message?.message}
        {...register('message')}
      />

      <Button
        type="submit"
        variant="primary"
        size="lg"
        fullWidth
        loading={isSubmitting}
        icon={ArrowRight}
        iconPosition="right"
      >
        {isSubmitting ? 'Submitting...' : 'Submit Support Request'}
      </Button>
    </form>
  )
}
