/** The data contract v2 types the web uses — generated from pipeline/atlas/schema/contract.py (never edit contract.ts).
 *  Nested types are derived by indexed access: json-schema-to-typescript names interfaces after titles, and a field
 *  titled "Topic" (EmergingKeyword.topic) pushes the Topic model to `Topic1` — container names are stable, nested ones are not. */
import type { EdgesFile, KeywordsFile, Latest, Overview, TaxonomyFile, TopicDetail, TopicsFile } from './contract'

export type { EdgesFile, KeywordsFile, Latest, Manifest, Overview, SeriesFile, TaxonomyFile, TopicDetail, TopicsFile } from './contract'

export type Topic = TopicsFile['topics'][number]
export type TopicMetrics = Topic['metrics']
export type TopicForecast = NonNullable<Topic['forecast']>
export type TopicNowcast = NonNullable<Topic['nowcast']>
export type Status = Topic['status']
export type GroupInfo = TaxonomyFile['groups'][number]
export type EmergingKeyword = KeywordsFile['keywords'][number]
export type Edge = EdgesFile['edges'][number]
export type Kpis = Overview['kpis']
export type Brief = NonNullable<Overview['brief']>
export type RepresentativeArticle = TopicDetail['articles'][number]
export type CountItem = NonNullable<TopicDetail['journals']>[number]

/** What `atlas publish` embeds in the offline HTML: the newest release only. */
export interface Bundle {
  latest: Latest
  files: Record<string, unknown>
}
