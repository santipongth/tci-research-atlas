import { useMemo, type ReactNode } from 'react'
import { DataTable, type Column } from '../../components/DataTable'
import { HowNote } from '../../components/HowNote'
import { OnThisPage } from '../../components/OnThisPage'
import { Section } from '../../components/Section'
import { DICTIONARY, type DictEntry } from '../../content/dictionary'
import { groupName, hasModule, MODULE_FILES, type AtlasRelease, type ModuleName } from '../../data/release'
import { dataUrl } from '../../data/source'
import type { EmergingKeyword, Topic } from '../../data/types'
import { fmtBytes, utf8Bytes } from '../../lib/bytes'
import { toCsv, downloadText } from '../../lib/csv'
import { fmtWindow, windows } from '../../lib/definition'
import { ciPct, fmtDate, fmtInt, fmtNum, fmtPct } from '../../lib/format'
import { useI18n, useStrings } from '../../lib/i18n'
import type { StrKey } from '../../strings'
import { openViz } from '../../strings/openViz'
import { ModuleDownloads } from './ModuleDownloads'

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
/** Text flags that report a repair already made — information, not a caveat. */
const REPAIRED = new Set(['thai_pua_repaired'])

interface QualityRow {
  label: string
  value: ReactNode
  note?: string
  /** ok = nothing to watch; note = worth knowing before using the figures */
  state: 'ok' | 'note'
}

function TableArt() {
  return (
    <svg className="ez-art" width="40" height="48" viewBox="0 0 40 48" aria-hidden="true" focusable="false">
      <path d="M2 2h26l10 10v34H2z" className="ez-sheet" />
      <path d="M28 2v10h10" className="ez-fold" />
      {[18, 26, 34].map((y) => <line key={y} x1="8" x2="32" y1={y} y2={y} className="ez-rule" />)}
      <line x1="17" x2="17" y1="14" y2="40" className="ez-rule" />
    </svg>
  )
}

function QualityIcon({ state }: { state: QualityRow['state'] }) {
  return state === 'ok' ? (
    <svg className="qc-ic" viewBox="0 0 20 20" width="20" height="20" aria-hidden="true" focusable="false">
      <circle cx="10" cy="10" r="9" className="qc-ok" />
      <path d="M5.5 10.3l3 3 6-6.2" className="qc-mark" />
    </svg>
  ) : (
    <svg className="qc-ic" viewBox="0 0 20 20" width="20" height="20" aria-hidden="true" focusable="false">
      <path d="M10 1.8 19 18H1z" className="qc-warn" />
      <path d="M10 7.5v5M10 14.6v1.4" className="qc-warn-mark" />
    </svg>
  )
}

