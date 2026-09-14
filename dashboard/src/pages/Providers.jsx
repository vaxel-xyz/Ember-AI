import { useEmberApi } from '../hooks/useEmberApi'

export default function Providers() {
  const { data } = useEmberApi('/api/providers', { intervalMs: 0 })
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-theme-text">Providers</h1>
      <div className="space-y-2">
        {(data?.providers || []).map((p) => (
          <div key={p.id} className="rounded-lg border border-theme-border bg-theme-card px-4 py-3 text-theme-text">
            <div className="font-medium">{p.name}</div>
            <div className="text-xs text-theme-text-muted">{p.configured ? 'configured' : 'not configured'}{p.base_url ? ` · ${p.base_url}` : ''}{p.model ? ` · ${p.model}` : ''}</div>
          </div>
        ))}
      </div>
      {data?.gateway && (
        <div className="rounded-lg border border-theme-border bg-theme-card px-4 py-3 text-sm text-theme-text">
          <div>Gateway (public): <code>{data.gateway.public_url}</code></div>
          <div>Gateway (LAN): <code>{data.gateway.internal_url}</code></div>
        </div>
      )}
    </div>
  )
}
