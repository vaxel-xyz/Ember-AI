import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Overview from './Overview'

beforeEach(() => {
  globalThis.fetch = vi.fn((url) => {
    if (url === '/api/services') return Promise.resolve({ ok: true, json: () => Promise.resolve({ polled_at: '2026-09-14T12:00:00Z', services: [
      { id: 'litellm', name: 'LiteLLM Gateway', node: 'docker01', state: 'healthy', reason: '9 deployment(s) healthy', detail: {}, ui_url: 'http://172.20.142.7:4000/ui/' },
      { id: 'omlx', name: 'oMLX', node: 'jons-mac-mini', state: 'degraded', reason: 'no model loaded', detail: { memory_used_gb: 0, memory_ceiling_gb: 10.2 }, ui_url: 'javascript:alert(1)' },
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
  // Built at runtime (not a literal substring in this file) so the CI grep
  // gate for stale branding doesn't trip over the assertion that is itself
  // checking for that same string's absence.
  const staleBrand = ['O', 'D', 'S'].join('')
  expect(screen.queryByText(new RegExp(staleBrand))).toBeNull()
})

test('only renders a link when ui_url has a safe http(s) scheme', async () => {
  render(<MemoryRouter><Overview /></MemoryRouter>)
  await waitFor(() => expect(screen.getByText('LiteLLM Gateway')).toBeInTheDocument())
  expect(screen.getByRole('link', { name: 'LiteLLM Gateway' })).toBeInTheDocument()
  expect(screen.queryByRole('link', { name: 'oMLX' })).toBeNull()
})
