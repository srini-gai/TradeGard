import { useState } from 'react'
import type { Trade } from '../types'
import { bookLevel } from '../services/api'

interface Props {
  trade: Trade
  onUpdated: () => void
}

const statusBadge: Record<string, string> = {
  OPEN: 'bg-blue-900/40 text-blue-400',
  PARTIAL: 'bg-yellow-900/40 text-yellow-400',
  CLOSED: 'bg-green-900/40 text-green-400',
  SL_HIT: 'bg-red-900/40 text-red-400',
}

export default function TradeRow({ trade, onUpdated }: Props) {
  const [booking, setBooking] = useState(false)
  const [exitPremium, setExitPremium] = useState('')

  const canBook = trade.status === 'OPEN' || trade.status === 'PARTIAL'
  const bookedLevels = trade.bookings.map((b) => b.level)
  const nextLevel = (['T1', 'T2', 'T3'] as const).find(
    (l) => !bookedLevels.includes(l),
  )

  const handleBook = async (level: string) => {
    const premium = parseFloat(exitPremium)
    if (!premium || Number.isNaN(premium)) return
    setBooking(true)
    try {
      await bookLevel(trade.id, level, premium)
      onUpdated()
      setExitPremium('')
    } catch (e) {
      console.error('Booking failed', e)
    } finally {
      setBooking(false)
    }
  }

  const handleSL = async () => {
    setBooking(true)
    try {
      await bookLevel(trade.id, 'SL', trade.sl_premium)
      onUpdated()
    } finally {
      setBooking(false)
    }
  }

  const pnlColor =
    trade.total_pnl === null
      ? 'text-brand-subtext'
      : trade.total_pnl >= 0
        ? 'text-green-400'
        : 'text-red-400'

  return (
    <div className="bg-brand-surface border border-brand-border rounded-lg p-3 sm:p-4 flex flex-col gap-3">
      {/* Header — wraps on narrow screens */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5 flex-wrap min-w-0">
          <span className="font-mono font-medium text-sm text-brand-text">
            {trade.symbol}
          </span>
          <span className={trade.direction === 'CE' ? 'badge-ce' : 'badge-pe'}>
            {trade.direction}
          </span>
          <span className="text-xs text-brand-subtext font-mono">
            ₹{trade.strike}
          </span>
          <span className="text-xs text-brand-muted hidden sm:inline">
            · {trade.expiry}
          </span>
        </div>
        <span
          className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${statusBadge[trade.status] ?? ''}`}
        >
          {trade.status.replace('_', ' ')}
        </span>
      </div>

      {/* Expiry on its own line for mobile */}
      <div className="text-xs text-brand-muted sm:hidden">
        Expiry: {trade.expiry}
      </div>

      {/* Metrics grid — 3 cols on mobile, 5 on sm+ */}
      <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 text-xs">
        {[
          {
            label: 'Entry',
            value: `₹${trade.entry_premium}`,
            color: 'text-brand-text',
          },
          {
            label: 'SL',
            value: `₹${trade.sl_premium}`,
            color: 'text-red-400',
          },
          {
            label: 'T1',
            value: `₹${trade.t1_premium}`,
            color: bookedLevels.includes('T1')
              ? 'text-green-400 line-through'
              : 'text-yellow-400',
          },
          {
            label: 'T2',
            value: `₹${trade.t2_premium}`,
            color: bookedLevels.includes('T2')
              ? 'text-green-400 line-through'
              : 'text-yellow-400',
          },
          {
            label: 'T3',
            value: `₹${trade.t3_premium}`,
            color: bookedLevels.includes('T3')
              ? 'text-green-400 line-through'
              : 'text-brand-subtext',
          },
        ].map(({ label, value, color }) => (
          <div key={label} className="metric-card text-center">
            <div className="text-brand-muted mb-0.5">{label}</div>
            <div className={`font-mono font-medium ${color}`}>{value}</div>
          </div>
        ))}
      </div>

      {trade.total_pnl !== null && (
        <div className="text-xs text-brand-subtext">
          Total P&L:{' '}
          <span className={`font-mono font-medium ${pnlColor}`}>
            {trade.total_pnl >= 0 ? '+' : ''}₹
            {trade.total_pnl.toLocaleString('en-IN')}
          </span>
          {' · '}
          {trade.lots} lot{trade.lots > 1 ? 's' : ''} × {trade.lot_size} qty
        </div>
      )}

      {trade.bookings.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {trade.bookings.map((b) => (
            <div
              key={b.id}
              className="text-xs bg-brand-card border border-brand-border rounded px-2 py-1"
            >
              <span className="text-brand-subtext">{b.level} @ </span>
              <span className="font-mono text-brand-text">₹{b.exit_premium}</span>
              <span
                className={` ml-1 font-mono ${b.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}
              >
                ({b.pnl >= 0 ? '+' : ''}₹{b.pnl.toFixed(0)})
              </span>
            </div>
          ))}
        </div>
      )}

      {canBook && (
        <div className="flex gap-2 items-center flex-wrap">
          <input
            type="number"
            step="0.05"
            placeholder="Exit premium"
            value={exitPremium}
            onChange={(e) => setExitPremium(e.target.value)}
            className="bg-brand-card border border-brand-border rounded px-3 py-1.5 text-xs text-brand-text w-32 sm:w-36 focus:outline-none focus:border-brand-accent"
          />
          {nextLevel && (
            <button
              type="button"
              onClick={() => void handleBook(nextLevel)}
              disabled={booking || !exitPremium}
              className="btn-primary text-xs py-1.5"
            >
              Book {nextLevel}
            </button>
          )}
          <button
            type="button"
            onClick={() => void handleSL()}
            disabled={booking}
            className="text-xs px-3 py-1.5 rounded border border-red-800 text-red-400 hover:bg-red-900/20 transition-colors"
          >
            Hit SL
          </button>
        </div>
      )}
    </div>
  )
}
