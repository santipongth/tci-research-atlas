import { describe, expect, it } from 'vitest'
import { dataDomain } from './scale'

describe('dataDomain', () => {
  it('covers every value and the reference marks, with a margin', () => {
    const [lo, hi] = dataDomain([0.5, 1.2943, -0.25, null, undefined, Number.NaN], [0, 0.1], [-1, 3])
    expect(lo).toBeLessThan(-0.25)
    expect(hi).toBeGreaterThan(1.2943)
    const [l2, h2] = dataDomain([0.3, 0.4], [0, 0.1], [-1, 3])
    expect(l2).toBeLessThan(0)
    expect(h2).toBeGreaterThan(0.4)
  })

  it('stops at the cap, so one extreme value cannot flatten the rest (it is drawn at the edge)', () => {
    expect(dataDomain([9, 0.2], [0], [-1, 3])[1]).toBe(3)
    expect(dataDomain([-4, 0.2], [0], [-1, 3])[0]).toBe(-1)
  })

  it('falls back to the reference marks when there is no data', () => {
    const [lo, hi] = dataDomain([], [-0.05, 0.05], [-1, 3])
    expect(lo).toBeLessThan(-0.05)
    expect(hi).toBeGreaterThan(0.05)
  })
})
