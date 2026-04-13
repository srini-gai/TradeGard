interface Metric {
  label: string
  value: string
  sub?: string
  color?: string
}

export default function MetricsBar({ metrics }: { metrics: Metric[] }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {metrics.map(({ label, value, sub, color }) => (
        <div key={label} className="metric-card">
          <div className="text-xs text-brand-subtext mb-1">{label}</div>
          <div
            className={`text-xl font-mono font-medium ${color ?? 'text-brand-text'}`}
          >
            {value}
          </div>
          {sub && (
            <div className="text-xs text-brand-muted mt-0.5">{sub}</div>
          )}
        </div>
      ))}
    </div>
  )
}
