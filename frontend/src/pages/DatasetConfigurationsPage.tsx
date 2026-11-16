import { useState, type FormEvent } from 'react'

import {
  listDatasetConfigurations,
  MAXIMUM_DATASET_RECORDS,
  MAXIMUM_NAME_LENGTH,
  MAXIMUM_SEED,
  MAXIMUM_TEAM_LENGTH,
  reproduceDatasetConfiguration,
  saveDatasetConfiguration,
  type DatasetConfiguration,
  type DatasetConfigurationBoundaries,
  type DatasetReproduction,
  type SaveDatasetConfigurationPayload,
} from '../api/datasetConfigurations'

function commaSeparated(raw: string): string[] {
  return raw
    .split(',')
    .map((category) => category.trim())
    .filter((category) => category.length > 0)
}

function boundedInteger(raw: string, minimum: number, maximum: number): number {
  const parsed = Number.parseInt(raw, 10)
  const withinBounds =
    !Number.isNaN(parsed) && parsed >= minimum && parsed <= maximum
  if (!withinBounds) {
    throw new Error(
      `${raw} is not a whole number between ${minimum} and ${maximum}`,
    )
  }
  return parsed
}

// Ceilings of the attributes a configuration bounds; a member lives no
// longer than these, and synthetic incomes stay within one order of the
// configured default range.
const MAXIMUM_AGE = 130
const MAXIMUM_INCOME = 10_000_000

function configurationFrom(
  form: DatasetConfigurationForm,
): DatasetConfigurationBoundaries {
  const ageMinimum = boundedInteger(form.ageMinimum(), 1, MAXIMUM_AGE)
  const ageMaximum = boundedInteger(form.ageMaximum(), ageMinimum + 1, MAXIMUM_AGE)
  const incomeMinimum = boundedInteger(form.incomeMinimum(), 1, MAXIMUM_INCOME)
  const incomeMaximum = boundedInteger(
    form.incomeMaximum(),
    incomeMinimum + 1,
    MAXIMUM_INCOME,
  )
  const genders = commaSeparated(form.genders())
  const geographies = commaSeparated(form.geographies())
  if (genders.length === 0 || geographies.length === 0) {
    throw new Error('At least one gender and one geography is required')
  }
  return {
    age_range: [ageMinimum, ageMaximum],
    genders,
    geographies,
    income_range: [incomeMinimum, incomeMaximum],
  }
}

interface DatasetConfigurationForm {
  ageMinimum(): string
  ageMaximum(): string
  genders(): string
  geographies(): string
  incomeMinimum(): string
  incomeMaximum(): string
}

function attributeHeadersOf(reproduction: DatasetReproduction): string[] {
  const first = reproduction.personas[0]
  return first ? Object.keys(first) : []
}

