'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { AlertCircle, UserPlus, Users, Shield } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/hooks/useAuth'
import { Role } from '@/types'
import { cn } from '@/lib/utils'

const schema = z
  .object({
    name: z.string().min(2, 'Name must be at least 2 characters'),
    email: z.string().email('Invalid email address'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string().min(1, 'Please confirm your password'),
    role: z.enum(['customer', 'admin'] as const),
  })
  .refine((d) => d.password === d.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

type FormData = z.infer<typeof schema>

export default function SignupPage() {
  const router = useRouter()
  const { signup } = useAuth()
  const [apiError, setApiError] = useState<string | null>(null)
  const [selectedRole, setSelectedRole] = useState<Role>('customer')

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { role: 'customer' },
  })

  const handleRoleSelect = (role: Role) => {
    setSelectedRole(role)
    setValue('role', role)
  }

  const onSubmit = async (data: FormData) => {
    setApiError(null)
    try {
      await signup(data.name, data.email, data.password, data.role)
      router.push('/dashboard')
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to create account'
          : 'Failed to create account. Please try again.'
      setApiError(msg)
    }
  }

  const roleOptions: { value: Role; label: string; description: string; icon: typeof Users }[] = [
    {
      value: 'customer',
      label: 'Customer',
      description: 'Get support and manage your tickets',
      icon: Users,
    },
    {
      value: 'admin',
      label: 'Admin',
      description: 'Manage the support platform',
      icon: Shield,
    },
  ]

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-100">Create your account</h1>
        <p className="text-sm text-slate-500 mt-1">Join SupportPilot AI and get started</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {apiError && (
          <div className="flex items-center gap-2 rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-400">
            <AlertCircle size={16} className="shrink-0" />
            {apiError}
          </div>
        )}

        <Input
          label="Full Name"
          type="text"
          placeholder="John Doe"
          autoComplete="name"
          error={errors.name?.message}
          {...register('name')}
        />

        <Input
          label="Email address"
          type="email"
          placeholder="you@example.com"
          autoComplete="email"
          error={errors.email?.message}
          {...register('email')}
        />

        <Input
          label="Password"
          type="password"
          placeholder="Min. 8 characters"
          autoComplete="new-password"
          error={errors.password?.message}
          helperText="Must be at least 8 characters"
          {...register('password')}
        />

        <Input
          label="Confirm Password"
          type="password"
          placeholder="Re-enter your password"
          autoComplete="new-password"
          error={errors.confirmPassword?.message}
          {...register('confirmPassword')}
        />

        {/* Role Selection */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-300">Account Type</label>
          <div className="grid grid-cols-2 gap-3">
            {roleOptions.map((opt) => {
              const Icon = opt.icon
              const isSelected = selectedRole === opt.value
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => handleRoleSelect(opt.value)}
                  className={cn(
                    'flex flex-col items-start gap-1 rounded-xl border p-3.5 text-left transition-all duration-150',
                    isSelected
                      ? opt.value === 'admin'
                        ? 'border-purple-500/40 bg-purple-500/10 ring-1 ring-purple-500/20'
                        : 'border-accent/40 bg-accent/10 ring-1 ring-accent/20'
                      : 'border-border bg-background hover:border-border-subtle hover:bg-background-elevated'
                  )}
                >
                  <Icon
                    size={18}
                    className={cn(
                      isSelected
                        ? opt.value === 'admin' ? 'text-purple-400' : 'text-accent'
                        : 'text-slate-500'
                    )}
                  />
                  <span className={cn(
                    'text-sm font-semibold',
                    isSelected ? 'text-slate-100' : 'text-slate-400'
                  )}>
                    {opt.label}
                  </span>
                  <span className="text-[10px] text-slate-600 leading-tight">{opt.description}</span>
                </button>
              )
            })}
          </div>
          {errors.role && (
            <p className="text-xs text-red-400">{errors.role.message}</p>
          )}
        </div>

        <Button
          type="submit"
          variant="primary"
          size="lg"
          fullWidth
          loading={isSubmitting}
          icon={UserPlus}
          className="mt-2"
        >
          {isSubmitting ? 'Creating account...' : 'Create Account'}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500">
        Already have an account?{' '}
        <Link href="/login" className="font-medium text-accent hover:text-accent-light transition-colors">
          Sign in
        </Link>
      </p>
    </div>
  )
}
