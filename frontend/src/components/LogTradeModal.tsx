import { useState } from 'react'
import type { Signal, TradeCreate } from '../types'
import { logTrade } from '../services/api'

function toDateInputValue(expiry: string | undefined): string {
  if (!expiry) return ''
  return expiry.slice(0, 10)
}

function formatApiDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail))
    return detail.map((x) => (typeof x === 'object' ? JSON.stringify(x) : String(x))).join(', ')
  return 'Failed to log trade — check if trading window is open'
}

interface Props {
  signal?: Signal
  onClose: () => void
  onLogged: () => void
}

export default function LogTradeModal({ signal, onClose, onLogged }: Props) {
  const [form, setForm] = useState<Partial<TradeCreate>>({
    symbol: signal?.symbol ?? '',
    direction: signal?.direction ?? 'CE',
    strike: signal?.strike ?? 0,
    expiry: toDateInputValue(signal?.expiry),
    entry_premium: signal?.entry_premium ?? 0,
    sl_premium: signal?.sl_premium ?? 0,
    t1_premium: signal?.t1_premium ?? 0,
    t2_premium: signal?.t2_premium ?? 0,
    t3_premium: signal?.t3_premium ?? 0,
    lots: 1,
    lot_size: 0,
    notes: '',
    signal_id: signal?.id,
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const set = (k: keyof TradeCreate, v: string | number) =>
    setForm((f) => ({ ...f, [k]: v }))

  const handleSubmit = async () => {
    setError(null)
    if (!form.symbol || !form.expiry || form.entry_premium == null) {
      setError('Fill in all required fields')
      return
    }
    setSubmitting(true)
    try {
      const payload: TradeCreate = {
        symbol: String(form.symbol).toUpperCase(),
        direction: (form.direction === 'PE' ? 'PE' : 'CE') as 'CE' | 'PE',
        strike: Number(form.strike ?? 0),
        expiry: String(form.expiry),
        entry_premium: Number(form.entry_premium),
        lots: Number(form.lots ?? 1),
        lot_size: Number(form.lot_size ?? 0),
        sl_premium: Number(form.sl_premium ?? 0),
        t1_premium: Number(form.t1_premium ?? 0),
        t2_premium: Number(form.t2_premium ?? 0),
        t3_premium: Number(form.t3_premium ?? 0),
        notes: form.notes,
        signal_id: form.signal_id,
      }
      await logTrade(payload)
      onLogged()
      onClose()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: unknown } } })?.response
        ?.data?.detail
      setError(formatApiDetail(detail))
    } finally {
      setSubmitting(false)
    }
  }

  const inp =
    'w-full bg-brand-surface border border-brand-border rounded px-3 py-2 text-sm text-brand-text focus:outline-none focus:border-brand-accent'
  const lbl = 'text-xs text-brand-subtext mb-1'

  return (
    /* On mobile: slide up from bottom. On sm+: centered dialog. */
    <div className="fixed inset-0 bg-black/60 flex items-end sm:items-center justify-center z-50 sm:p-4">
      <div className="bg-brand-card border border-brand-border rounded-t-2xl sm:rounded-xl p-4 sm:p-6 w-full sm:max-w-lg max-h-[92vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <div className="text-sm font-medium text-brand-text">Log trade</div>
          <button
            type="button"
            onClick={onClose}
            className="text-brand-muted hover:text-brand-text text-lg p-1"
          >
            ✕
          </button>
        </div>

        {error && (
          <div className="bg-red-900/30 border border-red-800 text-red-400 text-xs rounded px-3 py-2 mb-4">
            {error}
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className={lbl}>Symbol *</div>
            <input
              className={inp}
              value={form.symbol}
              onChange={(e) => set('symbol', e.target.value.toUpperCase())}
              placeholder="RELIANCE"
            />
          </div>
          <div>
            <div className={lbl}>Direction *</div>
            <select
              className={inp}
              value={form.direction}
              onChange={(e) =>
                set('direction', e.target.value as 'CE' | 'PE')
              }
            >
              <option value="CE">CE (Call)</option>
              <option value="PE">PE (Put)</option>
            </select>
          </div>
          <div>
            <div className={lbl}>Strike *</div>
            <input
              className={inp}
              type="number"
              value={form.strike}
              onChange={(e) => set('strike', +e.target.value)}
            />
          </div>
          <div>
            <div className={lbl}>Expiry *</div>
            <input
              className={inp}
              type="date"
              value={form.expiry}
              onChange={(e) => set('expiry', e.target.value)}
            />
          </div>
          <div>
            <div className={lbl}>Entry ₹ *</div>
            <input
              className={inp}
              type="number"
              step="0.05"
              value={form.entry_premium}
              onChange={(e) => set('entry_premium', +e.target.value)}
            />
          </div>
          <div>
            <div className={lbl}>SL ₹ *</div>
            <input
              className={inp}
              type="number"
              step="0.05"
              value={form.sl_premium}
              onChange={(e) => set('sl_premium', +e.target.value)}
            />
          </div>
          <div>
            <div className={lbl}>T1 target</div>
            <input
              className={inp}
              type="number"
              step="0.05"
              value={form.t1_premium}
              onChange={(e) => set('t1_premium', +e.target.value)}
            />
          </div>
          <div>
            <div className={lbl}>T2 target</div>
            <input
              className={inp}
              type="number"
              step="0.05"
              value={form.t2_premium}
              onChange={(e) => set('t2_premium', +e.target.value)}
            />
          </div>
          <div>
            <div className={lbl}>T3 target</div>
            <input
              className={inp}
              type="number"
              step="0.05"
              value={form.t3_premium}
              onChange={(e) => set('t3_premium', +e.target.value)}
            />
          </div>
          <div>
            <div className={lbl}>Lots</div>
            <input
              className={inp}
              type="number"
              min={1}
              value={form.lots}
              onChange={(e) => set('lots', +e.target.value)}
            />
          </div>
          <div className="col-span-2">
            <div className={lbl}>Lot size (0 = auto)</div>
            <input
              className={inp}
              type="number"
              value={form.lot_size}
              onChange={(e) => set('lot_size', +e.target.value)}
            />
          </div>
          <div className="col-span-2">
            <div className={lbl}>Notes</div>
            <input
              className={inp}
              value={form.notes ?? ''}
              onChange={(e) => set('notes', e.target.value)}
              placeholder="Optional notes"
            />
          </div>
        </div>

        <div className="flex gap-3 mt-5">
          <button type="button" onClick={onClose} className="btn-ghost flex-1">
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void handleSubmit()}
            disabled={submitting}
            className="btn-primary flex-1"
          >
            {submitting ? 'Logging...' : 'Log trade'}
          </button>
        </div>
      </div>
    </div>
  )
}
