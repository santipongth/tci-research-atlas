import { useEffect, useMemo, useState } from 'react'
import { useAtlas, useReleaseFile } from '../data/atlasContext'
import { createSearchFiles, SEARCH_VOCAB } from '../data/release'
import type { SearchMeta, SearchVocab } from '../data/types'
import { makeSource, runSearch, type SearchOutcome, type SearchSource } from './searchClient'

export type SourceState = { status: 'loading' | 'missing' | 'error'; source: null; vocab: null } | { status: 'ready'; source: SearchSource; vocab: SearchVocab }

/** search/vocab.json → a ready-to-query source over the release's sharded index (files cached by the release loader). */
export function useSearchSource(meta: SearchMeta): SourceState {
  const atlas = useAtlas()
  const file = atlas.status === 'ready' ? atlas.file : null
  const vocab = useReleaseFile<SearchVocab>(SEARCH_VOCAB)
  return useMemo<SourceState>(() => {
    if (vocab.status !== 'ready' || !file) return { status: vocab.status === 'ready' ? 'loading' : vocab.status, source: null, vocab: null }
    return { status: 'ready', source: makeSource(meta, vocab.data, createSearchFiles(file)), vocab: vocab.data }
  }, [meta, vocab, file])
}

export type SearchState = { status: 'idle' | 'loading' | 'error'; outcome: null } | { status: 'ready'; outcome: SearchOutcome }

/** The outcome of one query, keyed by (source, query) so a new query never shows the previous results. */
export function useArticleSearch(source: SearchSource | null, q: string): SearchState {
  const query = q.trim()
  const [entry, setEntry] = useState<{ source: SearchSource; q: string; result: SearchState } | null>(null)
  useEffect(() => {
    if (!source || !query) return
    let alive = true
    runSearch(source, query).then(
      (outcome) => {
        if (alive) setEntry({ source, q: query, result: { status: 'ready', outcome } })
      },
      () => {
        if (alive) setEntry({ source, q: query, result: { status: 'error', outcome: null } })
      },
    )
    return () => {
      alive = false
    }
  }, [source, query])
  if (!query) return { status: 'idle', outcome: null }
  return entry && entry.source === source && entry.q === query ? entry.result : { status: 'loading', outcome: null }
}
