import type { Alert } from '../types'

const dotColor: Record<string, string> = {
  BUY_CE: 'bg-green-400',
  BUY_PE: 'bg-red-400',
  EXIT: 'bg-gray-400',
}

export default function AlertsFeed({ alerts }: { alerts: Alert[] }) {
  return (
    <div className="card flex flex-col gap-2">
      <div className="text-xs text-brand-subtext font-medium uppercase tracking-wider mb-1">
        TradingView alerts
      </div>
      {alerts.length === 0 ? (
        <div className="text-xs text-brand-muted py-4 text-center">
          No alerts today — set up TradingView webhooks to see signals here
        </div>
      ) : (
        alerts.slice(0, 8).map((alert) => (
          <div
            key={alert.id}
            className="flex items-start gap-2.5 p-2 bg-brand-surface rounded-lg"
          >
            <span
              className={`w-2 h-2 rounded-full mt-1 flex-shrink-0 ${dotColor[alert.action] ?? 'bg-gray-500'}`}
            />
            <div className="flex-1 min-w-0">
              <div className="text-xs text-brand-text">
                <span className="font-mono font-medium">{alert.symbol}</span>
                {' · '}
                {alert.action.replaceAll('_', ' ')}
                {alert.price != null && ` · ₹${alert.price}`}
              </div>
              <div className="text-xs text-brand-muted">
                {new Date(alert.received_at).toLocaleTimeString('en-IN', {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  )
}
