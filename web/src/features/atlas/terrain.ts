import { MAP_H, MAP_W } from './mapSpace'

/** One topic as terrain input: map position, radius, weight w (share^0.75) and group index g (-1 = none). */
export interface TerrainPoint {
  x: number
  y: number
  r: number
  w: number
  g: number
}

export interface Terrain {
  gw: number
  gh: number
  cell: number
  /** group owning each cell (strongest density), -1 if none */
  owner: Int16Array
  /** density band 0 (empty) … LEVELS.length */
  band: Uint8Array
  /** contour segments per level: x0,y0,x1,y1,… in map units */
  segs: Float32Array[]
}

/** Contour levels as fractions of the peak density (every third line is drawn heavier). */
export const LEVELS = [0.035, 0.07, 0.12, 0.19, 0.28, 0.4, 0.55, 0.72, 0.9]

type Pt = [number, number]
const CASES: Record<number, (s: { T: Pt; R: Pt; B: Pt; L: Pt }) => Pt[][]> = {
  1: ({ L, B }) => [[L, B]],
  2: ({ B, R }) => [[B, R]],
  3: ({ L, R }) => [[L, R]],
  4: ({ T, R }) => [[T, R]],
  5: ({ L, T, B, R }) => [[L, T], [B, R]],
  6: ({ T, B }) => [[T, B]],
  7: ({ L, T }) => [[L, T]],
  8: ({ L, T }) => [[L, T]],
  9: ({ T, B }) => [[T, B]],
  10: ({ T, R, L, B }) => [[T, R], [L, B]],
  11: ({ T, R }) => [[T, R]],
  12: ({ L, R }) => [[L, R]],
  13: ({ B, R }) => [[B, R]],
  14: ({ L, B }) => [[L, B]],
}

/** Kernel width: at least 9 map units and 1.25 × the mark radius; widened towards the nearest neighbour (× SPREAD, up to
 *  MAX_SIGMA) so that a sparse release still forms connected fields. Dense releases (neighbours ≲ 16 units apart) are unchanged. */
const SPREAD = 0.55
const MAX_SIGMA = 32

function nearestDistances(points: readonly TerrainPoint[]): number[] {
  return points.map((p, i) => {
    let best = Infinity
    for (let j = 0; j < points.length; j++) {
      if (j === i || !(points[j].w > 0)) continue
      const d = Math.hypot(points[j].x - p.x, points[j].y - p.y)
      if (d < best) best = d
    }
    return best
  })
}

/** Gaussian density per group on a grid → hypsometric bands, the owning group per cell, marching-squares contours. */
export function buildTerrain(points: readonly TerrainPoint[], nGroups: number, width = MAP_W, height = MAP_H, cell = 4): Terrain {
  const gw = Math.ceil(width / cell)
  const gh = Math.ceil(height / cell)
  const groups = Math.max(1, nGroups)
  const per = Array.from({ length: groups }, () => new Float32Array(gw * gh))
  const total = new Float32Array(gw * gh)
  const nearest = nearestDistances(points)
  for (const [pi, p] of points.entries()) {
    if (!(p.w > 0)) continue
    const sig = Math.max(9, p.r * 1.25, Math.min(MAX_SIGMA, SPREAD * nearest[pi]))
    const rad = sig * 3
    const i0 = Math.max(0, Math.floor((p.x - rad) / cell))
    const i1 = Math.min(gw - 1, Math.ceil((p.x + rad) / cell))
    const j0 = Math.max(0, Math.floor((p.y - rad) / cell))
    const j1 = Math.min(gh - 1, Math.ceil((p.y + rad) / cell))
    const fi = p.g >= 0 && p.g < groups ? p.g : -1
    for (let j = j0; j <= j1; j++) {
      for (let i = i0; i <= i1; i++) {
        const dx = i * cell + cell / 2 - p.x
        const dy = j * cell + cell / 2 - p.y
        const v = p.w * Math.exp(-(dx * dx + dy * dy) / (2 * sig * sig))
        if (fi >= 0) per[fi][j * gw + i] += v
        total[j * gw + i] += v
      }
    }
  }
  let max = 0
  for (const v of total) if (v > max) max = v
  const levels = LEVELS.map((f) => f * max)
  const owner = new Int16Array(gw * gh).fill(-1)
  const band = new Uint8Array(gw * gh)
  for (let c = 0; c < total.length; c++) {
    let best = -1
    let bv = 0
    for (let f = 0; f < groups; f++) {
      if (per[f][c] > bv) {
        bv = per[f][c]
        best = f
      }
    }
    owner[c] = best
    let b = 0
    while (max > 0 && b < levels.length && total[c] >= levels[b]) b++
    band[c] = b
  }
  const segs = levels.map((lv) => {
    if (!(max > 0)) return new Float32Array(0)
    const out: number[] = []
    const val = (i: number, j: number) => total[j * gw + i]
    const lerp = (a: number, b: number, va: number, vb: number) => a + ((lv - va) / (vb - va || 1)) * (b - a)
    for (let j = 0; j < gh - 1; j++) {
      for (let i = 0; i < gw - 1; i++) {
        const v0 = val(i, j)
        const v1 = val(i + 1, j)
        const v2 = val(i + 1, j + 1)
        const v3 = val(i, j + 1)
        const idx = (v0 >= lv ? 8 : 0) | (v1 >= lv ? 4 : 0) | (v2 >= lv ? 2 : 0) | (v3 >= lv ? 1 : 0)
        if (idx === 0 || idx === 15) continue
        const x0 = i * cell + cell / 2
        const y0 = j * cell + cell / 2
        const x1 = x0 + cell
        const y1 = y0 + cell
        const sides = { T: [lerp(x0, x1, v0, v1), y0] as Pt, R: [x1, lerp(y0, y1, v1, v2)] as Pt, B: [lerp(x0, x1, v3, v2), y1] as Pt, L: [x0, lerp(y0, y1, v0, v3)] as Pt }
        for (const [a, b] of CASES[idx](sides)) out.push(a[0], a[1], b[0], b[1])
      }
    }
    return new Float32Array(out)
  })
  return { gw, gh, cell, owner, band, segs }
}
