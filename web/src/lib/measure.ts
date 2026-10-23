let ctx: CanvasRenderingContext2D | null | undefined

/** Rendered width of a label in Sarabun (canvas measureText); a character estimate where no canvas exists. */
export function textWidth(text: string, px: number, weight = 600): number {
  if (ctx === undefined) ctx = typeof document !== 'undefined' ? document.createElement('canvas').getContext('2d') : null
  if (!ctx) return text.length * px * 0.58
  ctx.font = `${weight} ${px}px Sarabun, "Noto Sans Thai", system-ui, sans-serif`
  return ctx.measureText(text).width
}

const hasSegmenter = typeof Intl !== 'undefined' && 'Segmenter' in Intl
const wordSeg = hasSegmenter ? new Intl.Segmenter('th', { granularity: 'word' }) : null
const graphemeSeg = hasSegmenter ? new Intl.Segmenter('th', { granularity: 'grapheme' }) : null

/**
 * `text` shortened with "…" so it is at most `max` px wide, cut after the last whole word that fits (Thai words from
 * Intl.Segmenter), or after the last whole grapheme when even the first word is too long — never between a Thai
 * consonant and its vowel or tone marks. Returns the text unchanged when it fits.
 */
export function fitText(text: string, max: number, px: number, weight = 600, measure: (s: string, px: number, weight: number) => number = textWidth): string {
  if (measure(text, px, weight) <= max) return text
  const fits = (s: string) => measure(`${s}…`, px, weight) <= max
  const words = wordSeg ? [...wordSeg.segment(text)].map((s) => s.segment) : text.split(/(?<=\s)/)
  let out = ''
  for (const w of words) {
    if (!fits(out + w)) break
    out += w
  }
  if (!out.trim()) {
    const parts = graphemeSeg ? [...graphemeSeg.segment(text)].map((g) => g.segment) : [...text]
    out = ''
    for (const g of parts) {
      if (!fits(out + g)) break
      out += g
    }
  }
  return `${out.trimEnd()}…`
}
