import { describe, expect, it } from 'vitest'
import { CHECK_FULL, CHECK_NONE, checkState, galaxyPicks, labelOrder, periodMix, riserOf, scatterLayout, weightedMean, type ScatterPoint } from './editorLayout'

const pt = (id: string, x: number, y: number, weight = 10, inferred = false): ScatterPoint => ({ id, label: id, x, y, weight, inferred })
const M = { t: 10, r: 10, b: 30, l: 40 }

describe('journals scatter', () => {
  it('fixes x to 0–100 and runs y from 0 past the highest share and the bar, on round ticks', () => {
    const L = scatterLayout([pt('a', 0, 0.12), pt('b', 100, 0.42)], { width: 540, height: 340, margin: M, yRef: 0.5 })
    expect(L.xTicks).toEqual([0, 20, 40, 60, 80, 100])
    expect(L.x(0)).toBe(M.l)
    expect(L.x(100)).toBe(540 - M.r)
    expect(L.x(140)).toBe(540 - M.r)                                  // clamped
    expect(L.yTicks[0]).toBe(0)
    expect(L.yTicks[L.yTicks.length - 1]).toBeGreaterThan(0.5)
    expect(L.yTicks.every((v, i) => i === 0 || Math.abs(v - L.yTicks[i - 1] - L.yStep) < 1e-9)).toBe(true)
    expect(L.y(0)).toBe(340 - M.b)
  })

  it('shades the band above the bar, and none without a bar', () => {
    const L = scatterLayout([pt('a', 50, 0.2)], { width: 500, height: 300, margin: M, yRef: 0.3 })
    expect(L.zone).not.toBeNull()
    expect(L.zone?.y).toBe(M.t)
    expect((L.zone?.y ?? 0) + (L.zone?.h ?? 0)).toBeCloseTo(L.y(0.3))
    expect(scatterLayout([pt('a', 50, 0.2)], { width: 500, height: 300, margin: M, yRef: null }).zone).toBeNull()
  })

  it('names journals above the bar first, then the largest', () => {
    const order = labelOrder([pt('small-above', 50, 0.6, 5), pt('big', 50, 0.2, 90), pt('mid', 50, 0.1, 40)], 0.5).map((p) => p.id)
    expect(order).toEqual(['small-above', 'big', 'mid'])
  })
})

describe('then vs now topic mix', () => {
  it('keeps the largest movers, one row per topic, and the rest as other in both periods', () => {
    const m = periodMix([
      { topic: 'T1', share_before: 0.12, share_after: 0.21 },
      { topic: 'T2', share_before: 0.14, share_after: 0.06 },
      { topic: 'T1', share_before: 0.5, share_after: 0.5 },          // duplicate: ignored
      { topic: 'T3', share_before: 0.01, share_after: 0.02 },
    ], 2)
    expect(m.rows.map((r) => r.topic)).toEqual(['T1', 'T2'])
    expect(m.other.before).toBeCloseTo(0.74)
    expect(m.other.after).toBeCloseTo(0.73)
  })

  it('never gives a negative remainder', () => {
    expect(periodMix([{ topic: 'A', share_before: 0.7, share_after: 0.6 }, { topic: 'B', share_before: 0.5, share_after: 0.5 }]).other.before).toBe(0)
  })
})

describe('record checklist', () => {
  it('ticks from 95 %, marks almost none at 5 % or less, and keeps unknown apart from zero', () => {
    expect(checkState(CHECK_FULL)).toBe('full')
    expect(checkState(0.949)).toBe('partial')
    expect(checkState(CHECK_NONE)).toBe('none')
    expect(checkState(0)).toBe('none')
    expect(checkState(null)).toBe('unknown')
    expect(checkState(Number.NaN)).toBe('unknown')
  })
})

describe('keyword risers', () => {
  it('compares the mean of the first two years with the last two', () => {
    const r = riserOf([2020, 2021, 2022, 2023, 2024], [0.01, 0.03, 0.04, 0.05, 0.07])
    expect(r?.from).toBeCloseTo(0.02)
    expect(r?.to).toBeCloseTo(0.06)
    expect([r?.firstYear, r?.lastYear]).toEqual([2020, 2024])
  })

  it('gives nothing for short or gappy series', () => {
    expect(riserOf([2022, 2023, 2024], [0.1, 0.2, 0.3])).toBeNull()
    expect(riserOf([2020, 2021, 2022, 2023], [null, 0.1, 0.2, 0.3])).toBeNull()
  })
})

describe('galaxy example picks', () => {
  it('takes the article nearest each field centre, largest field first, skipping articles without a topic', () => {
    const pts = {
      count: 6,
      wx: [0, 10, 5, 100, 104, 50],
      wy: [0, 0, 1, 100, 100, 50],
      slot: [0, 0, 0, 1, 1, 2],
      topic: [0, 0, 0, 1, 1, -1],
    }
    expect(galaxyPicks(pts, [1, 0, 2], 3)).toEqual([3, 2])           // field 2 has no article with a topic
    expect(galaxyPicks(pts, [0, 1], 1)).toEqual([2])
  })
})

describe('weighted mean', () => {
  it('weights by count and skips empty values', () => {
    expect(weightedMean([{ v: 0.4, w: 3 }, { v: 0.2, w: 1 }, { v: null, w: 9 }], (x) => x.v, (x) => x.w)).toBeCloseTo(0.35)
    expect(weightedMean([{ v: null, w: 1 }], (x) => x.v, (x) => x.w)).toBeNull()
  })
})
