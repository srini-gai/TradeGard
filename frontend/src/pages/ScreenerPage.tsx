import { useState, useEffect, useCallback } from 'react'
import type { Signal } from '../types'
import { getAllSignals, runScreener, refreshNifty500 } from '../services/api'
import SignalCard from '../components/SignalCard'
import LogTradeModal from '../components/LogTradeModal'
import StockSearchBox from '../components/StockSearchBox'

export default function ScreenerPage() {
  const [signals, setSignals] = useState<Signal[]>([])
  const [total, setTotal] = useState(0)
  const [running, setRunning] = useState(false)
  const [logSignal, setLogSignal] = useState<Signal | null>(null)
  const [loading, setLoading] = useState(true)
  const [dirFilter, setDirFilter] = useState<'ALL' | 'CE' | 'PE'>('ALL')
  const [minScore, setMinScore] = useState(70)
  const [page, setPage] = useState(0)
  const PAGE_SIZE = 10
  const [refreshing, setRefreshing] = useState(false)
  const [refreshMsg, setRefreshMsg] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const res = await getAllSignals(PAGE_SIZE, page * PAGE_SIZE, minScore)
      setSignals(res.signals ?? [])
      setTotal(res.total ?? 0)
    } finally {
      setLoading(false)
    }
  }, [page, minScore])

  useEffect(() => {
    void load()
  }, [load])

  const handleRefreshList = async () => {
    setRefreshing(true)
    setRefreshMsg(null)
    try {
      const res = await refreshNifty500()
      setRefreshMsg(`✓ ${res.message}`)
    } catch {
      setRefreshMsg('✗ Refresh failed — check if backend can reach niftyindices.com')
    } finally {
      setRefreshing(false)
    }
  }

  const handleRun = async () => {
    setRunning(true)
    try {
      await runScreener()
      setPage(0)
      void load()
    } finally {
      setRunning(false)
    }
  }

  const handleMinScoreChange = (score: number) => {
    setMinScore(score)
    setPage(0)
    setLoading(true)
  }

  const filtered =
    dirFilter === 'ALL' ? signals : signals.filter((s) => s.direction === dirFilter)

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-brand-text">Screener</h1>
          <p className="text-xs text-brand-subtext mt-0.5">
            Nifty 50 daily screener · {total} signals in history
          </p>
        </div>
        <button
          onClick={() => void handleRun()}
          disabled={running}
          className="btn-primary self-start sm:self-auto"
        >
          {running ? 'Scanning...' : '▶ Run screener'}
        </button>
      </div>

      {/* Stock search — Nifty 500 */}
      <div className="card">
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          <span className="text-sm font-medium text-brand-text">
            Analyse any Nifty 500 stock
          </span>
          <span className="text-xs bg-brand-accent/20 text-brand-accent px-2 py-0.5 rounded-full">
            500 stocks
          </span>
          <button
            onClick={() => void handleRefreshList()}
            disabled={refreshing}
            className="text-xs text-brand-muted hover:text-brand-subtext ml-auto"
            title="Refresh from NSE official list"
          >
            {refreshing ? 'Refreshing...' : '↻ Refresh list'}
          </button>
        </div>
        {refreshMsg && (
          <div className={`text-xs px-2 py-1 rounded mb-3 ${
            refreshMsg.startsWith('✓')
              ? 'text-green-400 bg-green-900/20'
              : 'text-red-400 bg-red-900/20'
          }`}>
            {refreshMsg}
          </div>
        )}
        <div className="text-xs text-brand-subtext mb-3">
          Search any stock — runs same RSI + EMA + volume analysis and gives
          you a confidence score
        </div>
        <StockSearchBox />
      </div>

      {/* Divider */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-brand-border" />
        <span className="text-xs text-brand-muted">Nifty 50 screener history</span>
        <div className="flex-1 h-px bg-brand-border" />
      </div>

      {/* Confidence score filter */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-brand-subtext font-medium">Min confidence:</span>
          {([0, 60, 70, 80, 90] as const).map((score) => (
            <button
              key={score}
              onClick={() => handleMinScoreChange(score)}
              className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${
                minScore === score
                  ? 'bg-brand-accent/20 text-brand-accent border border-brand-accent/30'
                  : 'text-brand-subtext hover:text-brand-text hover:bg-brand-surface'
              }`}
            >
              {score === 0 ? 'All' : `${score}+`}
            </button>
          ))}
          <span className="text-xs text-brand-muted ml-auto">
            {total} signal{total !== 1 ? 's' : ''}
            {minScore > 0 ? ` ≥ ${minScore}` : ''}
          </span>
        </div>
      </div>

      {/* Direction filters */}
      <div className="flex gap-1">
        {(['ALL', 'CE', 'PE'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setDirFilter(f)}
            className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${
              dirFilter === f
                ? 'bg-brand-accent/20 text-brand-accent border border-brand-accent/30'
                : 'text-brand-subtext hover:text-brand-text hover:bg-brand-surface'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Signal cards */}
      {loading ? (
        <div className="text-xs text-brand-muted text-center py-8">
          Loading...
        </div>
      ) : filtered.length === 0 ? (
        <div className="card text-center py-10">
          <div className="text-brand-subtext text-sm mb-2">No signals yet</div>
          <div className="text-xs text-brand-muted">
            Click &quot;Run screener&quot; to generate signals
          </div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            {filtered.map((s) => (
              <SignalCard key={s.id} signal={s} onLogTrade={setLogSignal} />
            ))}
          </div>
          {/* Pagination */}
          <div className="flex items-center justify-between text-xs text-brand-subtext">
            <span>
              Page {page + 1} of {Math.ceil(total / PAGE_SIZE) || 1}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="btn-ghost text-xs py-1"
              >
                ← Prev
              </button>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={(page + 1) * PAGE_SIZE >= total}
                className="btn-ghost text-xs py-1"
              >
                Next →
              </button>
            </div>
          </div>
        </>
      )}

      {logSignal && (
        <LogTradeModal
          signal={logSignal}
          onClose={() => setLogSignal(null)}
          onLogged={() => setLogSignal(null)}
        />
      )}
    </div>
  )
}
