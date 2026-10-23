/**
 * Query tokenisation of the whole-corpus article search (R2) — the browser twin of
 * pipeline/atlas/search_index.py `normalise`, `runs`, `keep_word`, `query_tokens` and `fnv1a32`,
 * pinned by pipeline/tests/fixtures/search_parity.json (searchTokens.test.ts).
 *
 * Text is normalised (NFC, NIKHAHIT + SARA AA → SARA AM, lower case, Thai digits → 0–9) and cut into runs: a Thai run is
 * a maximal run of Thai letters, vowels and marks (U+0E01–0E2E, U+0E30–0E3A, U+0E40–0E45, U+0E47–0E4E); a word run is a
 * maximal run of other letters/digits outside the Thai block; everything else separates. Word runs are kept when they
 * pass `keepWord` (known if in the vocabulary, else unknown); Thai runs are matched greedily against the vocabulary
 * (longest substring first, stopwords consumed silently, unmatched stretches of ≥ 2 code points reported as unknown).
 */
const cp = (...xs: number[]) => String.fromCodePoint(...xs)
const NIKHAHIT_SARA_AA = cp(0x0e4d, 0x0e32)
const SARA_AM = cp(0x0e33)
const THAI_ZERO = 0x0e50
const LETTER_OR_NUMBER = /^[\p{L}\p{N}]$/u
const ALL_DECIMAL = /^\p{Nd}+$/u

export const TOKENIZER_VERSION = 1

function isThai(c: number): boolean {
  return (c >= 0x0e01 && c <= 0x0e2e) || (c >= 0x0e30 && c <= 0x0e3a) || (c >= 0x0e40 && c <= 0x0e45) || (c >= 0x0e47 && c <= 0x0e4e)
}

function isWordChar(ch: string, c: number): boolean {
  return (c < 0x0e00 || c > 0x0e7f) && LETTER_OR_NUMBER.test(ch)
}

/** NFC, NIKHAHIT + SARA AA → SARA AM, lower case, Thai digits → ASCII digits (index and query alike). */
export function normalise(text: string): string {
  const s = (text ?? '').normalize('NFC').split(NIKHAHIT_SARA_AA).join(SARA_AM).toLowerCase()
  let out = ''
  for (const ch of s) {
    const c = ch.codePointAt(0) as number
    out += c >= THAI_ZERO && c <= THAI_ZERO + 9 ? String(c - THAI_ZERO) : ch
  }
  return out
}

/** [isThai, run] of the normalised text, in order. */
export function runs(text: string): [boolean, string][] {
  const out: [boolean, string][] = []
  let kind: 0 | 1 | 2 = 0 // 0 = separator, 1 = Thai, 2 = word
  let cur = ''
  for (const ch of normalise(text)) {
    const c = ch.codePointAt(0) as number
    const k: 0 | 1 | 2 = isThai(c) ? 1 : isWordChar(ch, c) ? 2 : 0
    if (k !== kind && cur) {
      out.push([kind === 1, cur])
      cur = ''
    }
    kind = k
    if (k) cur += ch
  }
  if (cur) out.push([kind === 1, cur])
  return out
}

const length = (s: string) => Array.from(s).length

/** ≥ 2 code points, not a stopword, digits only when there are exactly 4 of them (a year). */
export function keepWord(tok: string, stopwords: ReadonlySet<string>): boolean {
  const n = length(tok)
  return n >= 2 && !stopwords.has(tok) && (!ALL_DECIMAL.test(tok) || n === 4)
}

export interface QueryTokens {
  /** vocabulary words of the query (searched, AND) */
  known: string[]
  /** words not in the vocabulary — named to the user, never silently dropped */
  unknown: string[]
}

/** (known, unknown) words of a search query — greedy longest match against the vocabulary for Thai runs. */
export function queryTokens(q: string, vocab: ReadonlySet<string>, stopwords: ReadonlySet<string>, maxChars: number): QueryTokens {
  const known: string[] = []
  const unknown: string[] = []
  const add = (bucket: string[], w: string) => {
    if (!bucket.includes(w)) bucket.push(w)
  }
  for (const [thai, run] of runs(q)) {
    if (!thai) {
      if (keepWord(run, stopwords)) add(vocab.has(run) ? known : unknown, run)
      continue
    }
    const chars = Array.from(run)
    const n = chars.length
    let i = 0
    let pending = -1
    while (i < n) {
      let hit = ''
      let hitLen = 0
      for (let len = Math.min(maxChars, n - i); len > 1; len--) {
        const w = chars.slice(i, i + len).join('')
        if (vocab.has(w) || stopwords.has(w)) {
          hit = w
          hitLen = len
          break
        }
      }
      if (!hit) {
        if (pending < 0) pending = i
        i += 1
        continue
      }
      if (pending >= 0 && i - pending >= 2) add(unknown, chars.slice(pending, i).join(''))
      pending = -1
      if (!stopwords.has(hit)) add(known, hit)
      i += hitLen
    }
    if (pending >= 0 && n - pending >= 2) add(unknown, chars.slice(pending).join(''))
  }
  return { known, unknown }
}

/**
 * Stopwords the query contained: they are not searched (`queryTokens` consumes them silently), so the page says so
 * — a query of only "การ" must not read as "no article contains it". Same greedy scan as `queryTokens`; not part of the
 * parity fixtures (it never decides what is searched).
 */
export function ignoredWords(q: string, vocab: ReadonlySet<string>, stopwords: ReadonlySet<string>, maxChars: number): string[] {
  const out: string[] = []
  const add = (w: string) => {
    if (!out.includes(w)) out.push(w)
  }
  for (const [thai, run] of runs(q)) {
    if (!thai) {
      if (stopwords.has(run)) add(run)
      continue
    }
    const chars = Array.from(run)
    const n = chars.length
    let i = 0
    while (i < n) {
      let hitLen = 0
      for (let len = Math.min(maxChars, n - i); len > 1; len--) {
        const w = chars.slice(i, i + len).join('')
        if (vocab.has(w) || stopwords.has(w)) {
          hitLen = len
          if (stopwords.has(w)) add(w)
          break
        }
      }
      i += hitLen || 1
    }
  }
  return out
}

const FNV_OFFSET = 0x811c9dc5
const FNV_PRIME = 0x01000193
const utf8 = new TextEncoder()

/** FNV-1a 32-bit hash of the UTF-8 bytes of s (unsigned). */
export function fnv1a32(s: string): number {
  let h = FNV_OFFSET
  for (const b of utf8.encode(s)) h = Math.imul(h ^ b, FNV_PRIME) >>> 0
  return h >>> 0
}

/** search/idx-<NNN>.json that holds a token's postings. */
export function indexShardOf(token: string, indexShards: number): number {
  return fnv1a32(token) % indexShards
}

/** search/docs-<NNN>.json that holds a doc ordinal's row. */
export function docShardOf(ordinal: number, docsPerShard: number): number {
  return Math.floor(ordinal / docsPerShard)
}
