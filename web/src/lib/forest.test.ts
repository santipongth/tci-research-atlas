import { describe, expect, it } from 'vitest'
import type { Topic } from '../data/types'
import { forestSelection, hasCi } from './forest'

const topic = (id: string, status: string, g: number | null, lo: number | null, hi: number | null) =>
  ({ id, status, metrics: { share_growth: g, share_growth_lo: lo, share_growth_hi: hi } }) as unknown as Topic

const topics = [
  topic('T1', 'EMERGING', 0.4, 0.2, 0.6),
  topic('T2', 'EMERGING', 0.9, null, null),
  topic('T3', 'EMERGING', 0.3, 0.1, 0.5),
  topic('T4', 'DECLINING', -0.2, -0.3, -0.1),
  topic('T5', 'DECLINING', -0.4, -0.5, -0.3),
  topic('T6', 'EMERGING', null, null, null),
]

describe('forestSelection', () => {
  it('keeps topics without a confidence interval (as text rows) and counts them', () => {
    const s = forestSelection(topics, 'EMERGING')
    expect(s.rows.map((t) => t.id)).toEqual(['T2', 'T1', 'T3', 'T6'])
    expect(s.total).toBe(4)
    expect(s.noCi).toBe(2)
    expect(hasCi(s.rows[0])).toBe(false)
    expect(hasCi(s.rows[1])).toBe(true)
  })

  it('orders DECLINING by the steepest fall and applies the per-status limit', () => {
    expect(forestSelection(topics, 'DECLINING').rows.map((t) => t.id)).toEqual(['T5', 'T4'])
    const top = forestSelection(topics, 'EMERGING', 2)
    expect(top.rows.map((t) => t.id)).toEqual(['T2', 'T1'])
    expect(top.total).toBe(4)
    expect(top.noCi).toBe(2)
  })
})
