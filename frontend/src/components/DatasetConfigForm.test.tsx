import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'

const censusStyleDefaults = {
  distributions: {
    age: [
      { low: 18, high: 29, weight: 19.9 },
      { low: 30, high: 44, weight: 19.0 },
      { low: 45, high: 59, weight: 19.2 },
      { low: 60, high: 74, weight: 16.5 },
      { low: 75, high: 85, weight: 7.4 },
    ],
    gender: { Female: 50.4, Male: 48.7, 'Non-Binary': 0.9 },
    geography: {
      'Region North': 24.0,
      'Region South': 26.0,
      'Region East': 25.0,
      'Region West': 25.0,
    },
    income: [
      { low: 20000, high: 34999, weight: 18.2 },
      { low: 35000, high: 59999, weight: 27.5 },
      { low: 60000, high: 99999, weight: 29.8 },
      { low: 100000, high: 150000, weight: 24.5 },
    ],
  },
  limits: { max_count: 10000 },
}

function stubFetch(routes) {
  const calls = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input) => {
      const url = String(input)
      calls.push(url)
      for (const [path, body] of routes) {
        if (url.includes(path)) {
          return { ok: true, status: 200, json: async () => body }
        }
      }
      return { ok: false, status: 404, json: async () => ({}) }
    })
  )
  return calls
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

it('renders every demographic weight prefilled with the built-in census-style defaults', async () => {
  const { default: DatasetConfigForm } = await vi.importActual('./DatasetConfigForm')
  stubFetch([['/api/datasets/defaults', censusStyleDefaults]])

  render(<DatasetConfigForm onSubmit={vi.fn()} />)

  for (const [label, expected] of [
    ['Age 18-29 weight', 19.9],
    ['Age 75-85 weight', 7.4],
    ['Female weight', 50.4],
    ['Non-Binary weight', 0.9],
    ['Region South weight', 26.0],
    ['Income 100000-150000 weight', 24.5],
  ]) {
    const input = await screen.findByLabelText(label)
    expect(Number(input.value)).toBe(expected)
  }
  expect(screen.getByLabelText('Batch size')).toBeInTheDocument()
  expect(screen.getByLabelText('Seed')).toBeInTheDocument()
})

it('sends edited weights, batch size and seed in the submitted configuration', async () => {
  const { default: DatasetConfigForm } = await vi.importActual('./DatasetConfigForm')
  stubFetch([['/api/datasets/defaults', censusStyleDefaults]])
  const onSubmit = vi.fn()

  render(<DatasetConfigForm onSubmit={onSubmit} />)

  fireEvent.change(await screen.findByLabelText('Age 18-29 weight'), {
    target: { value: '25' },
  })
  fireEvent.change(screen.getByLabelText('Batch size'), {
    target: { value: '50' },
  })
  fireEvent.change(screen.getByLabelText('Seed'), {
    target: { value: '99' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Generate dataset' }))

  expect(onSubmit).toHaveBeenCalledTimes(1)
  const submitted = onSubmit.mock.calls[0][0]
  expect(submitted.count).toBe(50)
  expect(submitted.seed).toBe(99)
  expect(submitted.configuration).toMatchObject({
    age_distribution: [
      { low: 18, high: 29, weight: 25 },
      { low: 30, high: 44, weight: 19.0 },
    ],
    gender_distribution: { Female: 50.4, Male: 48.7, 'Non-Binary': 0.9 },
  })
})
