import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import { afterEach, describe, expect, it, vi } from 'vitest'

expect.extend(toHaveNoViolations)

describe('HomePage', () => {
  afterEach(() => {
    cleanup()
  })

  it('has no accessibility violations', async () => {
    const { default: HomePage } = await vi.importActual('./HomePage')

    const { container } = render(<HomePage />)

    expect(await axe(container)).toHaveNoViolations()
  })
})

describe('the composed configuration screen', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('has no accessibility violations in its form and preview states', async () => {
    const { default: HomePage } = await import('./HomePage')
    const defaultsOnce = Promise.resolve({
      ok: true,
      status: 200,
      json: async () => ({
        distributions: {
          age: [{ low: 18, high: 29, weight: 19.9 }],
          gender: { Female: 50.4, Male: 48.7, 'Non-Binary': 0.9 },
          geography: { 'Region North': 24.0, 'Region South': 26.0 },
          income: [{ low: 20000, high: 34999, weight: 18.2 }],
        },
        limits: { max_count: 10000 },
      }),
    })
    vi.stubGlobal('fetch', vi.fn((input) => {
      if (String(input).includes('/api/datasets/generate')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            seed: 99,
            count: 1,
            manifest_version: 1,
            configuration: {},
            personas: [
              {
                first_name: 'Ava Sample',
                last_name: 'Placeholder',
                age: 34,
                gender: 'Female',
                geography: 'Region North',
                income: 45000,
              },
            ],
          }),
        })
      }
      return defaultsOnce
    }))

    const { container } = render(<HomePage />)

    await screen.findByLabelText('Batch size')
    expect(await axe(container)).toHaveNoViolations()

    fireEvent.click(screen.getByRole('button', { name: 'Generate dataset' }))
    await screen.findByRole('table')
    expect(await axe(container)).toHaveNoViolations()
  })
})
