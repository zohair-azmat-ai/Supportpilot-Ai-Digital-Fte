'use client'

import React from 'react'
import { User, Mail, Shield, Bell } from 'lucide-react'
import { useAuth } from '../../../hooks/useAuth'
import { Card } from '../../../components/ui/Card'
import { RoleBadge } from '../../../components/ui/Badge'
import { formatDate, getInitials } from '../../../lib/utils'

export default function SettingsPage() {
  const { user } = useAuth()

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Settings</h1>
        <p className="text-sm text-slate-500 mt-0.5">Manage your account preferences</p>
      </div>

      {/* Profile */}
      <Card title="Profile" description="Your account information">
        <div className="flex items-center gap-4 mb-6">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-500 text-xl font-bold text-white">
            {user ? getInitials(user.name) : '?'}
          </div>
          <div>
            <p className="text-lg font-semibold text-slate-100">{user?.name}</p>
            <p className="text-sm text-slate-500">{user?.email}</p>
            <div className="mt-1">
              {user && <RoleBadge role={user.role} />}
            </div>
          </div>
        </div>

        <div className="space-y-3">
          {[
            { icon: User, label: 'Full Name', value: user?.name },
            { icon: Mail, label: 'Email Address', value: user?.email },
            { icon: Shield, label: 'Role', value: user?.role ? (user.role.charAt(0).toUpperCase() + user.role.slice(1)) : '' },
          ].map((field) => {
            const Icon = field.icon
            return (
              <div
                key={field.label}
                className="flex items-center gap-3 rounded-lg bg-background border border-border px-4 py-3"
              >
                <Icon size={16} className="text-slate-500 shrink-0" />
                <div className="flex-1">
                  <p className="text-xs text-slate-500">{field.label}</p>
                  <p className="text-sm text-slate-200">{field.value || '—'}</p>
                </div>
              </div>
            )
          })}
        </div>
      </Card>

      {/* Account Details */}
      <Card title="Account Details">
        <div className="space-y-3">
          <div className="flex items-center justify-between py-2 border-b border-border/50">
            <span className="text-sm text-slate-500">Account ID</span>
            <span className="text-xs font-mono text-slate-400">#{user?.id?.slice(0, 12)}</span>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-border/50">
            <span className="text-sm text-slate-500">Member Since</span>
            <span className="text-sm text-slate-400">{user?.created_at ? formatDate(user.created_at) : '—'}</span>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-sm text-slate-500">Account Status</span>
            <span className={`text-sm font-medium ${user?.is_active ? 'text-emerald-400' : 'text-red-400'}`}>
              {user?.is_active ? 'Active' : 'Inactive'}
            </span>
          </div>
        </div>
      </Card>

      {/* Notifications placeholder */}
      <Card title="Notifications" description="Manage your notification preferences">
        <div className="flex items-center gap-3 rounded-lg bg-background border border-border px-4 py-4">
          <Bell size={18} className="text-slate-500" />
          <div className="flex-1">
            <p className="text-sm font-medium text-slate-300">Email Notifications</p>
            <p className="text-xs text-slate-500">Receive updates about your tickets and conversations</p>
          </div>
          <div className="h-5 w-9 rounded-full bg-accent flex items-center px-0.5 cursor-pointer">
            <div className="h-4 w-4 rounded-full bg-white shadow translate-x-4 transition-transform" />
          </div>
        </div>
      </Card>
    </div>
  )
}
