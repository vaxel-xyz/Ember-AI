import { useEmberApi } from '../hooks/useEmberApi'

export default function Models() {
  const { data, error } = useEmberApi('/api/models', { intervalMs: 30000 })
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-theme-text">Models</h1>
      {error && <p className="text-sm text-rose-400">API error: {error}</p>}
      <table className="w-full text-sm">
        <thead className="text-left text-theme-text-secondary"><tr><th className="py-2">Alias</th><th>Provider</th><th>Model</th><th>Resident</th><th>Size</th></tr></thead>
        <tbody>
          {(data?.aliases || []).map((a) => (
            <tr key={a.alias} className="border-t border-theme-border text-theme-text">
              <td className="py-2 font-mono">{a.alias}</td><td>{a.provider}</td><td className="font-mono">{a.model}</td>
              <td>{a.resident === null ? '—' : a.resident ? 'yes' : 'no'}</td><td>{a.estimated_size_gb ? `${a.estimated_size_gb} GB` : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h2 className="text-sm uppercase tracking-wide text-theme-text-secondary">oMLX models on disk</h2>
      <ul className="space-y-1 text-sm text-theme-text">
        {(data?.omlx_models || []).map((m) => <li key={m.id} className="font-mono">{m.id} · {m.loaded ? 'loaded' : 'unloaded'}{m.estimated_size_gb ? ` · ${m.estimated_size_gb} GB` : ''}</li>)}
      </ul>
    </div>
  )
}
