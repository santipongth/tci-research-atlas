/** Collision-aware label placement shared by the terrain map and the portfolio matrix (screen pixels). The executive
 *  charts' point labels use charts/execLayout.ts placeLabels (see the note there for why both exist). */
export interface Box {
  x: number
  y: number
  w: number
  h: number
}

export function overlaps(a: Box, b: Box, pad = 0): boolean {
  return !(a.x + a.w + pad < b.x || b.x + b.w + pad < a.x || a.y + a.h + pad < b.y || b.y + b.h + pad < a.y)
}

/** A Thai line is taller than its font size: tone marks and stacked vowels rise to ~1 em above the baseline and tails fall ~0.3 em below. */
export const THAI_ASCENT = 1.0
export const THAI_LINE = 1.3
/**
 * Room kept on each side (left and right) of a measured label: the box is the text width plus 2 × LABEL_PAD.
 * Vertically the Thai line box (THAI_ASCENT, THAI_LINE) already holds the halo. 1 px a side, not the halo's full 2 px:
 * two halos may touch but never the glyphs, and the wider box left a 390 px phone map with a single name once the
 * text is measured with Linux font metrics. Used by every label layout (placeLabels here, features/atlas/mapSpace.ts).
 */
export const LABEL_PAD = 1

export interface LabelCandidate {
  id: string
  text: string
  width: number
  height: number
  x: number
  y: number
  radius: number
}

export interface PlacedLabel {
  id: string
  text: string
  x: number
  y: number
  anchor: 'start' | 'middle' | 'end'
  box: Box
}

/**
 * Greedy label placement around each mark (right, left, above, below), in candidate order. A label is skipped when
 * every position leaves the frame or hits a placed label or an obstacle (marks — except its own — and field labels).
 * Ids in `force` (hovered, selected) are always placed, above the mark if nothing else fits.
 */
export function placeLabels(cands: readonly LabelCandidate[], obstacles: readonly (Box & { id?: string })[], frame: Box, force: ReadonlySet<string> = new Set()): PlacedLabel[] {
  const placed: PlacedLabel[] = []
  for (const c of cands) {
    const options: [number, number, PlacedLabel['anchor']][] = [
      [c.x + c.radius + 5, c.y + c.height / 3, 'start'],
      [c.x - c.radius - 5, c.y + c.height / 3, 'end'],
      [c.x, c.y - c.radius - 7, 'middle'],
      [c.x, c.y + c.radius + c.height + 2, 'middle'],
    ]
    // the box covers the whole Thai line (tone marks above the baseline, tails below) and the outline halo
    const boxOf = (x: number, y: number, anchor: PlacedLabel['anchor']): Box => ({
      x: (anchor === 'start' ? x : anchor === 'end' ? x - c.width : x - c.width / 2) - LABEL_PAD,
      y: y - c.height * THAI_ASCENT,
      w: c.width + 2 * LABEL_PAD,
      h: c.height * THAI_LINE,
    })
    const inFrame = (b: Box) => b.x >= frame.x && b.y >= frame.y && b.x + b.w <= frame.x + frame.w && b.y + b.h <= frame.y + frame.h
    const free = (b: Box) => !placed.some((p) => overlaps(p.box, b, 4)) && !obstacles.some((o) => o.id !== c.id && overlaps(o, b, 2))
    const hit = options.find(([x, y, a]) => inFrame(boxOf(x, y, a)) && free(boxOf(x, y, a)))
    const chosen = hit ?? (force.has(c.id) ? options[2] : undefined)
    if (chosen) placed.push({ id: c.id, text: c.text, x: chosen[0], y: chosen[1], anchor: chosen[2], box: boxOf(chosen[0], chosen[1], chosen[2]) })
  }
  return placed
}
