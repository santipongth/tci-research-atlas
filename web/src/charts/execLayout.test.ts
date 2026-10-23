import { describe, expect, it } from 'vitest'
import { arcLayout, arcPath, bandPath, columnAxis, flowUnit, networkNodes, goalTiles, mixSegments, overlaps, placeLabels, quadrantLayout, statusFlow, textWidth, type QuadPoint } from './execLayout'

describe('arcLayout', () => {
  const nodes = [
    { id: 'a', weight: 1840 },
    { id: 'b', weight: 1210 },
    { id: 'c', weight: 640 },
    { id: 'd', weight: 420 },
    { id: 'lonely', weight: 5000 },
  ]
  const links = [
    { a: 'a', b: 'b', value: 214 },
    { a: 'a', b: 'd', value: 121 },
    { a: 'b', b: 'c', value: 64 },
    { a: 'c', b: 'd', value: 22 },
  ]

  it('rows only the institutions with a partnership, largest first, one row apart', () => {
    const L = arcLayout({ nodes, links }, { row: 50, width: 200 })
    expect(L.nodes.map((n) => n.id)).toEqual(['a', 'b', 'c', 'd'])
    expect(L.nodes.map((n) => n.y)).toEqual([25, 75, 125, 175])
    expect(L.height).toBe(200)
    expect(L.hidden).toBe(0)
  })

  it('makes stroke width linear in joint articles and wider arcs for rows farther apart', () => {
    const L = arcLayout({ nodes, links }, { row: 50, width: 200, minStroke: 2, maxStroke: 12 })
    const ab = L.links.find((l) => l.a === 'a' && l.b === 'b')!
    const ad = L.links.find((l) => l.a === 'a' && l.b === 'd')!
    const cd = L.links.find((l) => l.a === 'c' && l.b === 'd')!
    expect(ab.width).toBe(12)
    expect(cd.width).toBeCloseTo(2 + (22 / 214) * 10)
    expect(ad.bulge).toBeGreaterThan(ab.bulge)
    expect(ab.bulge).toBe(cd.bulge)
    expect(L.links[0].value).toBe(214)
  })

  it('keeps apex labels inside the width and never overlapping', () => {
    const many = Array.from({ length: 8 }, (_, i) => ({ id: `n${i}`, weight: 100 - i }))
    const dense = many.flatMap((p, i) => many.slice(i + 1).map((q) => ({ a: p.id, b: q.id, value: 10 + i })))
    const L = arcLayout({ nodes: many, links: dense }, { row: 40, width: 160 })
    const boxes = L.links.filter((l) => l.label).map((l) => ({ x: l.label!.x, y: l.label!.y - 9, w: textWidth(String(l.value), 14) + 6, h: 18 }))
    expect(boxes.length).toBeGreaterThan(0)
    boxes.forEach((b, i) => {
      expect(b.x + b.w).toBeLessThanOrEqual(161)
      boxes.slice(i + 1).forEach((c) => expect(overlaps(b, c)).toBe(false))
    })
  })

  it('drops pairs outside the top rows and counts them', () => {
    const L = arcLayout({ nodes, links }, { row: 50, width: 200, maxNodes: 2 })
    expect(L.nodes.map((n) => n.id)).toEqual(['a', 'b'])
    expect(L.links).toHaveLength(1)
    expect(L.hidden).toBe(3)
  })

  it('draws a half-ellipse to the right', () => {
    expect(arcPath(6, 25, 125, 40)).toBe('M6,25.0A40.0,50.0 0 0 1 6,125.0')
  })
})

describe('columnAxis', () => {
  it('starts at zero and tops out at or above the largest value', () => {
    const a = columnAxis([270, 294, 479])
    expect(a.ticks[0]).toBe(0)
    expect(a.max).toBeGreaterThanOrEqual(479)
    expect(a.ticks[a.ticks.length - 1]).toBe(a.max)
  })
  it('survives empty or all-zero data', () => {
    expect(columnAxis([])).toEqual({ max: 1, ticks: [0, 1] })
    expect(columnAxis([0, 0])).toEqual({ max: 1, ticks: [0, 1] })
  })
})

