import { DataTable, type Column } from '../components/DataTable'
import { OnThisPage } from '../components/OnThisPage'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { DICTIONARY, type DictEntry } from '../content/dictionary'
import { groupName, type AtlasRelease } from '../data/release'
import { dataUrl } from '../data/source'
import type { EmergingKeyword, Topic } from '../data/types'
import { toCsv, downloadText } from '../lib/csv'
import { fmtWindow, windows } from '../lib/definition'
import { ciPct, DASH, fmtDate, fmtInt, fmtNum, fmtPct } from '../lib/format'
import { useI18n } from '../lib/i18n'
import type { StrKey } from '../strings'

export default function DataPage() {
  const { t } = useI18n()
  return <RequireRelease title={t('data.title')}>{(release) => <OpenData release={release} />}</RequireRelease>
}

/** The release files as loaded (used to download from the offline file, where there is no data folder). */
function releaseFiles(r: AtlasRelease): Record<string, unknown> {
  const v = r.manifest.schema_version
  return {
    'manifest.json': r.manifest,
    'overview.json': r.overview,
    'taxonomy.json': r.taxonomy,
    'topics.json': { schema_version: v, topics: r.topics },
    'series.json': r.series,
    'edges.json': { schema_version: v, edges: r.edges },
    ...(r.keywords ? { 'keywords.json': { schema_version: v, keywords: r.keywords } } : {}),
  }
}

const FILE_INFO: Record<string, StrKey> = {
  'manifest.json': 'data.file.manifest',
  'overview.json': 'data.file.overview',
  'taxonomy.json': 'data.file.taxonomy',
  'topics.json': 'data.file.topics',
  'series.json': 'data.file.series',
  'edges.json': 'data.file.edges',
  'keywords.json': 'data.file.keywords',
}

const COMPLETENESS: Record<string, StrKey> = {
  median: 'data.q.method.median',
  configured: 'data.q.method.configured',
}

const QUALITY_FLAGS: Record<string, StrKey> = {
  thai_pua_repaired: 'data.flag.thai_pua_repaired',
  tone_marks_missing: 'data.flag.tone_marks_missing',
  stat_symbols_missing: 'data.flag.stat_symbols_missing',
  decode_replaced: 'data.flag.decode_replaced',
}

