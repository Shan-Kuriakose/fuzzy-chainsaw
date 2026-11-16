import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import { afterEach, expect, it, vi } from 'vitest'

expect.extend(toHaveNoViolations)

const censusStyleDefaults = {
  distributions: {
    age: [{ low: 18, high: 29, weight: 19.9 }],
    gender: { Female: 50.4, Male: 48.7, 'Non-Binary': 0.9 },
    geography: { 'Region North': 24.0, 'Region South': 26.0 },
    income: [{ low: 20000, high: 34999, weight: 18.2 }],
  },
  limits: { max_count: 10000 },
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

it('the configuration form has no accessibility violations', async () => {
  const { default: DatasetConfigForm } = await vi.importActual('./DatasetConfigForm')
  const loadedDefaults = Promise.resolve({
    ok: true,
    status: 200,
    json: async () => censusStyleDefaults,
  })
  vi.stubGlobal('fetch', vi.fn(() => loadedDefaults))

  const { container } = render(<DatasetConfigForm onSubmit={vi.fn()} />)

  await screen.findByLabelText('Age 18-29 weight')

  expect(await axe(container)).toHaveNoViolations()
})