describe('mixSegments', () => {
  const items = [
    { key: 'a', value: 0.3 },
    { key: 'b', value: 0.18 },
    { key: 'c', value: 0.13 },
    { key: 'd', value: 0.1 },
    { key: 'e', value: 0.08 },
  ]
  it('keeps the largest parts and folds the rest (and the unlisted remainder) into one "other" segment', () => {
    const s = mixSegments(items, { top: 4, total: 1, otherKey: 'other' })
    expect(s.map((x) => x.key)).toEqual(['a', 'b', 'c', 'd', 'other'])
    expect(s[4].other).toBe(true)
    expect(s[4].frac).toBeCloseTo(0.29)
    expect(s.reduce((n, x) => n + x.frac, 0)).toBeCloseTo(1)
    expect(s[2].start).toBeCloseTo(0.48)
  })
  it('scales to the parts when they add up to more than the total', () => {
    const s = mixSegments([{ key: 'a', value: 3 }, { key: 'b', value: 1 }], { total: 1, otherKey: 'o' })
    expect(s.map((x) => x.frac)).toEqual([0.75, 0.25])
  })
  it('returns nothing for empty input', () => {
    expect(mixSegments([], { otherKey: 'o' })).toEqual([])
  })
})

describe('quadrantLayout', () => {
  const pts: QuadPoint[] = [
    { id: 'ai', label: 'Artificial Intelligence', x: 0.32, y: 1.32, hot: true },
    { id: 'ed', label: 'Education', x: 2.0, y: 0.93, hot: false },
    { id: 'po', label: 'Pollution', x: 0.23, y: 1.41, hot: true },
  ]
  const L = quadrantLayout(pts, { width: 600, height: 400, margin: { t: 10, r: 10, b: 30, l: 40 }, xMax: 0.5, yMin: 1.2 })

  it('shades the top-left zone from the data thresholds', () => {
    expect(L.zone).not.toBeNull()
    expect(L.zone!.x).toBe(L.plot.x)
    expect(L.zone!.y).toBe(L.plot.y)
    expect(L.zone!.x + L.zone!.w).toBeCloseTo(L.x(0.5))
    expect(L.zone!.y + L.zone!.h).toBeCloseTo(L.y(1.2))
  })

  it('puts the opportunities inside the zone and the rest outside', () => {
    for (const p of pts) {
      const inside = L.x(p.x) <= L.x(0.5) && L.y(p.y) <= L.y(1.2)
      expect(inside, p.id).toBe(p.hot)
    }
  })

  it('always shows 1 on both axes and keeps every point in the plot', () => {
    expect(L.xTicks[0]).toBe(0)
    expect(Math.min(...L.yTicks)).toBeLessThanOrEqual(0.93)
    expect(Math.max(...L.xTicks)).toBeGreaterThanOrEqual(2)
    for (const p of pts) {
      expect(L.x(p.x)).toBeGreaterThanOrEqual(L.plot.x)
      expect(L.x(p.x)).toBeLessThanOrEqual(L.plot.x + L.plot.w)
      expect(L.y(p.y)).toBeGreaterThanOrEqual(L.plot.y)
      expect(L.y(p.y)).toBeLessThanOrEqual(L.plot.y + L.plot.h)
    }
  })

  it('draws no zone when the thresholds are unknown', () => {
    expect(quadrantLayout(pts, { width: 600, height: 400, margin: { t: 0, r: 0, b: 0, l: 0 } }).zone).toBeNull()
  })
})