/** /data below its title: easy CSV downloads first, then everything for developers. Loaded on demand. */
export default function OpenData({ release }: { release: AtlasRelease }) {
  const { t, lang } = useI18n()
  const s = useStrings(openViz)
  const rel = release.overview.release
  const files = releaseFiles(release)
  const sizes = new Map((release.manifest.files ?? []).map((f) => [f.path, f.bytes]))
  const ov = release.overview
  const dq = ov.data_quality
  const w = windows(ov.last_complete_year)
  const llmFallbacks = (release.manifest.llm ?? []).reduce((n, x) => n + x.fallback, 0)
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
  const kw = release.keywords ?? []
  const easy = useMemo(
    () => [
      { id: 'topics', file: 'topics.csv', title: s('ez.topics'), body: t('data.csv.topics', { n: fmtInt(release.topics.length) }), rows: release.topics.length, text: topicCsv },
      { id: 'series', file: 'series.csv', title: s('ez.series'), body: t('data.csv.series'), rows: seriesRows.length, text: seriesCsv },
      ...(kw.length ? [{ id: 'keywords', file: 'keywords.csv', title: s('ez.keywords'), body: t('data.csv.keywords'), rows: kw.length, text: () => keywordCsv(kw) }] : []),
    ].map((f) => ({ ...f, bytes: f.rows ? utf8Bytes(f.text()) : 0 })),
    // the CSV text is rebuilt only for a new release or language (it holds the field names in that language)
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [release, lang],
  )

  const trimmed = release.manifest.trimmed_years ?? []
  const quality: QualityRow[] = [
    { label: t('data.q.through'), value: s('qc.through', { y: ov.last_complete_year }), note: trimmed.length ? t('data.q.trimmed', { years: trimmed.join(', ') }) : undefined, state: 'ok' },
    { label: t('data.q.completeness'), value: COMPLETENESS[dq.completeness_method] ? t(COMPLETENESS[dq.completeness_method]) : dq.completeness_method, state: 'ok' },
    { label: t('data.q.windows'), value: t('data.q.windowsV', { r: fmtWindow(w.R), b: fmtWindow(w.B), w: fmtWindow(w.W) }), state: 'ok' },
    { label: t('data.q.yearMissing'), value: dq.year_missing ? s('qc.articles', { n: fmtInt(dq.year_missing) }) : s('qc.none'), state: dq.year_missing ? 'note' : 'ok' },
    {
      label: t('data.q.unassigned'),
      value: dq.unassigned_articles ? s('qc.articles', { n: fmtInt(dq.unassigned_articles) }) : s('qc.none'),
      note: dq.unassigned_articles && ov.kpis.articles ? t('data.q.ofArticles', { p: fmtPct(dq.unassigned_articles / ov.kpis.articles, 1) }) : undefined,
      state: dq.unassigned_articles ? 'note' : 'ok',
    },
    ...Object.entries(dq.text_quality ?? {}).map(([flag, n]): QualityRow => ({
      label: QUALITY_FLAGS[flag] ? t(QUALITY_FLAGS[flag]) : flag,
      value: n ? s('qc.articles', { n: fmtInt(n) }) : s('qc.none'),
      state: n && !REPAIRED.has(flag) ? 'note' : 'ok',
    })),
    release.manifest.ingest_errors == null
      ? { label: t('data.q.ingestErrors'), value: t('data.q.notRecorded'), state: 'note' }
      : { label: t('data.q.ingestErrors'), value: release.manifest.ingest_errors ? s('qc.files', { n: fmtInt(release.manifest.ingest_errors) }) : s('qc.none'), state: release.manifest.ingest_errors ? 'note' : 'ok' },
    { label: t('data.q.journalDriven'), value: s('qc.topics', { n: fmtInt(journalDriven) }), state: journalDriven ? 'note' : 'ok' },
    { label: t('data.q.orgsUnverified'), value: s('qc.topics', { n: fmtInt(release.manifest.n_orgs_unverified ?? 0) }), state: release.manifest.n_orgs_unverified ? 'note' : 'ok' },
    ...(labels ? [{ label: t('data.q.labels'), value: t('data.q.labelsV', { llm: fmtInt(labels.llm), kw: fmtInt(labels.keywords), ed: fmtInt(labels.overrides), re: fmtInt(labels.reused ?? 0) }), state: 'ok' as const }] : []),
    { label: t('data.q.llmFallback'), value: llmFallbacks ? s('qc.texts', { n: fmtInt(llmFallbacks) }) : s('qc.none'), state: llmFallbacks ? 'note' : 'ok' },
    { label: t('data.q.definition'), value: t('data.q.definitionV', { v: release.definitionVersion, level: ciPct(release.ciLevel) }), state: 'ok' },
    {
      label: t('data.q.taxonomy'),
      value: <code>{`${release.taxonomy.source}${release.taxonomy.version ? ` ${release.taxonomy.version}` : ''}`}</code>,
      note: release.taxonomy.holdout_accuracy_field != null ? t('data.q.taxonomyAcc', { f: fmtPct(release.taxonomy.holdout_accuracy_field, 0), s: fmtPct(release.taxonomy.holdout_accuracy_subfield ?? null, 0) }) : undefined,
      state: 'ok',
    },
    { label: t('data.q.embedding'), value: <code>{`${release.manifest.embedding_provider || '–'} · ${release.manifest.embedding_model}`}</code>, state: 'ok' },
    { label: t('data.q.build'), value: <code>{s('qc.buildV', { v: release.manifest.pipeline_version, h: release.manifest.config_hash })}</code>, note: fmtDate(release.manifest.generated_at, lang), state: 'ok' },
  ]

  const corpusRows = [
    ...ov.corpus_by_year.map((r) => ({ year: r.year, articles: r.articles, kind: 'actual' as const })),
    ...(ov.nowcast ? [{ year: ov.nowcast.year, articles: ov.nowcast.mean, kind: 'nowcast' as const }] : []),
    ...(ov.corpus_forecast ?? []).filter((r) => r.year !== ov.nowcast?.year).map((r) => ({ year: r.year, articles: r.articles, kind: 'forecast' as const })),
  ]
  const corpusColumns: Column<(typeof corpusRows)[number]>[] = [
    { key: 'year', csvHeader: 'year', header: t('col.year'), rowHeader: true, cell: (r) => (r.kind === 'actual' ? String(r.year) : t(r.kind === 'nowcast' ? 'data.corpus.nowcast' : 'data.corpus.forecast', { year: r.year })), csv: (r) => r.year },
    { key: 'kind', csvHeader: 'kind', header: 'kind', cell: () => null, csv: (r) => r.kind, csvOnly: true },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (r) => fmtInt(r.articles), csv: (r) => r.articles },
  ]
  const dictColumns: Column<DictEntry>[] = [
    { key: 'file', header: t('data.dict.file'), rowHeader: true, cell: (r) => <code>{r.file}</code>, sortValue: (r) => r.file },
    { key: 'field', header: t('data.dict.field'), cell: (r) => <code>{r.field}</code>, csv: (r) => r.field },
    { key: 'meaning', header: t('data.dict.meaning'), cell: (r) => (lang === 'en' ? r.en : r.th), csv: (r) => (lang === 'en' ? r.en : r.th) },
  ]
  const toc = [
    { id: 'csv', label: s('ez.h') },
    { id: 'developers', label: s('dev.h') },
    { id: 'downloads', label: t('data.dl.h') },
    ...((Object.keys(MODULE_FILES) as ModuleName[]).some((m) => hasModule(release, m)) ? [{ id: 'modules', label: t('data.mod.h') }] : []),
    { id: 'quality', label: t('data.q.h') },
    { id: 'dictionary', label: t('data.dict.h') },
    { id: 'cite', label: t('data.cite.h') },
  ]
  return (
    <div className="layout">
      <div className="main-col">
        <Section id="csv" title={s('ez.h')} intro={s('ez.intro')}>
          <ul className="ez-cards" aria-label={s('ez.cards')}>
            {easy.map((f) => (
              <li key={f.id} className="ez-card">
                <TableArt />
                <div className="ez-body">
                  <p className="ez-t">{f.title}</p>
                  <p className="ez-b">{f.body}</p>
                  <p className="ez-meta"><code>{f.file}</code> · {s('ez.meta', { n: fmtInt(f.rows), size: fmtBytes(f.bytes) })}</p>
                </div>
                <button type="button" className="btn" disabled={!f.rows} aria-label={`${t('csv.download')}: atlas-${rel}-${f.file}`} onClick={() => downloadText(`atlas-${rel}-${f.file}`, f.text())}>
                  <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">
                    <path d="M8 2v8M4.5 6.5 8 10l3.5-3.5M2.5 11.5v2h11v-2" fill="none" stroke="currentColor" strokeWidth="1.8" />
                  </svg>
                  <span>{t('csv.download')}</span>
                </button>
              </li>
            ))}
          </ul>
        </Section>

        <section className="sec dev" id="developers" aria-labelledby="developers-h">
          <h2 id="developers-h" tabIndex={-1}>{s('dev.h')}</h2>
          <p className="intro">{s('dev.intro')}</p>

          <div className="dev-sub" id="downloads">
            <h3 tabIndex={-1}>{t('data.dl.h')}</h3>
            <p className="intro">{t('data.dl.intro')}</p>
            <ul className="dl-list">
              {Object.entries(files).map(([path, value]) => (
                <li key={path}>
                  <div>
                    <code>{path}</code>
                    <span className="dl-note">{FILE_INFO[path] ? t(FILE_INFO[path]) : ''}{sizes.has(path) ? ` · ${fmtNum((sizes.get(path) ?? 0) / 1024, 0)} KB` : ''}</span>
                  </div>
                  {release.source === 'http' ? (
                    <a className="btn-secondary" href={dataUrl(import.meta.env.BASE_URL, `${rel}/${path}`)} download={`atlas-${rel}-${path}`} aria-label={`${t('data.dl.json')}: atlas-${rel}-${path}`}>
                      {t('data.dl.json')}
                    </a>
                  ) : (
                    <button type="button" className="btn-secondary" aria-label={`${t('data.dl.json')}: atlas-${rel}-${path}`} onClick={() => downloadText(`atlas-${rel}-${path}`, JSON.stringify(value), 'application/json')}>
                      {t('data.dl.json')}
                    </button>
                  )}
                </li>
              ))}
            </ul>
            <HowNote><p>{t(release.source === 'http' ? 'data.dl.devHttp' : 'data.dl.devOffline')}</p></HowNote>
          </div>

          <ModuleDownloads release={release} />

          <div className="dev-sub" id="quality">
            <h3 tabIndex={-1}>{t('data.q.h')}</h3>
            <p className="intro">{t('data.q.intro')}</p>
            <ul className="qc-key" aria-hidden="true">
              <li><QualityIcon state="ok" />{s('qc.ok')}</li>
              <li><QualityIcon state="note" />{s('qc.note')}</li>
            </ul>
            <ul className="qc" aria-label={s('qc.label')}>
              {quality.map((q) => (
                <li key={q.label} className={`qc-row is-${q.state}`}>
                  <span className="qc-state">
                    <QualityIcon state={q.state} />
                    <span className="sr-only">{s(q.state === 'ok' ? 'qc.ok' : 'qc.note')}: </span>
                  </span>
                  <span className="qc-label">{q.label}</span>
                  <span className="qc-value">
                    {q.value}
                    {q.note ? <small>{q.note}</small> : null}
                  </span>
                </li>
              ))}
            </ul>
            {corpusRows.length ? (
              <DataTable caption={t('table.n', { n: 1, title: t('data.corpus.table') })} rows={corpusRows} columns={corpusColumns} rowKey={(r) => `${r.kind}-${r.year}`} stack={false} csvFilename={`atlas-${rel}-corpus-by-year.csv`} />
            ) : null}
          </div>

          <div className="dev-sub" id="dictionary">
            <h3 tabIndex={-1}>{t('data.dict.h')}</h3>
            <p className="intro">{t('data.dict.intro')}</p>
            <DataTable caption={t('table.n', { n: 2, title: t('data.dict.table') })} rows={DICTIONARY} columns={dictColumns} rowKey={(r) => `${r.file}:${r.field}`} />
          </div>
        </section>

        <Section id="cite" title={t('data.cite.h')}>
          <p className="cite">{t('data.cite.text', { release: rel, date: fmtDate(release.manifest.generated_at, lang) })}</p>
          <p className="note">{t('data.cite.licence')}</p>
        </Section>
      </div>
      <aside className="rail" aria-label={t('onThisPage')}>
        <OnThisPage items={toc} />
      </aside>
    </div>
  )
}
