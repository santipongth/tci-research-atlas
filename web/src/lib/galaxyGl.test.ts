import { describe, expect, it } from 'vitest'
import type { GalaxyFile } from '../data/types'
import { contrastRatio } from './color'
import {
  buildGrid, clipTransform, combineView, dequantise, fitView, inFilter, MAX_ZOOM, nearest, NEUTRAL_SLOT, parseCssColor, pointShade, pointSize, preparePoints,
  quantise, RESET_VIEW, toScreen, toWorld, zoomAt, type Rgb,
} from './galaxyGl'

const B = { x0: 0, y0: 0, x1: 1040, y1: 660 }
const hex = ([r, g, b]: Rgb) => `#${[r, g, b].map((c) => c.toString(16).padStart(2, '0')).join('')}`

describe('quantise / dequantise', () => {
  it('round-trips within half a step and clamps to the scale', () => {
    for (const v of [0, 1, 123.4, 519.99, 1040]) {
      const q = quantise(v, B.x0, B.x1, 65535)
      expect(Math.abs(dequantise(q, B.x0, B.x1, 65535) - v)).toBeLessThanOrEqual((B.x1 - B.x0) / 65535)
    }
    expect(quantise(-5, 0, 10, 65535)).toBe(0)
    expect(quantise(50, 0, 10, 65535)).toBe(65535)
    expect(dequantise(65535, 10, 20, 65535)).toBe(20)
    expect(quantise(3, 5, 5, 65535)).toBe(0)
  })
})

describe('view transform', () => {
  it('fits the bounds centred with the aspect kept', () => {
    const v = fitView(B, 1040 + 32, 1000, 16)
    expect(v.k).toBeCloseTo(1)
    expect(toScreen(v, 0, 0)[0]).toBeCloseTo(16)
    expect(toScreen(v, 520, 330)).toEqual([536, 500])
  })

  it('maps screen ↔ world both ways', () => {
    const v = combineView(fitView(B, 800, 500), { s: 2.5, dx: 30, dy: -12 }, 800, 500)
    const [wx, wy] = toWorld(v, 123, 456)
    const [sx, sy] = toScreen(v, wx, wy)
    expect(sx).toBeCloseTo(123)
    expect(sy).toBeCloseTo(456)
  })

  it('zooms about the pointer and clamps the zoom', () => {
    const fit = fitView(B, 800, 500)
    const before = combineView(fit, RESET_VIEW, 800, 500)
    const after = combineView(fit, zoomAt(RESET_VIEW, 2, 200, 100, 800, 500), 800, 500)
    const w = toWorld(before, 200, 100)
    const s = toScreen(after, w[0], w[1])
    expect(s[0]).toBeCloseTo(200)
    expect(s[1]).toBeCloseTo(100)
    expect(zoomAt(RESET_VIEW, 1e6, 0, 0, 800, 500).s).toBe(MAX_ZOOM)
  })

  it('gives the shader a transform that lands bounds corners on the clip corners of the fitted area', () => {
    const W = 800
    const H = 500
    const v = combineView(fitView(B, W, H), { s: 1.7, dx: 40, dy: 25 }, W, H)
    const t = clipTransform(v, B, W, H)
    for (const [u, w] of [[0, 0], [1, 1], [0.25, 0.8]] as const) {
      const clipX = u * t.scale[0] + t.offset[0]
      const clipY = w * t.scale[1] + t.offset[1]
      const [sx, sy] = toScreen(v, B.x0 + u * (B.x1 - B.x0), B.y0 + w * (B.y1 - B.y0))
      expect(clipX).toBeCloseTo((sx / W) * 2 - 1)
      expect(clipY).toBeCloseTo(1 - (sy / H) * 2)
    }
  })

  it('draws smaller points for bigger collections and bigger points when zoomed in', () => {
    expect(pointSize(600, 1)).toBeGreaterThan(pointSize(200_000, 1))
    expect(pointSize(200_000, 1)).toBeGreaterThanOrEqual(2)
    expect(pointSize(600, 8)).toBeGreaterThan(pointSize(600, 1))
    expect(pointSize(600, 1e6)).toBeLessThanOrEqual(16)
  })
})

