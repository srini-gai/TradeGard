import { useCallback, useEffect, useState } from 'react'
import AlertsFeed from '../components/AlertsFeed'
import BacktestSummaryPanel from '../components/BacktestSummaryPanel'
import LogTradeModal from '../components/LogTradeModal'
import MetricsBar from '../components/MetricsBar'
import RiskPanel from '../components/RiskPanel'
import SignalCard from '../components/SignalCard'
import {
  getBacktestSummary,
  getTodayAlerts,
  getTodaySignals,
  getTodayTrades,
  runBacktest,
  runScreener,
} from '../services/api'
import type { Alert, BacktestSummary, Signal } from '../types'

function normalizeRunSignals(raw: unknown[]): Signal[] {
  return raw.map((item) => {
    const o = item as Record<string, unknown>
    return {
      id: typeof o.id === 'number' ? o.id : undefined,
      symbol: String(o.symbol ?? ''),
      signal_date: String(o.signal_date ?? ''),
      direction: (o.direction === 'PE' ? 'PE' : 'CE') as 'CE' | 'PE',
      strike: Number(o.strike ?? 0),
      expiry: String(o.expiry ?? ''),
      entry_premium: Number(o.entry_premium ?? 0),
      sl_premium: Number(o.sl_premium ?? 0),
      t1_premium: Number(o.t1_premium ?? 0),
      t2_premium: Number(o.t2_premium ?? 0),
      t3_premium: Number(o.t3_premium ?? 0),
      t1_date: o.t1_date != null ? String(o.t1_date) : null,
      t2_date: o.t2_date != null ? String(o.t2_date) : null,
      t3_date: o.t3_date != null ? String(o.t3_date) : null,
      confidence_score: Number(o.confidence_score ?? 0),
      rationale: Array.isArray(o.rationale)
        ? (o.rationale as string[])
        : null,
      created_at: o.created_at != null ? String(o.created_at) : null,
      current_price:
        o.current_price != null ? Number(o.current_price) : undefined,
      rsi: o.rsi != null ? Number(o.rsi) : undefined,
      ema20: o.ema20 != null ? Number(o.ema20) : undefined,
      volume_ratio:
        o.volume_ratio != null ? Number(o.volume_ratio) : undefined,
      days_to_expiry:
        o.days_to_expiry != null ? Number(o.days_to_expiry) : undefined,
    }
  })
}

