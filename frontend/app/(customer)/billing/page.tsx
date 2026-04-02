'use client'

import React, { useEffect, useState } from 'react'
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  CheckCircle,
  Clock,
  CreditCard,
  Cpu,
  Globe,
  History,
  Info,
  Mail,
  MessageSquare,
  RefreshCw,
  Ticket,
  Users,
  XCircle,
  Zap,
} from 'lucide-react'
import { customerBillingApi } from '../../../lib/api'
import { BillingSummary, BillingPlan, BillingEvent } from '../../../types'
import { Card } from '../../../components/ui/Card'
import { Button } from '../../../components/ui/Button'
import { LoadingSpinner } from '../../../components/ui/LoadingSpinner'
import { cn } from '../../../lib/utils'
import { useToast } from '../../../context/ToastContext'

// ── Subscription status badge ─────────────────────────────────────────────────

const SUB_STATUS_CFG: Record<string, { label: string; cls: string; dot: string }> = {
  none:     { label: 'No subscription',  cls: 'border-slate-700/50 bg-slate-800/40 text-slate-500',      dot: 'bg-slate-600' },
  trial:    { label: 'Trial',            cls: 'border-amber-500/30 bg-amber-500/10 text-amber-300',      dot: 'bg-amber-400 animate-pulse' },
  active:   { label: 'Active',           cls: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300', dot: 'bg-emerald-400 animate-pulse' },
  past_due: { label: 'Past due',         cls: 'border-red-500/30 bg-red-500/10 text-red-300',            dot: 'bg-red-400' },
  canceled: { label: 'Canceled',         cls: 'border-slate-600/40 bg-slate-700/20 text-slate-500',      dot: 'bg-slate-600' },
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

// ── Usage bar ────────────────────────────────────────────────────────────────

function UsageBar({ used, limit, unlimited, pct, softWarning, hardBlocked, label, icon: Icon }: {
  used: number; limit: number; unlimited: boolean; pct: number
  softWarning: boolean; hardBlocked: boolean; label: string; icon: React.ElementType
}) {
  const barColor   = hardBlocked ? 'bg-red-500' : softWarning ? 'bg-amber-500' : 'bg-emerald-500'
  const textColor  = hardBlocked ? 'text-red-400' : softWarning ? 'text-amber-400' : 'text-emerald-400'
  const clampedPct = unlimited ? 0 : Math.min(pct, 100)

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon size={14} className="text-slate-500" />
          <span className="text-sm font-medium text-slate-300">{label}</span>
          {hardBlocked && (
            <span className="inline-flex items-center gap-1 rounded-full border border-red-500/25 bg-red-500/15 px-2 py-0.5 text-[10px] font-semibold text-red-400">
              <XCircle size={10} /> Limit reached
            </span>
          )}
          {softWarning && !hardBlocked && (
            <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/25 bg-amber-500/15 px-2 py-0.5 text-[10px] font-semibold text-amber-400">
              <AlertTriangle size={10} /> Near limit
            </span>
          )}
        </div>
        <span className={cn('text-sm font-semibold tabular-nums', textColor)}>
          {unlimited
            ? <span className="text-slate-400">∞ Unlimited</span>
            : `${used.toLocaleString()} / ${limit.toLocaleString()}`}
        </span>
      </div>
      {!unlimited && (
        <div className="h-2 w-full overflow-hidden rounded-full bg-background-elevated">
          <div className={cn('h-full rounded-full transition-all duration-500', barColor)} style={{ width: `${clampedPct}%` }} />
        </div>
      )}
      {!unlimited && (
        <p className="text-[11px] text-slate-600">
          {hardBlocked
            ? 'Monthly cap reached — upgrade to continue'
            : softWarning
            ? `${(limit - used).toLocaleString()} remaining this month`
            : `${clampedPct.toFixed(0)}% used this month`}
        </p>
      )}
    </div>
  )
}

// ── Plan card ────────────────────────────────────────────────────────────────

const PLAN_STYLES: Record<string, { border: string; badge: string; badgeDot: string; highlight: boolean }> = {
  free:  { border: 'border-border',        badge: 'bg-slate-700/50 text-slate-400 border-slate-700/50',       badgeDot: 'bg-slate-500',  highlight: false },
  pro:   { border: 'border-accent/40',     badge: 'bg-accent/15 text-accent-light border-accent/25',          badgeDot: 'bg-accent',     highlight: true  },
  team:  { border: 'border-purple-500/40', badge: 'bg-purple-500/15 text-purple-300 border-purple-500/25',    badgeDot: 'bg-purple-500', highlight: false },
}

function PlanCard({ plan, isCurrent, onUpgrade, upgrading }: {
  plan: BillingPlan; isCurrent: boolean
  onUpgrade: (tier: string) => void; upgrading: boolean
}) {
  const style = PLAN_STYLES[plan.tier] ?? PLAN_STYLES.free

  return (
    <div className={cn(
      'relative flex flex-col rounded-2xl border p-6 bg-background-surface transition-all duration-200',
      style.border,
      style.highlight && 'shadow-lg shadow-accent/10',
      isCurrent && 'ring-1 ring-accent/30',
    )}>
      {style.highlight && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <span className="inline-flex items-center rounded-full bg-gradient-to-r from-indigo-600 to-purple-600 px-3 py-1 text-[11px] font-bold text-white shadow-lg">
            Most Popular
          </span>
        </div>
      )}

      <div className="mb-4">
        <div className="flex items-center justify-between mb-3">
          <span className={cn('inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold', style.badge)}>
            <span className={cn('h-1.5 w-1.5 rounded-full', style.badgeDot)} />
            {plan.display_name}
          </span>
          {isCurrent && (
            <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/25 bg-emerald-500/15 px-2.5 py-1 text-[11px] font-semibold text-emerald-400">
              <CheckCircle size={11} /> Current
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 gap-2 mt-3">
          <div className="rounded-xl bg-background-elevated p-3">
            <div className="flex items-center gap-1.5 mb-1">
              <MessageSquare size={11} className="text-slate-500" />
              <span className="text-[10px] text-slate-500 uppercase tracking-wider">Messages</span>
            </div>
            <p className="text-base font-bold text-slate-100">
              {plan.monthly_message_limit === -1 ? '∞' : plan.monthly_message_limit.toLocaleString()}
            </p>
          </div>
          <div className="rounded-xl bg-background-elevated p-3">
            <div className="flex items-center gap-1.5 mb-1">
              <Ticket size={11} className="text-slate-500" />
              <span className="text-[10px] text-slate-500 uppercase tracking-wider">Tickets</span>
            </div>
            <p className="text-base font-bold text-slate-100">
              {plan.monthly_ticket_limit === -1 ? '∞' : plan.monthly_ticket_limit.toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      <ul className="flex-1 space-y-2 mb-5">
        {plan.features.map((f, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-slate-400">
            <CheckCircle size={13} className="shrink-0 mt-0.5 text-emerald-500" />
            {f}
          </li>
        ))}
        <li className="pt-1 flex flex-wrap gap-1.5">
          {plan.whatsapp_enabled && <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-400"><Globe size={9} /> WhatsApp</span>}
          {plan.email_enabled    && <span className="inline-flex items-center gap-1 rounded-full border border-blue-500/20 bg-blue-500/10 px-2 py-0.5 text-[10px] font-medium text-blue-400"><Mail size={9} /> Email</span>}
          {plan.analytics_enabled && <span className="inline-flex items-center gap-1 rounded-full border border-purple-500/20 bg-purple-500/10 px-2 py-0.5 text-[10px] font-medium text-purple-400"><BarChart3 size={9} /> Analytics</span>}
          {plan.multi_agent_enabled && <span className="inline-flex items-center gap-1 rounded-full border border-indigo-500/20 bg-indigo-500/10 px-2 py-0.5 text-[10px] font-medium text-indigo-400"><Cpu size={9} /> Multi-agent</span>}
          {plan.sla_minutes && <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/20 bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-400"><Clock size={9} /> {plan.sla_minutes}m SLA</span>}
          <span className="inline-flex items-center gap-1 rounded-full border border-slate-700/40 bg-slate-500/10 px-2 py-0.5 text-[10px] font-medium text-slate-400"><Users size={9} /> {plan.max_agents} agent{plan.max_agents !== 1 ? 's' : ''}</span>
        </li>
      </ul>

      <div className="mt-auto">
        {isCurrent ? (
          <button disabled className="w-full rounded-xl border border-emerald-500/20 bg-emerald-500/10 py-2.5 text-sm font-semibold text-emerald-400 cursor-not-allowed">
            Current Plan
          </button>
        ) : plan.tier === 'team' ? (
          <button
            onClick={() => onUpgrade(plan.tier)}
            disabled={upgrading}
            className="w-full rounded-xl border border-purple-500/30 bg-purple-500/15 py-2.5 text-sm font-semibold text-purple-300 hover:bg-purple-500/25 transition-colors disabled:opacity-50"
          >
            Contact Sales
          </button>
        ) : (
          <button
            onClick={() => onUpgrade(plan.tier)}
            disabled={upgrading}
            className="w-full flex items-center justify-center gap-2 rounded-xl border border-accent/30 bg-accent/15 py-2.5 text-sm font-semibold text-accent-light hover:bg-accent/25 hover:border-accent/50 transition-colors disabled:opacity-50"
          >
            {upgrading ? <RefreshCw size={13} className="animate-spin" /> : <ArrowRight size={13} />}
            {upgrading ? 'Requesting…' : `Upgrade to ${plan.display_name}`}
          </button>
        )}
      </div>
    </div>
  )
}

// ── Billing event helpers ─────────────────────────────────────────────────────

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
  return new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function CustomerBillingPage() {
  const [summary, setSummary]   = useState<BillingSummary | null>(null)
  const [events, setEvents]     = useState<BillingEvent[]>([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState<string | null>(null)
  const [upgrading, setUpgrading] = useState(false)
  const toast = useToast()

  const fetchData = async (isRefresh = false) => {
    setLoading(true)
    setError(null)
    try {
      const [data, evts] = await Promise.all([
        customerBillingApi.getSummary(),
        customerBillingApi.getEvents().catch(() => ({ events: [], total: 0 })),
      ])
      setSummary(data)
      setEvents(evts.events)
      if (isRefresh) toast.success('Billing data refreshed')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load billing data'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const handleUpgrade = async (tier: string) => {
    setUpgrading(true)
    try {
      const res = await customerBillingApi.startCheckout(tier)
      if (res.checkout_url) {
        window.location.href = res.checkout_url
      } else {
        // Stripe not configured — stub/demo mode
        toast.info(res.message)
        customerBillingApi.getEvents().then((e) => setEvents(e.events)).catch(() => {})
        setUpgrading(false)
      }
    } catch {
      toast.error('Request failed. Please try again.')
      setUpgrading(false)
    }
    // Note: don't clear upgrading on success path — page is redirecting
  }

  useEffect(() => { fetchData() }, [])

  // Detect Stripe redirect-back query params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('checkout') === 'success') {
      toast.success('Payment successful! Your subscription is being activated.')
      fetchData()
      window.history.replaceState({}, '', window.location.pathname)
    } else if (params.get('checkout') === 'cancel') {
      toast.info('Checkout cancelled. No changes were made.')
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [])

  if (loading) return <LoadingSpinner center size="lg" label="Loading subscription..." />

  if (error) return (
    <div className="flex flex-col items-center justify-center gap-4 min-h-[300px]">
      <p className="text-sm text-red-400">{error}</p>
      <Button variant="outline" icon={RefreshCw} onClick={() => fetchData()}>Retry</Button>
    </div>
  )

  if (!summary) return null

  const { current_plan, current_plan_display, current_plan_detail, usage, available_plans, subscription } = summary
  const hasWarning = usage.messages.soft_warning || usage.tickets.soft_warning
  const hasBlock   = usage.messages.hard_blocked  || usage.tickets.hard_blocked

  return (
    <div className="space-y-8 max-w-5xl">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Subscription</h1>
          <p className="text-sm text-slate-500 mt-0.5">Your plan, usage, and billing history</p>
        </div>
        <Button variant="outline" size="sm" icon={RefreshCw} onClick={() => fetchData(true)}>
          Refresh
        </Button>
      </div>

      {/* Alert banners */}
      {hasBlock && (
        <div className="flex items-start gap-4 rounded-xl border border-red-500/25 bg-red-500/10 px-5 py-4">
          <XCircle size={18} className="shrink-0 mt-0.5 text-red-400" />
          <div>
            <p className="text-sm font-semibold text-red-300">Monthly limit reached</p>
            <p className="text-xs text-slate-400 mt-0.5">Upgrade your plan to continue using the service this month.</p>
          </div>
        </div>
      )}

      {hasWarning && !hasBlock && (
        <div className="flex items-start gap-4 rounded-xl border border-amber-500/25 bg-amber-500/10 px-5 py-4">
          <AlertTriangle size={18} className="shrink-0 mt-0.5 text-amber-400" />
          <div>
            <p className="text-sm font-semibold text-amber-300">Approaching monthly limit</p>
            <p className="text-xs text-slate-400 mt-0.5">You're above 80% on one or more resources. Consider upgrading.</p>
          </div>
        </div>
      )}

      {/* Current plan + subscription status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        <Card title="Current Plan" description="Your active plan and entitlements">
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-purple-600 shadow-lg shadow-indigo-500/25">
                <CreditCard size={20} className="text-white" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xl font-bold text-slate-100">{current_plan_display}</span>
                  <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/25 bg-emerald-500/15 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-400">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" /> Active
                  </span>
                </div>
                <p className="text-sm text-slate-500 mt-0.5">
                  {current_plan_detail.monthly_message_limit === -1
                    ? 'Unlimited messages & tickets'
                    : `${current_plan_detail.monthly_message_limit.toLocaleString()} messages / ${current_plan_detail.monthly_ticket_limit.toLocaleString()} tickets per month`}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {current_plan_detail.whatsapp_enabled && <span className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-400"><Globe size={11} /> WhatsApp</span>}
              {current_plan_detail.email_enabled && <span className="inline-flex items-center gap-1.5 rounded-lg border border-blue-500/20 bg-blue-500/10 px-2.5 py-1 text-xs font-medium text-blue-400"><Mail size={11} /> Email</span>}
              {current_plan_detail.analytics_enabled && <span className="inline-flex items-center gap-1.5 rounded-lg border border-purple-500/20 bg-purple-500/10 px-2.5 py-1 text-xs font-medium text-purple-400"><BarChart3 size={11} /> Analytics</span>}
              {current_plan_detail.multi_agent_enabled && <span className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-500/20 bg-indigo-500/10 px-2.5 py-1 text-xs font-medium text-indigo-400"><Cpu size={11} /> Multi-agent</span>}
              {!current_plan_detail.whatsapp_enabled && !current_plan_detail.email_enabled && (
                <span className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700/40 bg-slate-500/10 px-2.5 py-1 text-xs font-medium text-slate-400"><Globe size={11} /> Web only</span>
              )}
            </div>
          </div>
        </Card>

        <Card title="Subscription Status" description="Stripe lifecycle state for your account">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <SubStatusBadge status={subscription.status} />
            </div>
            {subscription.current_period_end ? (
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <Clock size={13} className="text-slate-600" />
                <span className="text-slate-600">Period ends:</span>
                <span className="font-medium text-slate-300">
                  {new Date(subscription.current_period_end).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
                </span>
              </div>
            ) : (
              <p className="text-sm text-slate-500">No active billing period — Stripe not yet connected.</p>
            )}
            <div className="flex items-start gap-2.5 rounded-xl border border-amber-500/20 bg-amber-500/8 p-3">
              <Info size={13} className="shrink-0 mt-0.5 text-amber-400" />
              <p className="text-xs text-slate-400">
                <span className="font-semibold text-amber-300">Coming soon — </span>
                Live Stripe checkout, subscription management, and invoices will be available in the next phase.
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Usage */}
      <Card title="Usage This Month" description="Your message and ticket consumption against plan limits">
        <div className="space-y-6">
          <UsageBar
            label="AI Messages" icon={MessageSquare}
            used={usage.messages.used} limit={usage.messages.limit}
            unlimited={usage.messages.unlimited} pct={usage.messages.pct}
            softWarning={usage.messages.soft_warning} hardBlocked={usage.messages.hard_blocked}
          />
          <UsageBar
            label="Support Tickets" icon={Ticket}
            used={usage.tickets.used} limit={usage.tickets.limit}
            unlimited={usage.tickets.unlimited} pct={usage.tickets.pct}
            softWarning={usage.tickets.soft_warning} hardBlocked={usage.tickets.hard_blocked}
          />
          <div className="flex items-center gap-2 text-xs text-slate-600 pt-1">
            <Info size={11} />
            <span>Usage resets monthly.</span>
          </div>
        </div>
      </Card>

      {/* Available plans */}
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Available Plans</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Upgrade when ready. Clicking upgrade records your interest — Stripe checkout is the next phase.
          </p>
        </div>

        <div className="rounded-xl border border-amber-500/20 bg-amber-500/8 px-4 py-3 flex items-center gap-3">
          <Zap size={14} className="shrink-0 text-amber-400" />
          <p className="text-xs text-slate-400">
            <span className="font-semibold text-amber-300">Demo mode — </span>
            No payment required during this phase. Upgrade buttons record your interest and will trigger real Stripe checkout once live.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
          {available_plans.map((plan) => (
            <PlanCard
              key={plan.tier}
              plan={plan}
              isCurrent={plan.tier === current_plan}
              onUpgrade={handleUpgrade}
              upgrading={upgrading}
            />
          ))}
        </div>
      </div>

      {/* Billing history */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <History size={16} className="text-slate-500" />
          <h2 className="text-lg font-semibold text-slate-100">Billing History</h2>
        </div>

        {events.length === 0 ? (
          <div className="rounded-xl border border-border bg-background-surface px-6 py-8 text-center">
            <p className="text-sm text-slate-500">No billing events yet.</p>
            <p className="text-xs text-slate-600 mt-1">Events are recorded when you request a plan upgrade.</p>
          </div>
        ) : (
          <div className="rounded-xl border border-border bg-background-surface divide-y divide-border">
            {events.slice(0, 10).map((evt) => {
              const cfg = EVENT_TYPE_CFG[evt.event_type] ?? { label: evt.event_type, cls: 'text-slate-400' }
              return (
                <div key={evt.id} className="flex items-center justify-between gap-4 px-4 py-3">
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
