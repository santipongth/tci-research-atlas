import { describe, expect, it } from 'vitest'
import type { Topic } from '../data/types'
import { pickRisers, spreadLabels } from './story'

const tp = (id: string, status: Topic['status'], g: number | null): Topic =>
  ({ id, status, th: id, en: id, metrics: { share_growth: g } }) as unknown as Topic

describe('pickRisers', () => {
  const TOPICS = [
    tp('e1', 'EMERGING', 0.5),
    tp('h1', 'HOT', 1.2),
    tp('w1', 'WATCH', 0.5),
    tp('s1', 'STABLE', 3),
    tp('d1', 'DECLINING', 2),
    tp('l1', 'LOW_DATA', 5),
    tp('e2', 'EMERGING', null),
    tp('h2', 'HOT', -0.1),
  ]
  it('ranks the rising statuses by growth, largest first, ties by id', () => {
    expect(pickRisers(TOPICS).map((t) => t.id)).toEqual(['h1', 'e1', 'w1'])
  })
  it('never takes a stable, declining or low-data topic, nor one without growth', () => {
    expect(pickRisers(TOPICS, 10).map((t) => t.status)).not.toContain('STABLE')
    expect(pickRisers([tp('l1', 'LOW_DATA', 5), tp('e2', 'EMERGING', null)])).toEqual([])
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
