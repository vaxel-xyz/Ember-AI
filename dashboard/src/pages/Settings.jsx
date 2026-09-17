import { useTheme } from '../contexts/ThemeContext'
import { useEmberApi } from '../hooks/useEmberApi'

export default function Settings() {
  const { theme, setTheme, themes, labels } = useTheme()
  const { data, refresh } = useEmberApi('/api/config/validate', { intervalMs: 0 })
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-theme-text">Settings</h1>
      <section className="space-y-2">
        <h2 className="text-sm uppercase tracking-wide text-theme-text-secondary">Theme</h2>
        <select value={theme} onChange={(e) => setTheme(e.target.value)} className="rounded border border-theme-border bg-theme-card px-2 py-1 text-theme-text">
          {themes.map((t) => <option key={t} value={t}>{labels[t]}</option>)}
        </select>
      </section>
      <section className="space-y-2">
        <div className="flex items-center justify-between"><h2 className="text-sm uppercase tracking-wide text-theme-text-secondary">Configuration checks</h2>
          <button onClick={refresh} className="text-xs text-theme-accent hover:underline">Re-run</button></div>
        <ul className="space-y-1 text-sm">
          {(data?.checks || []).map((c) => <li key={c.name} className={c.ok ? 'text-emerald-400' : 'text-rose-400'}>{c.ok ? '✓' : '✗'} {c.name} — {c.message}</li>)}
        </ul>
      </section>
    </div>
  )
}
