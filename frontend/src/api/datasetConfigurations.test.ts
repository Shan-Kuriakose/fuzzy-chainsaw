import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  listDatasetConfigurations,
  reproduceDatasetConfiguration,
  saveDatasetConfiguration,
  type DatasetConfiguration,
  type DatasetReproduction,
} from './datasetConfigurations'

const ATLAS_TEAM = 'atlas'
const SAVED_NAME = 'atlas-baseline'

const SAVED_CONFIGURATION: DatasetConfiguration = {
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
}

function respondWith(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body ?? ''), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('the dataset configurations client', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('saves a configuration into its team', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(respondWith(201, { name: SAVED_NAME, team: ATLAS_TEAM }))

    vi.stubGlobal('fetch', fetchMock)

    await expect(
      saveDatasetConfiguration(ATLAS_TEAM, {
        name: SAVED_NAME,
        count: 10,
        seed: 42,
        configuration: SAVED_CONFIGURATION.configuration,
      }),
    ).resolves.toBeUndefined()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/teams/atlas/dataset-configurations',
      expect.objectContaining({ method: 'PUT' }),
    )
  })

  it('lists the configurations saved for a team', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(respondWith(200, [SAVED_CONFIGURATION]))

    vi.stubGlobal('fetch', fetchMock)

    const listed = await listDatasetConfigurations(ATLAS_TEAM)

    expect(listed).toEqual([SAVED_CONFIGURATION])
  })

  it('reproduces a saved configuration', async () => {
    const reproduction: DatasetReproduction = {
      seed: 42,
      count: 2,
      personas: [
        { age: 30, first_name: 'Marshal', last_name: 'Rist' },
        { age: 41, first_name: 'Osborne', last_name: 'Hext' },
      ],
    }
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(respondWith(200, reproduction))

    vi.stubGlobal('fetch', fetchMock)

    await expect(
      reproduceDatasetConfiguration(ATLAS_TEAM, SAVED_NAME),
    ).resolves.toEqual(reproduction)

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/teams/atlas/dataset-configurations/atlas-baseline/reproduce',
    )
  })

  it('refuses loudly when the backend rejects the request', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>().mockResolvedValue(respondWith(409, ' Already saved ')),
    )

    await expect(
      saveDatasetConfiguration(ATLAS_TEAM, {
        name: SAVED_NAME,
        count: 10,
        seed: 42,
        configuration: SAVED_CONFIGURATION.configuration,
      }),
    ).rejects.toThrow(/409/)
  })
})
