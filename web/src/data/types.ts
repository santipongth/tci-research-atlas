/** The data contract v2 types the web uses — generated from pipeline/atlas/schema/contract.py (never edit contract.ts).
 *  Nested types are derived by indexed access: json-schema-to-typescript names interfaces after titles, and a field
 *  titled "Topic" (EmergingKeyword.topic) pushes the Topic model to `Topic1` — container names are stable, nested ones are not. */
import type {
  DiffFile, EdgesFile, GalaxyFile, GapsFile, GlobalFile, InstitutionDetail, InstitutionsFile, JournalDetail, JournalsFile, KeywordsFile, KwTrendsFile, Latest, MatchIndex, MethodsFile, Overview,
  ReferencesFile, RegionsFile, SdgFile, SearchDocShard, TaxonomyFile, TopicDetail, TopicsFile,
} from './contract'

export type {
  GalaxyFile, KwTrendsFile, ReferencesFile, SearchDocShard, SearchIndexShard, SearchMeta, SearchVocab,
} from './contract'
export type {
  DiffFile, EdgesFile, GapsFile, GlobalFile, InstitutionDetail, InstitutionsFile, JournalDetail, JournalsFile, KeywordsFile, Latest, Manifest, MatchIndex, MethodsFile, Overview, RegionsFile, SdgFile, SeriesFile, TaxonomyFile, TopicDetail, TopicsFile,
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

/* P3 executives' modules (contract 2.2) — optional files listed in manifest.modules */
export type InstitutionSummary = InstitutionsFile['institutions'][number]
export type CollabEdge = NonNullable<InstitutionsFile['edges']>[number]
export type CountryCount = NonNullable<InstitutionsFile['countries']>[number]
export type ProvinceName = NonNullable<InstitutionsFile['province_names']>[number]
export type Partner = NonNullable<InstitutionDetail['partners']>[number]
export type Suggestion = NonNullable<InstitutionDetail['suggested']>[number]
export type ProvinceStat = RegionsFile['provinces'][number]
export type RegionStat = RegionsFile['regions'][number]
export type GoalStat = SdgFile['goals'][number]
export type FrameworkInfo = SdgFile['frameworks'][number]
export type SubfieldBench = GlobalFile['subfields'][number]
export type FewInstitutions = GapsFile['few_institutions'][number]
export type Bridge = GapsFile['bridges'][number]
export type WorldGap = GapsFile['world'][number]
export type Concentration = GapsFile['concentration'][number]
export type ExecutiveSummary = NonNullable<Overview['executive']>

/* P4 researchers' modules (contract 2.3) — optional files listed in manifest.modules */
/** [article_id, title_th, title_en, year, journal_index, topic id | null, doi | null, url | null, cited_in_tci] */
export type SearchDocRow = SearchDocShard['docs'][number]
export type GlossaryItem = NonNullable<TopicDetail['glossary']>[number]
export type JournalRefs = ReferencesFile['journals'][number]
export type InternalCitations = NonNullable<ReferencesFile['internal']>
export type CitedArticle = InternalCitations['top_articles'][number]
export type KeywordTrend = KwTrendsFile['keywords'][number]
export type GalaxyBounds = GalaxyFile['bounds']

/** What `atlas publish` embeds in the offline HTML: the newest release only. */
export interface Bundle {
  latest: Latest
  files: Record<string, unknown>
}
