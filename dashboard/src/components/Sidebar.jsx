import { NavLink } from 'react-router-dom'
import { Activity, Boxes, Plug, Settings as SettingsIcon } from 'lucide-react'

const NAV = [
  { to: '/', icon: Activity, label: 'Overview' },
  { to: '/models', icon: Boxes, label: 'Models' },
  { to: '/providers', icon: Plug, label: 'Providers' },
  { to: '/settings', icon: SettingsIcon, label: 'Settings' },
]

export default function Sidebar() {
  return (
    <aside className="w-56 shrink-0 border-r border-theme-border bg-theme-sidebar p-4">
      <div className="mb-8 flex items-center gap-2 text-theme-text"><img src="/ember-logo.svg" alt="" className="h-7 w-7" /><span className="text-lg font-semibold">Ember AI</span></div>
      <nav className="space-y-1">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `flex items-center gap-2 rounded-md px-3 py-2 text-sm ${isActive ? 'bg-theme-accent-light text-theme-accent' : 'text-theme-text-secondary hover:bg-theme-surface-hover'}`}>
            <Icon className="h-4 w-4" />{label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
