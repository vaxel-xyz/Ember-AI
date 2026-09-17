### Task 7: Dashboard — strip to shell, Ember pages, branding

**Files:**
- Delete: `dashboard/src/pages/*` (all), `dashboard/src/components/*` except `Sidebar.jsx`, `dashboard/src/hooks/*`, `dashboard/src/plugins/`, `dashboard/src/lib/templates.js`, `dashboard/src/utils/`, `dashboard/public/ods-logo.png`, `dashboard/README.md`
- Modify: `dashboard/index.html`, `dashboard/package.json` (name/description only), `dashboard/src/App.jsx`, `dashboard/src/components/Sidebar.jsx`, `dashboard/nginx.conf`, `dashboard/entrypoint.sh`, `dashboard/Dockerfile`
- Create: `dashboard/src/hooks/useEmberApi.js`, `dashboard/src/components/StatusBadge.jsx`, `dashboard/src/pages/{Overview,Models,Providers,Settings}.jsx`, `dashboard/src/pages/Overview.test.jsx`, `dashboard/src/components/StatusBadge.test.jsx`, `dashboard/public/ember-logo.svg`

**Interfaces:**
- Consumes ember-api JSON from Task 6 via same-origin `/api/*` (nginx injects `Authorization: Bearer ${EMBER_API_KEY}`).
- Produces: `useEmberApi(path, {intervalMs}) -> {data, error, loading, refresh}`; `<StatusBadge state reason />`.

- [ ] **Step 1: Remove ODS UI**

```bash
cd dashboard
git rm -r -q src/pages src/plugins src/utils src/lib/templates.js src/hooks README.md public/ods-logo.png
git rm -q $(ls src/components/*.jsx | grep -v Sidebar.jsx) 
git rm -r -q src/components/__tests__ src/components/model-library src/components/settings
mkdir -p src/pages src/hooks
```

Keep: `src/main.jsx`, `src/App.jsx`, `src/index.css`, `src/contexts/ThemeContext.jsx`, `src/lib/serviceUrls.js` (+test), `src/test/`, `src/components/Sidebar.jsx`, configs, `nginx.conf`, `entrypoint.sh`, `Dockerfile`, `.dockerignore`, `eslint.config.js`.

- [ ] **Step 2: Failing tests**

`dashboard/src/components/StatusBadge.test.jsx`:

```jsx
import { render, screen } from '@testing-library/react'
import StatusBadge from './StatusBadge'

test('renders state label and reason', () => {
  render(<StatusBadge state="degraded" reason="no model loaded" />)
  expect(screen.getByText('Degraded')).toBeInTheDocument()
  expect(screen.getByTitle('no model loaded')).toBeInTheDocument()
})

test('unknown state falls back to Unknown', () => {
  render(<StatusBadge state="weird" />)
  expect(screen.getByText('Unknown')).toBeInTheDocument()
})
```

`dashboard/src/pages/Overview.test.jsx`:

```jsx
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Overview from './Overview'

beforeEach(() => {
  globalThis.fetch = vi.fn((url) => {
    if (url === '/api/services') return Promise.resolve({ ok: true, json: () => Promise.resolve({ polled_at: '2026-09-14T12:00:00Z', services: [
      { id: 'litellm', name: 'LiteLLM Gateway', node: 'docker01', state: 'healthy', reason: '9 deployment(s) healthy', detail: {} },
      { id: 'omlx', name: 'oMLX', node: 'jons-mac-mini', state: 'degraded', reason: 'no model loaded', detail: { memory_used_gb: 0, memory_ceiling_gb: 10.2 } },
    ] }) })
    if (url === '/api/capabilities') return Promise.resolve({ ok: true, json: () => Promise.resolve({ capabilities: { stt: { provider: 'omlx', state: 'degraded', model: 'parakeet-tdt-0.6b-v3' } } }) })
    return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) })
  })
})

test('groups services by node and shows capabilities', async () => {
  render(<MemoryRouter><Overview /></MemoryRouter>)
  await waitFor(() => expect(screen.getByText('LiteLLM Gateway')).toBeInTheDocument())
  expect(screen.getByText('Control plane · docker01')).toBeInTheDocument()
  expect(screen.getByText('Inference node · jons-mac-mini')).toBeInTheDocument()
  expect(screen.getByText('parakeet-tdt-0.6b-v3')).toBeInTheDocument()
  expect(screen.queryByText(/ODS/)).toBeNull()
})
```

