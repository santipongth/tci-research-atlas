import { describe, expect, it } from 'vitest'
import { assignSlots, SERIES_DASHES } from './series'

describe('compare series slots', () => {
  it('gives a fresh selection slots in order', () => {
    expect(assignSlots(['A', 'B', 'C'])).toEqual({ A: 0, B: 1, C: 2 })
  })

  it('never repaints the topics that stay when one is removed, and reuses the freed slot', () => {
    const before = assignSlots(['A', 'B', 'C'])
    const after = assignSlots(['B', 'C'], before)
    expect(after).toEqual({ B: 1, C: 2 })
    expect(assignSlots(['B', 'C', 'D'], after)).toEqual({ B: 1, C: 2, D: 0 })
  })

  it('repairs out-of-range or duplicated slots', () => {
    expect(assignSlots(['A', 'B'], { A: 7, B: 0 })).toEqual({ A: 1, B: 0 })
    expect(assignSlots(['A', 'B'], { A: 2, B: 2 })).toEqual({ A: 2, B: 0 })
  })

  it('has one dash pattern per slot, the first solid', () => {
    expect(SERIES_DASHES).toHaveLength(4)
    expect(SERIES_DASHES[0]).toBe('')
    expect(new Set(SERIES_DASHES).size).toBe(4)
  })
})
