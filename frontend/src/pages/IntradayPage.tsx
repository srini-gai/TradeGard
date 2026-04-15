import { useCallback, useEffect, useState } from 'react'
import IntradaySignalCard from '../components/IntradaySignalCard'
import { getIntradayStatus, getTodayIntradaySignals, scanIntraday } from '../services/api'
import type { IntradaySignal } from '../types'

export default function IntradayPage() {
  const [signals, setSignals] = useState<IntradaySignal[]>([])
  const [scanning, setScanning] = useState(false)
  const [marketOpen, setMarketOpen] = useState(false)
  const [currentTime, setCurrentTime] = useState('')
  const [lastScan, setLastScan] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [scanError, setScanError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const [statusRes, signalsRes] = await Promise.allSettled([
        getIntradayStatus(),
        getTodayIntradaySignals(),
      ])
      if (statusRes.status === 'fulfilled') {
        setMarketOpen(statusRes.value.scan_available)
        setCurrentTime(statusRes.value.current_time_ist)
      }
      if (signalsRes.status === 'fulfilled') {
        setSignals(signalsRes.value.signals ?? [])
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
    const interval = setInterval(() => void load(), 60_000)
    return () => clearInterval(interval)
  }, [load])

  const handleScan = async () => {
    setScanning(true)
    setScanError(null)
    try {
      const res = await scanIntraday()
      setSignals(res.signals ?? [])
      setLastScan(
        new Date().toLocaleTimeString('en-IN', {
          hour: '2-digit',
          minute: '2-digit',
        }),
      )
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail
      setScanError(msg ?? 'Scan failed — check if market is open and Upstox is configured')
    } finally {
      setScanning(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-brand-text">Intraday Screener</h1>
          <p className="text-xs text-brand-subtext mt-0.5">
            30-min candles · Weekly expiry · Exit by 3:00 PM IST
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${marketOpen ? 'bg-green-400' : 'bg-red-400'}`}
            />
            <span className="text-xs text-brand-subtext">
              {marketOpen ? 'Market open' : 'Market closed'}
              {currentTime ? ` · ${currentTime} IST` : ''}
            </span>
          </div>
          <button
            onClick={() => void handleScan()}
            disabled={scanning}
            className="btn-primary"
          >
            {scanning ? 'Scanning F&O stocks...' : '▶ Scan now'}
          </button>
        </div>
      </div>

      {/* How it works banner */}
      <div className="card border-l-4 border-l-blue-500">
        <div className="text-xs text-brand-text font-medium mb-1">
          How intraday screener works
        </div>
        <div className="text-xs text-brand-subtext space-y-0.5">
          <div>· Fetches 30-min candles from Upstox for all F&O eligible Nifty 500 stocks</div>
          <div>· Filters using RSI + EMA9/21 crossover + VWAP + Volume on 30-min chart</div>
          <div>· Uses weekly expiry options (nearest Thursday)</div>
          <div>· Tighter risk: SL -25%, T1 +30%, T2 +60%</div>
          <div>· All positions must be exited by 3:00 PM IST</div>
        </div>
      </div>

      {/* Scan error */}
      {scanError && (
        <div className="bg-red-900/20 border border-red-800 text-red-400 text-xs rounded-lg px-3 py-2">
          {scanError}
        </div>
      )}

      {/* Last scan info */}
      {lastScan && (
        <div className="text-xs text-brand-subtext">
          Last scan: {lastScan} · {signals.length} signal
          {signals.length !== 1 ? 's' : ''} found
        </div>
      )}

      {/* Signal cards */}
      {loading ? (
        <div className="text-xs text-brand-muted text-center py-8">Loading...</div>
      ) : signals.length === 0 ? (
        <div className="card text-center py-10">
          <div className="text-brand-subtext text-sm mb-2">
            {marketOpen ? 'No intraday signals yet' : 'Market is closed'}
          </div>
          <div className="text-xs text-brand-muted">
            {marketOpen
              ? 'Click "Scan now" to analyse F&O stocks on 30-min chart'
              : 'Intraday scanning available 9:15 AM – 3:00 PM IST on weekdays'}
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {signals.map((s) => (
            <IntradaySignalCard key={s.id} signal={s} />
          ))}
        </div>
      )}
    </div>
  )
}