function OpenData({ release }: { release: AtlasRelease }) {
  const { t, lang } = useI18n()
  const rel = release.overview.release
  const files = releaseFiles(release)
  const sizes = new Map((release.manifest.files ?? []).map((f) => [f.path, f.bytes]))
  const ov = release.overview
  const dq = ov.data_quality
  const w = windows(ov.last_complete_year)
  const llmFallbacks = (release.manifest.llm ?? []).reduce((n, s) => n + s.fallback, 0)
  const labels = release.manifest.labels
  const journalDriven = release.topics.filter((tp) => tp.metrics.journal_driven).length

  const topicCsv = () =>
    toCsv<Topic>(release.topics, [
      { header: 'id', value: (r) => r.id },
      { header: 'name_th', value: (r) => r.th },
      { header: 'name_en', value: (r) => r.en },
      { header: 'group', value: (r) => r.group },
      { header: 'group_name', value: (r) => groupName(release, r.group, lang) },
      { header: 'subfield', value: (r) => r.subfield ?? '' },
      { header: 'status', value: (r) => r.status },
      { header: 'score', value: (r) => r.score },
      { header: 'count_recent', value: (r) => r.metrics.count_recent },
      { header: 'share_recent', value: (r) => r.metrics.share_recent },
      { header: 'share_baseline', value: (r) => r.metrics.share_baseline },
      { header: 'share_ratio', value: (r) => r.metrics.share_ratio },
      { header: 'no_baseline', value: (r) => r.metrics.no_baseline ?? false },
      { header: 'share_growth', value: (r) => r.metrics.share_growth },
      { header: 'share_growth_lo', value: (r) => r.metrics.share_growth_lo },
      { header: 'share_growth_hi', value: (r) => r.metrics.share_growth_hi },
      { header: 'n_journals_R', value: (r) => r.metrics.n_journals_R },
      { header: 'n_orgs_R', value: (r) => r.metrics.n_orgs_R },
      { header: 'journal_driven', value: (r) => r.metrics.journal_driven },
      { header: 'orgs_unverified', value: (r) => r.metrics.orgs_unverified ?? false },
      { header: 'low_data_reason', value: (r) => r.metrics.low_data_reason ?? '' },
      { header: 'forecast_shown', value: (r) => r.forecast?.show ?? false },
      { header: 'cross_field', value: (r) => r.cross_field ?? false },
    ])
  const seriesRows = release.topics.flatMap((tp) => (release.series.topics[tp.id] ?? []).map((count, i) => ({ id: tp.id, year: release.series.years[i], count })))
  const seriesCsv = () =>
    toCsv(seriesRows, [
      { header: 'topic_id', value: (r) => r.id },
      { header: 'year', value: (r) => r.year },
      { header: 'articles', value: (r) => r.count },
    ])
  const keywordCsv = (rows: readonly EmergingKeyword[]) =>
    toCsv(rows, [
      { header: 'term', value: (r) => r.term },
      { header: 'count_recent', value: (r) => r.count_recent },
      { header: 'share_ratio', value: (r) => r.share_ratio },
      { header: 'no_baseline', value: (r) => r.no_baseline ?? false },
      { header: 'growth', value: (r) => r.growth },
      { header: 'growth_lo', value: (r) => r.growth_lo },
      { header: 'n_active_years', value: (r) => r.n_active_years },
      { header: 'n_orgs_R', value: (r) => r.n_orgs_R },
      { header: 'n_journals_R', value: (r) => r.n_journals_R },
      { header: 'journal_driven', value: (r) => r.journal_driven },
      { header: 'emerging', value: (r) => r.emerging },
      { header: 'topic', value: (r) => r.topic ?? '' },
    ])

  const quality: { label: string; value: string; note?: string }[] = [
    { label: t('data.q.through'), value: String(ov.last_complete_year), note: (release.manifest.trimmed_years ?? []).length ? t('data.q.trimmed', { years: (release.manifest.trimmed_years ?? []).join(', ') }) : undefined },
    { label: t('data.q.completeness'), value: dq.completeness_method, note: COMPLETENESS[dq.completeness_method] ? t(COMPLETENESS[dq.completeness_method]) : undefined },
    { label: t('data.q.windows'), value: t('data.q.windowsV', { r: fmtWindow(w.R), b: fmtWindow(w.B), w: fmtWindow(w.W) }) },
    { label: t('data.q.yearMissing'), value: fmtInt(dq.year_missing) },
    { label: t('data.q.unassigned'), value: fmtInt(dq.unassigned_articles), note: ov.kpis.articles ? t('data.q.ofArticles', { p: fmtPct(dq.unassigned_articles / ov.kpis.articles, 1) }) : undefined },
    ...Object.entries(dq.text_quality ?? {}).map(([flag, n]) => ({ label: QUALITY_FLAGS[flag] ? t(QUALITY_FLAGS[flag]) : flag, value: fmtInt(n) })),
    { label: t('data.q.ingestErrors'), value: fmtInt(release.manifest.ingest_errors ?? 0) },
    { label: t('data.q.journalDriven'), value: fmtInt(journalDriven) },
    { label: t('data.q.orgsUnverified'), value: fmtInt(release.manifest.n_orgs_unverified ?? 0) },
    ...(labels ? [{ label: t('data.q.labels'), value: t('data.q.labelsV', { llm: fmtInt(labels.llm), kw: fmtInt(labels.keywords), ed: fmtInt(labels.overrides) }) }] : []),
    { label: t('data.q.llmFallback'), value: fmtInt(llmFallbacks) },
    { label: t('data.q.embedding'), value: `${release.manifest.embedding_provider || DASH} · ${release.manifest.embedding_model}` },
    {
      label: t('data.q.taxonomy'),
      value: `${release.taxonomy.source}${release.taxonomy.version ? ` ${release.taxonomy.version}` : ''}`,
      note: release.taxonomy.holdout_accuracy_field != null ? t('data.q.taxonomyAcc', { f: fmtPct(release.taxonomy.holdout_accuracy_field, 0), s: fmtPct(release.taxonomy.holdout_accuracy_subfield ?? null, 0) }) : undefined,
    },
    { label: t('data.q.definition'), value: t('data.q.definitionV', { v: release.definitionVersion, level: ciPct(release.ciLevel) }) },
    { label: t('data.q.build'), value: `${release.manifest.pipeline_version} · ${release.manifest.config_hash}`, note: fmtDate(release.manifest.generated_at, lang) },
  ]

  const corpusRows = [
    ...ov.corpus_by_year.map((r) => ({ year: r.year, articles: r.articles, kind: 'actual' as const })),
    ...(ov.nowcast ? [{ year: ov.nowcast.year, articles: ov.nowcast.mean, kind: 'nowcast' as const }] : []),
    ...(ov.corpus_forecast ?? []).filter((r) => r.year !== ov.nowcast?.year).map((r) => ({ year: r.year, articles: r.articles, kind: 'forecast' as const })),
  ]
  const corpusColumns: Column<(typeof corpusRows)[number]>[] = [
    { key: 'year', header: t('col.year'), rowHeader: true, cell: (r) => (r.kind === 'actual' ? String(r.year) : t(r.kind === 'nowcast' ? 'data.corpus.nowcast' : 'data.corpus.forecast', { year: r.year })), csv: (r) => r.year },
    { key: 'kind', header: 'kind', cell: () => null, csv: (r) => r.kind, csvOnly: true },
    { key: 'articles', header: t('col.articles'), numeric: true, cell: (r) => fmtInt(r.articles), csv: (r) => r.articles },
  ]
  const dictColumns: Column<DictEntry>[] = [
    { key: 'file', header: t('data.dict.file'), rowHeader: true, cell: (r) => <code>{r.file}</code>, sortValue: (r) => r.file },
    { key: 'field', header: t('data.dict.field'), cell: (r) => <code>{r.field}</code>, csv: (r) => r.field },
    { key: 'meaning', header: t('data.dict.meaning'), cell: (r) => (lang === 'en' ? r.en : r.th), csv: (r) => (lang === 'en' ? r.en : r.th) },
  ]
  const toc = [
    { id: 'downloads', label: t('data.dl.h') },
    { id: 'csv', label: t('data.csv.h') },
    { id: 'quality', label: t('data.q.h') },
    { id: 'dictionary', label: t('data.dict.h') },
    { id: 'cite', label: t('data.cite.h') },
  ]
  return (
    <div className="container">
      <PageHeader title={t('data.title')} lede={t('data.lede', { release: rel })} />
      <div className="layout">
        <div className="main-col">
          <Section id="downloads" title={t('data.dl.h')} intro={t(release.source === 'http' ? 'data.dl.introHttp' : 'data.dl.introOffline')}>
            <ul className="dl-list">
              {Object.entries(files).map(([path, value]) => (
                <li key={path}>
                  <div>
                    <code>{path}</code>
                    <span className="dl-note">{FILE_INFO[path] ? t(FILE_INFO[path]) : ''}{sizes.has(path) ? ` · ${fmtNum((sizes.get(path) ?? 0) / 1024, 0)} KB` : ''}</span>
                  </div>
                  {release.source === 'http' ? (
                    <a className="btn-secondary" href={dataUrl(import.meta.env.BASE_URL, `${rel}/${path}`)} download={`atlas-${rel}-${path}`}>
                      {t('data.dl.json')}
                    </a>
                  ) : (
                    <button type="button" className="btn-secondary" onClick={() => downloadText(`atlas-${rel}-${path}`, JSON.stringify(value), 'application/json')}>
                      {t('data.dl.json')}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </Section>
          <Section id="csv" title={t('data.csv.h')} intro={t('data.csv.intro')}>
            <ul className="dl-list">
              <li>
                <div><code>topics.csv</code><span className="dl-note">{t('data.csv.topics', { n: fmtInt(release.topics.length) })}</span></div>
                <button type="button" className="btn-secondary" disabled={!release.topics.length} onClick={() => downloadText(`atlas-${rel}-topics.csv`, topicCsv())}>{t('csv.download')}</button>
              </li>
              <li>
                <div><code>series.csv</code><span className="dl-note">{t('data.csv.series')}</span></div>
                <button type="button" className="btn-secondary" disabled={!seriesRows.length} onClick={() => downloadText(`atlas-${rel}-series.csv`, seriesCsv())}>{t('csv.download')}</button>
              </li>
              {release.keywords?.length ? (
                <li>
                  <div><code>keywords.csv</code><span className="dl-note">{t('data.csv.keywords')}</span></div>
                  <button type="button" className="btn-secondary" onClick={() => downloadText(`atlas-${rel}-keywords.csv`, keywordCsv(release.keywords ?? []))}>{t('csv.download')}</button>
                </li>
              ) : null}
            </ul>
          </Section>
          <Section id="quality" title={t('data.q.h')} intro={t('data.q.intro')}>
            <dl className="summary">
              {quality.map((q) => (
                <div key={q.label}>
                  <dt>{q.label}</dt>
                  <dd>{q.value}{q.note ? <small>{q.note}</small> : null}</dd>
                </div>
              ))}
            </dl>
            {corpusRows.length ? (
              <DataTable caption={t('table.n', { n: 1, title: t('data.corpus.table') })} rows={corpusRows} columns={corpusColumns} rowKey={(r) => `${r.kind}-${r.year}`} stack={false} csvFilename={`atlas-${rel}-corpus-by-year.csv`} />
            ) : null}
          </Section>
          <Section id="dictionary" title={t('data.dict.h')} intro={t('data.dict.intro')}>
            <DataTable caption={t('table.n', { n: 2, title: t('data.dict.table') })} rows={DICTIONARY} columns={dictColumns} rowKey={(r) => `${r.file}:${r.field}`} />
          </Section>
          <Section id="cite" title={t('data.cite.h')}>
            <p className="cite">{t('data.cite.text', { release: rel, date: fmtDate(release.manifest.generated_at, lang) })}</p>
            <p className="note">{t('data.cite.licence')}</p>
          </Section>
        </div>
        <aside className="rail" aria-label={t('onThisPage')}>
          <OnThisPage items={toc} />
        </aside>
      </div>
    </div>
  )
}
