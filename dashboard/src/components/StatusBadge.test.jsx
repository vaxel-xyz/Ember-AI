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
