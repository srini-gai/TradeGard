import type { Signal } from '../types'

interface Props {
  signal: Signal
  onLogTrade?: (signal: Signal) => void
}

const fmt = (n: number) => `₹${n.toFixed(2)}`
const fmtDate = (d: string | null) =>
  d
    ? new Date(d).toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
      })
    : '—'

function LadderRow({
  label,
  price,
  desc,
  action,
  dotColor,
  actionColor,
}: {
  label: string
  price: string
  desc: string
  action: string
  dotColor: string
  actionColor: string
}) {
  return (
    <div className="flex items-center gap-3 py-2 border-b border-brand-border last:border-0">
      <span
        className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${dotColor}`}
      />
      <span className="text-brand-subtext text-xs w-16 flex-shrink-0">
        {label}
      </span>
      <div className="flex-1 h-px bg-brand-border" />
      <div className="text-right min-w-[160px]">
        <div className="font-mono text-sm font-medium text-brand-text">
          {price}
        </div>
        <div className="text-xs text-brand-subtext">{desc}</div>
        <div className={`text-xs font-medium ${actionColor}`}>{action}</div>
      </div>
    </div>
  )
}

export default function SignalCard({ signal, onLogTrade }: Props) {
  const isCE = signal.direction === 'CE'
  const accentColor = isCE ? 'border-l-green-500' : 'border-l-red-500'
  const scoreColor =
    signal.confidence_score >= 80
      ? 'bg-green-900/40 text-green-400'
      : signal.confidence_score >= 65
        ? 'bg-yellow-900/40 text-yellow-400'
        : 'bg-brand-surface text-brand-subtext'

  const ep = signal.entry_premium || 1
  const t1Pct = (((signal.t1_premium - ep) / ep) * 100).toFixed(0)
  const t2Pct = (((signal.t2_premium - ep) / ep) * 100).toFixed(0)
  const t3Pct = (((signal.t3_premium - ep) / ep) * 100).toFixed(0)
  const slPct = (((signal.sl_premium - ep) / ep) * 100).toFixed(0)

  const rationale = signal.rationale ?? []

  return (
    <div className={`card border-l-4 ${accentColor} flex flex-col gap-4`}>
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-lg font-semibold text-brand-text font-mono">
              {signal.symbol}
            </span>
            <span className={isCE ? 'badge-ce' : 'badge-pe'}>
              {signal.direction}
            </span>
          </div>
          <div className="text-xs text-brand-subtext">
            Strike {signal.strike} · Expiry {fmtDate(signal.expiry)} ·{' '}
            {signal.days_to_expiry ?? '—'} days left
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-brand-subtext">Score</span>
          <span
            className={`text-sm font-mono font-medium px-2 py-0.5 rounded ${scoreColor}`}
          >
            {signal.confidence_score}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {[
          {
            label: 'Entry',
            value: fmt(signal.entry_premium),
            sub: 'Buy at open',
            color: 'text-brand-text',
          },
          {
            label: 'Stop loss',
            value: fmt(signal.sl_premium),
            sub: `${slPct}% loss`,
            color: 'text-red-400',
          },
          {
            label: 'Full target',
            value: fmt(signal.t3_premium),
            sub: `+${t3Pct}% gain`,
            color: 'text-green-400',
          },
          {
            label: 'Expiry',
            value: fmtDate(signal.expiry),
            sub: `${signal.days_to_expiry ?? '—'} days`,
            color: 'text-brand-accent2',
          },
        ].map(({ label, value, sub, color }) => (
          <div key={label} className="metric-card">
            <div className="text-xs text-brand-subtext mb-1">{label}</div>
            <div className={`font-mono font-medium text-sm ${color}`}>
              {value}
            </div>
            <div className="text-xs text-brand-muted mt-0.5">{sub}</div>
          </div>
        ))}
      </div>

      <div>
        <div className="text-xs text-brand-subtext font-medium mb-2 uppercase tracking-wider">
          Profit booking ladder
        </div>
        <div className="bg-brand-surface rounded-lg px-3">
          <LadderRow
            label="SL"
            price={fmt(signal.sl_premium)}
            desc={`${slPct}% · exit 100%`}
            action="Hard stop — exit all"
            dotColor="bg-red-500"
            actionColor="text-red-400"
          />
          <LadderRow
            label="Entry"
            price={fmt(signal.entry_premium)}
            desc="9:15–9:25 AM"
            action="Enter full position"
            dotColor="bg-blue-400"
            actionColor="text-blue-400"
          />
          <LadderRow
            label="T1"
            price={fmt(signal.t1_premium)}
            desc={`+${t1Pct}% · book 30%`}
            action={`Sell 30% · SL → entry · ${fmtDate(signal.t1_date)}`}
            dotColor="bg-yellow-400"
            actionColor="text-yellow-400"
          />
          <LadderRow
            label="T2"
            price={fmt(signal.t2_premium)}
            desc={`+${t2Pct}% · book 40%`}
            action={`Sell 40% · trail SL · ${fmtDate(signal.t2_date)}`}
            dotColor="bg-green-400"
            actionColor="text-green-400"
          />
          <LadderRow
            label="T3 ✓"
            price={fmt(signal.t3_premium)}
            desc={`+${t3Pct}% · book 30%`}
            action={`Exit all · trade complete · ${fmtDate(signal.t3_date)}`}
            dotColor="bg-emerald-300"
            actionColor="text-emerald-300"
          />
        </div>
      </div>

      {rationale.length > 0 && (
        <div>
          <div className="text-xs text-brand-subtext font-medium mb-2 uppercase tracking-wider">
            Why this trade
          </div>
          <div className="flex flex-wrap gap-1.5">
            {rationale.map((r, i) => (
              <span
                key={i}
                className="text-xs px-2 py-0.5 rounded bg-brand-surface border border-brand-border text-brand-subtext"
              >
                {r}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-center justify-between pt-2 border-t border-brand-border">
        <div className="text-xs text-brand-subtext">
          Monthly expiry · {fmtDate(signal.expiry)}
        </div>
        {onLogTrade && (
          <button
            type="button"
            onClick={() => onLogTrade(signal)}
            className="btn-primary text-xs"
          >
            Log trade →
          </button>
        )}
      </div>
    </div>
  )
}
