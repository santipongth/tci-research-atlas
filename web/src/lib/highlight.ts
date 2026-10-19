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

export function segmentHeadline(text: string, topics: readonly Named[], opts: { figures?: boolean; minNameLength?: number } = {}): Segment[] {
  const figures = opts.figures ?? true
  const minLength = opts.minNameLength ?? 4
  const names = topics
    .flatMap((t) => [t.th, t.en].filter((n) => n && n.length >= minLength).map((name) => ({ id: t.id, name: name.toLowerCase() })))
    .sort((a, b) => b.name.length - a.name.length)
  const lower = text.toLowerCase()
  const taken: { start: number; end: number; id: string }[] = []
  for (const { id, name } of names) {
    for (let from = 0, i = lower.indexOf(name); i >= 0; from = i + name.length, i = lower.indexOf(name, from)) {
      const end = i + name.length
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
