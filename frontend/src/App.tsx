import { useState } from 'react'

import DatasetConfigurationsPage from './pages/DatasetConfigurationsPage'
import HomePage from './pages/HomePage'

const HOME_PAGE = 'home'
const DATASET_CONFIGURATIONS_PAGE = 'dataset-configurations'

const PAGES = [
  { name: HOME_PAGE, label: 'Home' },
  { name: DATASET_CONFIGURATIONS_PAGE, label: 'Dataset configurations' },
] as const

type PageName = (typeof PAGES)[number]['name']

const ACTIVE_NAV_LINK =
  'rounded bg-slate-200 px-3 py-1 font-medium text-slate-900'
const INACTIVE_NAV_LINK =
  'rounded px-3 py-1 font-medium text-slate-700 hover:bg-slate-100'

export default function App() {
  const [activePage, setActivePage] = useState<PageName>(HOME_PAGE)

  return (
    <div>
      <nav
        aria-label="Primary"
        className="flex gap-2 border-b border-slate-200 bg-white px-6 py-2"
      >
        {PAGES.map((page) => (
          <button
            key={page.name}
            type="button"
            onClick={() => setActivePage(page.name)}
            aria-current={activePage === page.name ? 'page' : undefined}
            className={activePage === page.name ? ACTIVE_NAV_LINK : INACTIVE_NAV_LINK}
          >
            {page.label}
          </button>
        ))}
      </nav>
      {activePage === HOME_PAGE ? (
        <HomePage />
      ) : (
        <DatasetConfigurationsPage />
      )}
    </div>
  )
}
