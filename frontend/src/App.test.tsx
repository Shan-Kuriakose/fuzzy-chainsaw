import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import App from './App'

describe('App', () => {
  afterEach(() => {
    cleanup()
  })

  it('shows the placeholder home page at the root', () => {
    render(<App />)

    const heading = screen.getByRole('heading', { level: 1 })

    expect(heading).toHaveTextContent('Fuzzy Chain Saw')
  })
})
