import type { BacktestSummary } from '../types'

export default function BacktestSummaryPanel({
  summary,
  onRunBacktest,
  running,
}: {
  summary: BacktestSummary | null
  onRunBacktest: () => void
  running: boolean
}) {
  const best = summary?.best_trade_pnl ?? 0
  const worst = summary?.worst_trade_pnl ?? 0

  return (
    <div className="card flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="text-xs text-brand-subtext font-medium uppercase tracking-wider">
          Backtest — last 3 months
        </div>
        <button
          type="button"
          onClick={onRunBacktest}
          disabled={running}
          className="btn-ghost text-xs"
        >
          {running ? 'Running...' : 'Run backtest →'}
        </button>
      </div>

      {!summary ? (
        <div className="text-xs text-brand-muted text-center py-4">
          No backtest run yet. Click &quot;Run backtest&quot; to analyse 3 months
          of signals.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2">
            {[
              {
                label: 'Win rate',
                value: `${summary.win_rate}%`,
                color:
                  summary.win_rate >= 50
                    ? 'text-green-400'
                    : 'text-yellow-400',
              },
              {
                label: 'Avg P&L',
                value: `${summary.avg_pnl > 0 ? '+' : ''}${summary.avg_pnl}%`,
                color:
                  summary.avg_pnl >= 0 ? 'text-green-400' : 'text-red-400',
              },
              {
                label: 'Best trade',
                value: `+${best}%`,
                color: 'text-green-400',
              },
              {
                label: 'Worst trade',
                value: `${worst}%`,
                color: 'text-red-400',
              },
            ].map(({ label, value, color }) => (
              <div key={label} className="metric-card">
                <div className="text-xs text-brand-subtext mb-1">{label}</div>
                <div className={`font-mono font-medium ${color}`}>{value}</div>
              </div>
            ))}
          </div>

          <div>
            <div className="text-xs text-brand-subtext font-medium mb-2">
              Monthly breakdown
            </div>
            <div className="flex flex-col gap-1">
              {Object.entries(summary.monthly_breakdown).map(
                ([month, stats]) => (
                  <div
                    key={month}
                    className="flex items-center justify-between text-xs py-1.5 border-b border-brand-border last:border-0 gap-2 flex-wrap"
                  >
                    <span className="text-brand-subtext">{month}</span>
                    <span className="text-brand-subtext">
                      {stats.trades} trades
                    </span>
                    <span
                      className={`font-mono ${stats.win_rate >= 50 ? 'text-green-400' : 'text-yellow-400'}`}
                    >
                      {stats.win_rate}% wins
                    </span>
                    <span
                      className={`font-mono ${stats.avg_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}
                    >
                      {stats.avg_pnl > 0 ? '+' : ''}
                      {stats.avg_pnl}%
                    </span>
                  </div>
                ),
              )}
            </div>
          </div>

          <div className="text-xs text-brand-muted">
            Period: {summary.period_start} → {summary.period_end} ·{' '}
            {summary.total_signals} signals
            {summary.max_drawdown != null && (
              <> · Max DD {summary.max_drawdown}%</>
            )}
          </div>
        </>
      )}
    </div>
  )
}
