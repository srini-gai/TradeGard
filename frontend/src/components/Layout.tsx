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
      {/* Sidebar — desktop only (md+) */}
      <aside className="hidden md:flex w-48 flex-shrink-0 border-r border-brand-border flex-col py-6 px-3 gap-1">
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

      {/* Main content — extra bottom padding on mobile to clear the tab bar */}
      <main className="flex-1 overflow-auto p-4 md:p-6 pb-24 md:pb-6">
        {/* Mobile-only top header */}
        <div className="flex md:hidden items-center justify-between mb-4">
          <div className="flex items-baseline gap-2">
            <span className="text-brand-accent font-mono font-semibold text-sm">
              TradeGuard
            </span>
            <span className="text-brand-muted text-xs">Nifty 50 Options</span>
          </div>
        </div>
        {children}
      </main>

      {/* Bottom tab bar — mobile only */}
      <nav
        className="fixed bottom-0 left-0 right-0 z-50 flex md:hidden bg-brand-surface border-t border-brand-border"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        {navItems.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex-1 flex flex-col items-center justify-center py-2.5 gap-0.5 transition-colors ${
                isActive ? 'text-brand-accent' : 'text-brand-muted'
              }`
            }
          >
            <span className="text-base leading-none">{icon}</span>
            <span className="text-[10px] leading-tight">{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
