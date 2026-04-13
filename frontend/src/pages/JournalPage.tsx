import { useCallback, useEffect, useState } from 'react'
import type { Trade, MonthlySummary } from '../types'
import {
  getMonthlySummaryTyped,
  getTrades,
  getWeeklySummary,
} from '../services/api'
import LogTradeModal from '../components/LogTradeModal'
import TradeRow from '../components/TradeRow'

type WeeklySummary = {
  total_pnl: number
  total_trades: number
  win_rate: number
}

export default function JournalPage() {
  const [trades, setTrades] = useState<Trade[]>([])
  const [monthly, setMonthly] = useState<MonthlySummary | null>(null)
  const [weekly, setWeekly] = useState<WeeklySummary | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<
    'ALL' | 'OPEN' | 'CLOSED' | 'SL_HIT'
  >('ALL')

  const load = useCallback(async () => {
    try {
      const [t, m, w] = await Promise.allSettled([
        getTrades(),
        getMonthlySummaryTyped(),
        getWeeklySummary(),
      ])
      if (t.status === 'fulfilled') setTrades(t.value)
      if (m.status === 'fulfilled') setMonthly(m.value)
      if (w.status === 'fulfilled') setWeekly(w.value as WeeklySummary)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const filtered =
    filter === 'ALL' ? trades : trades.filter((tr) => tr.status === filter)
  const fmt = (n: number | null) =>
    n == null
      ? '—'
      : `${n >= 0 ? '+' : ''}₹${Math.abs(n).toLocaleString('en-IN')}`
  const pnlColor = (n: number | null) =>
    n == null ? '' : n >= 0 ? 'text-green-400' : 'text-red-400'

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-brand-text">Trade Journal</h1>
          <p className="text-xs text-brand-subtext mt-0.5">
            Log and track every options trade
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowModal(true)}
          className="btn-primary"
        >
          + Log trade
        </button>
      </div>

      {monthly && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {(
            [
              {
                label: `${monthly.period} trades`,
                value: `${monthly.total_trades}`,
                sub: `${monthly.open_trades} open`,
              },
              {
                label: 'Win rate',
                value: `${monthly.win_rate}%`,
                sub: `${monthly.sl_hit} SL hits`,
                color:
                  monthly.win_rate >= 50
                    ? 'text-green-400'
                    : 'text-yellow-400',
              },
              {
                label: 'Month P&L',
                value: fmt(monthly.total_pnl),
                sub: monthly.period,
                color: pnlColor(monthly.total_pnl),
              },
              {
                label: 'Week P&L',
                value: weekly ? fmt(weekly.total_pnl) : '—',
                sub: `${weekly?.total_trades ?? 0} trades`,
                color: weekly ? pnlColor(weekly.total_pnl) : '',
              },
            ] satisfies {
              label: string
              value: string
              sub: string
              color?: string
            }[]
          ).map(({ label, value, sub, color }) => (
            <div key={label} className="metric-card">
              <div className="text-xs text-brand-subtext mb-1">{label}</div>
              <div
                className={`text-xl font-mono font-medium ${color ?? 'text-brand-text'}`}
              >
                {value}
              </div>
              <div className="text-xs text-brand-muted mt-0.5">{sub}</div>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-1">
        {(['ALL', 'OPEN', 'CLOSED', 'SL_HIT'] as const).map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${
              filter === f
                ? 'bg-brand-accent/20 text-brand-accent border border-brand-accent/30'
                : 'text-brand-subtext hover:text-brand-text hover:bg-brand-surface'
            }`}
          >
            {f.replace('_', ' ')}
            {f !== 'ALL' && (
              <span className="ml-1.5 opacity-60">
                {trades.filter((t) => t.status === f).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-xs text-brand-muted text-center py-8">
          Loading trades...
        </div>
      ) : filtered.length === 0 ? (
        <div className="card text-center py-10">
          <div className="text-brand-subtext text-sm mb-2">No trades yet</div>
          <div className="text-xs text-brand-muted">
            Click &quot;+ Log trade&quot; to record your first trade
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {filtered.map((trade) => (
            <TradeRow key={trade.id} trade={trade} onUpdated={load} />
          ))}
        </div>
      )}

      {showModal && (
        <LogTradeModal
          onClose={() => setShowModal(false)}
          onLogged={load}
        />
      )}
    </div>
  )
}
