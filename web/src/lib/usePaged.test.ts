import { describe, expect, it } from 'vitest'
import { pagedCount } from './usePaged'

describe('pagedCount', () => {
  it('shows one step more each press, never more than the list', () => {
    expect(pagedCount(25, 10, 0)).toBe(10)
    expect(pagedCount(25, 10, 1)).toBe(20)
    expect(pagedCount(25, 10, 2)).toBe(25)
    expect(pagedCount(25, 10, 9)).toBe(25)
  })

  it('handles short and empty lists', () => {
    expect(pagedCount(3, 10, 0)).toBe(3)
    expect(pagedCount(0, 10, 0)).toBe(0)
  })
})
