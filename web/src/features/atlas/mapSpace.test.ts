import { describe, expect, it } from 'vitest'
import type { GroupInfo, Topic } from '../../data/types'
import { combineView, fitScreen, gridRef, MAP_H, MAP_W, NEUTRAL_TINT, overlaps, placeCentered, placeLabels, tintTokens, toMapPoints, zoomAt } from './mapSpace'
import { buildTerrain } from './terrain'

const topic = (id: string, x: number, y: number, share: number, group = 'F01') =>
  ({ id, x, y, group, status: 'STABLE', metrics: { share_recent: share } }) as unknown as Topic
const groups = [{ id: 'F01' }, { id: 'F02' }] as unknown as GroupInfo[]

describe('map space', () => {
  it('names grid references A–J across and 1–6 down', () => {
    expect(gridRef(0, 0)).toBe('A1')
    expect(gridRef(999, 639)).toBe('J6')
    expect(gridRef(550, 330)).toBe('F4')
    expect(gridRef(-20, 9999)).toBe('A6')
  })

  it('fits any layout into the sheet with a margin, sizing marks by share', () => {
    const pts = toMapPoints([topic('T000001', -5, 2, 0.01), topic('T000002', 40, -8, 0.04, 'F02'), topic('T000003', 12, 30, 0.0)], groups)
    for (const p of pts) {
      expect(p.x).toBeGreaterThanOrEqual(29.9)
      expect(p.x).toBeLessThanOrEqual(MAP_W - 29.9)
      expect(p.y).toBeGreaterThanOrEqual(29.9)
      expect(p.y).toBeLessThanOrEqual(MAP_H - 29.9)
    }
    expect(pts[1].r).toBeGreaterThan(pts[0].r)
    expect(pts[1].groupIndex).toBe(1)
    expect(toMapPoints([topic('T000009', 7, 7, 0.1)], groups)[0]).toMatchObject({ x: MAP_W / 2, y: MAP_H / 2 })
    expect(toMapPoints([], groups)).toEqual([])
  })

  it('zooms about the pointer without moving the map point under it, within the zoom limits', () => {
    const W = 900
    const H = 600
    const fit = fitScreen(W, H)
    const start = { s: 1, dx: 30, dy: -10 }
    const before = combineView(fit, start, W, H)
    const mx = (200 - before.tx) / before.k
    const my = (150 - before.ty) / before.k
    const after = combineView(fit, zoomAt(start, 1.4, 200, 150, W, H), W, H)
    expect(mx * after.k + after.tx).toBeCloseTo(200, 6)
    expect(my * after.k + after.ty).toBeCloseTo(150, 6)
    expect(zoomAt({ s: 5.5, dx: 0, dy: 0 }, 2, 0, 0, W, H).s).toBe(6)
  })

  it('places labels without overlaps, drops blocked ones and always places forced ones', () => {
    const frame = { x: 0, y: 0, w: 400, h: 300 }
    const at = (id: string) => ({ id, text: id, width: 60, height: 13, x: 100, y: 100, radius: 6 })
    const placed = placeLabels(['a', 'b', 'c', 'd', 'e'].map(at), [], frame, new Set(['e']))
    expect(placed.map((p) => p.id)).toEqual(['a', 'b', 'e'])
    expect(placed.map((p) => p.anchor)).toEqual(['start', 'end', 'middle'])
    expect(placeLabels([at('a')], [{ x: 0, y: 0, w: 400, h: 300 }], frame)).toEqual([])
    const fields = placeCentered([{ id: 'x', text: 'X', width: 80, height: 16, x: 100, y: 100 }, { id: 'y', text: 'Y', width: 80, height: 16, x: 110, y: 104 }], frame)
    expect(fields.map((p) => p.id)).toEqual(['x'])
  })

  it('moves a field name off the status markers under it, but never drops it for a marker', () => {
    const frame = { x: 0, y: 0, w: 400, h: 300 }
    const name = { id: 'x', text: 'X', width: 80, height: 16, x: 100, y: 100 }
    const marker = { x: 94, y: 92, w: 12, h: 12 }
    const [moved] = placeCentered([name], frame, [marker])
    expect(moved.y).not.toBe(100)
    expect(overlaps(moved.box, marker, 2)).toBe(false)
    const everywhere = [{ x: 0, y: 0, w: 400, h: 300 }]
    expect(placeCentered([name], frame, everywhere)).toMatchObject([{ id: 'x', x: 100, y: 100 }])
  })

  it('tints OpenAlex fields by their token and puts stale-taxonomy fallback groups on neutral terrain', () => {
    const mixed = [{ id: 'F27', color: 'cat-01' }, { id: 'G03', color: 'cat-02' }, { id: 'F11', color: 'cat-03' }] as unknown as GroupInfo[]
    expect(tintTokens(mixed)).toEqual(['cat-01', NEUTRAL_TINT, 'cat-03'])
    // a release clustered without OpenAlex has only G groups: they keep their own tints so the fields stay apart
    const fallback = [{ id: 'G01', color: 'cat-01' }, { id: 'G02', color: 'cat-02' }] as unknown as GroupInfo[]
    expect(tintTokens(fallback)).toEqual(['cat-01', 'cat-02'])
  })
})

describe('terrain', () => {
  it('builds density bands, owners and contours for two groups', () => {
    const t = buildTerrain([{ x: 200, y: 200, r: 10, w: 1, g: 0 }, { x: 700, y: 400, r: 10, w: 1, g: 1 }], 2)
    const at = (x: number, y: number) => Math.floor(y / t.cell) * t.gw + Math.floor(x / t.cell)
    expect(t.owner[at(200, 200)]).toBe(0)
    expect(t.owner[at(700, 400)]).toBe(1)
    expect(t.band[at(200, 200)]).toBeGreaterThan(0)
    expect(t.band[at(5, 630)]).toBe(0)
    expect(t.segs.some((s) => s.length > 0)).toBe(true)
  })

  it('joins sparse neighbouring topics into one field instead of isolated rings', () => {
    const t = buildTerrain([{ x: 300, y: 300, r: 5, w: 1, g: 0 }, { x: 360, y: 300, r: 5, w: 1, g: 0 }], 1)
    const at = (x: number, y: number) => Math.floor(y / t.cell) * t.gw + Math.floor(x / t.cell)
    expect(t.band[at(330, 300)]).toBeGreaterThanOrEqual(t.band[at(300, 300)] - 1)
    expect(t.band[at(330, 300)]).toBeGreaterThan(0)
  })

  it('survives an empty map', () => {
    const t = buildTerrain([], 0)
    expect(t.band.every((b) => b === 0)).toBe(true)
    expect(t.segs.every((s) => s.length === 0)).toBe(true)
  })
})
