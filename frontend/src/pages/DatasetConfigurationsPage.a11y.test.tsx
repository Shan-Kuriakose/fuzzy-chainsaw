import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { DatasetConfiguration } from '../api/datasetConfigurations'

expect.extend(toHaveNoViolations)

const LOADED_LIST: DatasetConfiguration[] = [
  {
    name: 'atlas-baseline',
    team: 'atlas',
    seed: 42,
    count: 10,
    configuration: {
      age_range: [25, 45],
      genders: ['Female', 'Male'],
      geographies: ['Region North'],
      income_range: [30_000, 90_000],
    },
    createdAt: '2026-11-16T10:00:00Z',
  },
]

describe('DatasetConfigurationsPage', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('has no accessibility violations, with the list loaded', async () => {
    vi.stubGlobal('fetch', () =>
      Promise.resolve(
        new Response(JSON.stringify(LOADED_LIST), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    const { default: DatasetConfigurationsPage } = await vi.importActual(
      './DatasetConfigurationsPage',
    )

    const { container, getByRole } = render(<DatasetConfigurationsPage />)

    fireEvent.click(getByRole('button', { name: 'List saved configurations' }))
    expect(
      await screen.findByRole('table', {
        name: /Dataset configurations saved for team/,
      }),
    ).toBeInTheDocument()

    expect(await axe(container)).toHaveNoViolations()
  })

  it('keeps the reference-population override notice accessible', async () => {
    vi.stubGlobal('fetch', () =>
      Promise.resolve(
        new Response(JSON.stringify(LOADED_LIST), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    const { default: DatasetConfigurationsPage } = await vi.importActual(
      './DatasetConfigurationsPage',
    )

    const { container, getByLabelText } = render(<DatasetConfigurationsPage />)

    fireEvent.change(getByLabelText('Age minimum'), { target: { value: '30' } })

    expect(
      screen.getByText(/no longer reflects the built-in reference population/i),
    ).toBeInTheDocument()
    expect(await axe(container)).toHaveNoViolations()
  })
})
