import { useState, useEffect, useRef, useCallback } from 'react'
import type { Nifty500Symbol, StockAnalysis, Signal, StrikeData } from '../types'
import { getNifty500Symbols, analyseSymbol, getStrikes } from '../services/api'
import SignalCard from './SignalCard'
import LogTradeModal from './LogTradeModal'

function ScoreBar({ score }: { score: number }) {
  const color =
    score >= 80 ? 'bg-green-500' : score >= 60 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-brand-surface rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="text-xs font-mono font-medium text-brand-text w-8 text-right">
        {score}
      </span>
    </div>
  )
}

export default function StockSearchBox() {
  const [symbols, setSymbols] = useState<Nifty500Symbol[]>([])
  const [query, setQuery] = useState('')
  const [filtered, setFiltered] = useState<Nifty500Symbol[]>([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [analysing, setAnalysing] = useState(false)
  const [result, setResult] = useState<StockAnalysis | null>(null)
  const [logSignal, setLogSignal] = useState<Signal | null>(null)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Strike selector state
  const [strikes, setStrikes] = useState<StrikeData[]>([])
  const [strikesExpiry, setStrikesExpiry] = useState<string | null>(null)
  const [selectedStrike, setSelectedStrike] = useState<number | null>(null)
  const [selectedDirection, setSelectedDirection] = useState<'CE' | 'PE'>('CE')
  const [strikesLoading, setStrikesLoading] = useState(false)
  const [customSignal, setCustomSignal] = useState<Signal | null>(null)

  useEffect(() => {
    getNifty500Symbols()
      .then((res) => setSymbols(res.symbols))
      .catch(() => setError('Could not load symbol list'))
  }, [])

  useEffect(() => {
    if (!query || query.length < 1) {
      setFiltered([])
      setShowDropdown(false)
      return
    }
    const q = query.toUpperCase()
    const matches = symbols
      .filter((s) => s.symbol.startsWith(q) || s.symbol.includes(q))
      .slice(0, 10)
    setFiltered(matches)
    setShowDropdown(matches.length > 0)
  }, [query, symbols])

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(e.target as Node)
      ) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const buildCustomSignal = useCallback(
    (base: Signal, strike: number, direction: 'CE' | 'PE', strikesData: StrikeData[]): Signal => {
      const row = strikesData.find((s) => s.strike === strike)
      const ltp = row ? (direction === 'CE' ? row.ce_ltp : row.pe_ltp) : base.entry_premium
      const entry = ltp || base.entry_premium
      return {
        ...base,
        strike,
        direction,
        entry_premium: entry,
        sl_premium: parseFloat((entry * 0.6).toFixed(2)),   // -40%
        t1_premium: parseFloat((entry * 1.38).toFixed(2)),  // +38%
        t2_premium: parseFloat((entry * 1.79).toFixed(2)),  // +79%
        t3_premium: parseFloat((entry * 2.14).toFixed(2)),  // +114%
      }
    },
    [],
  )

  const handleSelect = useCallback(async (symbol: string) => {
    setQuery(symbol)
    setShowDropdown(false)
    setResult(null)
    setError(null)
    setStrikes([])
    setStrikesExpiry(null)
    setSelectedStrike(null)
    setCustomSignal(null)
    setAnalysing(true)
    try {
      const analysis = await analyseSymbol(symbol)
      setResult(analysis)

      if (analysis.qualified && analysis.signal) {
        const dir: 'CE' | 'PE' = analysis.signal.direction ?? 'CE'
        setSelectedDirection(dir)
        // Fetch strikes in background — don't block showing the result
        setStrikesLoading(true)
        getStrikes(symbol)
          .then((res) => {
            setStrikes(res.strikes)
            setStrikesExpiry(res.expiry)
            const atm = res.atm_strike ?? analysis.signal!.strike
            setSelectedStrike(atm)
            setCustomSignal(buildCustomSignal(analysis.signal!, atm, dir, res.strikes))
          })
          .catch(() => {
            // Upstox not configured — fall back silently
          })
          .finally(() => setStrikesLoading(false))
      }
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail
      setError(detail ?? `Could not analyse ${symbol}`)
    } finally {
      setAnalysing(false)
    }
  }, [buildCustomSignal])

  const handleStrikeChange = (strike: number) => {
    setSelectedStrike(strike)
    if (result?.signal) {
      setCustomSignal(buildCustomSignal(result.signal, strike, selectedDirection, strikes))
    }
  }

  const handleDirectionChange = (dir: 'CE' | 'PE') => {
    setSelectedDirection(dir)
    if (result?.signal && selectedStrike !== null) {
      setCustomSignal(buildCustomSignal(result.signal, selectedStrike, dir, strikes))
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && filtered.length > 0) {
      void handleSelect(filtered[0].symbol)
    }
    if (e.key === 'Escape') setShowDropdown(false)
  }

  const handleClear = () => {
    setQuery('')
    setResult(null)
    setError(null)
    setStrikes([])
    setStrikesExpiry(null)
    setSelectedStrike(null)
    setCustomSignal(null)
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Search input */}
      <div className="relative">
        <div className="flex items-center gap-2 bg-brand-surface border border-brand-border rounded-xl px-4 py-3 focus-within:border-brand-accent transition-colors">
          <svg
            className="w-4 h-4 text-brand-muted flex-shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value.toUpperCase())}
            onKeyDown={handleKeyDown}
            onFocus={() => filtered.length > 0 && setShowDropdown(true)}
            placeholder="Search any Nifty 500 stock… (e.g. ZOMATO, DMART, HAL)"
            className="flex-1 bg-transparent text-sm text-brand-text placeholder-brand-muted focus:outline-none font-mono"
          />
          {analysing && (
            <div className="w-4 h-4 border-2 border-brand-accent border-t-transparent rounded-full animate-spin flex-shrink-0" />
          )}
          {query && !analysing && (
            <button
              onClick={handleClear}
              className="text-brand-muted hover:text-brand-text text-sm flex-shrink-0"
            >
              ✕
            </button>
          )}
        </div>

        {/* Autocomplete dropdown */}
        {showDropdown && (
          <div
            ref={dropdownRef}
            className="absolute top-full left-0 right-0 mt-1 bg-brand-card border border-brand-border rounded-xl shadow-xl z-50 overflow-hidden"
          >
            {filtered.map((s, i) => (
              <button
                key={s.symbol}
                onClick={() => void handleSelect(s.symbol)}
                className={`w-full flex items-center justify-between px-4 py-2.5 text-sm hover:bg-brand-surface transition-colors text-left ${
                  i < filtered.length - 1 ? 'border-b border-brand-border' : ''
                }`}
              >
                <span className="font-mono font-medium text-brand-text">
                  {s.symbol}
                </span>
                <span className="text-xs text-brand-muted">NSE</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-900/20 border border-red-800 text-red-400 text-xs rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {/* Analysing spinner */}
      {analysing && (
        <div className="card text-center py-6">
          <div className="text-xs text-brand-subtext animate-pulse">
            Analysing {query} — fetching 90 days of data…
          </div>
        </div>
      )}

      {/* Result */}
      {result && !analysing && (
        <div className="flex flex-col gap-4">
          {/* Quick stats card */}
          <div className="card flex flex-col gap-3">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <span className="font-mono font-semibold text-brand-text">
                  {result.symbol}
                </span>
                {result.current_price != null && (
                  <span className="text-sm text-brand-subtext">
                    ₹{result.current_price}
                  </span>
                )}
                <span
                  className={`text-xs px-2 py-0.5 rounded-full border ${
                    result.qualified
                      ? 'bg-green-900/40 text-green-400 border-green-800'
                      : 'bg-red-900/40 text-red-400 border-red-800'
                  }`}
                >
                  {result.qualified ? '✓ Qualifies' : '✗ No signal'}
                </span>
              </div>
              <div className="text-xs text-brand-subtext">{result.reason}</div>
            </div>

            {/* Indicator readout */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {[
                {
                  label: 'RSI (14)',
                  value:
                    result.rsi != null ? result.rsi.toFixed(1) : '—',
                  note:
                    result.rsi != null
                      ? result.rsi >= 55 && result.rsi <= 70
                        ? 'Bullish zone'
                        : result.rsi >= 30 && result.rsi <= 45
                          ? 'Bearish zone'
                          : 'Neutral'
                      : '',
                  color:
                    result.rsi != null
                      ? result.rsi >= 55 && result.rsi <= 70
                        ? 'text-green-400'
                        : result.rsi >= 30 && result.rsi <= 45
                          ? 'text-red-400'
                          : 'text-brand-subtext'
                      : 'text-brand-subtext',
                },
                {
                  label: 'EMA 20',
                  value:
                    result.ema20 != null
                      ? `₹${result.ema20.toFixed(0)}`
                      : '—',
                  note: result.above_ema
                    ? 'Price above EMA'
                    : 'Price below EMA',
                  color: result.above_ema ? 'text-green-400' : 'text-red-400',
                },
                {
                  label: 'Volume ratio',
                  value:
                    result.volume_ratio != null
                      ? `${result.volume_ratio}x`
                      : '—',
                  note:
                    result.volume_ratio != null && result.volume_ratio >= 1.5
                      ? 'Volume surge'
                      : 'Normal',
                  color:
                    result.volume_ratio != null && result.volume_ratio >= 1.5
                      ? 'text-green-400'
                      : 'text-brand-subtext',
                },
                {
                  label: 'Trend',
                  value: result.above_ema ? 'Bullish' : 'Bearish',
                  note: result.above_ema ? 'CE candidate' : 'PE candidate',
                  color: result.above_ema ? 'text-green-400' : 'text-red-400',
                },
              ].map(({ label, value, note, color }) => (
                <div key={label} className="metric-card">
                  <div className="text-xs text-brand-muted mb-1">{label}</div>
                  <div className={`font-mono font-medium text-sm ${color}`}>
                    {value}
                  </div>
                  <div className="text-xs text-brand-muted mt-0.5">{note}</div>
                </div>
              ))}
            </div>

            {/* Confidence score */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-brand-subtext">
                  Confidence score
                </span>
                <span className="text-xs text-brand-muted">
                  Min threshold: 60
                </span>
              </div>
              <ScoreBar score={result.confidence_score} />
            </div>
          </div>

          {/* Strike selector — shown when qualified and strikes available */}
          {result.qualified && result.signal && (
            <div className="card flex flex-col gap-3">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <span className="text-xs font-medium text-brand-subtext uppercase tracking-wider">
                  Strike &amp; Direction
                </span>
                {strikesExpiry && (
                  <span className="text-xs text-brand-muted">Expiry: {strikesExpiry}</span>
                )}
              </div>

              {/* CE / PE toggle */}
              <div className="flex gap-1">
                {(['CE', 'PE'] as const).map((d) => (
                  <button
                    key={d}
                    onClick={() => handleDirectionChange(d)}
                    className={`text-xs px-4 py-1.5 rounded-lg font-mono transition-colors ${
                      selectedDirection === d
                        ? d === 'CE'
                          ? 'bg-green-900/40 text-green-400 border border-green-700'
                          : 'bg-red-900/40 text-red-400 border border-red-700'
                        : 'text-brand-subtext hover:text-brand-text hover:bg-brand-surface border border-transparent'
                    }`}
                  >
                    {d}
                  </button>
                ))}
              </div>

              {/* Strike dropdown */}
              {strikesLoading ? (
                <div className="text-xs text-brand-muted animate-pulse">
                  Loading strikes from Upstox…
                </div>
              ) : strikes.length > 0 ? (
                <div className="flex flex-col gap-1">
                  <label className="text-xs text-brand-muted">Strike price</label>
                  <select
                    value={selectedStrike ?? ''}
                    onChange={(e) => handleStrikeChange(Number(e.target.value))}
                    className="bg-brand-surface border border-brand-border text-brand-text text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-brand-accent font-mono"
                  >
                    {strikes.map((s) => (
                      <option key={s.strike} value={s.strike}>
                        {s.strike} — CE ₹{s.ce_ltp.toFixed(1)} / PE ₹{s.pe_ltp.toFixed(1)}
                        {s.strike === (result.signal ? result.signal.strike : null) ? ' (ATM)' : ''}
                      </option>
                    ))}
                  </select>
                  {selectedStrike !== null && (
                    <div className="text-xs text-brand-muted mt-0.5">
                      {selectedDirection} LTP:{' '}
                      <span className="font-mono text-brand-text">
                        ₹{(strikes.find((s) => s.strike === selectedStrike)?.[selectedDirection === 'CE' ? 'ce_ltp' : 'pe_ltp'] ?? 0).toFixed(1)}
                      </span>
                      {' · '}premiums recalculated below
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-xs text-brand-muted">
                  Strike data unavailable — Upstox not configured or market closed.
                  Showing default ATM values.
                </div>
              )}
            </div>
          )}

          {/* Signal card if qualified */}
          {result.qualified && result.signal && (
            <div>
              <div className="text-xs text-brand-subtext font-medium uppercase tracking-wider mb-2">
                Trade signal
              </div>
              <SignalCard
                signal={
                  customSignal
                    ? { ...customSignal, id: customSignal.id ?? 0 }
                    : ({ ...result.signal, id: result.signal.id ?? 0 } as Signal)
                }
                onLogTrade={setLogSignal}
              />
            </div>
          )}

          {/* Not qualified explanation */}
          {!result.qualified && (
            <div className="card border-l-4 border-l-yellow-600">
              <div className="text-sm font-medium text-brand-text mb-2">
                Why {result.symbol} doesn&apos;t qualify right now
              </div>
              <div className="text-xs text-brand-subtext space-y-1">
                {result.rsi != null &&
                  !(result.rsi >= 55 && result.rsi <= 70) &&
                  !(result.rsi >= 30 && result.rsi <= 45) && (
                    <div>
                      · RSI {result.rsi.toFixed(1)} is in neutral zone (need
                      55–70 for CE or 30–45 for PE)
                    </div>
                  )}
                {result.volume_ratio != null && result.volume_ratio < 1.2 && (
                  <div>
                    · Volume {result.volume_ratio}x is too low (need at least
                    1.2x average)
                  </div>
                )}
                <div>
                  · Confidence score {result.confidence_score} is below the 60
                  threshold
                </div>
                <div className="mt-2 text-brand-muted">
                  Check back when market conditions change — RSI and volume
                  levels shift daily.
                </div>
              </div>
            </div>
          )}
        </div>
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
