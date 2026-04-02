'use client'

import React, { useEffect, useState } from 'react'
import {
  CreditCard,
  Zap,
  CheckCircle,
  AlertTriangle,
  XCircle,
  ArrowRight,
  RefreshCw,
  MessageSquare,
  Ticket,
  Shield,
  Cpu,
  Globe,
  Mail,
  BarChart3,
  Users,
  Clock,
  Info,
  X,
  Sparkles,
  History,
  ExternalLink,
} from 'lucide-react'
import { billingApi } from '../../../../lib/api'
import { BillingSummary, BillingPlan, UsageCounter, BillingEvent } from '../../../../types'
import { Card } from '../../../../components/ui/Card'
import { Button } from '../../../../components/ui/Button'
import { Badge } from '../../../../components/ui/Badge'
import { LoadingSpinner } from '../../../../components/ui/LoadingSpinner'
import { cn } from '../../../../lib/utils'
import { useToast } from '../../../../context/ToastContext'

// ── Usage progress bar ───────────────────────────────────────────────────────

function UsageBar({ counter, label, icon: Icon }: {
  counter: UsageCounter
  label: string
  icon: React.ElementType
}) {
  const barColor = counter.hard_blocked
    ? 'bg-red-500'
    : counter.soft_warning
    ? 'bg-amber-500'
    : 'bg-emerald-500'

  const textColor = counter.hard_blocked
    ? 'text-red-400'
    : counter.soft_warning
    ? 'text-amber-400'
    : 'text-emerald-400'

  const pct = counter.unlimited ? 0 : Math.min(counter.pct, 100)

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon size={14} className="text-slate-500" />
          <span className="text-sm font-medium text-slate-300">{label}</span>
          {counter.hard_blocked && (
            <span className="inline-flex items-center gap-1 rounded-full bg-red-500/15 border border-red-500/25 px-2 py-0.5 text-[10px] font-semibold text-red-400">
              <XCircle size={10} /> Limit reached
            </span>
          )}
          {counter.soft_warning && !counter.hard_blocked && (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 border border-amber-500/25 px-2 py-0.5 text-[10px] font-semibold text-amber-400">
              <AlertTriangle size={10} /> Near limit
            </span>
          )}
        </div>
        <span className={cn('text-sm font-semibold tabular-nums', textColor)}>
          {counter.unlimited
            ? <span className="text-slate-400">∞ Unlimited</span>
            : `${counter.used.toLocaleString()} / ${counter.limit.toLocaleString()}`}
        </span>
      </div>

      {!counter.unlimited && (
        <div className="h-2 w-full overflow-hidden rounded-full bg-background-elevated">
          <div
            className={cn('h-full rounded-full transition-all duration-500', barColor)}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}

      {!counter.unlimited && (
        <p className="text-[11px] text-slate-600">
          {counter.hard_blocked
            ? 'Monthly cap reached — upgrade to continue'
            : counter.soft_warning
            ? `${(counter.limit - counter.used).toLocaleString()} remaining this month`
            : `${pct.toFixed(0)}% used this month`}
        </p>
      )}
    </div>
  )
}

// ── Upgrade modal ────────────────────────────────────────────────────────────

const UPGRADE_BENEFITS: Record<string, string[]> = {
  pro: [
    '2,000 AI messages per month (10× Free)',
    '500 support tickets per month',
    'WhatsApp + Email channel support',
    'Full analytics dashboard',
    'Multi-agent routing (Billing / Technical / Account)',
    '30-minute SLA',
    'Priority support',
  ],
  team: [
    'Unlimited messages & tickets',
    'All Pro features included',
    'Dedicated agent slots',
    '15-minute SLA',
    'Custom integrations & API access',
    'Dedicated account manager',
  ],
}

