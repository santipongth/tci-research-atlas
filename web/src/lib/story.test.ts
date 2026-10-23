import { describe, expect, it } from 'vitest'
import type { Topic } from '../data/types'
import { pickRisers, spreadLabels } from './story'

const tp = (id: string, status: Topic['status'], g: number | null): Topic =>
  ({ id, status, th: id, en: id, metrics: { share_growth: g } }) as unknown as Topic

const tpm = (id: string, status: Topic['status'], g: number, lo: number | null, extra: Record<string, unknown> = {}, score = 0): Topic =>
  ({ id, status, score, th: id, en: id, metrics: { share_growth: g, share_growth_lo: lo, ...extra } }) as unknown as Topic

describe('pickRisers', () => {
  const TOPICS = [
    tpm('e1', 'EMERGING', 0.5, 0.2),
    tpm('h1', 'HOT', 1.2, 0.6),
    tpm('w1', 'WATCH', 9, 4),
    tpm('s1', 'STABLE', 3, 1),
    tpm('d1', 'DECLINING', 2, 1),
    tpm('l1', 'LOW_DATA', 5, 2),
    tpm('nb', 'EMERGING', 8, 3, { no_baseline: true }),
    tp('e2', 'EMERGING', null),
    tpm('h2', 'HOT', -0.1, -0.3),
  ]
  it('ranks confirmed risers (EMERGING, HOT) by the lower bound of the growth interval', () => {
    expect(pickRisers(TOPICS).map((t) => t.id)).toEqual(['h1', 'e1'])
    // a wide interval loses to a tighter one even with a bigger point estimate
    expect(pickRisers([tpm('wide', 'HOT', 5, 0.1), tpm('tight', 'HOT', 0.9, 0.7)]).map((t) => t.id)).toEqual(['tight', 'wide'])
  })
  it('never takes WATCH, a topic with no baseline, nor a stable, declining or low-data one', () => {
    const ids = pickRisers(TOPICS, 10).map((t) => t.id)
    expect(ids).not.toContain('w1')
    expect(ids).not.toContain('nb')
    expect(pickRisers([tpm('l1', 'LOW_DATA', 5, 2), tp('e2', 'EMERGING', null)])).toEqual([])
  })
  it('puts a topic without an interval after those with one, ranked by score, then id', () => {
    const noCi = [tpm('a', 'EMERGING', 0.4, null, {}, 10), tpm('b', 'EMERGING', 0.4, null, {}, 30), tpm('c', 'HOT', 0.3, 0.1)]
    expect(pickRisers(noCi).map((t) => t.id)).toEqual(['c', 'b', 'a'])
  })
  it('stops at n', () => {
    expect(pickRisers(TOPICS, 1).map((t) => t.id)).toEqual(['h1'])
  })
})

describe('spreadLabels', () => {
  it('keeps labels at their lines when they already clear each other', () => {
    expect(spreadLabels([10, 50, 90], 20, 0, 100)).toEqual([10, 50, 90])
  })
  it('pushes crowded labels apart in line order and keeps the input order', () => {
    expect(spreadLabels([50, 40, 45], 20, 0, 200)).toEqual([80, 40, 60])
  })
  it('keeps a pinned label exactly at its line and moves the others around it', () => {
    // the pinned label (index 1) stays at 52; the one just above it moves up, the one just below moves down
    expect(spreadLabels([50, 52, 60], 20, 0, 200, 1)).toEqual([32, 52, 72])
  })
  it('never stacks labels past the bottom: the stack under the pinned label is pulled back up', () => {
    // pinned at 90 with three labels crowded at 95–100 and hi = 100: nothing may overlap or pass 100
    const out = spreadLabels([95, 90, 98, 100, 20], 10, 0, 100, 1)
    const sorted = [...out].sort((a, b) => a - b)
    for (let k = 1; k < sorted.length; k++) expect(sorted[k] - sorted[k - 1]).toBeGreaterThanOrEqual(10 - 1e-9)
    expect(Math.max(...out)).toBeLessThanOrEqual(100)
    expect(out[4]).toBe(20)
  })

  it('moves a label under the pinned one when there is no room above it', () => {
    // pinned at 15 near the top (lo = 10): the label at 12 cannot sit 20 above, so it goes 20 below
    expect(spreadLabels([12, 15, 80], 20, 10, 200, 1)).toEqual([35, 15, 80])
  })
  it('pulls the stack back up when it would run past the bottom', () => {
    const out = spreadLabels([95, 96, 97], 10, 0, 100)
    expect(out).toEqual([80, 90, 100])
    expect(Math.max(...out)).toBeLessThanOrEqual(100)
  })
})
