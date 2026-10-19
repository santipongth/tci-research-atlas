import type { GroupInfo, Topic } from '../../data/types'
import { overlaps, type Box, type PlacedLabel } from '../../lib/labels'
import type { StatusId } from '../../lib/status'

export { overlaps, placeLabels, type Box, type LabelCandidate, type PlacedLabel } from '../../lib/labels'

/** The map sheet: a fixed 1000 × 640 space with a 10 × 6 reference grid (A–J across, 1–6 down). */
export const MAP_W = 1000
export const MAP_H = 640
export const COLS = 'ABCDEFGHIJ'
export const ROWS = 6
export const MIN_ZOOM = 0.8
export const MAX_ZOOM = 6

export interface MapPoint {
  id: string
  x: number
  y: number
  r: number
  status: StatusId
  group: string
  groupIndex: number
  share: number
}

/** Map space → screen: screen = map × k + t. */
export interface View {
  k: number
  tx: number
  ty: number
}

/** The visitor's zoom (s) and pan (dx, dy) on top of the fitted view. */
export interface UserView {
  s: number
  dx: number
  dy: number
}


/** Fit the topics' layout coordinates into the sheet (aspect kept, `pad` margin); radius grows with √share. */
export function toMapPoints(topics: readonly Topic[], groups: readonly GroupInfo[], pad = 30): MapPoint[] {
  if (topics.length === 0) return []
  const xs = topics.map((t) => t.x)
  const ys = topics.map((t) => t.y)
  const x0 = Math.min(...xs)
  const y0 = Math.min(...ys)
  const spanX = Math.max(...xs) - x0
  const spanY = Math.max(...ys) - y0
  const k = Math.min((MAP_W - 2 * pad) / (spanX || 1), (MAP_H - 2 * pad) / (spanY || 1))
  const ox = (MAP_W - spanX * k) / 2 - x0 * k
  const oy = (MAP_H - spanY * k) / 2 - y0 * k
  const maxShare = Math.max(1e-9, ...topics.map((t) => t.metrics.share_recent))
  const index = new Map(groups.map((g, i) => [g.id, i]))
  return topics.map((t) => ({
    id: t.id,
    x: t.x * k + ox,
    y: t.y * k + oy,
    r: 3.5 + 12 * Math.sqrt(Math.max(0, t.metrics.share_recent) / maxShare),
    status: t.status,
    group: t.group,
    groupIndex: index.get(t.group) ?? -1,
    share: t.metrics.share_recent,
  }))
}

/** Token for terrain that belongs to no field (a neutral grey matched to the field tints' lightness in both themes). */
export const NEUTRAL_TINT = 'dot'

/**
 * Terrain tint token per group, in taxonomy order. OpenAlex fields (F…) keep their `cat-NN` key. Fallback groups (G…)
 * that topics unknown to a stale taxonomy get sit on neutral terrain when real fields are present — they are named on
 * the map and in the gazetteer, so the grey only says "not a field". A release with no OpenAlex fields at all keeps
 * every group's own tint, so neighbouring groups stay apart.
 */
export function tintTokens(groups: readonly GroupInfo[]): string[] {
  const hasFields = groups.some((g) => g.id.startsWith('F'))
  return groups.map((g) => (hasFields && g.id.startsWith('G') ? NEUTRAL_TINT : g.color))
}

export function gridRef(x: number, y: number): string {
  const col = Math.max(0, Math.min(COLS.length - 1, Math.floor(x / 100)))
  const row = Math.max(1, Math.min(ROWS, Math.floor(y / (MAP_H / ROWS)) + 1))
  return `${COLS[col]}${row}`
}

/** The whole sheet centred in a width × height viewport. */
export function fitScreen(width: number, height: number, pad = 18): View {
  const k = Math.max(0.01, Math.min((width - 2 * pad) / MAP_W, (height - 2 * pad) / MAP_H))
  return { k, tx: (width - MAP_W * k) / 2, ty: (height - MAP_H * k) / 2 }
}

export function combineView(fit: View, user: UserView, width: number, height: number): View {
  const cx = width / 2
  const cy = height / 2
  return { k: fit.k * user.s, tx: (fit.tx - cx) * user.s + cx + user.dx, ty: (fit.ty - cy) * user.s + cy + user.dy }
}

/** Zoom by `factor` keeping the screen point (px, py) over the same map point. */
export function zoomAt(user: UserView, factor: number, px: number, py: number, width: number, height: number): UserView {
  const s = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, user.s * factor))
  const f = s / user.s
  const cx = width / 2
  const cy = height / 2
  return { s, dx: px - cx - f * (px - cx - user.dx), dy: py - cy - f * (py - cy - user.dy) }
}

/** Mean position of each group's topics (key = group index). */
export function groupCentroids(points: readonly MapPoint[]): Map<number, { x: number; y: number; n: number }> {
  const acc = new Map<number, { x: number; y: number; n: number }>()
  for (const p of points) {
    if (p.groupIndex < 0) continue
    const a = acc.get(p.groupIndex) ?? { x: 0, y: 0, n: 0 }
    acc.set(p.groupIndex, { x: a.x + p.x, y: a.y + p.y, n: a.n + 1 })
  }
  return new Map([...acc].map(([g, a]) => [g, { x: a.x / a.n, y: a.y / a.n, n: a.n }]))
}

/**
 * Field names centred on their group, biggest groups first; a name that would collide with another field name or leave
 * the frame is dropped. A name over status markers (`obstacles`) steps one line up or down, or a third of its width
 * sideways, to a clear spot; if none is clear it is skipped (the gazetteer and the legend still name every field).
 */
export function placeCentered(cands: readonly { id: string; text: string; width: number; height: number; x: number; y: number }[], frame: Box, obstacles: readonly Box[] = []): PlacedLabel[] {
  const placed: PlacedLabel[] = []
  for (const c of cands) {
    const line = c.height + 6
    const at = ([dx, dy]: [number, number]): Box => ({ x: c.x + dx - c.width / 2, y: c.y + dy - c.height, w: c.width, h: c.height + 4 })
    const usable = (b: Box) => b.x >= frame.x && b.y >= frame.y && b.x + b.w <= frame.x + frame.w && b.y + b.h <= frame.y + frame.h && !placed.some((p) => overlaps(p.box, b, 8))
    const shifts: [number, number][] = [[0, 0], [0, -line], [0, line], [-c.width / 3, 0], [c.width / 3, 0]]
    const clear = shifts.find((s) => usable(at(s)) && !obstacles.some((o) => overlaps(o, at(s), 2)))
    const shift = clear
    if (shift) placed.push({ id: c.id, text: c.text, x: c.x + shift[0], y: c.y + shift[1], anchor: 'middle', box: at(shift) })
  }
  return placed
}
