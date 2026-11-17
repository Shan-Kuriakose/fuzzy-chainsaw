import '@testing-library/jest-dom/vitest'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import DatasetConfigurationsPage from './DatasetConfigurationsPage'
import type { DatasetConfiguration, DatasetReproduction } from '../api/datasetConfigurations'

const ATLAS_TEAM = 'atlas'
const SAVED_NAME = 'atlas-baseline'

const SAVED_LIST: DatasetConfiguration[] = [
  {
    name: SAVED_NAME,
    team: ATLAS_TEAM,
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

const REPRODUCTION: DatasetReproduction = {
  seed: 42,
  count: 2,
  personas: [
    {
      first_name: 'Marshal',
      last_name: 'Rist',
      gender: 'Female',
      age: 30,
      geography: 'Region North',
      income: 41_000,
    },
    {
      first_name: 'Osborne',
      last_name: 'Hext',
      gender: 'Male',
      age: 41,
      geography: 'Region North',
      income: 67_000,
    },
  ],
}

interface FetchEntry {
  method: string
  url: string
  body?: string
}

type Responder = (entry: FetchEntry) => Response

function respondWith(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('DatasetConfigurationsPage', () => {
  let fetchCalls: FetchEntry[]
  let respond: Responder

  beforeEach(() => {
    fetchCalls = []
    respond = () => respondWith(200, SAVED_LIST)
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: string | Request, init?: RequestInit) => {
        const method =
          init?.method ?? (typeof input === 'string' ? 'GET' : input.method)
        const url = typeof input === 'string' ? input : input.url
        const entry: FetchEntry = {
          method: String(method),
          url,
          body: init?.body as string | undefined,
        }
        fetchCalls.push(entry)
        return respond(entry)
      }),
    )
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  function typeInto(label: string, value: string): void {
    fireEvent.change(screen.getByLabelText(label), { target: { value } })
  }

  function click(labelText: string): void {
    fireEvent.click(screen.getByRole('button', { name: labelText }))
  }

  function configure(team: string, name: string): void {
    typeInto('Team', team)
    typeInto('Configuration name', name)
  }

  it('saves a configuration and lists it for the team afterwards', async () => {
    respond = (entry) =>
      entry.method === 'PUT'
        ? respondWith(201, { name: SAVED_NAME, team: ATLAS_TEAM })
        : respondWith(200, SAVED_LIST)
    render(<DatasetConfigurationsPage />)

    configure(ATLAS_TEAM, SAVED_NAME)
    click('Save configuration')

    await waitFor(() =>
      expect(
        screen.getByText(
          `Saved the configuration "${SAVED_NAME}" for team ${ATLAS_TEAM}.`,
        ),
      ).toBeInTheDocument(),
    )
    expect(
      fetchCalls.some(
        (entry) =>
          entry.method === 'PUT' &&
          entry.url === '/api/teams/atlas/dataset-configurations',
      ),
    ).toBe(true)
    expect(
      fetchCalls.some(
        (entry) =>
          entry.method === 'GET' &&
          entry.url === '/api/teams/atlas/dataset-configurations',
      ),
    ).toBe(true)
    expect(screen.getByRole('table')).toBeInTheDocument()
  })

  it('lists the configurations saved for the team', async () => {
    render(<DatasetConfigurationsPage />)

    configure(ATLAS_TEAM, '')
    click('List saved configurations')

    const listing = await screen.findByRole('table', {
      name: `Dataset configurations saved for team ${ATLAS_TEAM}`,
    })
    expect(listing).toBeInTheDocument()
    expect(
      screen.getByRole('row', { name: new RegExp(SAVED_NAME) }),
    ).toBeInTheDocument()
  })

  it('reproduces a saved configuration and shows the exact records', async () => {
    respond = (entry) =>
      entry.url.includes('/reproduce')
        ? respondWith(200, REPRODUCTION)
        : respondWith(200, SAVED_LIST)
    render(<DatasetConfigurationsPage />)

    configure(ATLAS_TEAM, '')
    click('List saved configurations')
    fireEvent.click(
      await screen.findByRole('button', { name: `Reproduce ${SAVED_NAME}` }),
    )

    expect(
      await screen.findByRole('table', {
        name: /The exact 2 records of seed 42/,
      }),
    ).toBeInTheDocument()
    expect(screen.getByText('Marshal')).toBeInTheDocument()
    expect(screen.getByText('Hext')).toBeInTheDocument()
    expect(screen.getByText(/Reproduced 2 records from/)).toBeInTheDocument()
  })

  it('does not save silently: the refusal is announced', async () => {
    respond = () => respondWith(409, ' Already saved ')
    render(<DatasetConfigurationsPage />)

    configure(ATLAS_TEAM, SAVED_NAME)
    click('Save configuration')

    await waitFor(() =>
      expect(
        screen.getByText(/The configuration was not saved: /),
      ).toBeInTheDocument(),
    )
  })

  it('announces an invalid configuration instead of sending it', async () => {
    respond = () => {
      throw new Error('no request should reach the backend')
    }
    render(<DatasetConfigurationsPage />)

    configure(ATLAS_TEAM, SAVED_NAME)
    typeInto('Genders (comma separated)', '')
    click('Save configuration')

    expect(screen.getByText(/At least one gender/)).toBeInTheDocument()
    expect(fetchCalls).toHaveLength(0)
  })

  it('announces a record count above the maximum instead of sending it', async () => {
    respond = () => {
      throw new Error('no request should reach the backend')
    }
    render(<DatasetConfigurationsPage />)

    configure(ATLAS_TEAM, SAVED_NAME)
    typeInto('Number of records', '999999999')
    click('Save configuration')

    expect(
      await screen.findByText(/not a whole number between 0 and/),
    ).toBeInTheDocument()
    expect(fetchCalls).toHaveLength(0)
  })

  it('tells the user when an override leaves the built-in reference population', () => {
    render(<DatasetConfigurationsPage />)

    typeInto('Age minimum', '30')

    expect(
      screen.getByText(/no longer reflects the built-in reference population/i),
    ).toBeInTheDocument()
  })

  it('does not tell untouched defaults they left the reference population', () => {
    render(<DatasetConfigurationsPage />)

    expect(
      screen.queryByText(/no longer reflects the built-in reference population/i),
    ).not.toBeInTheDocument()
  })

  it('announces a team name longer than the API accepts instead of sending it', async () => {
    respond = () => {
      throw new Error('no request should reach the backend')
    }
    render(<DatasetConfigurationsPage />)

    typeInto('Team', 't'.repeat(65))
    typeInto('Configuration name', SAVED_NAME)
    click('Save configuration')

    expect(screen.getByText(/longer than 64 characters/)).toBeInTheDocument()
    expect(fetchCalls).toHaveLength(0)
  })
})
