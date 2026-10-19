/** The data contract v2 types the web uses — generated from pipeline/atlas/schema/contract.py (never edit contract.ts).
 *  Nested types are derived by indexed access: json-schema-to-typescript names interfaces after titles, and a field
 *  titled "Topic" (EmergingKeyword.topic) pushes the Topic model to `Topic1` — container names are stable, nested ones are not. */
import type {
  DiffFile, EdgesFile, JournalDetail, JournalsFile, KeywordsFile, Latest, MatchIndex, MethodsFile, Overview, TaxonomyFile, TopicDetail, TopicsFile,
} from './contract'

export type {
  DiffFile, EdgesFile, JournalDetail, JournalsFile, KeywordsFile, Latest, Manifest, MatchIndex, MethodsFile, Overview, SeriesFile, TaxonomyFile, TopicDetail, TopicsFile,
} from './contract'

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

/* P2 editors' modules (contract 2.1) — optional files listed in manifest.modules */
export type JournalSummary = JournalsFile['journals'][number]
export type SpecialIssueTopic = NonNullable<JournalsFile['special_issue']>[number]
export type YearWindow = JournalsFile['window']
export type TopicShare = NonNullable<JournalDetail['topics']>[number]
export type DriftPoint = NonNullable<JournalDetail['drift']>[number]
export type TopicShift = NonNullable<JournalDetail['gained']>[number]
export type Peer = NonNullable<JournalDetail['peers']>[number]
export type CompletenessItem = NonNullable<JournalDetail['completeness']>[number]
export type MethodShare = NonNullable<JournalDetail['methods']>[number]
export type JournalOpportunity = NonNullable<JournalDetail['opportunities']>[number]
export type TopicMethods = MethodsFile['topics'][number]
export type MethodInfo = MethodsFile['methods'][number]
export type KpiChange = DiffFile['kpis'][number]
export type NewTopic = DiffFile['new_topics'][number]
export type RetiredTopic = DiffFile['retired'][number]
export type StatusChange = DiffFile['status_changes'][number]
export type Mover = DiffFile['movers'][number]
export type MatchTopic = MatchIndex['topics'][number]
export type MatchJournal = NonNullable<MatchIndex['journals']>[number]

/** What `atlas publish` embeds in the offline HTML: the newest release only. */
export interface Bundle {
  latest: Latest
  files: Record<string, unknown>
}
