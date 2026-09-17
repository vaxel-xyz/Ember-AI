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
