import { describe, expect, it } from 'vitest'
import type { Topic } from '../data/types'
import { DEFINITION, largeShareThreshold, quadrantOf, quantile, windows } from './definition'
import { sortBy } from './sort'

const topic = (status: Topic['status'], share: number, growth: number | null) =>
  ({ id: 'T000001', status, metrics: { share_recent: share, share_growth: growth } }) as unknown as Topic

describe('definition helpers', () => {
  it('derives the R, B and W windows from the last complete year', () => {
    expect(windows(2024)).toEqual({ R: [2022, 2024], B: [2017, 2021], W: [2020, 2024] })
    expect(DEFINITION.emergingMinGrowthLo).toBe(0.1)
  })

  it('computes the large-topic threshold like pandas quantile (linear), ignoring LOW_DATA', () => {
    expect(quantile([1, 2, 3, 4], 0.75)).toBe(3.25)
    expect(largeShareThreshold([topic('STABLE', 0.01, 0), topic('HOT', 0.04, 0.1), topic('STABLE', 0.02, 0), topic('STABLE', 0.03, 0), topic('LOW_DATA', 0.9, null)])).toBeCloseTo(0.0325)
    expect(largeShareThreshold([])).toBeNull()
  })

  it('places topics in the portfolio quadrants', () => {
    expect(quadrantOf(topic('HOT', 0.05, 0.08), 0.03)).toBe('stars')
    expect(quadrantOf(topic('EMERGING', 0.005, 0.4), 0.03)).toBe('rising')
    expect(quadrantOf(topic('STABLE', 0.05, -0.01), 0.03)).toBe('mature')
    expect(quadrantOf(topic('DECLINING', 0.01, -0.2), 0.03)).toBe('declining')
    expect(quadrantOf(topic('LOW_DATA', 0.01, 0.2), 0.03)).toBeNull()
    expect(quadrantOf(topic('STABLE', 0.01, null), 0.03)).toBeNull()
  })
})

describe('sortBy', () => {
  const rows = [{ n: 'ข', v: 2 }, { n: 'ก', v: null }, { n: 'ค', v: 1 }]
  it('sorts numbers both ways and always puts missing values last', () => {
    expect(sortBy(rows, (r) => r.v, 'desc').map((r) => r.n)).toEqual(['ข', 'ค', 'ก'])
    expect(sortBy(rows, (r) => r.v, 'asc').map((r) => r.n)).toEqual(['ค', 'ข', 'ก'])
  })
  it('sorts Thai text in dictionary order and does not touch the input', () => {
    expect(sortBy(rows, (r) => r.n, 'asc').map((r) => r.n)).toEqual(['ก', 'ข', 'ค'])
    expect(rows.map((r) => r.n)).toEqual(['ข', 'ก', 'ค'])
  })
})