describe('placeLabels', () => {
  const bounds = { x: 0, y: 0, w: 400, h: 300 }

  it('never overlaps another label, a mark or an avoided box, and stays inside the bounds', () => {
    const pts = Array.from({ length: 12 }, (_, i) => ({ id: `p${i}`, text: `Subfield ${i}`, cx: 60 + (i % 4) * 30, cy: 80 + Math.floor(i / 4) * 16 }))
    const avoid = [{ x: 0, y: 0, w: 120, h: 30 }]
    const out = placeLabels(pts, { px: 14, r: 6, bounds, avoid, max: 12 })
    const marks = pts.map((p) => ({ x: p.cx - 6, y: p.cy - 6, w: 12, h: 12 }))
    out.forEach((l, i) => {
      expect(l.box.x).toBeGreaterThanOrEqual(0)
      expect(l.box.x + l.box.w).toBeLessThanOrEqual(400)
      expect(overlaps(l.box, avoid[0])).toBe(false)
      marks.forEach((m) => expect(overlaps(l.box, m, 1)).toBe(false))
      out.slice(i + 1).forEach((o) => expect(overlaps(l.box, o.box)).toBe(false))
    })
  })

  it('labels points in the given order and stops at max', () => {
    const pts = [
      { id: 'first', text: 'A', cx: 100, cy: 100 },
      { id: 'second', text: 'B', cx: 300, cy: 200 },
      { id: 'third', text: 'C', cx: 200, cy: 150 },
    ]
    expect(placeLabels(pts, { px: 14, r: 6, bounds, max: 2 }).map((l) => l.id)).toEqual(['first', 'second'])
  })

  it('examines at most `tries` points, in order', () => {
    const pts = Array.from({ length: 50 }, (_, i) => ({ id: `p${i}`, text: 'A', cx: 20 + (i % 10) * 36, cy: 30 + Math.floor(i / 10) * 50 }))
    const out = placeLabels(pts, { px: 14, r: 6, bounds, max: 50, tries: 7 })
    expect(out.length).toBeLessThanOrEqual(7)
    expect(out.every((l) => Number(l.id.slice(1)) < 7)).toBe(true)
    expect(placeLabels(pts, { px: 14, r: 6, bounds, max: 50 }).length).toBeGreaterThan(7)
  })

  it('goes left when the right side is off the sheet', () => {
    const [l] = placeLabels([{ id: 'edge', text: 'Near the edge', cx: 390, cy: 150 }], { px: 14, r: 6, bounds })
    expect(l.anchor).toBe('end')
  })
})

describe('networkNodes', () => {
  it('draws the strongest partnership even when its institutions are not among the largest', () => {
    // a–b are big but write little together; x–y are small but the strongest pair
    const edges = [
      { a: 'a', b: 'b', articles: 3 },
      { a: 'x', b: 'y', articles: 40 },
      { a: 'a', b: 'c', articles: 10 },
      { a: 'c', b: 'd', articles: 2 },
    ]
    const net = networkNodes(edges, 4)
    expect(net.ids).toEqual(['x', 'y', 'a', 'c'])
    expect(net.links.map((e) => `${e.a}-${e.b}`)).toEqual(['x-y', 'a-c'])
    // a pair that does not fit whole is left to the table
    expect(networkNodes(edges, 3).ids).toEqual(['x', 'y'])
    const all = networkNodes(edges, 10)
    expect(new Set(all.ids)).toEqual(new Set(['a', 'b', 'c', 'd', 'x', 'y']))
    expect(all.links).toHaveLength(4)
  })
})

describe('flowUnit', () => {
  it('keeps 26 px per topic for a few changes and shrinks so the bands stay within 520 px', () => {
    expect(flowUnit(5)).toBe(26)
    expect(flowUnit(20)).toBe(26)
    expect(flowUnit(52)).toBe(10)
    expect(flowUnit(300) * 300).toBeCloseTo(520)
    expect(flowUnit(0)).toBe(26)
  })
})

