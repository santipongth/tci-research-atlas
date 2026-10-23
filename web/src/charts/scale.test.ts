import { describe, expect, it } from 'vitest'
import { countTicks, dataDomain, niceTicks, tickDecimals, tickLabels } from './scale'

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

describe('countTicks', () => {
  it('uses whole numbers only, from 0', () => {
    expect(countTicks(2.1, 4)).toEqual([0, 1, 2])
    expect(countTicks(1.05, 4)).toEqual([0, 1])
    expect(countTicks(0.5, 4)).toEqual([0, 1])
    for (const hi of [3.15, 7.35, 12, 880]) expect(countTicks(hi, 4).every(Number.isInteger)).toBe(true)
  })
})

describe('tick precision', () => {
  it('chooses decimals from the step', () => {
    expect(tickDecimals(0.05)).toBe(2)
    expect(tickDecimals(0.2)).toBe(1)
    expect(tickDecimals(1)).toBe(0)
    expect(tickDecimals(50)).toBe(0)
    expect(tickDecimals(0.005, 100)).toBe(1)
    expect(tickDecimals(0.05, 100)).toBe(0)
  })

  it('never prints the same label twice (the journal drift bug: 0.2, 0.2, 0.1, 0.1, 0.0)', () => {
    const ticks = niceTicks(0, 0.21, 4)
    const step = ticks[1] - ticks[0]
    const labels = tickLabels(ticks, (v) => v.toFixed(tickDecimals(step)))
    expect(new Set(labels).size).toBe(labels.length)
    expect(labels).toEqual(['0.00', '0.05', '0.10', '0.15', '0.20'])
    // a formatter that rounds too hard still cannot repeat a label: repeats are blanked
    const rough = tickLabels(ticks, (v) => v.toFixed(1))
    expect(rough.filter((l) => l !== '')).toEqual([...new Set(rough.filter((l) => l !== ''))])
    expect(rough.filter((l) => l !== '').length).toBeLessThan(ticks.length)
  })
})
