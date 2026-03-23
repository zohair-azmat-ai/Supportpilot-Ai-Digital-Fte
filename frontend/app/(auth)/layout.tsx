import React from 'react'
import Link from 'next/link'
import { Zap } from 'lucide-react'

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center px-4 py-12 relative overflow-hidden">
      {/* Background blobs */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-indigo-600/8 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-purple-600/8 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-500/4 rounded-full blur-3xl pointer-events-none" />

      {/* Dot pattern */}
      <div className="absolute inset-0 dot-bg opacity-30 pointer-events-none" />

      {/* Logo */}
      <Link href="/" className="relative z-10 flex items-center gap-2.5 mb-8 group">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-purple-600 shadow-xl shadow-indigo-500/30 group-hover:shadow-indigo-500/50 transition-shadow">
          <Zap size={20} className="text-white" />
        </div>
        <div>
          <span className="text-xl font-bold text-slate-100 block leading-tight">SupportPilot</span>
          <span className="text-xs text-slate-500 leading-tight">AI Platform</span>
        </div>
      </Link>

      {/* Card */}
      <div className="relative z-10 w-full max-w-md rounded-2xl border border-border bg-background-surface shadow-2xl shadow-black/40">
        {children}
      </div>

      <p className="relative z-10 mt-8 text-xs text-slate-600 text-center">
        By continuing, you agree to our{' '}
        <span className="text-slate-500 hover:text-slate-400 cursor-pointer">Terms of Service</span>
        {' '}and{' '}
        <span className="text-slate-500 hover:text-slate-400 cursor-pointer">Privacy Policy</span>
      </p>
    </div>
  )
}
