/**
 * The quarterly story's share images: a 1080 × 1080 PNG per fact, drawn on a canvas in the browser (no server, no
 * third-party request). `wrapLines` is pure (tested); `drawStoryCard` paints one card.
 */

export interface StoryCardText {
  /** "1 / 5" */
  index: string
  big: string
  line: string
  sub: string
  /** "ที่มา: TCI Research Atlas · รอบ 2026Q4" */
  footer: string
  /** "ข้อมูลตัวอย่าง" on synthetic releases, else null */
  sample: string | null
}

/**
 * Break text into lines no wider than `max`, at the segment boundaries `segment` returns (Thai has no spaces between
 * words, so the caller passes a word segmenter). A single segment wider than `max` gets a line of its own.
 */
export function wrapLines(text: string, max: number, measure: (s: string) => number, segment: (s: string) => string[]): string[] {
  const lines: string[] = []
  let cur = ''
  for (const part of segment(text)) {
    const next = cur + part
    if (cur && measure(next.trimEnd()) > max) {
      lines.push(cur.trimEnd())
      cur = part.trimStart()
    } else {
      cur = next
    }
  }
  if (cur.trim()) lines.push(cur.trimEnd())
  return lines
}

/** Word segments for Thai and English (Intl.Segmenter; falls back to spaces). */
export function segmentWords(text: string): string[] {
  if (typeof Intl !== 'undefined' && 'Segmenter' in Intl) {
    const seg = new Intl.Segmenter('th', { granularity: 'word' })
    return [...seg.segment(text)].map((x) => x.segment)
  }
  return text.split(/(?<=\s)/)
}

const C = { bg: '#ffffff', ink: '#14182b', ink2: '#4d536b', ink3: '#6b7088', brand: '#283894', mark: '#e07000', rule: '#e6e8f0', sampleBg: '#fcefd3', sampleInk: '#573700' }
const FONT = '"Sarabun", "Noto Sans Thai", sans-serif'

/** Paint one card on a 1080 × 1080 canvas: logo + index, the big number, an orange rule, the line, the sub line, the footer. */
export function drawStoryCard(canvas: HTMLCanvasElement, card: StoryCardText, logo: HTMLImageElement | null): void {
  const S = 1080
  const M = 96
  canvas.width = S
  canvas.height = S
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.fillStyle = C.bg
  ctx.fillRect(0, 0, S, S)
  ctx.textBaseline = 'alphabetic'
  if (logo && logo.naturalWidth) {
    const h = 84
    ctx.drawImage(logo, M, M - 10, (logo.naturalWidth / logo.naturalHeight) * h, h)
  }
  ctx.fillStyle = C.ink3
  ctx.font = `600 34px ${FONT}`
  ctx.textAlign = 'right'
  ctx.fillText(card.index, S - M, M + 44)
  ctx.textAlign = 'left'
  ctx.fillStyle = C.brand
  ctx.font = `700 34px ${FONT}`
  ctx.fillText('TCI Research Atlas', M, M + 140)

  ctx.fillStyle = C.brand
  ctx.font = `700 168px ${FONT}`
  ctx.fillText(card.big, M - 6, 470)
  ctx.fillStyle = C.mark
  ctx.fillRect(M, 512, 132, 12)

  const measure = (s: string) => ctx.measureText(s).width
  let y = 618
  ctx.fillStyle = C.ink
  ctx.font = `700 60px ${FONT}`
  for (const l of wrapLines(card.line, S - 2 * M, measure, segmentWords).slice(0, 3)) {
    ctx.fillText(l, M, y)
    y += 84
  }
  y += 10
  ctx.fillStyle = C.ink2
  ctx.font = `400 38px ${FONT}`
  for (const l of wrapLines(card.sub, S - 2 * M, measure, segmentWords).slice(0, 3)) {
    ctx.fillText(l, M, y)
    y += 56
  }

  ctx.fillStyle = C.rule
  ctx.fillRect(M, S - M - 58, S - 2 * M, 2)
  ctx.fillStyle = C.ink3
  ctx.font = `400 30px ${FONT}`
  ctx.fillText(card.footer, M, S - M)
  if (card.sample) {
    ctx.font = `700 28px ${FONT}`
    const w = ctx.measureText(card.sample).width + 36
    ctx.fillStyle = C.sampleBg
    ctx.fillRect(S - M - w, S - M - 38, w, 50)
    ctx.fillStyle = C.sampleInk
    ctx.fillText(card.sample, S - M - w + 18, S - M - 2)
  }
}
