/**
 * "Match my abstract" (R3) and "where to publish" (R4), entirely in the browser: no model download, nothing sent.
 * The analyzer is the pipeline's (pipeline/atlas/matcher.py): foldText (search.ts) then char_wb trigrams — every
 * space-separated word padded with one space each side, every 3-character slice (a padded word of ≤ 3 characters
 * is one gram). Slices are cut by CODE POINT (Array.from), as Python does, so an astral character is one character.
 * foldText collapses exactly the JavaScript \s class, which the pipeline's fold reproduces (_JS_SPACE).
 * pipeline/tests/fixtures/match_parity.json pins both implementations to the same output.
 * Query weight = (1 + ln tf) · idf over the grams the index knows; topics are ranked by cosine similarity;
 * journals by Σ over the closest fit_topics topics of (similarity share) × (the topic's share of the journal).
 */
import type { MatchIndex } from '../data/types'
import { foldText } from './search'

export function charGrams(folded: string): string[] {
  const out: string[] = []
  for (const word of folded ? folded.split(' ') : []) {
    const w = Array.from(` ${word} `)
    if (w.length <= 3) out.push(w.join(''))
    else for (let i = 0; i + 3 <= w.length; i++) out.push(w.slice(i, i + 3).join(''))
  }
  return out
}

export function analyze(text: string): string[] {
  return charGrams(foldText(text))
}

/** Characters that count toward match.min_query_chars (folded, spaces collapsed). */
export function queryLength(text: string): number {
  return Array.from(foldText(text)).length
}

export interface PreparedIndex {
  index: MatchIndex
  pos: Map<string, number>
}

export function prepareIndex(index: MatchIndex): PreparedIndex {
  return { index, pos: new Map(index.grams.map((g, i) => [g, i])) }
}

/** Unit-length query vector over the index's grams (gram position → weight). */
export function queryVector(p: PreparedIndex, text: string): Map<number, number> {
  const tf = new Map<number, number>()
  for (const g of analyze(text)) {
    const i = p.pos.get(g)
    if (i !== undefined) tf.set(i, (tf.get(i) ?? 0) + 1)
  }
  const q = new Map<number, number>()
  let norm = 0
  for (const [i, n] of tf) {
    const v = (1 + Math.log(n)) * p.index.idf[i]
    q.set(i, v)
    norm += v * v
  }
  norm = Math.sqrt(norm) || 1
  for (const [i, v] of q) q.set(i, v / norm)
  return q
}

export interface TopicHit {
  id: string
  score: number
}

/** Topics with cosine ≥ index.min_similarity, best first (ties by id). */
export function rankTopics(p: PreparedIndex, text: string, limit = 10): TopicHit[] {
  const q = queryVector(p, text)
  if (q.size === 0) return []
  const hits: TopicHit[] = []
  for (const t of p.index.topics) {
    let s = 0
    for (let k = 0; k < t.terms.length; k++) s += (q.get(t.terms[k]) ?? 0) * t.weights[k]
    if (s >= p.index.min_similarity) hits.push({ id: t.id, score: s })
  }
  hits.sort((a, b) => b.score - a.score || a.id.localeCompare(b.id))
  return hits.slice(0, limit)
}

export interface JournalFit {
  id: string
  fit: number
  /** the closest topics this journal publishes in, with their share of its articles */
  topics: { id: string; share: number }[]
}

/** Journals ranked by fit = Σ_t w_t · share_j(t) over the fit_topics best topic hits, w_t = score_t / Σ score. */
export function rankJournals(index: MatchIndex, hits: readonly TopicHit[], limit = 8): JournalFit[] {
  const top = hits.slice(0, index.fit_topics)
  const total = top.reduce((a, h) => a + h.score, 0)
  if (!total) return []
  const weight = new Map(top.map((h) => [h.id, h.score / total]))
  const out: JournalFit[] = []
  for (const j of index.journals ?? []) {
    let fit = 0
    const topics: { id: string; share: number }[] = []
    j.topics.forEach((tid, k) => {
      const w = weight.get(tid)
      if (w !== undefined) {
        fit += w * j.shares[k]
        topics.push({ id: tid, share: j.shares[k] })
      }
    })
    if (fit > 0) out.push({ id: j.id, fit, topics })
  }
  out.sort((a, b) => b.fit - a.fit || a.id.localeCompare(b.id))
  return out.slice(0, limit)
}