describe('preparePoints', () => {
  const file: GalaxyFile = {
    n: 5, scale: 65535, bounds: B, topics: ['T000101', 'T000201', 'T000999'],
    x: [0, -1, 65535, 32768, 100], y: [0, -1, 65535, 32768, 200], t: [0, -1, 1, -1, 2], yr: [2019, 2020, 2021, 2022, 2023],
  }
  const slots: Record<string, number> = { T000101: 0, T000201: 3 }
  const pts = preparePoints(file, (code) => slots[code] ?? -1)

  it('keeps only points with a coordinate and remembers their doc ordinals', () => {
    expect(pts.count).toBe(4)
    expect(pts.total).toBe(5)
    expect([...pts.ord]).toEqual([0, 2, 3, 4])
    expect(pts.wx[1]).toBeCloseTo(1040)
    expect(pts.wy[2]).toBeCloseTo(330, 1)
  })

  it('colours by field slot; no topic and unknown topics take the neutral slot', () => {
    expect([...pts.slot]).toEqual([0, 3, NEUTRAL_SLOT, NEUTRAL_SLOT])
    expect([...pts.topic]).toEqual([0, 1, -1, 2])
  })

  it('filters by year range and field', () => {
    const on = (f: Parameters<typeof inFilter>[2]) => [0, 1, 2, 3].filter((i) => inFilter(pts, i, f))
    expect(on({ from: null, to: null, slot: null })).toEqual([0, 1, 2, 3])
    expect(on({ from: 2021, to: 2022, slot: null })).toEqual([1, 2])
    expect(on({ from: null, to: null, slot: 3 })).toEqual([1])
  })
})

describe('pick grid', () => {
  // a deterministic scatter (LCG) checked against brute force
  let seed = 7
  const rnd = () => ((seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648)
  const n = 3000
  const wx = new Float32Array(n).map(() => rnd() * 1040)
  const wy = new Float32Array(n).map(() => rnd() * 660)
  const grid = buildGrid(wx, wy, B)
  const brute = (x: number, y: number, r: number, accept?: (i: number) => boolean) => {
    let best = -1
    let bd = r * r
    for (let i = 0; i < n; i++) {
      const d = (wx[i] - x) ** 2 + (wy[i] - y) ** 2
      if ((d < bd || (d === bd && (best < 0 || i < best))) && (!accept || accept(i))) {
        best = i
        bd = d
      }
    }
    return best
  }

  it('puts every point in exactly one cell', () => {
    expect(grid.items.length).toBe(n)
    expect(new Set(grid.items).size).toBe(n)
    expect(grid.start[grid.start.length - 1]).toBe(n)
  })

  it('finds the same nearest point as brute force, within the radius, honouring a filter', () => {
    for (let k = 0; k < 200; k++) {
      const x = rnd() * 1100 - 30
      const y = rnd() * 700 - 20
      const r = 2 + rnd() * 40
      expect(nearest(grid, x, y, r)).toBe(brute(x, y, r))
      const even = (i: number) => i % 2 === 0
      expect(nearest(grid, x, y, r, even)).toBe(brute(x, y, r, even))
    }
  })

  it('returns −1 when nothing is within the radius', () => {
    const one = buildGrid(new Float32Array([10]), new Float32Array([10]), B)
    expect(nearest(one, 500, 500, 5)).toBe(-1)
    expect(nearest(one, 12, 10, 5)).toBe(0)
  })
})

describe('colour', () => {
  it('reads the colour forms getComputedStyle returns', () => {
    expect(parseCssColor(' #e8b5a6 ')).toEqual([232, 181, 166])
    expect(parseCssColor('#fff')).toEqual([255, 255, 255])
    expect(parseCssColor('rgb(11, 12, 14)')).toEqual([11, 12, 14])
    expect(parseCssColor('rgba(11 12 14 / 0.4)')).toEqual([11, 12, 14])
    expect(parseCssColor('var(--x)')).toBeNull()
  })

  it('turns every terrain tint into a dot that stands out from the page in both themes (≥ 3:1)', () => {
    const light = ['#e8b5a6', '#dbc99d', '#c3d59c', '#e8d095', '#a8d1a4', '#b1c4da', '#d4bad6', '#9ccfca', '#bfd8e8', '#e3bfcd', '#cfd3a6', '#d9cbb8', '#c7cbce']
    const dark = ['#5b3229', '#4d4329', '#39492a', '#544423', '#284732', '#293c52', '#46314c', '#1f4746', '#213f50', '#4e2e3a', '#3f4425', '#463d31', '#3b4247']
    for (const t of light) expect(contrastRatio(hex(pointShade(parseCssColor(t) as Rgb, 'light')), '#ffffff')).toBeGreaterThanOrEqual(3)
    for (const t of dark) expect(contrastRatio(hex(pointShade(parseCssColor(t) as Rgb, 'dark')), '#0f1214')).toBeGreaterThanOrEqual(3)
  })
})
