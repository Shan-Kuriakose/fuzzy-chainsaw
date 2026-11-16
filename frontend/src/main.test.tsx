import '@testing-library/jest-dom/vitest'
import { afterEach, describe, expect, it } from 'vitest'

function mountPointInsertion() {
  const mountPoint = document.createElement('div')
  mountPoint.id = 'root'
  document.body.appendChild(mountPoint)
}

describe('the SPA entry point', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('mounts the application into the #root element of index.html', async () => {
    mountPointInsertion()

    await import('./main')
    await new Promise((resolve) => setTimeout(resolve, 0))

    const heading = document.querySelector('#root h1')

    expect(heading).toHaveTextContent('Fuzzy Chain Saw')
  })
})
