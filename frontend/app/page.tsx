import React from 'react'
import Link from 'next/link'
import {
  Zap,
  Bot,
  Ticket,
  BarChart3,
  Clock,
  Shield,
  ArrowRight,
  CheckCircle,
  MessageSquare,
  Users,
  Star,
  Github,
} from 'lucide-react'

const features = [
  {
    icon: Bot,
    title: 'AI-Powered Responses',
    description:
      'Leverage advanced AI to instantly respond to customer inquiries with context-aware, accurate answers around the clock.',
    color: 'indigo',
  },
  {
    icon: Ticket,
    title: 'Smart Ticket Management',
    description:
      'Automatically categorize, prioritize, and route support tickets to the right team. Never miss an important request.',
    color: 'purple',
  },
  {
    icon: BarChart3,
    title: 'Real-time Analytics',
    description:
      'Track resolution rates, response times, and customer satisfaction scores with comprehensive dashboards.',
    color: 'emerald',
  },
  {
    icon: Clock,
    title: '24/7 Availability',
    description:
      'Your AI support team never sleeps. Provide instant, consistent support across all channels at any hour.',
    color: 'amber',
  },
]

const stats = [
  { value: '< 2s', label: 'Avg. Response Time' },
  { value: '98%', label: 'Customer Satisfaction' },
  { value: '70%', label: 'Tickets Auto-Resolved' },
  { value: '24/7', label: 'Always Available' },
]