export default function DatasetConfigurationsPage() {
  const [team, setTeam] = useState('')
  const [name, setName] = useState('')
  const [seed, setSeed] = useState('42')
  const [count, setCount] = useState('10')
  const [genders, setGenders] = useState('Female, Male, Non-Binary')
  const [geographies, setGeographies] = useState(
    'Region North, Region South, Region East, Region West',
  )
  const [ageMinimum, setAgeMinimum] = useState('18')
  const [ageMaximum, setAgeMaximum] = useState('85')
  const [incomeMinimum, setIncomeMinimum] = useState('20000')
  const [incomeMaximum, setIncomeMaximum] = useState('150000')
  const [saved, setSaved] = useState<DatasetConfiguration[] | null>(null)
  const [reproduction, setReproduction] = useState<DatasetReproduction | null>(
    null,
  )
  const [status, setStatus] = useState('')

  const form: DatasetConfigurationForm = {
    ageMinimum: () => ageMinimum,
    ageMaximum: () => ageMaximum,
    genders: () => genders,
    geographies: () => geographies,
    incomeMinimum: () => incomeMinimum,
    incomeMaximum: () => incomeMaximum,
  }

  async function refreshSavedList(theTeam: string): Promise<void> {
    setSaved(await listDatasetConfigurations(theTeam))
  }

  function refusalOfSaveRequest(): string | null {
    if (team.length === 0) return 'A team is required'
    if (team.length > MAXIMUM_TEAM_LENGTH) {
      return `The team name is longer than ${MAXIMUM_TEAM_LENGTH} characters, which the API does not accept`
    }
    if (name.length === 0) return 'A configuration name is required'
    if (name.length > MAXIMUM_NAME_LENGTH) {
      return `The configuration name is longer than ${MAXIMUM_NAME_LENGTH} characters, which the API does not accept`
    }
    return null
  }

  async function save(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    try {
      const refused = refusalOfSaveRequest()
      if (refused !== null) throw new Error(refused)
      const payload: SaveDatasetConfigurationPayload = {
        name,
        count: boundedInteger(count, 0, MAXIMUM_DATASET_RECORDS),
        seed: boundedInteger(seed, 0, MAXIMUM_SEED),
        configuration: configurationFrom(form),
      }
      await saveDatasetConfiguration(team, payload)
      setStatus(`Saved the configuration "${name}" for team ${team}.`)
      await refreshSavedList(team)
    } catch (failure) {
      setStatus(`The configuration was not saved: ${(failure as Error).message}`)
    }
  }

  async function showSavedList(): Promise<void> {
    try {
      setReproduction(null)
      await refreshSavedList(team)
    } catch (failure) {
      setStatus(`The saved configurations could not be listed: ${(failure as Error).message}`)
    }
  }

  async function reproduce(savingName: string): Promise<void> {
    try {
      const regenerated = await reproduceDatasetConfiguration(team, savingName)
      setReproduction(regenerated)
      setStatus(
        `Reproduced ${regenerated.count} records from "${savingName}" for the defect hand-off.`,
      )
    } catch (failure) {
      setStatus(`The dataset could not be reproduced: ${(failure as Error).message}`)
    }
  }

  return (
    <main className="mx-auto min-h-screen max-w-5xl bg-slate-50 px-6 py-8 text-slate-800">
      <h1 className="text-3xl font-semibold">Dataset configurations</h1>
      <p className="mt-2 text-slate-600">
        Save a synthetic dataset configuration with its seed, share it with
        your team, and reproduce the exact records for defect hand-off.
      </p>

      <section className="mt-6" aria-labelledby="save-configuration-heading">
        <h2 id="save-configuration-heading" className="text-xl font-semibold">
          Save a configuration
        </h2>
        <form onSubmit={save} className="mt-3 grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="configuration-team" className="block font-medium">
              Team
            </label>
            <input
              id="configuration-team"
              value={team}
              onChange={(enter) => setTeam(enter.target.value)}
              className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1"
            />
          </div>
          <div>
            <label htmlFor="configuration-name" className="block font-medium">
              Configuration name
            </label>
            <input
              id="configuration-name"
              value={name}
              onChange={(enter) => setName(enter.target.value)}
              className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1"
            />
          </div>
          <div>
            <label htmlFor="configuration-seed" className="block font-medium">
              Seed
            </label>
            <input
              id="configuration-seed"
              type="number"
              value={seed}
              onChange={(enter) => setSeed(enter.target.value)}
              className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1"
            />
          </div>
          <div>
            <label htmlFor="configuration-count" className="block font-medium">
              Number of records
            </label>
            <p
              id="configuration-count-hint"
              className="text-sm text-slate-600"
            >
              Up to {MAXIMUM_DATASET_RECORDS.toLocaleString()} records per
              configuration
            </p>
            <input
              id="configuration-count"
              type="number"
              aria-describedby="configuration-count-hint"
              value={count}
              onChange={(enter) => setCount(enter.target.value)}
              className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1"
            />
          </div>
          <div>
            <label htmlFor="configuration-genders" className="block font-medium">
              Genders (comma separated)
            </label>
            <input
              id="configuration-genders"
              value={genders}
              onChange={(enter) => setGenders(enter.target.value)}
              className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1"
            />
          </div>
          <div>
            <label htmlFor="configuration-geographies" className="block font-medium">
              Geographies (comma separated)
            </label>
            <input
              id="configuration-geographies"
              value={geographies}
              onChange={(enter) => setGeographies(enter.target.value)}
              className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1"
            />
          </div>
          <div>
            <label htmlFor="configuration-age-minimum" className="block font-medium">
              Age minimum
            </label>
            <input
              id="configuration-age-minimum"
              type="number"
              min="1"
              value={ageMinimum}
              onChange={(enter) => setAgeMinimum(enter.target.value)}
              className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1"
            />
          </div>
          <div>
            <label htmlFor="configuration-age-maximum" className="block font-medium">
              Age maximum
            </label>
            <input
              id="configuration-age-maximum"
              type="number"
              min="1"
              value={ageMaximum}
              onChange={(enter) => setAgeMaximum(enter.target.value)}
              className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1"
            />
          </div>
          <div>
            <label htmlFor="configuration-income-minimum" className="block font-medium">
              Income minimum
            </label>
            <input
              id="configuration-income-minimum"
              type="number"
              min="1"
              value={incomeMinimum}
              onChange={(enter) => setIncomeMinimum(enter.target.value)}
              className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1"
            />
          </div>
          <div>
            <label htmlFor="configuration-income-maximum" className="block font-medium">
              Income maximum
            </label>
            <input
              id="configuration-income-maximum"
              type="number"
              min="1"
              value={incomeMaximum}
              onChange={(enter) => setIncomeMaximum(enter.target.value)}
              className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1"
            />
          </div>
          <div className="sm:col-span-2">
            <button
              type="submit"
              className="rounded bg-slate-800 px-4 py-2 font-medium text-white"
            >
              Save configuration
            </button>
          </div>
        </form>
      </section>

      <section className="mt-8" aria-labelledby="saved-configurations-heading">
        <h2 id="saved-configurations-heading" className="text-xl font-semibold">
          Saved for the team
        </h2>
        <p>
          <button
            type="button"
            onClick={showSavedList}
            className="mt-3 rounded border border-slate-500 px-4 py-2 font-medium text-slate-800"
          >
            List saved configurations
          </button>
        </p>
        {saved && (
          <div className="mt-3 overflow-x-auto">
          <table className="w-full border border-slate-300 text-left">
            <caption className="text-left text-slate-600">
              Dataset configurations saved for team {team}
            </caption>
            <thead>
              <tr>
                <th scope="col" className="border border-slate-300 px-2 py-1">Name</th>
                <th scope="col" className="border border-slate-300 px-2 py-1">Seed</th>
                <th scope="col" className="border border-slate-300 px-2 py-1">Records</th>
                <th scope="col" className="border border-slate-300 px-2 py-1">Age range</th>
                <th scope="col" className="border border-slate-300 px-2 py-1">Actions</th>
              </tr>
            </thead>
            <tbody>
              {saved.map((oneSaved) => (
                <tr key={oneSaved.name}>
                  <th scope="row" className="border border-slate-300 px-2 py-1">
                    {oneSaved.name}
                  </th>
                  <td className="border border-slate-300 px-2 py-1">{oneSaved.seed}</td>
                  <td className="border border-slate-300 px-2 py-1">{oneSaved.count}</td>
                  <td className="border border-slate-300 px-2 py-1">
                    {oneSaved.configuration.age_range[0]}–
                    {oneSaved.configuration.age_range[1]}
                  </td>
                  <td className="border border-slate-300 px-2 py-1">
                    <button
                      type="button"
                      onClick={() => reproduce(oneSaved.name)}
                      className="rounded border border-slate-500 px-3 py-1 font-medium text-slate-800"
                    >
                      Reproduce {oneSaved.name}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </section>

      {reproduction && (
        <section className="mt-8" aria-labelledby="reproduction-heading">
          <h2 id="reproduction-heading" className="text-xl font-semibold">
            Reproduced dataset
          </h2>
          <div className="mt-3 overflow-x-auto">
          <table className="w-full border border-slate-300 text-left">
            <caption className="text-left text-slate-600">
              The exact {reproduction.count} records of seed {reproduction.seed},
              unchanged from the failing cycle
            </caption>
            <thead>
              <tr>
                {attributeHeadersOf(reproduction).map((attribute) => (
                  <th scope="col" key={attribute} className="border border-slate-300 px-2 py-1">
                    {attribute}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {reproduction.personas.map((record, recordNumber) => (
                <tr key={recordNumber}>
                  {attributeHeadersOf(reproduction).map((attribute) => (
                    <td key={attribute} className="border border-slate-300 px-2 py-1">
                      {String(record[attribute])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </section>
      )}

      <p role="status" className="mt-6 text-slate-700" aria-live="polite">
        {status}
      </p>
    </main>
  )
}