Run: `cd dashboard && npm ci && npm test` → Expected: FAIL (modules missing).

- [ ] **Step 3: Hook, badge, pages**

`dashboard/src/hooks/useEmberApi.js`:

```js
import { useCallback, useEffect, useRef, useState } from 'react'

export function useEmberApi(path, { intervalMs = 15000 } = {}) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const timer = useRef(null)

  const refresh = useCallback(async () => {
    try {
      const res = await fetch(path, { headers: { Accept: 'application/json' } })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setData(await res.json())
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [path])

  useEffect(() => {
    refresh()
    if (intervalMs > 0) timer.current = setInterval(refresh, intervalMs)
    return () => timer.current && clearInterval(timer.current)
  }, [refresh, intervalMs])

  return { data, error, loading, refresh }
}
```

`dashboard/src/components/StatusBadge.jsx`:

```jsx
const STYLES = {
  healthy: ['Healthy', 'bg-emerald-500/15 text-emerald-400 border-emerald-500/40'],
  degraded: ['Degraded', 'bg-amber-500/15 text-amber-400 border-amber-500/40'],
  starting: ['Starting', 'bg-sky-500/15 text-sky-400 border-sky-500/40'],
  'reachable-unhealthy': ['Unhealthy', 'bg-rose-500/15 text-rose-400 border-rose-500/40'],
  unreachable: ['Unreachable', 'bg-zinc-500/15 text-zinc-400 border-zinc-500/40'],
}

export default function StatusBadge({ state, reason = '' }) {
  const [label, cls] = STYLES[state] || ['Unknown', 'bg-zinc-500/15 text-zinc-400 border-zinc-500/40']
  return (
    <span title={reason} className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${cls}`}>
      {label}
    </span>
  )
}
```

`dashboard/src/pages/Overview.jsx`:

```jsx
import StatusBadge from '../components/StatusBadge'
import { useEmberApi } from '../hooks/useEmberApi'

const NODES = [
  { id: 'docker01', title: 'Control plane · docker01' },
  { id: 'jons-mac-mini', title: 'Inference node · jons-mac-mini' },
]

