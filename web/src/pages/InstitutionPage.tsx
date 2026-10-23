import { Link, useParams } from 'react-router'
import { BarRank } from '../charts/BarRank'
import { ColumnChart } from '../charts/ColumnChart'
import { mixSegments } from '../charts/execLayout'
import { rankBars } from '../charts/infographic'
import { MixBar } from '../charts/MixBar'
import { DataTable, type Column } from '../components/DataTable'
import { Figure } from '../components/Figure'
import { InstitutionLink } from '../components/InstitutionLink'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { StatGrid, StatTile } from '../components/StatTile'
import { ShareBar } from '../components/ShareBar'
import { TopicLink } from '../components/TopicLink'
import { useReleaseFile } from '../data/atlasContext'
import { MODULE_FILES, type AtlasRelease } from '../data/release'
import type { CountryCount, InstitutionDetail, InstitutionSummary, InstitutionsFile, Partner, Topic, TopicShare } from '../data/types'
import { instName, otherInstName } from '../lib/executive'
import { DASH, fmtInt, fmtNum, fmtPct } from '../lib/format'
import { useI18n, useStrings } from '../lib/i18n'
import { figureCsv } from '../lib/tableCsv'
import { institutionCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import type { StrKey } from '../strings'
import { execViz } from '../strings/execViz'

export default function InstitutionPage() {
  const { id } = useParams()
  const { t } = useI18n()
  return (
    <RequireRelease title={t('in.title')}>
      {(release) => (
        <ModuleFile<InstitutionsFile> release={release} module="institutions" path={MODULE_FILES.institutions} title={t('in.title')}>
          {(file) => <InstitutionView release={release} file={file} id={id ?? ''} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

function InstitutionView({ release, file, id }: { release: AtlasRelease; file: InstitutionsFile; id: string }) {
  const { t } = useI18n()
  const inst = file.institutions.find((i) => i.id === id)
  if (!inst) {
    return (
      <div className="container">
        <PageHeader title={t('in.notFound', { id: id || DASH })} lede={t('in.notFound.body')} />
        <p className="mt-6"><Link to="/institutions">{t('in.back')}</Link></p>
      </div>
    )
  }
  return <InstitutionContent key={inst.id} release={release} file={file} inst={inst} />
}

const MIX_TOP = 4

function InstitutionContent({ release, file, inst }: { release: AtlasRelease; file: InstitutionsFile; inst: InstitutionSummary }) {
  const { t, lang, name } = useI18n()
  const x = useStrings(execViz)
  const [view, setView] = useUrlState(institutionCodec)
  const detailFile = useReleaseFile<InstitutionDetail>(`institutions/${inst.id}.json`)
  const detail = detailFile.status === 'ready' ? detailFile.data : null
  const byId = new Map(file.institutions.map((i) => [i.id, i]))
  const topicOf = (tid: string): Topic | undefined => release.topicById.get(tid)
  const topics = (detail?.topics ?? []).filter((s) => topicOf(s.topic))
  const signals = topics.map((s) => topicOf(s.topic) as Topic).filter((tp) => tp.status === 'EMERGING' || tp.status === 'WATCH')
  const partners = (detail?.partners ?? []).filter((p) => byId.has(p.id))
  const countries = detail?.countries ?? []
  const suggested = (detail?.suggested ?? []).filter((s) => byId.has(s.id))
  const years = detail?.years ?? []
  const shown = instName(inst, lang)
  const other = otherInstName(inst, lang)
  const province = (file.province_names ?? []).find((p) => p.code === inst.province)
  const place = province ? (lang === 'en' ? province.name_en : province.name_th) : inst.country && inst.country !== 'TH' ? t('in.abroad', { c: inst.country }) : t('in.unplaced')
  const w = file.window
  const r = file.recent
  const rel = release.overview.release
  const maxShare = Math.max(0.0001, ...topics.map((s) => s.share))
  const topicColumns: Column<TopicShare>[] = [
    { key: 'topic', csvHeader: 'topic_id', header: t('col.topic'), rowHeader: true, cell: (s) => <TopicLink topic={topicOf(s.topic) as Topic} showStatus />, sortValue: (s) => name(topicOf(s.topic) as Topic), csv: (s) => s.topic },
    { key: 'count', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (s) => fmtInt(s.count), sortValue: (s) => s.count },
    { key: 'share', csvHeader: 'share', header: t('col.share'), numeric: true, cell: (s) => <ShareBar value={s.share} max={maxShare} />, sortValue: (s) => s.share },
  ]
  const partnerColumns: Column<Partner>[] = [
    { key: 'name', csvHeader: 'institution_id', header: t('col.institution'), rowHeader: true, cell: (p) => <InstitutionLink inst={byId.get(p.id) as InstitutionSummary} />, sortValue: (p) => instName(byId.get(p.id) as InstitutionSummary, lang).text, csv: (p) => p.id },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (p) => fmtInt(p.articles), sortValue: (p) => p.articles },
  ]
  const countryColumns: Column<CountryCount>[] = [
    { key: 'name', csvHeader: 'country', header: t('in.col.country'), rowHeader: true, cell: (c) => (lang === 'en' ? c.name_en : c.name_th), csv: (c) => c.code },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (c) => fmtInt(c.articles), sortValue: (c) => c.articles },
  ]
  const pname = (id: string) => instName(byId.get(id) as InstitutionSummary, lang).text
  const tname = (id: string) => {
    const tp = topicOf(id)
    return tp ? (lang === 'en' ? tp.en || tp.th : tp.th) : id
  }
  const mix = mixSegments(topics.map((s) => ({ key: s.topic, id: s.topic, value: s.share })), { top: MIX_TOP, total: 1, otherKey: '__other' }).map((m) => ({
    ...m,
    name: m.other ? x('xv.other') : <TopicLink topic={topicOf(m.key) as Topic} showStatus />,
    text: fmtPct(m.frac, 0),
  }))
  const mixText = mix.map((m) => `${m.other ? x('xv.other') : tname(m.key)} ${m.text}`).join(', ')
  const partnerBars = rankBars(partners.map((p) => ({ key: pname(p.id), id: p.id, count: p.articles })), 6)
  const countryBars = rankBars(countries.map((c) => ({ key: lang === 'en' ? c.name_en : c.name_th, id: c.code, count: c.articles })), 6)
  const tbl = (n: number, title: string) => t('table.n', { n, title })
  const source = t('source.line', { release: rel })
  // figures and tables are numbered in page order, over the sections this institution has
  const present = [years.length > 0, topics.length > 0, partners.length > 0, countries.length > 0]
  const num = (k: number) => present.slice(0, k + 1).filter(Boolean).length
  const yearColumns: Column<{ year: number; articles: number }>[] = [
    { key: 'year', csvHeader: 'year', header: t('col.year'), rowHeader: true, cell: (y) => String(y.year), sortValue: (y) => y.year },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (y) => fmtInt(y.articles), sortValue: (y) => y.articles },
  ]
  return (
    <div className="container">
      <PageHeader title={shown.text} titleLang={shown.lang ?? undefined}>
        {other ? <p className="tp-alt" lang={lang === 'en' ? 'th' : 'en'}>{other}</p> : null}
        <div className="j-tags">
          <span className="tp-badge">{t(`in.type.${inst.type ?? 'other'}` as StrKey)}</span>
          <span>{place}</span>
          <span className="tp-sub">{t(`in.source.${inst.source}` as StrKey)}</span>
          {inst.ror ? (
            <a href={`https://ror.org/${inst.ror}`} target="_blank" rel="noopener noreferrer">ROR<span className="sr-only"> {t('newTab')}</span></a>
          ) : null}
        </div>
      </PageHeader>
      <div className="layout">
        <div className="main-col">
          <Section id="numbers" title={t('in.numbers.h')}>
            <StatGrid cols={3}>
              <StatTile
                wide
                label={t('col.articles')}
                value={fmtInt(inst.articles)}
                sub={t('in.articlesSub', { a: w.start, b: w.end, all: fmtInt(inst.articles_total) })}
              />
              <StatTile label={t('in.col.recent', { r: `${r.start}–${r.end}` })} value={fmtInt(inst.articles_recent ?? null)} sub={t('in.recentSub')} />
              <StatTile label={t('in.col.intl')} value={fmtPct(inst.intl_share ?? null, 0)} sub={t('in.intlSub')} />
              <StatTile label={t('in.col.partners')} value={fmtInt(inst.partners ?? null)} sub={t('in.partnersSub', { a: w.start, b: w.end })} />
              <StatTile label={t('col.topic')} value={fmtInt(inst.topics ?? null)} sub={t('in.topicsSub')} />
            </StatGrid>
          </Section>

          {years.length ? (
            <Section id="years" title={t('in.years.h')}>
              <Figure
                id="fig-years"
                number={1}
                title={x('xv.yr.title')}
                tableTitle={tbl(1, t('in.years.table'))}
                csv={figureCsv(`atlas-${rel}-${inst.id}-years.csv`, years, yearColumns)}
                how={<p>{x('xv.yr.how')}</p>}
                source={source}
                view={view.yr}
                onView={(v) => setView({ yr: v })}
                chart={
                  <ColumnChart
                    items={years.map((y) => ({ key: String(y.year), value: y.articles }))}
                    format={fmtInt}
                    label={x('xv.yr.label', { a: years[0].year, b: years[years.length - 1].year, values: years.map((y) => fmtInt(y.articles)).join(', ') })}
                  />
                }
                table={<DataTable caption={tbl(1, t('in.years.table'))} rows={years} columns={yearColumns} rowKey={(y) => String(y.year)} stack={false} defaultSort={{ key: 'year', dir: 'asc' }} />}
              />
            </Section>
          ) : null}

          {topics.length ? (
            <Section id="topics" title={t('in.topics.h')}>
              <Figure
                id="fig-mix"
                number={num(1)}
                title={x('xv.mix.title')}
                tableTitle={tbl(num(1), t('in.topics.table'))}
                csv={figureCsv(`atlas-${rel}-${inst.id}-topics.csv`, topics, topicColumns)}
                how={<p>{x('xv.mix.how', { n: MIX_TOP })}</p>}
                source={source}
                view={view.mix}
                onView={(v) => setView({ mix: v })}
                chart={<MixBar parts={mix} label={x('xv.mix.label', { parts: mixText })} />}
                table={<DataTable caption={tbl(num(1), t('in.topics.table'))} rows={topics} columns={topicColumns} rowKey={(s) => s.topic} defaultSort={{ key: 'count', dir: 'desc' }} limit={25} />}
              />
              {signals.length ? (
                <>
                  <h3 className="mt-6">{t('in.emerging')}</h3>
                  <ul className="opp-list">
                    {signals.map((tp) => (
                      <li key={tp.id}><TopicLink topic={tp} showStatus /></li>
                    ))}
                  </ul>
                </>
              ) : null}
            </Section>
          ) : null}

          {partners.length ? (
            <Section id="partners" title={t('in.partners.h')}>
              <Figure
                id="fig-partners"
                number={num(2)}
                title={x('xv.ptn.title')}
                tableTitle={tbl(num(2), t('in.partners.table'))}
                csv={figureCsv(`atlas-${rel}-${inst.id}-partners.csv`, partners, partnerColumns)}
                how={<p>{x('xv.bar.how')}</p>}
                source={source}
                view={view.ptn}
                onView={(v) => setView({ ptn: v })}
                chart={
                  <>
                    <BarRank rows={partnerBars.rows} href={(r) => (r.id ? `/institutions/${r.id}` : null)} value={(r) => fmtInt(r.count)} label={x('xv.ptn.label')} />
                    {partnerBars.rest > 0 ? <p className="br-more">{x('xv.more', { n: fmtInt(partnerBars.rest) })}</p> : null}
                  </>
                }
                table={<DataTable caption={tbl(num(2), t('in.partners.table'))} rows={partners} columns={partnerColumns} rowKey={(p) => p.id} stack={false} defaultSort={{ key: 'articles', dir: 'desc' }} limit={25} />}
              />
            </Section>
          ) : null}

          {countries.length ? (
            <Section id="abroad" title={t('in.countries.h')}>
              <Figure
                id="fig-abroad"
                number={num(3)}
                title={t('in.countries.table')}
                tableTitle={tbl(num(3), t('in.countries.table'))}
                csv={figureCsv(`atlas-${rel}-${inst.id}-countries.csv`, countries, countryColumns)}
                how={<p>{x('xv.bar.how')}</p>}
                source={source}
                view={view.ctry}
                onView={(v) => setView({ ctry: v })}
                chart={<BarRank rows={countryBars.rows} value={(r) => fmtInt(r.count)} label={x('xv.ctry.label')} />}
                table={<DataTable caption={tbl(num(3), t('in.countries.table'))} rows={countries} columns={countryColumns} rowKey={(c) => c.code} stack={false} limit={25} />}
              />
            </Section>
          ) : null}

          {suggested.length ? (
            <Section id="suggested" title={t('in.suggest.h')} intro={t('in.suggest.intro', { x: instName(byId.get(suggested[0].id) as InstitutionSummary, lang).text, a: w.start, b: w.end })}>
              <ul className="sug-list">
                {suggested.map((s) => (
                  <li key={s.id}>
                    <InstitutionLink inst={byId.get(s.id) as InstitutionSummary} />
                    <span className="sug-topics">
                      <span className="topic-sub">{t('in.suggest.sub', { s: fmtNum(s.similarity, 2) })}</span>
                      {(s.topics ?? []).map((tid) => topicOf(tid)).filter((tp): tp is Topic => tp !== undefined).map((tp) => (
                        <TopicLink key={tp.id} topic={tp} />
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
            </Section>
          ) : null}

          {detailFile.status === 'loading' ? <p className="loading" role="status">{t('loading')}</p> : null}
        </div>
        <p className="page-back"><Link to="/institutions">{t('in.back')}</Link></p>
      </div>
    </div>
  )
}