function UpgradeModal({
  plan,
  onClose,
  onConfirm,
  loading,
}: {
  plan: BillingPlan
  onClose: () => void
  onConfirm: (tier: string) => void
  loading: boolean
}) {
  const benefits = UPGRADE_BENEFITS[plan.tier] ?? plan.features

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

      {/* Panel */}
      <div className="relative w-full max-w-lg rounded-2xl border border-border bg-background-surface shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between p-6 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-purple-600">
              <Sparkles size={18} className="text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-100">
                Upgrade to {plan.display_name}
              </h2>
              <p className="text-sm text-slate-500">
                Unlock higher limits and premium features
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-300 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Benefits */}
        <div className="px-6 pb-4 space-y-2.5">
          {benefits.map((b, i) => (
            <div key={i} className="flex items-start gap-2.5 text-sm text-slate-300">
              <CheckCircle size={15} className="shrink-0 mt-0.5 text-emerald-500" />
              <span>{b}</span>
            </div>
          ))}
        </div>

        {/* Dev note */}
        <div className="mx-6 mb-4 flex items-start gap-2.5 rounded-xl border border-amber-500/20 bg-amber-500/8 p-3">
          <Info size={14} className="shrink-0 mt-0.5 text-amber-400" />
          <p className="text-xs text-slate-400">
            <span className="font-semibold text-amber-300">Demo mode — </span>
            No payment required. This updates your plan tier directly in the DB.
            Stripe billing integration is the next phase.
          </p>
        </div>

        {/* Actions */}
        <div className="flex gap-3 px-6 pb-6">
          <button
            onClick={onClose}
            className="flex-1 rounded-xl border border-border py-2.5 text-sm font-medium text-slate-400 hover:text-slate-200 hover:border-slate-500 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(plan.tier)}
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 py-2.5 text-sm font-semibold text-white hover:from-indigo-500 hover:to-purple-500 disabled:opacity-60 disabled:cursor-not-allowed transition-all"
          >
            {loading ? (
              <RefreshCw size={14} className="animate-spin" />
            ) : (
              <ArrowRight size={14} />
            )}
            {loading ? 'Activating…' : `Activate ${plan.display_name}`}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Plan card ────────────────────────────────────────────────────────────────

const PLAN_STYLES: Record<string, {
  border: string
  bg: string
  badge: string
  badgeDot: string
  cta: string
  highlight: boolean
}> = {
  free: {
    border: 'border-border',
    bg: 'bg-background-surface',
    badge: 'bg-slate-700/50 text-slate-400 border-slate-700/50',
    badgeDot: 'bg-slate-500',
    cta: 'secondary',
    highlight: false,
  },
  pro: {
    border: 'border-accent/40',
    bg: 'bg-background-surface',
    badge: 'bg-accent/15 text-accent-light border-accent/25',
    badgeDot: 'bg-accent',
    cta: 'primary',
    highlight: true,
  },
  team: {
    border: 'border-purple-500/40',
    bg: 'bg-background-surface',
    badge: 'bg-purple-500/15 text-purple-300 border-purple-500/25',
    badgeDot: 'bg-purple-500',
    cta: 'secondary',
    highlight: false,
  },
}

function formatLimit(value: number): string {
  if (value === -1) return 'Unlimited'
  if (value >= 1000) return `${(value / 1000).toFixed(0)}k`
  return value.toString()
}

