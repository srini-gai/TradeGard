import { useState, useEffect, useCallback } from 'react'
import type { Alert } from '../types'
import { getTodayAlerts, getAllAlerts, sendTestWebhook } from '../services/api'

const actionColor: Record<string, string> = {
  BUY_CE: 'bg-green-900/40 text-green-400 border-green-800',
  BUY_PE: 'bg-red-900/40 text-red-400 border-red-800',
  EXIT_CE: 'bg-gray-800 text-gray-400 border-gray-700',
  EXIT_PE: 'bg-gray-800 text-gray-400 border-gray-700',
  EXIT: 'bg-gray-800 text-gray-400 border-gray-700',
  ALERT: 'bg-blue-900/40 text-blue-400 border-blue-800',
}

function AlertCard({ alert }: { alert: Alert }) {
  const color = actionColor[alert.action] ?? 'bg-brand-surface text-brand-subtext border-brand-border'
  return (
    <div className="bg-brand-surface border border-brand-border rounded-lg p-3 flex items-start gap-3">
      <span className={`text-xs px-2 py-0.5 rounded border font-mono flex-shrink-0 ${color}`}>
        {alert.action}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-mono font-medium text-sm text-brand-text">{alert.symbol}</span>
          {alert.price != null && (
            <span className="text-xs text-brand-subtext">@ ₹{alert.price}</span>
          )}
          {alert.rsi != null && (
            <span className="text-xs text-brand-muted">RSI {alert.rsi}</span>
          )}
        </div>
        <div className="text-xs text-brand-muted mt-0.5">
          {new Date(alert.received_at).toLocaleString('en-IN', {
            timeZone: 'Asia/Kolkata',
            day: 'numeric', month: 'short',
            hour: '2-digit', minute: '2-digit',
          })} · {alert.source}
        </div>
      </div>
    </div>
  )
}

export default function AlertsPage() {
  const [todayAlerts, setTodayAlerts] = useState<Alert[]>([])
  const [allAlerts, setAllAlerts] = useState<Alert[]>([])
  const [symbolFilter, setSymbolFilter] = useState('')
  const [testSending, setTestSending] = useState(false)
  const [testResult, setTestResult] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'today' | 'all'>('today')

  const load = useCallback(async () => {
    try {
      const [todayRes, allRes] = await Promise.allSettled([
        getTodayAlerts(),
        getAllAlerts(symbolFilter || undefined),
      ])
      if (todayRes.status === 'fulfilled') setTodayAlerts(todayRes.value.alerts ?? [])
      if (allRes.status === 'fulfilled') setAllAlerts(allRes.value.alerts ?? [])
    } finally {
      setLoading(false)
    }
  }, [symbolFilter])

  useEffect(() => { void load() }, [load])

  const handleTestWebhook = async () => {
    setTestSending(true)
    setTestResult(null)
    try {
      const res = await sendTestWebhook({
        symbol: 'TEST',
        action: 'ALERT',
        price: 1234.5,
        rsi: 55.0,
        timestamp: new Date().toISOString(),
      }) as { alert_id: number }
      setTestResult(`✓ Alert #${res.alert_id} saved — webhook is working`)
      void load()
    } catch {
      setTestResult('✗ Webhook test failed — is backend running?')
    } finally {
      setTestSending(false)
    }
  }

  const displayed = tab === 'today' ? todayAlerts : allAlerts

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-brand-text">TradingView Alerts</h1>
          <p className="text-xs text-brand-subtext mt-0.5">
            Webhook: POST /webhook/tradingview
          </p>
        </div>
        <button onClick={() => void handleTestWebhook()} disabled={testSending} className="btn-ghost text-xs">
          {testSending ? 'Sending...' : '⚡ Test webhook'}
        </button>
      </div>

      {/* Test result */}
      {testResult && (
        <div className={`text-xs px-3 py-2 rounded border ${
          testResult.startsWith('✓')
            ? 'bg-green-900/20 border-green-800 text-green-400'
            : 'bg-red-900/20 border-red-800 text-red-400'
        }`}>
          {testResult}
        </div>
      )}

      {/* ngrok setup info */}
      <div className="card border-l-4 border-l-brand-accent2">
        <div className="text-xs font-medium text-brand-text mb-2">TradingView webhook setup</div>
        <div className="text-xs text-brand-subtext space-y-1">
          <div>1. Install ngrok → run: <code className="font-mono bg-brand-surface px-1 rounded">ngrok http 8000</code></div>
          <div>2. Copy the ngrok URL e.g. <code className="font-mono bg-brand-surface px-1 rounded">https://abc123.ngrok.io</code></div>
          <div>3. In TradingView alert → Webhook URL: <code className="font-mono bg-brand-surface px-1 rounded">https://abc123.ngrok.io/webhook/tradingview</code></div>
          <div>4. Alert message (JSON):</div>
          <pre className="bg-brand-surface rounded p-2 text-xs font-mono mt-1 overflow-x-auto">{`{
  "symbol": "{{ticker}}",
  "action": "BUY_CE",
  "price": {{close}},
  "rsi": 0,
  "timestamp": "{{time}}"
}`}</pre>
        </div>
      </div>

      {/* Tabs + filter */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex gap-1">
          {(['today', 'all'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`text-xs px-3 py-1.5 rounded-lg transition-colors capitalize ${
                tab === t
                  ? 'bg-brand-accent/20 text-brand-accent border border-brand-accent/30'
                  : 'text-brand-subtext hover:text-brand-text hover:bg-brand-surface'
              }`}
            >
              {t === 'today' ? `Today (${todayAlerts.length})` : `All (${allAlerts.length})`}
            </button>
          ))}
        </div>
        {tab === 'all' && (
          <input
            type="text"
            placeholder="Filter by symbol..."
            value={symbolFilter}
            onChange={e => setSymbolFilter(e.target.value.toUpperCase())}
            className="bg-brand-surface border border-brand-border rounded px-3 py-1.5 text-xs text-brand-text w-36 focus:outline-none focus:border-brand-accent"
          />
        )}
        <button onClick={() => void load()} className="text-xs text-brand-muted hover:text-brand-subtext ml-auto">
          ↻ Refresh
        </button>
      </div>

      {/* Alerts list */}
      {loading ? (
        <div className="text-xs text-brand-muted text-center py-8">Loading alerts...</div>
      ) : displayed.length === 0 ? (
        <div className="card text-center py-10">
          <div className="text-brand-subtext text-sm mb-2">
            {tab === 'today' ? 'No alerts today' : 'No alerts yet'}
          </div>
          <div className="text-xs text-brand-muted">
            Set up TradingView webhooks or click &quot;Test webhook&quot; above
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {displayed.map(a => <AlertCard key={a.id} alert={a} />)}
        </div>
      )}
    </div>
  )
}
