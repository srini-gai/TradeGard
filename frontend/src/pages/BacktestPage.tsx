import { useState, useEffect, useCallback } from 'react'
import { getBacktestSummary, runBacktest, getBacktestRuns, getBacktestRunDetail } from '../services/api'
import type { BacktestSummary } from '../types'

interface BacktestTrade {
  id: number
  symbol: string
  direction: string
  entry_date: string
  exit_date: string | null
  entry_premium: number
  exit_premium: number | null
  outcome: string
  pnl: number | null
  pnl_pct: number
}

const outcomeColor: Record<string, string> = {
  T3: 'text-emerald-400',
  T2: 'text-green-400',
  T1: 'text-yellow-400',
  SL: 'text-red-400',
  EXPIRED: 'text-brand-muted',
}

export default function BacktestPage() {
  const [summary, setSummary] = useState<BacktestSummary | null>(null)
  const [runs, setRuns] = useState<{ id: number; run_date: string; win_rate: number; total_signals: number }[]>([])
  const [trades, setTrades] = useState<BacktestTrade[]>([])
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null)
  const [running, setRunning] = useState(false)
  const [months, setMonths] = useState(3)
  const [loading, setLoading] = useState(true)
  const [loadingTrades, setLoadingTrades] = useState(false)

  const load = useCallback(async () => {
    try {
      const [sumRes, runsRes] = await Promise.allSettled([
        getBacktestSummary(),
        getBacktestRuns(),
      ])
      if (sumRes.status === 'fulfilled' && sumRes.value.has_results) {
        setSummary(sumRes.value.summary)
      }
      if (runsRes.status === 'fulfilled') setRuns(runsRes.value as typeof runs)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const handleRun = async () => {
    setRunning(true)
    try {
      await runBacktest(months)
      void load()
    } finally {
      setRunning(false)
    }
  }

  const handleSelectRun = async (id: number) => {
    setSelectedRunId(id)
    setLoadingTrades(true)
    try {
      const detail = await getBacktestRunDetail(id) as { trades?: BacktestTrade[] }
      setTrades(detail.trades ?? [])
    } finally {
      setLoadingTrades(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-brand-text">Backtesting</h1>
          <p className="text-xs text-brand-subtext mt-0.5">Simulate signals on historical data</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={months}
            onChange={e => setMonths(+e.target.value)}
            className="bg-brand-surface border border-brand-border rounded px-3 py-2 text-xs text-brand-text focus:outline-none"
          >
            <option value={1}>1 month</option>
            <option value={2}>2 months</option>
            <option value={3}>3 months</option>
          </select>
          <button onClick={() => void handleRun()} disabled={running} className="btn-primary">
            {running ? `Running ${months}m backtest...` : `▶ Run ${months}m backtest`}
          </button>
        </div>
      </div>

      {running && (
        <div className="bg-brand-surface border border-brand-border rounded-lg p-4 text-xs text-brand-subtext">
          Pre-fetching data for 50 stocks then simulating day by day...
          This takes 2-5 minutes. Do not close the browser.
        </div>
      )}

      {/* Latest summary */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Win rate', value: `${summary.win_rate}%`, color: summary.win_rate >= 50 ? 'text-green-400' : 'text-yellow-400' },
            { label: 'Avg P&L', value: `${summary.avg_pnl > 0 ? '+' : ''}${summary.avg_pnl}%`, color: summary.avg_pnl >= 0 ? 'text-green-400' : 'text-red-400' },
            { label: 'Total signals', value: `${summary.total_signals}`, color: 'text-brand-text' },
            { label: 'Max drawdown', value: `${summary.max_drawdown ?? '—'}%`, color: 'text-yellow-400' },
            { label: 'Best trade', value: `+${summary.best_trade_pnl ?? '—'}%`, color: 'text-green-400' },
            { label: 'Worst trade', value: `${summary.worst_trade_pnl ?? '—'}%`, color: 'text-red-400' },
            { label: 'Period', value: summary.period_start, color: 'text-brand-subtext' },
            { label: 'To', value: summary.period_end, color: 'text-brand-subtext' },
          ].map(({ label, value, color }) => (
            <div key={label} className="metric-card">
              <div className="text-xs text-brand-subtext mb-1">{label}</div>
              <div className={`font-mono font-medium ${color}`}>{value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Monthly breakdown */}
      {summary && Object.keys(summary.monthly_breakdown).length > 0 && (
        <div className="card">
          <div className="text-xs text-brand-subtext font-medium uppercase tracking-wider mb-3">
            Monthly breakdown
          </div>
          <div className="flex flex-col gap-0">
            {Object.entries(summary.monthly_breakdown).map(([month, stats]) => (
              <div key={month} className="flex items-center justify-between py-2 border-b border-brand-border last:border-0 text-xs">
                <span className="text-brand-text font-medium w-24">{month}</span>
                <span className="text-brand-subtext">{stats.trades} trades</span>
                <span className={`font-mono ${stats.win_rate >= 50 ? 'text-green-400' : 'text-yellow-400'}`}>
                  {stats.win_rate}% wins
                </span>
                <span className={`font-mono ${stats.avg_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {stats.avg_pnl > 0 ? '+' : ''}{stats.avg_pnl}% avg
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Past runs */}
      {runs.length > 0 && (
        <div className="card">
          <div className="text-xs text-brand-subtext font-medium uppercase tracking-wider mb-3">
            Past runs
          </div>
          <div className="flex flex-col gap-1">
            {runs.map(run => (
              <button
                key={run.id}
                onClick={() => void handleSelectRun(run.id)}
                className={`flex items-center justify-between text-xs px-3 py-2 rounded-lg transition-colors text-left ${
                  selectedRunId === run.id
                    ? 'bg-brand-accent/10 border border-brand-accent/20 text-brand-text'
                    : 'hover:bg-brand-surface text-brand-subtext'
                }`}
              >
                <span>Run #{run.id} · {new Date(run.run_date).toLocaleDateString('en-IN')}</span>
                <span className={`font-mono ${run.win_rate >= 50 ? 'text-green-400' : 'text-yellow-400'}`}>
                  {run.win_rate}% · {run.total_signals} signals
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Individual trades for selected run */}
      {selectedRunId && (
        <div className="card">
          <div className="text-xs text-brand-subtext font-medium uppercase tracking-wider mb-3">
            Trades — Run #{selectedRunId}
          </div>
          {loadingTrades ? (
            <div className="text-xs text-brand-muted py-4 text-center">Loading trades...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-brand-muted border-b border-brand-border">
                    {['Symbol', 'Dir', 'Entry date', 'Entry ₹', 'Exit ₹', 'Outcome', 'P&L %'].map(h => (
                      <th key={h} className="text-left py-2 pr-4 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {trades.map(t => (
                    <tr key={t.id} className="border-b border-brand-border last:border-0">
                      <td className="py-2 pr-4 font-mono font-medium text-brand-text">{t.symbol}</td>
                      <td className="pr-4">
                        <span className={t.direction === 'CE' ? 'badge-ce' : 'badge-pe'}>{t.direction}</span>
                      </td>
                      <td className="pr-4 text-brand-subtext">{t.entry_date}</td>
                      <td className="pr-4 font-mono text-brand-text">₹{t.entry_premium}</td>
                      <td className="pr-4 font-mono text-brand-subtext">
                        {t.exit_premium != null ? `₹${t.exit_premium}` : '—'}
                      </td>
                      <td className={`pr-4 font-medium ${outcomeColor[t.outcome] ?? 'text-brand-subtext'}`}>
                        {t.outcome}
                      </td>
                      <td className={`font-mono font-medium ${t.pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {t.pnl_pct > 0 ? '+' : ''}{t.pnl_pct}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {!loading && runs.length === 0 && (
        <div className="card text-center py-10">
          <div className="text-brand-subtext text-sm mb-2">No backtest runs yet</div>
          <div className="text-xs text-brand-muted">Click &quot;Run backtest&quot; to analyse historical signals</div>
        </div>
      )}
    </div>
  )
}
