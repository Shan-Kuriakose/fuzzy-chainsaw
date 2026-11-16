import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

describe('HomePage', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders the placeholder home page heading without console errors', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

    const { default: HomePage } = await vi.importActual('./HomePage')

    render(<HomePage />)

    const heading = screen.getByRole('heading', { level: 1 })

    expect(heading).toBeInTheDocument()
    expect(heading.textContent).toContain('Fuzzy Chain Saw')
    expect(consoleError).not.toHaveBeenCalled()
  })

  it('states the page task in exactly one heading', async () => {
    const { default: HomePage } = await vi.importActual('./HomePage')

    render(<HomePage />)

    const headings = screen.getAllByRole('heading')

    expect(headings).toHaveLength(1)
    expect(headings[0].tagName).toBe('H1')
  })
})
