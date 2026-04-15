import type { IntradaySignal } from '../types'

interface Props {
  signal: IntradaySignal
  onLogTrade?: (signal: IntradaySignal) => void
}

const fmt = (n: number) => `₹${n.toFixed(2)}`

export default function IntradaySignalCard({ signal, onLogTrade }: Props) {
  const isCE = signal.direction === 'CE'
  const accentColor = isCE ? 'border-l-green-500' : 'border-l-red-500'

  const t1Pct = (
    ((signal.t1_premium - signal.entry_premium) / signal.entry_premium) *
    100
  ).toFixed(0)
  const t2Pct = (
    ((signal.t2_premium - signal.entry_premium) / signal.entry_premium) *
    100
  ).toFixed(0)
  const slPct = (
    ((signal.sl_premium - signal.entry_premium) / signal.entry_premium) *
    100
  ).toFixed(0)

  return (
    <div className={`card border-l-4 ${accentColor} flex flex-col gap-4`}>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-lg font-semibold text-brand-text font-mono">
              {signal.symbol}
            </span>
            <span className={isCE ? 'badge-ce' : 'badge-pe'}>{signal.direction}</span>
            <span className="text-xs bg-blue-900/40 text-blue-400 border border-blue-800 px-2 py-0.5 rounded-full font-mono">
              30min
            </span>
            <span className="text-xs bg-purple-900/40 text-purple-400 border border-purple-800 px-2 py-0.5 rounded-full font-mono">
              Weekly
            </span>
          </div>
          <div className="text-xs text-brand-subtext">
            Strike {signal.strike} · Weekly expiry {signal.expiry} · Exit by{' '}
            {signal.exit_by}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-xs text-brand-subtext">Score</span>
          <span
            className={`text-sm font-mono font-medium px-2 py-0.5 rounded ${
              signal.confidence_score >= 80
                ? 'bg-green-900/40 text-green-400'
                : signal.confidence_score >= 65
                  ? 'bg-yellow-900/40 text-yellow-400'
                  : 'bg-brand-surface text-brand-subtext'
            }`}
          >
            {signal.confidence_score}
          </span>
        </div>
      </div>

      {/* Exit warning */}
      <div className="bg-orange-900/20 border border-orange-800/40 rounded-lg px-3 py-2 text-xs text-orange-400">
        ⚠️ Intraday trade — must exit all positions by 3:00 PM IST
      </div>

      {/* Price strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {[
          {
            label: 'Entry',
            value: fmt(signal.entry_premium),
            sub: 'Buy now',
            color: 'text-brand-text',
          },
          {
            label: 'Stop loss',
            value: fmt(signal.sl_premium),
            sub: `${slPct}% loss`,
            color: 'text-red-400',
          },
          {
            label: 'T2 target',
            value: fmt(signal.t2_premium),
            sub: `+${t2Pct}% gain`,
            color: 'text-green-400',
          },
          {
            label: 'VWAP',
            value: signal.vwap ? `₹${signal.vwap.toFixed(0)}` : '—',
            sub:
              signal.current_price && signal.vwap
                ? signal.current_price > signal.vwap
                  ? 'Price above'
                  : 'Price below'
                : '',
            color: isCE ? 'text-green-400' : 'text-red-400',
          },
        ].map(({ label, value, sub, color }) => (
          <div key={label} className="metric-card">
            <div className="text-xs text-brand-subtext mb-1">{label}</div>
            <div className={`font-mono font-medium text-sm ${color}`}>{value}</div>
            <div className="text-xs text-brand-muted mt-0.5">{sub}</div>
          </div>
        ))}
      </div>

      {/* Profit ladder */}
      <div>
        <div className="text-xs text-brand-subtext font-medium mb-2 uppercase tracking-wider">
          Intraday profit ladder
        </div>
        <div className="bg-brand-surface rounded-lg px-3">
          {[
            {
              dot: 'bg-red-500',
              label: 'SL',
              price: fmt(signal.sl_premium),
              desc: `${slPct}% · exit 100%`,
              action: 'Hard stop — exit all',
              actionColor: 'text-red-400',
            },
            {
              dot: 'bg-blue-400',
              label: 'Entry',
              price: fmt(signal.entry_premium),
              desc: 'Enter now',
              action: 'Full position',
              actionColor: 'text-blue-400',
            },
            {
              dot: 'bg-yellow-400',
              label: 'T1',
              price: fmt(signal.t1_premium),
              desc: `+${t1Pct}% · book 40%`,
              action: 'Sell 40% · move SL to entry',
              actionColor: 'text-yellow-400',
            },
            {
              dot: 'bg-green-400',
              label: 'T2',
              price: fmt(signal.t2_premium),
              desc: `+${t2Pct}% · book 60%`,
              action: 'Exit all · trade complete',
              actionColor: 'text-green-400',
            },
          ].map(({ dot, label, price, desc, action, actionColor }) => (
            <div
              key={label}
              className="flex items-center gap-3 py-2 border-b border-brand-border last:border-0"
            >
              <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${dot}`} />
              <span className="text-brand-subtext text-xs w-10 flex-shrink-0">{label}</span>
              <div className="flex-1 h-px bg-brand-border" />
              <div className="text-right min-w-[160px]">
                <div className="font-mono text-sm font-medium text-brand-text">{price}</div>
                <div className="text-xs text-brand-subtext">{desc}</div>
                <div className={`text-xs font-medium ${actionColor}`}>{action}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Indicator tags */}
      <div className="flex flex-wrap gap-1.5">
        {signal.rationale.map((r, i) => (
          <span
            key={i}
            className="text-xs px-2 py-0.5 rounded bg-brand-surface border border-brand-border text-brand-subtext"
          >
            {r}
          </span>
        ))}
        {signal.rsi != null && (
          <span className="text-xs px-2 py-0.5 rounded bg-brand-surface border border-brand-border text-brand-subtext">
            RSI {signal.rsi}
          </span>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-brand-border">
        <span className="text-xs text-brand-subtext">
          Weekly expiry · {signal.expiry} · Scanned{' '}
          {new Date(signal.scan_time).toLocaleTimeString('en-IN', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
        {onLogTrade && (
          <button onClick={() => onLogTrade(signal)} className="btn-primary text-xs">
            Log trade →
          </button>
        )}
      </div>
    </div>
  )
}
