import { useState, useEffect, useCallback } from 'react'
import type { Signal } from '../types'
import { getAllSignals, runScreener } from '../services/api'
import SignalCard from '../components/SignalCard'
import LogTradeModal from '../components/LogTradeModal'

export default function ScreenerPage() {
  const [signals, setSignals] = useState<Signal[]>([])
  const [total, setTotal] = useState(0)
  const [running, setRunning] = useState(false)
  const [logSignal, setLogSignal] = useState<Signal | null>(null)
  const [loading, setLoading] = useState(true)
  const [dirFilter, setDirFilter] = useState<'ALL' | 'CE' | 'PE'>('ALL')
  const [page, setPage] = useState(0)
  const PAGE_SIZE = 10

  const load = useCallback(async () => {
    try {
      const res = await getAllSignals(PAGE_SIZE, page * PAGE_SIZE)
      setSignals(res.signals ?? [])
      setTotal(res.total ?? 0)
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => { void load() }, [load])

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

  const filtered = dirFilter === 'ALL'
    ? signals
    : signals.filter(s => s.direction === dirFilter)

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-brand-text">Screener History</h1>
          <p className="text-xs text-brand-subtext mt-0.5">
            All signals generated · {total} total
          </p>
        </div>
        <button onClick={() => void handleRun()} disabled={running} className="btn-primary">
          {running ? 'Scanning 50 stocks...' : '▶ Run screener'}
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-1">
        {(['ALL', 'CE', 'PE'] as const).map(f => (
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
        <div className="text-xs text-brand-muted text-center py-8">Loading...</div>
      ) : filtered.length === 0 ? (
        <div className="card text-center py-10">
          <div className="text-brand-subtext text-sm mb-2">No signals yet</div>
          <div className="text-xs text-brand-muted">Click &quot;Run screener&quot; to generate signals</div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            {filtered.map(s => (
              <SignalCard key={s.id} signal={s} onLogTrade={setLogSignal} />
            ))}
          </div>
          {/* Pagination */}
          <div className="flex items-center justify-between text-xs text-brand-subtext">
            <span>Page {page + 1} of {Math.ceil(total / PAGE_SIZE) || 1}</span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="btn-ghost text-xs py-1"
              >← Prev</button>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={(page + 1) * PAGE_SIZE >= total}
                className="btn-ghost text-xs py-1"
              >Next →</button>
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
