import '@testing-library/jest-dom/vitest'
import { cleanup, render } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import { afterEach, describe, expect, it, vi } from 'vitest'

expect.extend(toHaveNoViolations)

describe('HomePage', () => {
  afterEach(() => {
    cleanup()
  })

  it('has no accessibility violations', async () => {
    const { default: HomePage } = await vi.importActual('./HomePage')

    const { container } = render(<HomePage />)

    expect(await axe(container)).toHaveNoViolations()
  })
})
