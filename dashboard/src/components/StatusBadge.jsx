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
