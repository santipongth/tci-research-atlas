import { THAI } from './script'

/** Split a sentence into plain text, figures to highlight and topic names to link (Editorial headline). */
export type Segment = { kind: 'text'; text: string } | { kind: 'figure'; text: string } | { kind: 'topic'; text: string; id: string }

interface Named {
  id: string
  th: string
  en: string
}

// A number (Arabic or Thai digits) with an optional sign and unit, not glued to a Latin letter, digit or hyphen
// (so "COVID-19" and "2026Q4" stay plain text).
const FIGURE = /(?<![A-Za-z0-9.,\-−])[+−-]?(?:\d[\d,]*(?:\.\d+)?|[๐-๙][๐-๙,]*(?:\.[๐-๙]+)?)(?![A-Za-z0-9])(?:\s?(?:%|×|เท่า))?/g
const YEAR = /^(19|20)\d{2}$/

/** A Thai name shorter than this is not linked: a 5-letter Thai word turns up inside unrelated words (Thai has no spaces to stop it). */
export const MIN_THAI_NAME = 8
// Thai syllable edges: a name may not start on a vowel or tone mark that only follows a consonant, nor sit right after a
// leading vowel (เ แ โ ใ ไ), nor end on one — each would cut a syllable in two.
const NO_START = 'ะัาำิีึืฺุู็่้๊๋์ํๆฯ'
const LEADING = 'เแโใไ'
function atSyllableEdge(text: string, start: number, end: number): boolean {
  if (NO_START.includes(text.charAt(start))) return false
  if (start > 0 && LEADING.includes(text.charAt(start - 1))) return false
  return !LEADING.includes(text.charAt(end - 1))
}

const words = typeof Intl !== 'undefined' && 'Segmenter' in Intl ? new Intl.Segmenter('th', { granularity: 'word' }) : null

/**
 * Offsets where a word starts or ends (Intl.Segmenter's Thai dictionary, plus every switch between Thai and other
 * script: ICU keeps "และAI" as one word); null when the browser has no Segmenter.
 */
function wordEdges(text: string): Set<number> | null {
  if (!words) return null
  const edges = new Set<number>([text.length])
  for (const s of words.segment(text)) edges.add(s.index)
  for (let k = 1; k < text.length; k++) if (THAI.test(text.charAt(k - 1)) !== THAI.test(text.charAt(k))) edges.add(k)
  return edges
}

/**
 * A Thai name links only when it starts and ends on word edges: "การปลูกข้าว" is not linked inside "การปลูกข้าวโพด",
 * nor "การจัดการน้ำ" inside "การจัดการน้ำมันรั่วไหล". Without Segmenter the syllable rule above is the fallback.
 */
function thaiNameFits(text: string, edges: Set<number> | null, start: number, end: number): boolean {
  if (!atSyllableEdge(text, start, end)) return false
  return edges === null || (edges.has(start) && edges.has(end))
}

export function segmentHeadline(text: string, topics: readonly Named[], opts: { figures?: boolean; minNameLength?: number } = {}): Segment[] {
  const figures = opts.figures ?? true
  const minLength = opts.minNameLength ?? 4
  const names = topics
    .flatMap((t) => [t.th, t.en].filter((n) => n && n.length >= (THAI.test(n) ? Math.max(minLength, MIN_THAI_NAME) : minLength)).map((name) => ({ id: t.id, name: name.toLowerCase(), thai: THAI.test(name) })))
    .sort((a, b) => b.name.length - a.name.length)
  const lower = text.toLowerCase()
  const edges = names.some((n) => n.thai) ? wordEdges(lower) : null
  const taken: { start: number; end: number; id: string }[] = []
  for (const { id, name, thai } of names) {
    for (let from = 0, i = lower.indexOf(name); i >= 0; from = i + name.length, i = lower.indexOf(name, from)) {
      const end = i + name.length
      if (thai && !thaiNameFits(lower, edges, i, end)) continue
      if (!taken.some((r) => i < r.end && end > r.start)) taken.push({ start: i, end, id })
    }
  }
  taken.sort((a, b) => a.start - b.start)

  const out: Segment[] = []
  const pushText = (s: string) => {
    if (!s) return
    if (!figures) {
      out.push({ kind: 'text', text: s })
      return
    }
    let last = 0
    for (const m of s.matchAll(FIGURE)) {
      const value = m[0]
      const start = m.index ?? 0
      if (YEAR.test(value.replace(/^[+−-]/, ''))) continue
      if (start > last) out.push({ kind: 'text', text: s.slice(last, start) })
      out.push({ kind: 'figure', text: value })
      last = start + value.length
    }
    if (last < s.length) out.push({ kind: 'text', text: s.slice(last) })
  }
  let pos = 0
  for (const r of taken) {
    pushText(text.slice(pos, r.start))
    out.push({ kind: 'topic', text: text.slice(r.start, r.end), id: r.id })
    pos = r.end
  }
  pushText(text.slice(pos))
  return out
}