function ServiceRow({ s }) {
  const mem = s.detail?.memory_ceiling_gb ? `${s.detail.memory_used_gb} / ${s.detail.memory_ceiling_gb} GB` : null
  return (
    <div className="flex items-center justify-between rounded-lg border border-theme-border bg-theme-card px-4 py-3">
      <div>
        <div className="font-medium text-theme-text">{s.ui_url ? <a href={s.ui_url} target="_blank" rel="noreferrer" className="hover:underline">{s.name}</a> : s.name}</div>
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
          {services.filter((s) => s.node === n.id).map((s) => <ServiceRow key={s.id} s={s} />)}
        </section>
      ))}
      <section className="space-y-2">
        <h2 className="text-sm uppercase tracking-wide text-theme-text-secondary">Capabilities</h2>
        <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
          {Object.entries(caps.data?.capabilities || {}).map(([cap, c]) => (
            <div key={cap} className="rounded-lg border border-theme-border bg-theme-card px-4 py-3">
              <div className="flex items-center justify-between"><span className="font-medium uppercase text-theme-text">{cap}</span><StatusBadge state={c.state} /></div>
              <div className="text-xs text-theme-text-muted">{c.model} · {c.provider}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
```

`dashboard/src/pages/Models.jsx`:

```jsx
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
```

`dashboard/src/pages/Providers.jsx`:

```jsx
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
```

`dashboard/src/pages/Settings.jsx`:

```jsx
import { useTheme } from '../contexts/ThemeContext'
import { useEmberApi } from '../hooks/useEmberApi'

export default function Settings() {
  const { theme, setTheme } = useTheme()
  const { data, refresh } = useEmberApi('/api/config/validate', { intervalMs: 0 })
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-theme-text">Settings</h1>
      <section className="space-y-2">
        <h2 className="text-sm uppercase tracking-wide text-theme-text-secondary">Theme</h2>
        <select value={theme} onChange={(e) => setTheme(e.target.value)} className="rounded border border-theme-border bg-theme-card px-2 py-1 text-theme-text">
          <option value="dark">Dark</option><option value="light">Light</option>
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
```

(If `ThemeContext.jsx` exports differently — check its exports and adapt the import; keep its API.)

- [ ] **Step 4: App.jsx, Sidebar.jsx, index.html, branding**

`dashboard/src/App.jsx`:

```jsx
import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Overview from './pages/Overview'
import Models from './pages/Models'
import Providers from './pages/Providers'
import Settings from './pages/Settings'

export default function App() {
  return (
    <div className="flex min-h-screen bg-theme-bg">
      <Sidebar />
      <main className="flex-1 p-6 md:p-10">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/models" element={<Models />} />
          <Route path="/providers" element={<Providers />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}
```

`dashboard/src/components/Sidebar.jsx` — rewrite to a minimal nav (keep theme classes from the donor):

```jsx
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
```

`dashboard/index.html`: set `<title>Ember AI</title>`, `apple-mobile-web-app-title` → `Ember AI`, replace loading text `ODS` → `Ember AI`, favicon → `/ember-logo.svg`. Remove any `manifest`/PWA references to ODS assets.

`dashboard/public/ember-logo.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><path d="M16 2c3 6 9 8 9 16a9 9 0 1 1-18 0c0-4 2-6 4-9 0 4 2 6 5 7-2-4-1-9 0-14z" fill="#f97316"/></svg>
```

`dashboard/package.json`: `"name": "ember-dashboard"`, `"description": "Ember AI — infrastructure dashboard"`.

`dashboard/src/main.jsx`: ensure it wraps `<BrowserRouter>` and `<ThemeProvider>` around `<App />` (keep donor structure; remove any ODS splash/service-worker registration).

- [ ] **Step 5: nginx.conf, entrypoint.sh, Dockerfile**

`dashboard/nginx.conf`:

```nginx
server {
    listen 3001;
    listen [::]:3001;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;
    resolver 127.0.0.11 valid=10s ipv6=off;
    set $ember_api ember-api:3002;
    gzip on;
    gzip_types text/plain text/css application/json application/javascript image/svg+xml;

    location / { try_files $uri $uri/ /index.html; }

    location /api/ {
        proxy_pass http://$ember_api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Authorization "Bearer ${EMBER_API_KEY}";
        proxy_read_timeout 60s;
    }

    location ~* \.(js|css|svg|png|woff2)$ { expires 1y; add_header Cache-Control "public, immutable"; }
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Content-Security-Policy "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self';" always;
}
```

`dashboard/entrypoint.sh`:

```sh
#!/bin/sh
set -eu
CONF=/etc/nginx/conf.d/default.conf
if [ -z "${EMBER_API_KEY:-}" ]; then echo "[ember-dashboard] EMBER_API_KEY not set; /api calls will 401" >&2; fi
ESCAPED=$(printf '%s\n' "${EMBER_API_KEY:-}" | sed 's/[&/\]/\\&/g')
sed -i "s|Bearer \${EMBER_API_KEY}|Bearer ${ESCAPED}|g" "$CONF"
exec nginx -g 'daemon off;'
```

`dashboard/Dockerfile`: keep donor two-stage build; change user/group names `odser` → `ember`; ensure `COPY nginx.conf /etc/nginx/conf.d/default.conf`, `COPY entrypoint.sh /entrypoint.sh`, `ENTRYPOINT ["/entrypoint.sh"]`, `EXPOSE 3001`, healthcheck `wget -qO- http://127.0.0.1:3001/ >/dev/null || exit 1`.

- [ ] **Step 6: Lint, test, build, grep for ODS strings, commit**

Run: `cd dashboard && npm run lint && npm test && npm run build && ! grep -rn "ODS" src index.html` → Expected: lint clean, tests pass, build ok, grep finds nothing.

```bash
git add -A dashboard
git commit -m "feat(dashboard): Ember AI shell with Overview, Models, Providers, Settings"
```

---

