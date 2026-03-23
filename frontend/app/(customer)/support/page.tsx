'use client'

import React from 'react'
import { HeadphonesIcon, Shield, Zap, Clock } from 'lucide-react'
import { SupportForm } from '@/components/forms/SupportForm'
import { useAuth } from '@/hooks/useAuth'
import { Card } from '@/components/ui/Card'

const highlights = [
  {
    icon: Zap,
    title: 'Instant AI Response',
    description: 'Our AI analyzes your request and provides an immediate response',
  },
  {
    icon: Clock,
    title: '24/7 Support',
    description: 'Available around the clock, every day of the year',
  },
  {
    icon: Shield,
    title: 'Secure & Private',
    description: 'Your information is encrypted and kept confidential',
  },
]

export default function SupportPage() {
  const { user } = useAuth()

  return (
    <div className="max-w-5xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Submit a Support Request</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Describe your issue and our AI will help you immediately
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form */}
        <div className="lg:col-span-2">
          <Card title="Support Request" description="Fill out the form below to get help">
            <SupportForm
              defaultName={user?.name}
              defaultEmail={user?.email}
            />
          </Card>
        </div>

        {/* Sidebar info */}
        <div className="space-y-4">
          <div className="rounded-xl border border-indigo-500/20 bg-gradient-to-br from-indigo-500/10 to-transparent p-5">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-purple-600 shadow-lg shadow-indigo-500/25 mb-4">
              <HeadphonesIcon size={20} className="text-white" />
            </div>
            <h3 className="text-base font-semibold text-slate-100 mb-1">
              Intelligent Support
            </h3>
            <p className="text-sm text-slate-500 leading-relaxed">
              Your request is analyzed by AI to provide the fastest, most relevant response possible.
            </p>
          </div>

          {highlights.map((item) => {
            const Icon = item.icon
            return (
              <div
                key={item.title}
                className="flex gap-3 rounded-xl border border-border bg-background-surface p-4"
              >
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-background-elevated border border-border">
                  <Icon size={15} className="text-accent" />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-200">{item.title}</p>
                  <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{item.description}</p>
                </div>
              </div>
            )
          })}

          <div className="rounded-xl border border-border bg-background-surface p-4">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
              Response Time
            </p>
            <div className="space-y-2">
              {[
                { priority: 'Urgent', time: '< 1 hour', color: 'text-red-400' },
                { priority: 'High', time: '< 4 hours', color: 'text-amber-400' },
                { priority: 'Medium', time: '< 24 hours', color: 'text-blue-400' },
                { priority: 'Low', time: '< 72 hours', color: 'text-slate-400' },
              ].map((item) => (
                <div key={item.priority} className="flex items-center justify-between text-xs">
                  <span className={item.color}>{item.priority}</span>
                  <span className="text-slate-500">{item.time}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
