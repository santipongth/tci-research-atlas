import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { docShardOf, fnv1a32, ignoredWords, indexShardOf, keepWord, normalise, queryTokens, TOKENIZER_VERSION } from './searchTokens'

/** The parity fixture written from pipeline/atlas/search_index.py — the browser must cut queries exactly like it. */
interface Parity {
  tokenizer_version: number
  max_token_chars: number
  index_shards: number
  docs_per_shard: number
  stopwords: string[]
  vocab: string[]
  queries: { q: string; known: string[]; unknown: string[] }[]
  fnv1a32: { s: string; hash: number; shard: number }[]
  doc_shards: { ordinal: number; shard: number }[]
}

const parity = JSON.parse(readFileSync(fileURLToPath(new URL('../../../pipeline/tests/fixtures/search_parity.json', import.meta.url)), 'utf8')) as Parity
const vocab = new Set(parity.vocab)
const stop = new Set(parity.stopwords)

describe('ignoredWords', () => {
  const stopwords = new Set(['การ', 'the'])
  const words = new Set(['ผู้สูงอายุ', 'ageing'])
  it('names the stopwords of a query, which queryTokens consumes without a word', () => {
    expect(ignoredWords('การ', words, stopwords, 20)).toEqual(['การ'])
    expect(queryTokens('การ', words, stopwords, 20)).toEqual({ known: [], unknown: [] })
    expect(ignoredWords('the ageing', words, stopwords, 20)).toEqual(['the'])
    expect(ignoredWords('การผู้สูงอายุ', words, stopwords, 20)).toEqual(['การ'])
  })
  it('says nothing when no stopword was used', () => {
    expect(ignoredWords('ผู้สูงอายุ ageing', words, stopwords, 20)).toEqual([])
  })
})

describe('searchTokens parity with atlas.search_index', () => {
  it('uses the same tokenizer version', () => {
    expect(TOKENIZER_VERSION).toBe(parity.tokenizer_version)
  })

  it.each(parity.queries)('cuts "$q" like the pipeline', ({ q, known, unknown }) => {
    expect(queryTokens(q, vocab, stop, parity.max_token_chars)).toEqual({ known, unknown })
  })

  it.each(parity.fnv1a32)('hashes "$s" with FNV-1a over UTF-8 and picks its index shard', ({ s, hash, shard }) => {
    expect(fnv1a32(s)).toBe(hash)
    expect(indexShardOf(s, parity.index_shards)).toBe(shard)
  })

  it.each(parity.doc_shards)('puts ordinal $ordinal in doc shard $shard', ({ ordinal, shard }) => {
    expect(docShardOf(ordinal, parity.docs_per_shard)).toBe(shard)
  })

  it('normalises Thai digits, the decomposed SARA AM and case', () => {
    const am = String.fromCodePoint(0x0e33)
    expect(normalise(`${String.fromCodePoint(0x0e52, 0x0e55, 0x0e56, 0x0e53)} ABC`)).toBe('2563 abc')
    expect(normalise(`${String.fromCodePoint(0x0e19, 0x0e4d, 0x0e32)}`)).toBe(`${String.fromCodePoint(0x0e19)}${am}`)
  })

  it('keeps 4-digit years and drops other numbers, single characters and stopwords', () => {
    expect(keepWord('2563', stop)).toBe(true)
    expect(keepWord('19', stop)).toBe(false)
    expect(keepWord('a', stop)).toBe(false)
    expect(keepWord('the', stop)).toBe(false)
    expect(keepWord('covid', stop)).toBe(true)
  })
})
