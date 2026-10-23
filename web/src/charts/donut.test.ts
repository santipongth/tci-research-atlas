import { describe, expect, it } from 'vitest'
import { donutArcs } from './donut'

describe('donutArcs', () => {
  it('splits the ring by share, clockwise from 12 o\'clock, in input order', () => {
    const arcs = donutArcs([{ key: 'a', value: 1 }, { key: 'b', value: 3 }], 50, 50, 30, 40)
    expect(arcs.map((a) => a.key)).toEqual(['a', 'b'])
    expect(arcs[0].frac).toBeCloseTo(0.25)
    expect(arcs[0].start).toBe(0)
    expect(arcs[0].end).toBeCloseTo(Math.PI / 2)
    expect(arcs[1].end).toBeCloseTo(Math.PI * 2)
    // the first segment starts at the top of the outer ring
    expect(arcs[0].d.startsWith('M50.00,10.00')).toBe(true)
    // a segment over half the ring takes the large arc
    expect(arcs[1].d).toContain('A40,40 0 1 1')
  })

  it('keeps empty and invalid values in place with no path', () => {
    const arcs = donutArcs([{ key: 'a', value: 0 }, { key: 'b', value: Number.NaN }, { key: 'c', value: 2 }], 0, 0, 1, 2)
    expect(arcs.map((a) => a.d === '')).toEqual([true, true, false])
    expect(arcs[2].frac).toBe(1)
  })

  it('draws a full ring as two halves', () => {
    const [arc] = donutArcs([{ key: 'a', value: 5 }], 0, 0, 1, 2)
    expect(arc.d.match(/M/g)?.length).toBe(2)
  })

  it('returns zero shares when everything is empty', () => {
    expect(donutArcs([{ key: 'a', value: 0 }], 0, 0, 1, 2)[0]).toMatchObject({ frac: 0, d: '' })
  })
})
