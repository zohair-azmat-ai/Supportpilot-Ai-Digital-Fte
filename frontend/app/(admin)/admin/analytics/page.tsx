'use client'

import React, { useEffect, useMemo, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Brain,
  Cpu,
  Frown,
  RefreshCw,
  Smile,
  Ticket,
  TimerReset,
  Zap,
} from 'lucide-react'
import { metricsApi } from '../../../../lib/api'
import { ChannelMetricsResponse, MetricsOverview, RoutedAgentCount } from '../../../../types'
import { StatsCard } from '../../../../components/dashboard/StatsCard'
import { Card } from '../../../../components/ui/Card'
import { Button } from '../../../../components/ui/Button'
import { ChannelBadge } from '../../../../components/ui/Badge'
import { LoadingSpinner } from '../../../../components/ui/LoadingSpinner'
import { formatMs, formatPercent } from '../../../../lib/utils'

function ChannelBars({
  channels,
  maxInteractions,
}: {
  channels: ChannelMetricsResponse['channels']
  maxInteractions: number
}) {
  return (
    <div className="space-y-4">
      {channels.map((channel) => (
        <div key={channel.channel} className="space-y-2">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <ChannelBadge channel={channel.channel} />
              <span className="text-xs text-slate-500">{channel.interaction_count} interactions</span>
            </div>
            <span className="text-xs text-slate-400">{formatPercent(channel.escalation_rate, 1)} escalated</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-background">
            <div
              className="h-full rounded-full bg-gradient-to-r from-sky-500 via-cyan-400 to-emerald-400"
              style={{ width: `${maxInteractions > 0 ? (channel.interaction_count / maxInteractions) * 100 : 0}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Specialist routing widget ────────────────────────────────────────────────

const AGENT_META: Record<string, { label: string; color: string; bar: string; dot: string }> = {
  billing:   { label: 'Billing',   color: 'text-indigo-300',  bar: 'bg-indigo-500',  dot: 'bg-indigo-400' },
  technical: { label: 'Technical', color: 'text-amber-300',   bar: 'bg-amber-500',   dot: 'bg-amber-400' },
  account:   { label: 'Account',   color: 'text-purple-300',  bar: 'bg-purple-500',  dot: 'bg-purple-400' },
  general:   { label: 'General',   color: 'text-slate-400',   bar: 'bg-slate-500',   dot: 'bg-slate-500' },
}

function agentMeta(agent: string) {
  return AGENT_META[agent] ?? { label: agent, color: 'text-slate-400', bar: 'bg-slate-600', dot: 'bg-slate-600' }
}

function SpecialistRoutingCard({ breakdown }: { breakdown: RoutedAgentCount[] }) {
  const total = breakdown.reduce((s, r) => s + r.count, 0)
  const top = breakdown[0]

  return (
    <Card
      title="Specialist Routing"
      description="Which Phase 6 agent handled each AI interaction"
    >
      {breakdown.length === 0 ? (
        <p className="text-sm text-slate-500">No specialist routing data recorded yet.</p>
      ) : (
        <div className="space-y-4">
          {/* Top agent highlight */}
          {top && (
            <div className="flex items-center gap-3 rounded-xl border border-border bg-background px-4 py-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-background-elevated border border-border">
                <Cpu size={15} className={agentMeta(top.agent).color} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-slate-500 uppercase tracking-wider">Top agent</p>
                <p className={`text-sm font-semibold capitalize ${agentMeta(top.agent).color}`}>
                  {agentMeta(top.agent).label}
                </p>
              </div>
              <div className="text-right shrink-0">
                <p className="text-sm font-semibold text-slate-100">{top.count}</p>
                <p className="text-xs text-slate-500">
                  {total > 0 ? `${Math.round((top.count / total) * 100)}%` : '—'}
                </p>
              </div>
            </div>
          )}

          {/* All agents */}
          <div className="space-y-3">
            {breakdown.map((r) => {
              const meta = agentMeta(r.agent)
              const pct = total > 0 ? (r.count / total) * 100 : 0
              return (
                <div key={r.agent} className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`h-2 w-2 rounded-full ${meta.dot}`} />
                      <span className={`text-xs font-medium capitalize ${meta.color}`}>
                        {meta.label}
                      </span>
                    </div>
                    <span className="text-xs text-slate-400 tabular-nums">
                      {r.count} · {Math.round(pct)}%
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-background">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${meta.bar}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </Card>
  )
}

export default function AdminAnalyticsPage() {
  const [overview, setOverview] = useState<MetricsOverview | null>(null)
  const [channelMetrics, setChannelMetrics] = useState<ChannelMetricsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchMetrics = async () => {
    setLoading(true)
    setError(null)
    try {
      const [overviewData, channelData] = await Promise.all([
        metricsApi.getOverview(),
        metricsApi.getChannels(),
      ])
      setOverview(overviewData)
      setChannelMetrics(channelData)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load metrics'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMetrics()
  }, [])

  const sortedChannels = useMemo(() => {
    return [...(channelMetrics?.channels || [])].sort((a, b) => b.interaction_count - a.interaction_count)
  }, [channelMetrics])

  const maxInteractions = sortedChannels[0]?.interaction_count || 0

  if (loading) return <LoadingSpinner center size="lg" label="Loading metrics..." />

  if (error || !overview || !channelMetrics) {
    return (
      <div className="flex flex-col items-center gap-4 py-20">
        <p className="text-sm text-red-400">{error || 'Metrics unavailable'}</p>
        <Button variant="outline" icon={RefreshCw} onClick={fetchMetrics}>
          Retry
        </Button>
      </div>
    )
  }

  return (
    <div className="max-w-7xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">AI Metrics</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Live portfolio view of interactions, channel mix, and escalation health
          </p>
        </div>
        <Button variant="outline" size="sm" icon={RefreshCw} onClick={fetchMetrics}>
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <StatsCard
          label="Total Interactions"
          value={overview.total_interactions}
          icon={Activity}
          color="blue"
        />
        <StatsCard
          label="Avg Confidence"
          value={formatPercent(overview.avg_confidence)}
          icon={Brain}
          color="emerald"
        />
        <StatsCard
          label="Escalation Rate"
          value={formatPercent(overview.escalation_rate, 1)}
          icon={AlertTriangle}
          color="red"
        />
        <StatsCard
          label="Ticket Creation"
          value={formatPercent(overview.ticket_creation_rate, 1)}
          icon={Ticket}
          color="purple"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.5fr_1fr]">
        <Card
          title="Channel Breakdown"
          description="Interaction volume and escalation mix across web, email, and WhatsApp"
        >
          {sortedChannels.length === 0 ? (
            <p className="text-sm text-slate-500">No channel metrics recorded yet.</p>
          ) : (
            <ChannelBars channels={sortedChannels} maxInteractions={maxInteractions} />
          )}
        </Card>

        <Card
          title="Escalation Snapshot"
          description="Quick read on how often the assistant is routing to humans"
        >
          <div className="space-y-4">
            <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-4">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-red-300">Escalations</p>
              <p className="mt-2 text-3xl font-bold text-slate-100">{overview.escalation_count}</p>
              <p className="mt-1 text-sm text-slate-400">
                {formatPercent(overview.escalation_rate, 1)} of all recorded AI interactions
              </p>
            </div>
            <div className="space-y-3 rounded-2xl border border-border bg-background px-4 py-4">
              {sortedChannels.map((channel) => (
                <div key={channel.channel} className="flex items-center justify-between gap-3">
                  <ChannelBadge channel={channel.channel} />
                  <div className="text-right">
                    <p className="text-sm font-semibold text-slate-100">{channel.escalation_count}</p>
                    <p className="text-xs text-slate-500">{formatPercent(channel.escalation_rate, 1)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card title="Performance Summary" description="AI responsiveness and workflow efficiency">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <TimerReset size={14} className="text-sky-400" />
                Avg response time
              </div>
              <span className="text-sm font-semibold text-slate-100">{formatMs(overview.avg_response_ms)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">Avg tools per run</span>
              <span className="text-sm font-semibold text-slate-100">{overview.avg_tools_per_run.toFixed(1)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">Avg iterations</span>
              <span className="text-sm font-semibold text-slate-100">{overview.avg_iterations.toFixed(1)}</span>
            </div>
            {overview.similar_issue_count > 0 && (
              <div className="flex items-center justify-between border-t border-border pt-4">
                <div className="flex items-center gap-2 text-sm text-slate-400">
                  <Zap size={14} className="text-amber-400" />
                  Similar issues detected
                </div>
                <span className="text-sm font-semibold text-amber-300">
                  {overview.similar_issue_count} ({formatPercent(overview.similar_issue_rate, 1)})
                </span>
              </div>
            )}
          </div>
        </Card>

        <Card title="Channel Detail" description="Confidence and response time by channel">
          <div className="space-y-4">
            {sortedChannels.length === 0 ? (
              <p className="text-sm text-slate-500">No channel data recorded yet.</p>
            ) : sortedChannels.map((channel) => (
              <div key={channel.channel} className="rounded-xl border border-border bg-background px-4 py-3">
                <div className="flex items-center justify-between gap-2">
                  <ChannelBadge channel={channel.channel} />
                  <span className="text-xs text-slate-500">{channel.interaction_count} runs</span>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Confidence</p>
                    <p className="mt-1 text-sm font-semibold text-slate-100">
                      {formatPercent(channel.avg_confidence)}
                    </p>
                  </div>
                  <div>
                    <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Response</p>
                    <p className="mt-1 text-sm font-semibold text-slate-100">{formatMs(channel.avg_response_ms)}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Top Intents" description="Most common AI-detected support themes">
          {overview.top_intents.length === 0 ? (
            <p className="text-sm text-slate-500">No intent data recorded yet.</p>
          ) : (
            <div className="space-y-3">
              {overview.top_intents.map((intent, index) => (
                <div key={intent.intent} className="flex items-center justify-between rounded-xl border border-border bg-background px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-7 w-7 items-center justify-center rounded-full bg-sky-500/15 text-xs font-semibold text-sky-300">
                      {index + 1}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-100">{intent.intent.replace(/_/g, ' ')}</p>
                      <p className="text-xs text-slate-500">Detected support intent</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-100">
                    <BarChart3 size={14} className="text-slate-500" />
                    {intent.count}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Specialist Routing */}
      {(overview.routing_breakdown?.length > 0) && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <SpecialistRoutingCard breakdown={overview.routing_breakdown} />
        </div>
      )}

      {/* Sentiment + Escalation Cause */}
      {(overview.sentiment_breakdown?.length > 0 || overview.escalation_cause_breakdown?.length > 0) && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {overview.sentiment_breakdown?.length > 0 && (
            <Card title="Sentiment Breakdown" description="Customer sentiment distribution across all AI interactions">
              <div className="space-y-3">
                {overview.sentiment_breakdown.map((s) => {
                  const isPositive = s.sentiment.toLowerCase() === 'positive'
                  const isNegative = ['negative', 'frustrated'].includes(s.sentiment.toLowerCase())
                  const Icon = isPositive ? Smile : isNegative ? Frown : Activity
                  const color = isPositive ? 'text-emerald-400' : isNegative ? 'text-red-400' : 'text-slate-400'
                  const bg = isPositive ? 'bg-emerald-500/10 border-emerald-500/20' : isNegative ? 'bg-red-500/10 border-red-500/20' : 'bg-background border-border'
                  const total = overview.sentiment_breakdown.reduce((sum, x) => sum + x.count, 0)
                  const pct = total > 0 ? Math.round((s.count / total) * 100) : 0
                  return (
                    <div key={s.sentiment} className={`flex items-center justify-between rounded-xl border px-4 py-3 ${bg}`}>
                      <div className="flex items-center gap-2">
                        <Icon size={14} className={color} />
                        <span className="text-sm font-medium text-slate-200 capitalize">{s.sentiment}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="h-1.5 w-20 overflow-hidden rounded-full bg-white/10">
                          <div className={`h-full rounded-full ${isPositive ? 'bg-emerald-400' : isNegative ? 'bg-red-400' : 'bg-slate-400'}`} style={{ width: `${pct}%` }} />
                        </div>
                        <span className="w-8 text-right text-sm font-semibold text-slate-100">{s.count}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </Card>
          )}

          {overview.escalation_cause_breakdown?.length > 0 && (
            <Card title="Escalation Causes" description="Why the AI escalated conversations to human agents">
              <div className="space-y-3">
                {overview.escalation_cause_breakdown.map((c) => (
                  <div key={c.cause} className="flex items-center justify-between rounded-xl border border-border bg-background px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-slate-200">{c.cause.replace(/_/g, ' ')}</p>
                      <p className="text-xs text-slate-500">Escalation trigger</p>
                    </div>
                    <div className="flex items-center gap-2 text-sm font-semibold text-red-300">
                      <AlertTriangle size={13} className="text-red-400" />
                      {c.count}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