function PlanCard({
  plan,
  isCurrent,
  onUpgrade,
}: {
  plan: BillingPlan
  isCurrent: boolean
  onUpgrade?: (plan: BillingPlan) => void
}) {
  const style = PLAN_STYLES[plan.tier] ?? PLAN_STYLES.free

  return (
    <div className={cn(
      'relative flex flex-col rounded-2xl border p-6 transition-all duration-200',
      style.border,
      style.bg,
      style.highlight && 'shadow-lg shadow-accent/10',
      isCurrent && 'ring-1 ring-accent/30',
    )}>
      {/* Popular badge for Pro */}
      {style.highlight && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <span className="inline-flex items-center rounded-full bg-gradient-to-r from-indigo-600 to-purple-600 px-3 py-1 text-[11px] font-bold text-white shadow-lg">
            Most Popular
          </span>
        </div>
      )}

      {/* Plan header */}
      <div className="mb-5">
        <div className="flex items-center justify-between mb-3">
          <span className={cn(
            'inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold',
            style.badge,
          )}>
            <span className={cn('h-1.5 w-1.5 rounded-full', style.badgeDot)} />
            {plan.display_name}
          </span>
          {isCurrent && (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 border border-emerald-500/25 px-2.5 py-1 text-[11px] font-semibold text-emerald-400">
              <CheckCircle size={11} /> Current
            </span>
          )}
        </div>

        {/* Limits summary */}
        <div className="grid grid-cols-2 gap-3 mt-4">
          <div className="rounded-xl bg-background-elevated p-3">
            <div className="flex items-center gap-1.5 mb-1">
              <MessageSquare size={12} className="text-slate-500" />
              <span className="text-[10px] text-slate-500 uppercase tracking-wider">Messages</span>
            </div>
            <p className="text-lg font-bold text-slate-100">{formatLimit(plan.monthly_message_limit)}</p>
            <p className="text-[10px] text-slate-600">per month</p>
          </div>
          <div className="rounded-xl bg-background-elevated p-3">
            <div className="flex items-center gap-1.5 mb-1">
              <Ticket size={12} className="text-slate-500" />
              <span className="text-[10px] text-slate-500 uppercase tracking-wider">Tickets</span>
            </div>
            <p className="text-lg font-bold text-slate-100">{formatLimit(plan.monthly_ticket_limit)}</p>
            <p className="text-[10px] text-slate-600">per month</p>
          </div>
        </div>
      </div>

      {/* Feature list */}
      <ul className="flex-1 space-y-2.5 mb-6">
        {plan.features.map((feature, i) => (
          <li key={i} className="flex items-start gap-2.5 text-sm text-slate-400">
            <CheckCircle size={14} className="shrink-0 mt-0.5 text-emerald-500" />
            <span>{feature}</span>
          </li>
        ))}
        {/* Extra capability chips */}
        <li className="pt-1 flex flex-wrap gap-1.5">
          {plan.whatsapp_enabled && (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
              <Globe size={9} /> WhatsApp
            </span>
          )}
          {plan.email_enabled && (
            <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 text-[10px] font-medium text-blue-400">
              <Mail size={9} /> Email
            </span>
          )}
          {plan.analytics_enabled && (
            <span className="inline-flex items-center gap-1 rounded-full bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 text-[10px] font-medium text-purple-400">
              <BarChart3 size={9} /> Analytics
            </span>
          )}
          {plan.multi_agent_enabled && (
            <span className="inline-flex items-center gap-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 text-[10px] font-medium text-indigo-400">
              <Cpu size={9} /> Multi-agent
            </span>
          )}
          {plan.sla_minutes && (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 text-[10px] font-medium text-amber-400">
              <Clock size={9} /> {plan.sla_minutes}m SLA
            </span>
          )}
        </li>
      </ul>

      {/* CTA */}
      <div className="mt-auto">
        {isCurrent ? (
          <button
            disabled
            className="w-full rounded-xl bg-emerald-500/10 border border-emerald-500/20 py-2.5 text-sm font-semibold text-emerald-400 cursor-not-allowed"
          >
            Current Plan
          </button>
        ) : plan.tier === 'team' ? (
          <button className="w-full rounded-xl bg-purple-500/15 border border-purple-500/30 py-2.5 text-sm font-semibold text-purple-300 hover:bg-purple-500/25 transition-colors">
            Contact Sales
          </button>
        ) : (
          <button
            onClick={() => onUpgrade?.(plan)}
            className="w-full rounded-xl bg-accent/15 border border-accent/30 py-2.5 text-sm font-semibold text-accent-light hover:bg-accent/25 hover:border-accent/50 transition-colors flex items-center justify-center gap-2"
          >
            <ArrowRight size={14} />
            Upgrade to {plan.display_name}
          </button>
        )}
      </div>
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

// ── Subscription status badge ────────────────────────────────────────────────

const SUB_STATUS_CFG: Record<string, { label: string; cls: string; dot: string }> = {
  none:      { label: 'No subscription',   cls: 'border-slate-700/50 bg-slate-800/40 text-slate-500',   dot: 'bg-slate-600' },
  trial:     { label: 'Trial',             cls: 'border-amber-500/30 bg-amber-500/10  text-amber-300',  dot: 'bg-amber-400 animate-pulse' },
  active:    { label: 'Active',            cls: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300', dot: 'bg-emerald-400 animate-pulse' },
  past_due:  { label: 'Past due',          cls: 'border-red-500/30 bg-red-500/10 text-red-300',         dot: 'bg-red-400' },
  canceled:  { label: 'Canceled',          cls: 'border-slate-600/40 bg-slate-700/20 text-slate-500',   dot: 'bg-slate-600' },
}

function SubStatusBadge({ status }: { status: string }) {
  const cfg = SUB_STATUS_CFG[status] ?? SUB_STATUS_CFG.none
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${cfg.cls}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  )
}

// ── Event type display ────────────────────────────────────────────────────────

const EVENT_TYPE_CFG: Record<string, { label: string; cls: string }> = {
  plan_activated:         { label: 'Plan activated',         cls: 'text-emerald-400' },
  plan_changed:           { label: 'Plan changed',           cls: 'text-indigo-400' },
  trial_started:          { label: 'Trial started',          cls: 'text-amber-400' },
  checkout_requested:     { label: 'Checkout requested',     cls: 'text-sky-400' },
  subscription_activated: { label: 'Subscription activated', cls: 'text-emerald-400' },
  subscription_canceled:  { label: 'Subscription canceled',  cls: 'text-red-400' },
  payment_failed:         { label: 'Payment failed',         cls: 'text-red-400' },
}

function formatEventDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function BillingPage() {
  const [summary, setSummary] = useState<BillingSummary | null>(null)
  const [history, setHistory] = useState<BillingEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [upgradeTarget, setUpgradeTarget] = useState<BillingPlan | null>(null)
  const [upgrading, setUpgrading] = useState(false)
  const [checkoutLoading, setCheckoutLoading] = useState(false)
  const toast = useToast()

  const fetchData = async (isRefresh = false) => {
    setLoading(true)
    setError(null)
    try {
      const [data, hist] = await Promise.all([
        billingApi.getSummary(),
        billingApi.getHistory().catch(() => ({ events: [], total: 0 })),
      ])
      setSummary(data)
      setHistory(hist.events)
      if (isRefresh) toast.success('Billing data refreshed')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load billing data'
      setError(msg)
      if (isRefresh) toast.error('Failed to refresh billing data')
    } finally {
      setLoading(false)
    }
  }

  const handleCheckoutRequest = async (tier: string) => {
    setCheckoutLoading(true)
    try {
      const res = await billingApi.startCheckout(tier)
      toast.info(res.message)
      // Refresh history so the checkout_requested event appears
      billingApi.getHistory().then((h) => setHistory(h.events)).catch(() => {})
    } catch {
      toast.error('Checkout request failed.')
    } finally {
      setCheckoutLoading(false)
    }
  }

  const handleUpgradeConfirm = async (tier: string) => {
    console.log('checkout_clicked', tier)
    setUpgrading(true)
    try {
      // Record checkout intent + surface "Stripe coming soon" message
      const checkoutRes = await billingApi.startCheckout(tier).catch(() => null)
      if (checkoutRes) toast.info(checkoutRes.message)
      // Demo: directly update plan tier in DB (no payment required)
      await billingApi.updatePlan(tier)
      toast.success(`Plan activated: ${tier.charAt(0).toUpperCase() + tier.slice(1)} (demo mode)`)
      setUpgradeTarget(null)
      await fetchData()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upgrade failed'
      toast.error(msg)
    } finally {
      setUpgrading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  if (loading) return <LoadingSpinner center size="lg" label="Loading billing data..." />

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 min-h-[300px]">
        <p className="text-red-400 text-sm">{error}</p>
        <Button variant="outline" icon={RefreshCw} onClick={() => fetchData()}>
          Retry
        </Button>
      </div>
    )
  }

  if (!summary) return null

  const { current_plan, current_plan_display, current_plan_detail, usage, available_plans, monetization_status, subscription } = summary
  const hasWarning = usage.messages.soft_warning || usage.tickets.soft_warning
  const hasBlock   = usage.messages.hard_blocked  || usage.tickets.hard_blocked

  return (
    <div className="space-y-8 max-w-6xl">

      {/* ── Upgrade modal (portal-less, rendered at top of tree) ── */}
      {upgradeTarget && (
        <UpgradeModal
          plan={upgradeTarget}
          onClose={() => setUpgradeTarget(null)}
          onConfirm={handleUpgradeConfirm}
          loading={upgrading}
        />
      )}

      {/* ── Page header ── */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Plans &amp; Billing</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Platform usage, plan limits, and monetization readiness
          </p>
        </div>
        <Button variant="outline" size="sm" icon={RefreshCw} onClick={() => fetchData(true)}>
          Refresh
        </Button>
      </div>

      {/* ── Alert banners ── */}
      {hasBlock && (
        <div className="flex items-start gap-4 rounded-xl border border-red-500/25 bg-red-500/10 px-5 py-4">
          <XCircle size={18} className="shrink-0 mt-0.5 text-red-400" />
          <div>
            <p className="text-sm font-semibold text-red-300">Monthly limit reached</p>
            <p className="text-xs text-slate-400 mt-0.5">
              One or more resources have hit their monthly cap. Upgrade to Pro or Team to continue.
            </p>
          </div>
        </div>
      )}

      {hasWarning && !hasBlock && (
        <div className="flex items-start gap-4 rounded-xl border border-amber-500/25 bg-amber-500/10 px-5 py-4">
          <AlertTriangle size={18} className="shrink-0 mt-0.5 text-amber-400" />
          <div>
            <p className="text-sm font-semibold text-amber-300">Approaching monthly limit</p>
            <p className="text-xs text-slate-400 mt-0.5">
              Usage is above 80% on one or more resources. Consider upgrading before the cap is reached.
            </p>
          </div>
        </div>
      )}

      {/* ── Current plan + usage — 2 col ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Current Plan */}
        <Card title="Current Plan" description="Your active plan and entitlements">
          <div className="space-y-5">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-purple-600 shadow-lg shadow-indigo-500/25">
                <CreditCard size={22} className="text-white" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xl font-bold text-slate-100">{current_plan_display}</span>
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 border border-emerald-500/25 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-400">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    Active
                  </span>
                </div>
                <p className="text-sm text-slate-500 mt-0.5">
                  {current_plan_detail.monthly_message_limit === -1
                    ? 'Unlimited messages & tickets'
                    : `${current_plan_detail.monthly_message_limit.toLocaleString()} messages / ${current_plan_detail.monthly_ticket_limit.toLocaleString()} tickets per month`}
                </p>
              </div>
            </div>

            {/* Capabilities row */}
            <div className="flex flex-wrap gap-2">
              {current_plan_detail.whatsapp_enabled && (
                <span className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 text-xs font-medium text-emerald-400">
                  <Globe size={11} /> WhatsApp
                </span>
              )}
              {current_plan_detail.email_enabled && (
                <span className="inline-flex items-center gap-1.5 rounded-lg bg-blue-500/10 border border-blue-500/20 px-2.5 py-1 text-xs font-medium text-blue-400">
                  <Mail size={11} /> Email
                </span>
              )}
              {current_plan_detail.analytics_enabled && (
                <span className="inline-flex items-center gap-1.5 rounded-lg bg-purple-500/10 border border-purple-500/20 px-2.5 py-1 text-xs font-medium text-purple-400">
                  <BarChart3 size={11} /> Analytics
                </span>
              )}
              {current_plan_detail.multi_agent_enabled && (
                <span className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-1 text-xs font-medium text-indigo-400">
                  <Cpu size={11} /> Multi-agent
                </span>
              )}
              {!current_plan_detail.whatsapp_enabled && !current_plan_detail.email_enabled && (
                <span className="inline-flex items-center gap-1.5 rounded-lg bg-slate-500/10 border border-slate-700/40 px-2.5 py-1 text-xs font-medium text-slate-400">
                  <Globe size={11} /> Web only
                </span>
              )}
              <span className="inline-flex items-center gap-1.5 rounded-lg bg-slate-500/10 border border-slate-700/40 px-2.5 py-1 text-xs font-medium text-slate-400">
                <Users size={11} /> {current_plan_detail.max_agents} agent{current_plan_detail.max_agents !== 1 ? 's' : ''}
              </span>
              {current_plan_detail.sla_minutes && (
                <span className="inline-flex items-center gap-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 text-xs font-medium text-amber-400">
                  <Clock size={11} /> {current_plan_detail.sla_minutes}m SLA
                </span>
              )}
            </div>

            {/* Features list */}
            <div className="rounded-xl border border-border/60 bg-background-elevated p-4 space-y-2">
              {current_plan_detail.features.map((f, i) => (
                <div key={i} className="flex items-center gap-2.5 text-sm text-slate-400">
                  <CheckCircle size={13} className="shrink-0 text-emerald-500" />
                  {f}
                </div>
              ))}
            </div>
          </div>
        </Card>

        {/* Usage Overview */}
        <Card title="Usage This Month" description="Real-time resource consumption against plan limits">
          <div className="space-y-6">
            <UsageBar counter={usage.messages} label="AI Messages" icon={MessageSquare} />
            <UsageBar counter={usage.tickets} label="Support Tickets" icon={Ticket} />

            <div className="rounded-xl border border-border/60 bg-background-elevated p-4 space-y-2">
              <div className="flex items-center gap-2 mb-3">
                <Shield size={13} className="text-slate-500" />
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Limit Policy</span>
              </div>
              <div className="flex items-center gap-2.5 text-xs text-slate-500">
                <span className="h-2 w-2 rounded-full bg-emerald-500 shrink-0" />
                Under 80% — all systems normal
              </div>
              <div className="flex items-center gap-2.5 text-xs text-slate-500">
                <span className="h-2 w-2 rounded-full bg-amber-500 shrink-0" />
                80–99% — soft warning shown
              </div>
              <div className="flex items-center gap-2.5 text-xs text-slate-500">
                <span className="h-2 w-2 rounded-full bg-red-500 shrink-0" />
                100% — hard block, upgrade required
              </div>
            </div>

            <div className="flex items-center gap-2 text-xs text-slate-600 pt-1">
              <Info size={12} />
              <span>Usage resets monthly. In-memory meter — persists until server restart.</span>
            </div>
          </div>
        </Card>
      </div>

      {/* ── Subscription Status ── */}
      <Card title="Subscription Status" description="Stripe lifecycle state for this account">
        <div className="flex flex-wrap items-center gap-6">
          <div className="flex items-center gap-3">
            <SubStatusBadge status={subscription.status} />
          </div>
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <span className="text-slate-600">Plan:</span>
            <span className="font-medium text-slate-300">{current_plan_display}</span>
          </div>
          {subscription.current_period_end ? (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <Clock size={13} className="text-slate-600" />
              <span className="text-slate-600">Period ends:</span>
              <span className="font-medium text-slate-300">
                {new Date(subscription.current_period_end).toLocaleDateString('en-GB', {
                  day: '2-digit', month: 'short', year: 'numeric',
                })}
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Clock size={13} className="text-slate-600" />
              <span>No active billing period — Stripe not yet connected</span>
            </div>
          )}
        </div>
      </Card>

      {/* ── Plan comparison ── */}
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Available Plans</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Compare plans and upgrade when ready. Stripe billing integration is the next phase.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-3">
          {available_plans.map((plan) => (
            <PlanCard
              key={plan.tier}
              plan={plan}
              isCurrent={plan.tier === current_plan}
              onUpgrade={setUpgradeTarget}
            />
          ))}
        </div>
      </div>

      {/* ── Monetization readiness note ── */}
      <div className="rounded-2xl border border-border bg-background-surface p-6">
        <div className="flex items-start gap-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600/30 to-purple-600/30 border border-indigo-500/20">
            <Zap size={18} className="text-indigo-400" />
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-slate-200 mb-3">
              Phase 6 — SaaS Monetization Readiness
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {/* Live */}
              <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3">
                <div className="flex items-center gap-2 mb-1.5">
                  <CheckCircle size={13} className="text-emerald-400" />
                  <span className="text-xs font-semibold text-emerald-400">Live</span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Plan definitions (Free / Pro / Team), monthly limits, soft-warning at 80%, hard-block at 100%, usage metering per user
                </p>
              </div>
              {/* Also live */}
              <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3">
                <div className="flex items-center gap-2 mb-1.5">
                  <CheckCircle size={13} className="text-emerald-400" />
                  <span className="text-xs font-semibold text-emerald-400">Live</span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Multi-agent routing — BillingAgent, TechnicalAgent, AccountAgent wired into live pipeline
                </p>
              </div>
              {/* Roadmap */}
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3">
                <div className="flex items-center gap-2 mb-1.5">
                  <AlertTriangle size={13} className="text-amber-400" />
                  <span className="text-xs font-semibold text-amber-400">Next Phase</span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Stripe checkout, subscription lifecycle, plan upgrades, webhook entitlement, DB-backed usage persistence
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Billing History ── */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <History size={16} className="text-slate-500" />
          <h2 className="text-lg font-semibold text-slate-100">Billing History</h2>
        </div>

        {history.length === 0 ? (
          <div className="rounded-xl border border-border bg-background-surface px-6 py-8 text-center">
            <p className="text-sm text-slate-500">No billing events yet.</p>
            <p className="text-xs text-slate-600 mt-1">Events are recorded when you change plans or request checkout.</p>
          </div>
        ) : (
          <div className="rounded-xl border border-border bg-background-surface divide-y divide-border">
            {history.slice(0, 10).map((evt) => {
              const cfg = EVENT_TYPE_CFG[evt.event_type] ?? { label: evt.event_type, cls: 'text-slate-400' }
              return (
                <div key={evt.id} className="flex items-center justify-between px-4 py-3 gap-4">
                  <span className={`text-sm font-medium ${cfg.cls}`}>{cfg.label}</span>
                  {(evt.new_tier || evt.old_tier) && (
                    <span className="text-xs text-slate-500">
                      {evt.old_tier ?? '—'}{' → '}<span className="text-slate-300">{evt.new_tier ?? '—'}</span>
                    </span>
                  )}
                  <span className="ml-auto shrink-0 text-xs text-slate-600 tabular-nums">
                    {formatEventDate(evt.created_at)}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>

    </div>
  )
}
