import { MultiLineChart, type LineSeries } from '../charts/MultiLineChart'
import { DataTable, type Column } from '../components/DataTable'
import { Figure } from '../components/Figure'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { ShareBar } from '../components/ShareBar'
import { TopicLink } from '../components/TopicLink'
import { MODULE_FILES, type AtlasRelease } from '../data/release'
import type { MethodShare, MethodsFile, Topic, TopicMethods } from '../data/types'
import { DASH, fmtInt, fmtPct } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { methodsCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'

export default function MethodsPage() {
  const { t } = useI18n()
  return (
    <RequireRelease title={t('me.title')}>
      {(release) => (
        <ModuleFile<MethodsFile> release={release} module="methods" path={MODULE_FILES.methods} title={t('me.title')}>
          {(file) => <Methods release={release} file={file} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

function Methods({ release, file }: { release: AtlasRelease; file: MethodsFile }) {
  const { t, lang } = useI18n()
  const [state, update] = useUrlState(methodsCodec)
  const info = new Map(file.methods.map((m) => [m.key, m]))
  const mName = (key: string) => {
    const m = info.get(key)
    return m ? (lang === 'en' ? m.en : m.th) : key
  }
  const w = file.window
  const monoNames = file.monoculture_methods.map(mName).join(' + ')
  const rel = release.overview.release
  const source = t('source.line', { release: rel, v: release.definitionVersion })
  const by = file.by_year
  const top4 = [...file.corpus].sort((a, b) => b.count - a.count).slice(0, 4).filter((m) => by.shares[m.method])
  const series: LineSeries[] = top4.map((m, i) => ({ id: m.method, label: mName(m.method), values: by.shares[m.method], slot: i }))
  const yearRows = by.years.map((year, i) => ({ year, i }))
  const yearColumns: Column<{ year: number; i: number }>[] = [
    { key: 'year', csvHeader: 'year', header: t('col.year'), rowHeader: true, cell: (r) => String(r.year), csv: (r) => r.year },
    { key: 'n', csvHeader: 'articles_with_method', header: t('col.coverage'), numeric: true, cell: (r) => fmtInt(by.articles[r.i]), csv: (r) => by.articles[r.i] },
    ...Object.keys(by.shares).map((k): Column<{ year: number; i: number }> => ({ key: k, csvHeader: k, header: mName(k), numeric: true, cell: (r) => fmtPct(by.shares[k][r.i], 0), csv: (r) => by.shares[k][r.i] })),
  ]
  const corpusColumns: Column<MethodShare>[] = [
    { key: 'method', csvHeader: 'method', header: t('col.method'), rowHeader: true, cell: (m) => mName(m.method), sortValue: (m) => mName(m.method), csv: (m) => m.method },
    { key: 'count', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (m) => fmtInt(m.count), sortValue: (m) => m.count },
    { key: 'share', csvHeader: 'share', header: t('col.share'), numeric: true, cell: (m) => <ShareBar value={m.share} />, sortValue: (m) => m.share },
  ]
  const topicRows = file.topics.filter((r) => release.topicById.has(r.topic) && (state.mono === 'all' || r.monoculture))
  const topicOf = (r: TopicMethods) => release.topicById.get(r.topic) as Topic
  const topicColumns: Column<TopicMethods>[] = [
    { key: 'topic', csvHeader: 'topic_id', header: t('col.topic'), rowHeader: true, cell: (r) => <TopicLink topic={topicOf(r)} showStatus />, sortValue: (r) => r.topic, csv: (r) => r.topic },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (r) => fmtInt(r.articles), sortValue: (r) => r.articles },
    { key: 'coverage', csvHeader: 'coverage', header: t('col.coverage'), numeric: true, cell: (r) => fmtPct(r.coverage, 0), sortValue: (r) => r.coverage },
    {
      key: 'top', header: t('col.topMethods'), cell: (r) => r.methods.slice(0, 2).map((m) => `${mName(m.method)} ${fmtPct(m.share, 0)}`).join(' · ') || DASH,
      csv: (r) => r.methods.map((m) => `${m.method}:${m.share}`).join(';'), csvHeader: 'methods',
    },
    {
      key: 'sample', csvHeader: 'sample_size_median', header: t('col.sample'), numeric: true, sortValue: (r) => r.sample_size_median ?? null,
      cell: (r) => (r.sample_size_median == null ? DASH : t('me.sampleRange', { m: fmtInt(r.sample_size_median), q1: fmtInt(r.sample_size_q1 ?? null), q3: fmtInt(r.sample_size_q3 ?? null) })),
    },
    {
      key: 'mono', csvHeader: 'monoculture_share', header: t('col.mono'), numeric: true, sortValue: (r) => r.monoculture_share ?? null,
      cell: (r) => (
        <>
          <ShareBar value={r.monoculture_share} />
          {r.monoculture ? <span className="flag">{t('me.mono')}</span> : null}
        </>
      ),
    },
  ]
  const notes = file.topics.filter((r) => r.note && release.topicById.has(r.topic))
  return (
    <div className="container">
      <PageHeader title={t('me.title')} lede={t('me.lede', { a: w.start, b: w.end })} />
      <dl className="summary">
        <div>
          <dt>{t('me.kpi.coverage')}</dt>
          <dd>{fmtPct(file.articles ? file.with_methods / file.articles : null, 0)}<small>{t('me.kpi.coverageSub', { n: fmtInt(file.with_methods), all: fmtInt(file.articles) })}</small></dd>
        </div>
        <div>
          <dt>{t('me.kpi.mono', { methods: monoNames })}</dt>
          <dd>{fmtPct(file.monoculture_share ?? null, 0)}<small>{t('me.kpi.monoSub')}</small></dd>
        </div>
      </dl>
      {series.length && by.years.length ? (
        <Section id="trend" title={t('me.trend.h')}>
          <Figure
            id="fig-methods"
            number={1}
            title={t('me.trend.fig', { a: by.years[0], b: by.years[by.years.length - 1] })}
            source={source}
            view={state.trend}
            onView={(v) => update({ trend: v })}
            chart={<MultiLineChart years={by.years} series={series} format={(v) => fmtPct(v, 0)} axisFormat={(v) => fmtPct(v, 0)} label={t('me.trend.fig', { a: by.years[0], b: by.years[by.years.length - 1] })} />}
            table={<DataTable caption={t('table.n', { n: 1, title: t('me.trend.table') })} rows={yearRows} columns={yearColumns} rowKey={(r) => String(r.year)} stack={false} wide csvFilename={`atlas-${rel}-methods-by-year.csv`} />}
          />
        </Section>
      ) : null}
      <Section id="corpus" title={t('me.corpus.h')}>
        <DataTable caption={t('table.n', { n: 2, title: t('me.corpus.table', { a: w.start, b: w.end }) })} rows={file.corpus} columns={corpusColumns} rowKey={(m) => m.method} defaultSort={{ key: 'count', dir: 'desc' }} csvFilename={`atlas-${rel}-methods.csv`} />
      </Section>
      {file.topics.length ? (
        <Section
          id="topics"
          title={t('me.topics.h')}
          intro={t('me.topics.intro', { n: fmtInt(file.min_articles), a: w.start, b: w.end, p: fmtPct(file.monoculture_min_share, 0), methods: monoNames })}
        >
          <label className="check">
            <input type="checkbox" checked={state.mono === 'only'} onChange={(e) => update({ mono: e.target.checked ? 'only' : 'all' })} />
            {t('me.onlyMono')}
          </label>
          <DataTable caption={t('table.n', { n: 3, title: t('me.topics.table') })} rows={topicRows} columns={topicColumns} rowKey={(r) => r.topic} defaultSort={{ key: 'mono', dir: 'desc' }} csvFilename={`atlas-${rel}-methods-by-topic.csv`} />
        </Section>
      ) : null}
      {notes.length ? (
        <Section id="notes" title={t('me.notes.h')}>
          <ul className="opp-list">
            {notes.map((r) => (
              <li key={r.topic}>
                <TopicLink topic={topicOf(r)} />
                <span>{lang === 'en' ? r.note?.en : r.note?.th}</span>
                <span className="headline-src">{t(r.note?.source === 'llm' ? 'autoSummary.llm' : 'autoSummary.template')}</span>
              </li>
            ))}
          </ul>
        </Section>
      ) : null}
      <Section id="lexicon" title={t('me.lexicon.h')} intro={t('me.lexicon.intro', { v: file.lexicon_version })}>
        <ul className="kw-list">
          {file.methods.map((m) => <li key={m.key}>{lang === 'en' ? m.en : m.th}</li>)}
        </ul>
      </Section>
    </div>
  )
}