export default function Dashboard() {
  const [signals, setSignals] = useState<Signal[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [backtestSummary, setBacktestSummary] =
    useState<BacktestSummary | null>(null)
  const [tradesToday, setTradesToday] = useState(0)
  const [logSignal, setLogSignal] = useState<Signal | null>(null)
  const [screeningRunning, setScreeningRunning] = useState(false)
  const [backtestRunning, setBacktestRunning] = useState(false)
  const [lastRun, setLastRun] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const [sigRes, alertRes, btRes, tradeRes] = await Promise.allSettled([
        getTodaySignals(),
        getTodayAlerts(),
        getBacktestSummary(),
        getTodayTrades(),
      ])
      if (sigRes.status === 'fulfilled')
        setSignals(sigRes.value.signals ?? [])
      if (alertRes.status === 'fulfilled') {
        const data = alertRes.value
        setAlerts(Array.isArray(data) ? data : data.alerts ?? [])
      }
      if (btRes.status === 'fulfilled' && btRes.value.has_results)
        setBacktestSummary(btRes.value.summary)
      if (tradeRes.status === 'fulfilled') {
        const v = tradeRes.value as
          | unknown[]
          | { count?: number; trades?: unknown[] }
        if (Array.isArray(v)) setTradesToday(v.length)
        else if (typeof v.count === 'number') setTradesToday(v.count)
        else if (Array.isArray(v.trades)) setTradesToday(v.trades.length)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const handleRunScreener = async () => {
    setScreeningRunning(true)
    try {
      const res = await runScreener()
      const raw = (res.signals ?? []) as unknown[]
      setSignals(normalizeRunSignals(raw))
      setLastRun(new Date().toLocaleTimeString('en-IN'))
    } catch (e) {
      console.error('Screener failed', e)
    } finally {
      setScreeningRunning(false)
    }
  }

  const handleRunBacktest = async () => {
    setBacktestRunning(true)
    try {
      await runBacktest(3)
      const res = await getBacktestSummary()
      if (res.has_results) setBacktestSummary(res.summary)
    } catch (e) {
      console.error('Backtest failed', e)
    } finally {
      setBacktestRunning(false)
    }
  }

  const now = new Date()
  const istTime = now.toLocaleTimeString('en-IN', {
    timeZone: 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
  })
  const istDate = now.toLocaleDateString('en-IN', {
    timeZone: 'Asia/Kolkata',
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })

  const metrics = [
    {
      label: "Today's signals",
      value: `${signals.length} / 2`,
      sub: lastRun ? `Last run ${lastRun}` : 'Not run yet',
      color: signals.length > 0 ? 'text-brand-accent' : 'text-brand-text',
    },
    {
      label: 'Backtest win rate',
      value: backtestSummary ? `${backtestSummary.win_rate}%` : '—',
      sub: backtestSummary
        ? `${backtestSummary.total_signals} signals tested`
        : 'Run backtest',
      color:
        backtestSummary && backtestSummary.win_rate >= 50
          ? 'text-green-400'
          : 'text-brand-text',
    },
    {
      label: 'Trades today',
      value: `${tradesToday} / 2`,
      sub: `${2 - tradesToday} slot${2 - tradesToday !== 1 ? 's' : ''} remaining`,
      color: tradesToday >= 2 ? 'text-red-400' : 'text-brand-text',
    },
    {
      label: 'IST time',
      value: istTime,
      sub: istDate,
      color: 'text-brand-subtext',
    },
  ]

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-brand-text">Dashboard</h1>
          <p className="text-xs text-brand-subtext mt-0.5">
            Nifty 50 options · Monthly expiry
          </p>
        </div>
        <button
          type="button"
          onClick={() => void handleRunScreener()}
          disabled={screeningRunning}
          className="btn-primary"
        >
          {screeningRunning ? 'Scanning 50 stocks...' : '▶ Run screener'}
        </button>
      </div>

      <MetricsBar metrics={metrics} />

      <div>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-sm font-medium text-brand-text">
            Today&apos;s signals
          </span>
          {signals.length > 0 && (
            <span className="text-xs bg-brand-accent/20 text-brand-accent px-2 py-0.5 rounded-full">
              {signals.length} ready
            </span>
          )}
        </div>
        {loading ? (
          <div className="text-xs text-brand-muted text-center py-8">
            Loading...
          </div>
        ) : signals.length === 0 ? (
          <div className="card text-center py-8">
            <div className="text-brand-subtext text-sm mb-2">
              No signals yet today
            </div>
            <div className="text-xs text-brand-muted">
              Click &quot;Run screener&quot; to scan all 50 Nifty stocks
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            {signals.map((s, idx) => (
              <SignalCard
                key={s.id ?? `${s.symbol}-${s.signal_date}-${idx}`}
                signal={s}
                onLogTrade={setLogSignal}
              />
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <BacktestSummaryPanel
            summary={backtestSummary}
            onRunBacktest={() => void handleRunBacktest()}
            running={backtestRunning}
          />
        </div>
        <div className="flex flex-col gap-4">
          <RiskPanel winRate={backtestSummary?.win_rate} />
          <AlertsFeed alerts={alerts} />
        </div>
      </div>

      {logSignal && (
        <LogTradeModal
          signal={logSignal}
          onClose={() => setLogSignal(null)}
          onLogged={() => {
            setLogSignal(null)
            void load()
          }}
        />
      )}
    </div>
  )
}
