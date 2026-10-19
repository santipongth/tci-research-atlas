/** Dash pattern per compare-series slot: the secondary encoding next to colour (--series-1…4) and the end label. */
export const SERIES_DASHES = ['', '8 4', '3 3', '10 3 2 3'] as const

/**
 * Colour/dash slot (0–3) per chosen topic. A topic keeps the slot it already had, so removing one topic never repaints
 * the others (colour follows the topic, not its position); a newcomer takes the lowest free slot.
 */
export function assignSlots(ids: readonly string[], previous: Readonly<Record<string, number>> = {}): Record<string, number> {
  const out: Record<string, number> = {}
  const used = new Set<number>()
  for (const id of ids) {
    const s = previous[id]
    if (s !== undefined && Number.isInteger(s) && s >= 0 && s < SERIES_DASHES.length && !used.has(s)) {
      out[id] = s
      used.add(s)
    }
  }
  for (const id of ids) {
    if (out[id] !== undefined) continue
    let s = 0
    while (used.has(s)) s++
    out[id] = s
    used.add(s)
  }
  return out
}
