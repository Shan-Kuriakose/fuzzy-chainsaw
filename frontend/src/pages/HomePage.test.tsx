import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
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
})

const censusStyleDefaults = {
  distributions: {
    age: [
      { low: 18, high: 29, weight: 19.9 },
      { low: 30, high: 44, weight: 19.0 },
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
    ],
  },
  limits: { max_count: 10000 },
}

const generatedManifest = (count) => ({
  seed: 99,
  count,
  manifest_version: 1,
  configuration: {},
  personas: Array.from({ length: count }, (_, row) => ({
    first_name: ['Ava Sample', 'Ben Sample', 'Cora Sample'][row % 3],
    last_name: 'Placeholder',
    age: 30 + row,
    gender: 'Female',
    geography: 'Region North',
    income: 45000 + row * 100,
  })),
})

function stubFetch(routes) {
  const calls = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input, init) => {
      const url = String(input)
      calls.push({ url, body: init?.body ?? null })
      for (const [path, makeBody] of routes) {
        if (url.includes(path)) {
          return { ok: true, status: 200, json: async () => makeBody() }
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

it('generating displays the dataset preview in the same session', async () => {
  const { default: HomePage } = await import('./HomePage')
  stubFetch([
    ['/api/datasets/defaults', () => censusStyleDefaults],
    ['/api/datasets/generate', () => generatedManifest(3)],
  ])

  render(<HomePage />)

  await screen.findByLabelText('Batch size')
  expect(screen.getByLabelText('Seed')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Generate dataset' }))

  expect(await screen.findByRole('table')).toBeInTheDocument()
  expect(await screen.findByText('Ava Sample')).toBeInTheDocument()
  expect(screen.getByText(/3 rows generated/i)).toBeInTheDocument()
  expect(screen.getByLabelText('Batch size')).toBeInTheDocument()
})

it('completes a full generate, preview, and export cycle unaided', async () => {
  const { default: HomePage } = await import('./HomePage')
  const calls = stubFetch([
    ['/api/datasets/defaults', () => censusStyleDefaults],
    ['/api/datasets/generate', () => generatedManifest(2)],
  ])
  const exported = []
  const originalCreateObjectURL = URL.createObjectURL
  const originalRevokeObjectURL = URL.revokeObjectURL
  URL.createObjectURL = (blob) => {
    exported.push(blob)
    return `blob:export-${exported.length}`
  }
  URL.revokeObjectURL = () => {}

  render(<HomePage />)

  await screen.findByLabelText('Batch size')
  fireEvent.change(screen.getByLabelText('Batch size'), {
    target: { value: '2' },
  })
  fireEvent.change(screen.getByLabelText('Seed'), { target: { value: '99' } })
  fireEvent.click(screen.getByRole('button', { name: 'Generate dataset' }))

  await screen.findByRole('table')
  expect(await screen.findByText('Ben Sample')).toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: 'Download CSV' }))

  const generateCall = calls.find((call) =>
    call.url.includes('/api/datasets/generate')
  )
  expect(JSON.parse(generateCall.body)).toMatchObject({
    count: 2,
    seed: 99,
  })
  expect(exported).toHaveLength(1)
  const csvText = await exported[0].text()
  expect(csvText).toContain('first_name')
  expect(csvText).toContain('Ava Sample')

  URL.createObjectURL = originalCreateObjectURL
  URL.revokeObjectURL = originalRevokeObjectURL
})