const benefits = [
  'Instant AI responses with 95%+ accuracy',
  'Automatic ticket creation and routing',
  'Multi-channel support (Web, Email, WhatsApp)',
  'Real-time admin dashboard and analytics',
  'Seamless human escalation when needed',
  'Enterprise-grade security and compliance',
]

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background overflow-hidden">
      {/* Background pattern */}
      <div className="fixed inset-0 dot-bg opacity-40 pointer-events-none" />

      {/* Gradient blobs */}
      <div className="fixed top-0 left-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="fixed top-1/4 right-1/4 w-80 h-80 bg-purple-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="fixed bottom-1/3 left-1/3 w-72 h-72 bg-indigo-500/8 rounded-full blur-3xl pointer-events-none" />

      {/* Navbar */}
      <nav className="relative z-10 border-b border-border/50 bg-background/60 backdrop-blur-xl sticky top-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-600 to-purple-600 shadow-lg shadow-indigo-500/25">
                <Zap size={16} className="text-white" />
              </div>
              <span className="text-base font-bold text-slate-100">
                SupportPilot <span className="text-accent">AI</span>
              </span>
            </div>

            {/* Nav links */}
            <div className="hidden md:flex items-center gap-6">
              <a href="#features" className="text-sm text-slate-400 hover:text-slate-200 transition-colors">
                Features
              </a>
              <a href="#stats" className="text-sm text-slate-400 hover:text-slate-200 transition-colors">
                Stats
              </a>
              <a href="#benefits" className="text-sm text-slate-400 hover:text-slate-200 transition-colors">
                Benefits
              </a>
            </div>

            {/* CTA */}
            <div className="flex items-center gap-3">
              <Link
                href="/login"
                className="text-sm font-medium text-slate-400 hover:text-slate-200 transition-colors hidden sm:block"
              >
                Sign In
              </Link>
              <Link
                href="/signup"
                className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 px-4 py-2 text-sm font-medium text-white hover:from-indigo-500 hover:to-purple-500 transition-all shadow-lg shadow-indigo-500/25"
              >
                Get Started
                <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative z-10 py-20 sm:py-32 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-4 py-1.5 text-xs font-medium text-indigo-400 mb-8">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-400" />
            </span>
            Powered by Advanced AI · Built for Scale
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-7xl font-extrabold tracking-tight text-slate-100 mb-6 leading-none">
            AI-Powered Support{' '}
            <span className="block gradient-text">
              That Never Sleeps
            </span>
          </h1>

          <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Transform your customer support with intelligent AI that understands context,
            resolves issues instantly, and escalates when human touch is needed —
            all in one beautiful platform.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/signup"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-8 py-4 text-base font-semibold text-white hover:from-indigo-500 hover:to-purple-500 transition-all shadow-xl shadow-indigo-500/30 active:scale-[0.98]"
            >
              Get Started Free
              <ArrowRight size={18} />
            </Link>
            <Link
              href="/dashboard"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-border bg-background-surface px-8 py-4 text-base font-semibold text-slate-300 hover:border-accent/40 hover:text-white transition-all active:scale-[0.98]"
            >
              <BarChart3 size={18} />
              View Dashboard
            </Link>
          </div>

          {/* Social proof */}
          <div className="mt-12 flex items-center justify-center gap-6 text-sm text-slate-600">
            <div className="flex items-center gap-1">
              {[...Array(5)].map((_, i) => (
                <Star key={i} size={12} className="fill-amber-400 text-amber-400" />
              ))}
              <span className="ml-1">5.0 rating</span>
            </div>
            <span className="text-border">|</span>
            <span>No credit card required</span>
            <span className="text-border">|</span>
            <span>Free forever plan</span>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section id="stats" className="relative z-10 py-12 px-4 sm:px-6 lg:px-8 border-y border-border/50 bg-background-surface/30">
        <div className="max-w-6xl mx-auto grid grid-cols-2 lg:grid-cols-4 gap-8">
          {stats.map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="text-3xl sm:text-4xl font-extrabold gradient-text mb-1">{stat.value}</div>
              <div className="text-sm text-slate-500">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="relative z-10 py-20 sm:py-28 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-100 mb-4">
              Everything you need to{' '}
              <span className="gradient-text">scale support</span>
            </h2>
            <p className="text-slate-400 text-lg max-w-2xl mx-auto">
              A complete AI support platform with all the tools your team needs to deliver exceptional customer experiences.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {features.map((feature) => {
              const Icon = feature.icon
              const colorMap: Record<string, string> = {
                indigo: 'from-indigo-600/20 to-indigo-600/5 border-indigo-500/20 text-indigo-400 bg-indigo-500/15',
                purple: 'from-purple-600/20 to-purple-600/5 border-purple-500/20 text-purple-400 bg-purple-500/15',
                emerald: 'from-emerald-600/20 to-emerald-600/5 border-emerald-500/20 text-emerald-400 bg-emerald-500/15',
                amber: 'from-amber-600/20 to-amber-600/5 border-amber-500/20 text-amber-400 bg-amber-500/15',
              }
              const [gradFrom, gradTo, borderCol, iconText, iconBg] = colorMap[feature.color].split(' ')

              return (
                <div
                  key={feature.title}
                  className={`relative rounded-2xl bg-gradient-to-br ${gradFrom} ${gradTo} border ${borderCol} p-6 hover:scale-[1.01] transition-transform duration-200`}
                >
                  <div className={`inline-flex rounded-xl ${iconBg} p-3 mb-4`}>
                    <Icon size={22} className={iconText} />
                  </div>
                  <h3 className="text-lg font-semibold text-slate-100 mb-2">{feature.title}</h3>
                  <p className="text-slate-400 text-sm leading-relaxed">{feature.description}</p>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* Benefits */}
      <section id="benefits" className="relative z-10 py-20 px-4 sm:px-6 lg:px-8 bg-background-surface/20">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl sm:text-4xl font-bold text-slate-100 mb-4">
                Built for modern{' '}
                <span className="gradient-text">support teams</span>
              </h2>
              <p className="text-slate-400 text-lg mb-8 leading-relaxed">
                SupportPilot AI combines the power of large language models with
                a seamless ticket management system to help your team deliver faster,
                better support.
              </p>
              <ul className="space-y-3">
                {benefits.map((benefit) => (
                  <li key={benefit} className="flex items-start gap-3 text-sm">
                    <CheckCircle size={18} className="text-emerald-400 shrink-0 mt-0.5" />
                    <span className="text-slate-300">{benefit}</span>
                  </li>
                ))}
              </ul>
              <div className="flex gap-4 mt-8">
                <Link
                  href="/signup"
                  className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-3 text-sm font-semibold text-white hover:from-indigo-500 hover:to-purple-500 transition-all shadow-lg shadow-indigo-500/25"
                >
                  Start Free Trial
                  <ArrowRight size={16} />
                </Link>
              </div>
            </div>

            {/* Mock dashboard preview */}
            <div className="relative">
              <div className="rounded-2xl border border-border bg-background-surface p-5 shadow-2xl shadow-black/50 glow-indigo">
                <div className="flex items-center gap-2 mb-4 pb-3 border-b border-border">
                  <div className="flex gap-1.5">
                    <div className="h-3 w-3 rounded-full bg-red-500/60" />
                    <div className="h-3 w-3 rounded-full bg-amber-500/60" />
                    <div className="h-3 w-3 rounded-full bg-emerald-500/60" />
                  </div>
                  <span className="text-xs text-slate-500 ml-2">SupportPilot Dashboard</span>
                </div>

                <div className="grid grid-cols-2 gap-3 mb-4">
                  {[
                    { label: 'Open Tickets', val: '24', color: 'text-blue-400' },
                    { label: 'Resolved Today', val: '47', color: 'text-emerald-400' },
                    { label: 'Avg. Response', val: '1.8s', color: 'text-indigo-400' },
                    { label: 'Active Chats', val: '12', color: 'text-purple-400' },
                  ].map((item) => (
                    <div key={item.label} className="rounded-lg bg-background border border-border p-3">
                      <div className={`text-xl font-bold ${item.color} tabular-nums`}>{item.val}</div>
                      <div className="text-[10px] text-slate-600 mt-0.5">{item.label}</div>
                    </div>
                  ))}
                </div>

                <div className="rounded-lg bg-background border border-border p-3 mb-3">
                  <div className="flex items-start gap-2">
                    <div className="h-6 w-6 rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center shrink-0">
                      <Bot size={12} className="text-white" />
                    </div>
                    <div className="flex-1">
                      <div className="text-xs font-medium text-slate-300 mb-1">AI Assistant</div>
                      <div className="text-xs text-slate-500 leading-relaxed">
                        I understand you&apos;re having trouble with billing. Let me help you resolve this immediately...
                      </div>
                      <div className="inline-flex mt-1.5 rounded-full bg-indigo-500/15 border border-indigo-500/20 px-2 py-0.5 text-[9px] font-medium text-indigo-400">
                        billing_inquiry · 96% confidence
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <div className="flex-1 h-7 rounded-lg bg-background border border-border" />
                  <div className="h-7 w-7 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 flex items-center justify-center">
                    <MessageSquare size={12} className="text-white" />
                  </div>
                </div>
              </div>

              {/* Floating badges */}
              <div className="absolute -top-3 -right-3 rounded-lg bg-emerald-500/20 border border-emerald-500/30 px-3 py-1.5 text-xs font-semibold text-emerald-400">
                Live
              </div>
              <div className="absolute -bottom-3 -left-3 rounded-lg bg-indigo-500/20 border border-indigo-500/30 px-3 py-1.5 text-xs font-semibold text-indigo-400 flex items-center gap-1.5">
                <Users size={11} />
                2.4k active users
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="relative z-10 py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto text-center">
          <div className="rounded-2xl border border-indigo-500/20 bg-gradient-to-br from-indigo-500/10 via-purple-500/5 to-background p-10 sm:p-14 relative overflow-hidden">
            <div className="absolute inset-0 dot-bg opacity-30" />
            <div className="relative z-10">
              <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-600 to-purple-600 shadow-xl shadow-indigo-500/30 mb-6">
                <Zap size={24} className="text-white" />
              </div>
              <h2 className="text-3xl sm:text-4xl font-bold text-slate-100 mb-4">
                Ready to transform your support?
              </h2>
              <p className="text-slate-400 mb-8 text-lg">
                Join thousands of teams delivering faster, smarter support with AI.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href="/signup"
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 px-8 py-4 text-base font-semibold text-white hover:from-indigo-500 hover:to-purple-500 transition-all shadow-xl shadow-indigo-500/25 active:scale-[0.98]"
                >
                  Get Started Free
                  <ArrowRight size={18} />
                </Link>
                <Link
                  href="/login"
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-border px-8 py-4 text-base font-semibold text-slate-300 hover:border-accent/40 hover:text-white transition-all"
                >
                  Sign In
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-border py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-gradient-to-br from-indigo-600 to-purple-600">
              <Zap size={12} className="text-white" />
            </div>
            <span className="text-sm font-semibold text-slate-400">SupportPilot AI</span>
          </div>
          <p className="text-xs text-slate-600">
            Built with Next.js, TypeScript, and Tailwind CSS
          </p>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-xs text-slate-600 hover:text-slate-400 transition-colors">
              Sign In
            </Link>
            <Link href="/signup" className="text-xs text-slate-600 hover:text-slate-400 transition-colors">
              Sign Up
            </Link>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-600 hover:text-slate-400 transition-colors"
            >
              <Github size={14} />
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}
