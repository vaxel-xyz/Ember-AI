import StatusBadge from '../components/StatusBadge'
import { useEmberApi } from '../hooks/useEmberApi'

const NODES = [
  { id: 'docker01', title: 'Control plane · docker01' },
  { id: 'jons-mac-mini', title: 'Inference node · jons-mac-mini' },
  { id: 'consumers', title: 'Consumers' },
]

const SAFE_URL_SCHEME = /^https?:\/\//i

function ServiceRow({ s }) {
  const mem = s.detail?.memory_ceiling_gb ? `${s.detail.memory_used_gb} / ${s.detail.memory_ceiling_gb} GB` : null
  const hasSafeUrl = Boolean(s.ui_url) && SAFE_URL_SCHEME.test(s.ui_url)
  return (
    <div className="flex items-center justify-between rounded-lg border border-theme-border bg-theme-card px-4 py-3">
      <div>
        <div className="font-medium text-theme-text">{hasSafeUrl ? <a href={s.ui_url} target="_blank" rel="noreferrer" className="hover:underline">{s.name}</a> : s.name}</div>
        <div className="text-xs text-theme-text-muted">{s.reason}{mem ? ` · ${mem}` : ''}{s.latency_ms ? ` · ${s.latency_ms} ms` : ''}</div>
      </div>
      <StatusBadge state={s.state} reason={s.reason} />
    </div>
  )
}

export default function Overview() {
  const { data, error } = useEmberApi('/api/services')
  const caps = useEmberApi('/api/capabilities', { intervalMs: 30000 })
  const services = data?.services || []
  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-theme-text">Ember AI</h1>
        <p className="text-sm text-theme-text-muted">Shared inference infrastructure · {data?.polled_at ? `polled ${new Date(data.polled_at).toLocaleTimeString('en-GB')}` : 'polling…'}</p>
        {error && <p className="text-sm text-rose-400">API error: {error}</p>}
      </header>
      {NODES.map((n) => (
        <section key={n.id} className="space-y-2">
          <h2 className="text-sm uppercase tracking-wide text-theme-text-secondary">{n.title}</h2>
          {services.filter((s) => (n.id === 'consumers' ? s.role === 'consumer' : s.node === n.id && s.role !== 'consumer')).map((s) => <ServiceRow key={s.id} s={s} />)}
        </section>
      ))}
      <section className="space-y-2">
        <h2 className="text-sm uppercase tracking-wide text-theme-text-secondary">Capabilities</h2>
        <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
          {Object.entries(caps.data?.capabilities || {}).map(([cap, c]) => (
            <div key={cap} className="rounded-lg border border-theme-border bg-theme-card px-4 py-3">
              <div className="flex items-center justify-between"><span className="font-medium uppercase text-theme-text">{cap}</span><StatusBadge state={c.state} /></div>
              <div className="text-xs text-theme-text-muted"><span>{c.model}</span> · {c.provider}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
