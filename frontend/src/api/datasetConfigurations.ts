export interface DatasetConfiguration {
  name: string
  team: string
  seed: number
  count: number
  configuration: DatasetConfigurationBoundaries
  createdAt: string
}

export interface DatasetConfigurationBoundaries {
  age_range: [number, number]
  genders: string[]
  geographies: string[]
  income_range: [number, number]
}

export interface DatasetRecord {
  [attribute: string]: string | number
}

export interface DatasetReproduction {
  seed: number
  count: number
  personas: DatasetRecord[]
}

export interface SaveDatasetConfigurationPayload {
  name: string
  count: number
  seed: number
  configuration: DatasetConfigurationBoundaries
}

// The bounds the API contract declares; mirrors the storage columns the
// backend refuses a request beyond, so the form refuses them before
// sending instead of delivering an unexplained response.
export const MAXIMUM_DATASET_RECORDS = 10_000
export const MAXIMUM_SEED = 2_147_483_647
export const MAXIMUM_TEAM_LENGTH = 64
export const MAXIMUM_NAME_LENGTH = 255

async function assertSucceeded(response: Response): Promise<Response> {
  if (!response.ok) {
    throw new Error(
      `The dataset configuration request failed: ${response.status} ${await response.text()}`,
    )
  }
  return response
}

export async function saveDatasetConfiguration(
  team: string,
  payload: SaveDatasetConfigurationPayload,
): Promise<void> {
  await assertSucceeded(
    await fetch(
      `/api/teams/${encodeURIComponent(team)}/dataset-configurations`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      },
    ),
  )
}

export async function listDatasetConfigurations(
  team: string,
): Promise<DatasetConfiguration[]> {
  const response = await assertSucceeded(
    await fetch(`/api/teams/${encodeURIComponent(team)}/dataset-configurations`),
  )
  return response.json() as Promise<DatasetConfiguration[]>
}

export async function reproduceDatasetConfiguration(
  team: string,
  name: string,
): Promise<DatasetReproduction> {
  const response = await assertSucceeded(
    await fetch(
      `/api/teams/${encodeURIComponent(team)}/dataset-configurations/${encodeURIComponent(name)}/reproduce`,
    ),
  )
  return response.json() as Promise<DatasetReproduction>
}