describe('statusFlow', () => {
  const changes = [
    { topic: 't1', previous: 'WATCH', current: 'EMERGING' },
    { topic: 't2', previous: 'STABLE', current: 'EMERGING' },
    { topic: 't3', previous: 'STABLE', current: 'WATCH' },
    { topic: 't4', previous: 'STABLE', current: 'DECLINING' },
    { topic: 't5', previous: 'HOT', current: 'STABLE' },
    { topic: 't6', previous: 'BOGUS', current: 'STABLE' },
  ]
  const L = statusFlow(changes, { unit: 20, minH: 30, gap: 10 })

  it('aggregates transitions and drops unknown statuses', () => {
    expect(L.links.map((l) => `${l.from}>${l.to}:${l.count}`)).toEqual(['WATCH>EMERGING:1', 'HOT>STABLE:1', 'STABLE>EMERGING:1', 'STABLE>WATCH:1', 'STABLE>DECLINING:1'])
    expect(L.links.find((l) => l.from === 'STABLE' && l.to === 'WATCH')!.topics).toEqual(['t3'])
  })

  it('orders nodes by status and sizes them by count (with a minimum)', () => {
    expect(L.left.map((n) => `${n.status}:${n.count}`)).toEqual(['WATCH:1', 'HOT:1', 'STABLE:3'])
    expect(L.right.map((n) => `${n.status}:${n.count}`)).toEqual(['EMERGING:2', 'WATCH:1', 'DECLINING:1', 'STABLE:1'])
    expect(L.left.map((n) => n.h)).toEqual([30, 30, 60])
    expect(L.left[1].y).toBe(40)
  })

  it('stacks each node’s bands in order without gaps, centred in the node', () => {
    for (const n of L.left) {
      const bands = L.links.filter((l) => l.from === n.status).sort((p, q) => p.y0 - q.y0)
      const stack = n.count * 20
      expect(bands[0].y0).toBeCloseTo(n.y + (n.h - stack) / 2)
      expect(bands[bands.length - 1].y0b).toBeCloseTo(n.y + (n.h + stack) / 2)
      bands.slice(1).forEach((b, i) => expect(b.y0).toBeCloseTo(bands[i].y0b))
    }
    for (const n of L.right) {
      const bands = L.links.filter((l) => l.to === n.status)
      expect(bands.reduce((s, b) => s + (b.y1b - b.y1), 0)).toBeCloseTo(n.count * 20)
    }
    expect(L.height).toBe(Math.max(...[...L.left, ...L.right].map((n) => n.y + n.h)))
    expect(bandPath(L.links[0], 0, 100).startsWith('M0,')).toBe(true)
  })

  it('keeps a band the same thickness at both ends when the unit shrinks below the node minimum (200 changes)', () => {
    const many = Array.from({ length: 200 }, (_, i) => ({ topic: `m${i}`, previous: i < 5 ? 'WATCH' : 'STABLE', current: i < 5 ? 'EMERGING' : i < 120 ? 'STABLE' : 'DECLINING' }))
    const unit = flowUnit(many.length)
    const F = statusFlow(many, { unit, minH: 48, gap: 10 })
    for (const l of F.links) {
      expect(l.y0b - l.y0, `${l.from}>${l.to}`).toBeCloseTo(l.count * unit)
      expect(l.y1b - l.y1, `${l.from}>${l.to}`).toBeCloseTo(l.count * unit)
    }
    const small = F.links.find((l) => l.from === 'WATCH')!
    const node = F.left.find((n) => n.status === 'WATCH')!
    expect(node.h).toBe(48)
    expect(small.y0 - node.y).toBeCloseTo(node.y + node.h - small.y0b)
  })

  it('is empty without changes', () => {
    expect(statusFlow([], { unit: 20, minH: 30, gap: 10 })).toEqual({ left: [], right: [], links: [], height: 0 })
  })
})

describe('goalTiles', () => {
  const goals = [
    { id: 'sdg-03', framework: 'sdg', number: 3, topics: ['T1', 'T2', 'Tgone'], share_recent: 0.12 },
    { id: 'sdg-01', framework: 'sdg', number: 1, topics: [], share_recent: 0 },
    { id: 'sdg-02', framework: 'sdg', number: 2, topics: ['T3'], share_recent: 0.04 },
    { id: 'bcg-1', framework: 'bcg', number: 1, topics: ['T1'], share_recent: 0.5 },
  ]
  it('lists one framework in goal order with counts of known topics and bars relative to the largest goal', () => {
    const tiles = goalTiles(goals, 'sdg', (id) => id !== 'Tgone')
    expect(tiles.map((g) => g.number)).toEqual([1, 2, 3])
    expect(tiles.map((g) => g.count)).toEqual([0, 1, 2])
    expect(tiles[2].frac).toBe(1)
    expect(tiles[1].frac).toBeCloseTo(1 / 3)
    expect(tiles[0].frac).toBe(0)
  })
  it('keeps every goal, even with no topic', () => {
    expect(goalTiles(goals, 'sdg').filter((g) => g.count === 0)).toHaveLength(1)
    expect(goalTiles(goals, 'none')).toEqual([])
  })
})

describe('textWidth', () => {
  it('gives combining Thai marks no width', () => {
    const ko = String.fromCodePoint(0xe01)
    expect(textWidth(ko + String.fromCodePoint(0xe34), 14)).toBe(textWidth(ko, 14))
    expect(textWidth('AB', 10)).toBeGreaterThan(textWidth('ab', 10))
  })
})
