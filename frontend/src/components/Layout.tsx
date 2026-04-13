import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'

const navItems = [
  { to: '/', label: 'Dashboard', icon: '⬡' },
  { to: '/screener', label: 'Screener', icon: '◎' },
  { to: '/backtest', label: 'Backtest', icon: '◈' },
  { to: '/journal', label: 'Journal', icon: '◉' },
  { to: '/alerts', label: 'Alerts', icon: '◆' },
]

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-brand-bg flex">
      <aside className="w-48 flex-shrink-0 border-r border-brand-border flex flex-col py-6 px-3 gap-1">
        <div className="px-3 mb-6">
          <div className="text-brand-accent font-mono font-semibold text-sm">
            TradeGuard
          </div>
          <div className="text-brand-muted text-xs">Nifty 50 Options</div>
        </div>
        {navItems.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-brand-accent/10 text-brand-accent border border-brand-accent/20'
                  : 'text-brand-subtext hover:text-brand-text hover:bg-brand-surface'
              }`
            }
          >
            <span className="text-xs opacity-60">{icon}</span>
            {label}
          </NavLink>
        ))}
      </aside>

      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  )
}
