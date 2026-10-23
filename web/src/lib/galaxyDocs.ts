import type { SearchDocRow } from '../data/types'

/**
 * The article rows behind the galaxy (/galaxy): search/docs-<NNN>.json holds the rows of ordinals start … start + n − 1,
 * and a galaxy point's index is its ordinal (atlas.search_index.doc_order). The word index of search/ is no longer read.
 */
export interface GalaxyDoc {
  ordinal: number
  id: string
  titleTh: string
  titleEn: string
  year: number
  journal: string
  topic: string | null
  doi: string | null
  url: string | null
  cited: number
}

/** One docs-shard row as a document (the journal is an index into the shard's journal list). */
export function rowToDoc(row: SearchDocRow, ordinal: number, journals: readonly string[]): GalaxyDoc {
  const [id, titleTh, titleEn, year, j, topic, doi, url, cited] = row
  return { ordinal, id, titleTh, titleEn, year, journal: journals[j] ?? '', topic, doi, url, cited }
}

/** search/docs-<NNN>.json that holds a doc ordinal's row. */
export function docShardOf(ordinal: number, docsPerShard: number): number {
  return Math.floor(ordinal / docsPerShard)
}
