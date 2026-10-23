import { describe, expect, it } from 'vitest'
import type { Topic } from '../data/types'
import { pickFindings } from '../lib/findings'
import { stepOf, STATUS_STEPS } from '../lib/statusSteps'
import { STATUSES } from '../lib/status'
import { dotDomain, pctAt, percentOf, rankBars, topMovers, waffleCells, waffleGroups, waffleUnit } from './infographic'

const tp = (id: string, status: Topic['status'], g: number | null, score = 0, share = 0.01): Topic =>
  ({ id, status, score, th: id, en: id, metrics: { share_growth: g, share_recent: share } }) as unknown as Topic

const TOPICS = [
  tp('e1', 'EMERGING', 0.5, 60, 0.004),
  tp('e2', 'EMERGING', 1.1, 80, 0.003),
  tp('h1', 'HOT', 0.05, 40, 0.06),
  tp('h2', 'HOT', 0.2, 45, 0.03),
  tp('d1', 'DECLINING', -0.1, 20, 0.02),
  tp('d2', 'DECLINING', -0.3, 25, 0.01),
  tp('s1', 'STABLE', 0.01, 5, 0.02),
  tp('l1', 'LOW_DATA', null, 0, 0.001),
]

describe('waffleGroups', () => {
  it('gives every status a row in display order, one square per topic, strongest first', () => {
    const groups = waffleGroups(TOPICS)
    expect(groups.map((g) => g.status)).toEqual([...STATUSES])
    expect(groups.reduce((n, g) => n + g.topics.length, 0)).toBe(TOPICS.length)
    expect(groups[0].topics.map((t) => t.id)).toEqual(['e2', 'e1'])
    expect(groups.find((g) => g.status === 'WATCH')?.topics).toEqual([])
  })

  it('percentOf rounds and never divides by zero', () => {
    expect(percentOf(5, 48)).toBe(10)
    expect(percentOf(3, 0)).toBe(0)
  })
})

describe('waffleUnit / waffleCells', () => {
  it('draws a square per topic up to 300 topics, then groups topics in round numbers', () => {
    expect(waffleUnit(48)).toBe(1)
    expect(waffleUnit(300)).toBe(1)
    expect(waffleUnit(301)).toBe(5)
    expect(waffleUnit(750)).toBe(5)
    expect(waffleUnit(1500)).toBe(10)
    expect(waffleUnit(6000)).toBe(50)
    expect([5, 10, 25, 50, 100, 250, 500, 1000]).toContain(waffleUnit(3_000_000))
  })

  it('keeps the squares near 150 however many topics there are', () => {
    for (const n of [301, 800, 1500, 4000]) expect(Math.ceil(n / waffleUnit(n))).toBeLessThanOrEqual(150 + 1)
  })

  it('cuts a status into runs of the unit, strongest first, and never loses a topic', () => {
    const topics = Array.from({ length: 23 }, (_, i) => tp('t' + i, 'HOT', 0.1, 50 - i))
    const cells = waffleCells(topics, 10)
    expect(cells.map((c) => c.length)).toEqual([10, 10, 3])
    expect(cells.flat().map((x) => x.id)).toEqual(topics.map((x) => x.id))
    expect(waffleCells(topics, 1)).toHaveLength(23)
    expect(waffleCells([], 10)).toEqual([])
    expect(waffleCells(topics.slice(0, 1), 10)).toHaveLength(1)
  })
})

describe('dotDomain / pctAt', () => {
  it('covers every value and zero on whole tick steps', () => {
    const { domain, ticks } = dotDomain([1.134, -0.169, 0.6])
    expect(domain[0]).toBeLessThanOrEqual(-0.169)
    expect(domain[1]).toBeGreaterThanOrEqual(1.134)
    expect(ticks).toContain(0)
    expect(ticks[0]).toBe(domain[0])
    expect(ticks[ticks.length - 1]).toBe(domain[1])
  })

  it('includes zero even when every value is positive', () => {
    expect(dotDomain([0.2, 0.4]).domain[0]).toBe(0)
  })

  it('places values in percent and clamps the ends', () => {
    expect(pctAt(0, [-1, 1])).toBe(50)
    expect(pctAt(5, [-1, 1])).toBe(100)
    expect(pctAt(-5, [-1, 1])).toBe(0)
  })
})

describe('topMovers', () => {
  it('takes the fastest risers and fallers among signal topics, biggest rise first', () => {
    expect(topMovers(TOPICS, 3, 1).map((t) => t.id)).toEqual(['e2', 'e1', 'h2', 'd2'])
  })
  it('never lists stable or low-data topics', () => {
    expect(topMovers(TOPICS).some((t) => t.status === 'STABLE' || t.status === 'LOW_DATA')).toBe(false)
  })
})

describe('rankBars', () => {
  it('keeps the n largest, scales bars to the first and counts the rest', () => {
    const { rows, rest } = rankBars([{ key: 'a', count: 5 }, { key: 'b', count: 20 }, { key: 'c', count: 10 }], 2)
    expect(rows.map((r) => r.key)).toEqual(['b', 'c'])
    expect(rows.map((r) => r.frac)).toEqual([1, 0.5])
    expect(rest).toBe(1)
  })
  it('handles an empty list', () => {
    expect(rankBars([])).toEqual({ rows: [], rest: 0 })
  })
})

describe('pickFindings', () => {
  it('picks the strongest emerging, the largest hot and the fastest-shrinking topic', () => {
    expect(pickFindings(TOPICS).map((f) => [f.kind, f.topic.id])).toEqual([['emerging', 'e2'], ['large', 'h1'], ['decline', 'd2']])
  })
  it('leaves out a kind the release does not have', () => {
    expect(pickFindings(TOPICS.filter((t) => t.status !== 'DECLINING')).map((f) => f.kind)).toEqual(['emerging', 'large'])
    expect(pickFindings([])).toEqual([])
  })
})

describe('status steps', () => {
  it('puts every status on exactly one step, low data first', () => {
    for (const s of STATUSES) expect(STATUS_STEPS[stepOf(s)].outcomes).toContain(s)
    expect(stepOf('LOW_DATA')).toBe(0)
    expect(STATUS_STEPS.flatMap((s) => s.outcomes).sort()).toEqual([...STATUSES].sort())
  })
})
