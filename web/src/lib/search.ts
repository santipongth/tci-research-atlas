/**
 * Topic search in Thai and English, entirely in the browser.
 * Text is folded before matching: Thai tone marks and other above-marks (U+0E47–U+0E4C) are removed, the decomposed
 * sara am (U+0E4D U+0E32) is joined, zero-width characters vanish, Latin is lower-cased without accents — so text damaged
 * by PDF conversion ("ความตองการ") still finds "ความต้องการ". Thai words come from Intl.Segmenter('th').
 */
const ABOVE_MARKS = /[็-์]/g
const INVISIBLE = /[\u200B-\u200D\uFEFF\u00AD]/g
const DECOMPOSED_AM = /ํา/g
const LATIN_ACCENTS = /[̀-ͯ]/g

export function foldText(s: string): string {
  return s
    .normalize('NFC')
    .replace(DECOMPOSED_AM, 'ำ')
    .replace(INVISIBLE, '')
    .normalize('NFD')
    .replace(LATIN_ACCENTS, '')
    .replace(ABOVE_MARKS, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim()
}

const segmenter = typeof Intl !== 'undefined' && 'Segmenter' in Intl ? new Intl.Segmenter('th', { granularity: 'word' }) : null

export function segmentWords(s: string): string[] {
  if (!segmenter) return s.split(/\s+/).filter(Boolean)
  return [...segmenter.segment(s)].filter((x) => x.isWordLike).map((x) => x.segment)
}

export interface SearchDoc {
  id: string
  th: string
  en: string
  keywords: readonly string[]
  size: number
}

interface Indexed {
  id: string
  size: number
  names: string[]
  nameWords: string[]
  keywords: string
}

export interface SearchIndex {
  docs: Indexed[]
}

export function buildSearchIndex(docs: readonly SearchDoc[]): SearchIndex {
  return {
    docs: docs.map((d) => {
      const names = [d.th, d.en].map(foldText).filter(Boolean)
      return { id: d.id, size: d.size, names, nameWords: names.flatMap((n) => segmentWords(n)), keywords: d.keywords.map(foldText).join(' | ') }
    }),
  }
}

export interface SearchHit {
  id: string
  score: number
}

/** Name exact 100 · name prefix 80 · name contains 60 · every word in the name 40 · keyword phrase 30 · every word in keywords 20. */
export function searchTopics(index: SearchIndex, query: string, limit = 10): SearchHit[] {
  const q = foldText(query)
  if (!q) return []
  const tokens = segmentWords(q)
  const hits: (SearchHit & { size: number })[] = []
  for (const d of index.docs) {
    let score = 0
    for (const n of d.names) {
      if (n === q) score = Math.max(score, 100)
      else if (n.startsWith(q)) score = Math.max(score, 80)
      else if (n.includes(q)) score = Math.max(score, 60)
    }
    if (score === 0 && tokens.length > 0 && tokens.every((tk) => d.nameWords.some((w) => w.startsWith(tk)) || d.names.some((n) => n.includes(tk)))) score = 40
    if (score === 0 && d.keywords.includes(q)) score = 30
    if (score === 0 && tokens.length > 0 && tokens.every((tk) => d.keywords.includes(tk))) score = 20
    if (score > 0) hits.push({ id: d.id, score, size: d.size })
  }
  hits.sort((a, b) => b.score - a.score || b.size - a.size || a.id.localeCompare(b.id))
  return hits.slice(0, limit).map(({ id, score }) => ({ id, score }))
}
