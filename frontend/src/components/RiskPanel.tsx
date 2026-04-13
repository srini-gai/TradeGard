import { useState, useEffect } from 'react'
import { getRiskStatus } from '../services/api'
import type { RiskStatus } from '../types'

function ProgressBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = Math.min((value / max) * 100, 100)
  return (
    <div className="w-20 h-1.5 bg-brand-surface rounded-full overflow-hidden">
      <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
    </div>
  )
}

export default function RiskPanel({ winRate }: { winRate?: number }) {
  const [risk, setRisk] = useState<RiskStatus | null>(null)

  useEffect(() => {
    getRiskStatus().then(setRisk).catch(console.error)
    const interval = setInterval(() => {
      getRiskStatus().then(setRisk).catch(console.error)
    }, 60_000)
    return () => clearInterval(interval)
  }, [])

  const rows = risk
    ? [
        {
          label: 'Daily trades',
          value: `${risk.trades_today} / ${risk.max_trades}`,
          bar: <ProgressBar value={risk.trades_today} max={risk.max_trades}
                 color={risk.trades_today >= risk.max_trades ? 'bg-red-500' : 'bg-brand-accent'} />,
        },
        {
          label: 'Slots remaining',
          value: `${risk.slots_remaining}`,
          color: risk.slots_remaining === 0 ? 'text-red-400' : 'text-green-400',
        },
        {
          label: 'Trading window',
          value: risk.trading_window_open ? 'Open' : 'Closed',
          color: risk.trading_window_open ? 'text-green-400' : 'text-red-400',
        },
        {
          label: 'IST hour',
          value: `${risk.current_hour_ist}:00`,
          color: 'text-brand-subtext',
        },
        {
          label: 'Cutoff',
          value: `${risk.cutoff_hour_ist}:00 IST`,
        },
        {
          label: 'Win rate (backtest)',
          value: winRate !== undefined ? `${winRate}%` : '—',
          bar: winRate !== undefined
            ? <ProgressBar value={winRate} max={100}
                color={winRate >= 50 ? 'bg-green-500' : 'bg-yellow-500'} />
            : null,
        },
        {
          label: 'Max risk / trade',
          value: '2% capital',
        },
      ]
    : []

  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-center justify-between mb-1">
        <div className="text-xs text-brand-subtext font-medium uppercase tracking-wider">
          Risk dashboard
        </div>
        {risk && (
          <span className={`text-xs px-2 py-0.5 rounded-full ${
            risk.trading_window_open
              ? 'bg-green-900/40 text-green-400'
              : 'bg-red-900/40 text-red-400'
          }`}>
            {risk.trading_window_open ? 'Window open' : 'Window closed'}
          </span>
        )}
      </div>

      {!risk ? (
        <div className="text-xs text-brand-muted text-center py-3">Loading...</div>
      ) : (
        rows.map(({ label, value, bar, color }) => (
          <div key={label} className="flex items-center justify-between py-1.5 border-b border-brand-border last:border-0">
            <span className="text-xs text-brand-subtext">{label}</span>
            <div className="flex items-center gap-2">
              {bar}
              <span className={`text-xs font-medium font-mono ${color ?? 'text-brand-text'}`}>{value}</span>
            </div>
          </div>
        ))
      )}

      {risk && !risk.trading_window_open && (
        <div className="text-xs text-red-400/80 bg-red-900/20 rounded px-2 py-1.5 border border-red-900/40">
          {risk.reason}
        </div>
      )}
    </div>
  )
}
