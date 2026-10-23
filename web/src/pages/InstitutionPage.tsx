import { Link, useParams } from 'react-router'
import { BarRank } from '../charts/BarRank'
import { ColumnChart } from '../charts/ColumnChart'
import { mixSegments } from '../charts/execLayout'
import { rankBars } from '../charts/infographic'
import { MixBar } from '../charts/MixBar'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { DashGrid } from '../components/dashboard/Card'
import { KpiCard, KpiRow } from '../components/dashboard/KpiCard'
import { PageBar } from '../components/dashboard/PageBar'
import { RankRows } from '../components/dashboard/RankRows'
import { TopicLink } from '../components/TopicLink'
import { useReleaseFile } from '../data/atlasContext'
import { MODULE_FILES, type AtlasRelease } from '../data/release'
import type { InstitutionDetail, InstitutionSummary, InstitutionsFile, Topic } from '../data/types'
import { instName, otherInstName } from '../lib/executive'
import { DASH, fmtInt, fmtPct, yearSpan } from '../lib/format'
import { useI18n, useStrings } from '../lib/i18n'
import { execViz } from '../strings/execViz'
import { execPages } from '../strings/execPages'

export default function InstitutionPage() {
  const { id } = useParams()
  const sx = useStrings(execPages)
  return (
    <RequireRelease title={sx('in.title')}>
      {(release) => (
        <ModuleFile<InstitutionsFile> release={release} module="institutions" path={MODULE_FILES.institutions} title={sx('in.title')}>
          {(file) => <InstitutionView release={release} file={file} id={id ?? ''} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

function InstitutionView({ release, file, id }: { release: AtlasRelease; file: InstitutionsFile; id: string }) {
  const sx = useStrings(execPages)
  const inst = file.institutions.find((i) => i.id === id)
  if (!inst) {
    return (
      <div className="container">
        <PageHeader title={sx('in.notFound', { id: id || DASH })} lede={sx('in.notFound.body')} />
        <p className="mt-6"><Link to="/places">{sx('in.back')}</Link></p>
      </div>
    )
  }
  return <InstitutionContent key={inst.id} release={release} file={file} inst={inst} />
}

const MIX_TOP = 4

function InstitutionContent({ release, file, inst }: { release: AtlasRelease; file: InstitutionsFile; inst: InstitutionSummary }) {
  const { t, lang, name } = useI18n()
  const sx = useStrings(execPages)
  const x = useStrings(execViz)
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
  const place = province ? (lang === 'en' ? province.name_en : province.name_th) : inst.country && inst.country !== 'TH' ? sx('in.abroad', { c: inst.country }) : sx('in.unplaced')
  const w = file.window
  const r = file.recent
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
  return (
    <>
      <PageBar
        title={shown.text}
        titleLang={shown.lang ?? undefined}
        sub={[other ?? '', sx(`in.type.${inst.type ?? 'other'}` as keyof typeof execPages), place].filter(Boolean).join(' · ')}
        info={sx(`in.source.${inst.source}` as keyof typeof execPages)}
        actions={inst.ror ? <a className="see-all" href={`https://ror.org/${inst.ror}`} target="_blank" rel="noopener noreferrer">ROR<span className="sr-only"> {t('newTab')}</span></a> : null}
      />
      <div className="dash">
        <KpiRow>
          <KpiCard icon="articles" label={t('col.articles')} value={fmtInt(inst.articles)} sub={sx('in.articlesSub', { a: w.start, b: w.end, all: fmtInt(inst.articles_total) })} />
          <KpiCard icon="topics" label={sx('in.col.recent', { r: yearSpan(r.start, r.end) })} value={fmtInt(inst.articles_recent ?? null)} />
          <KpiCard icon="goals" label={sx('in.col.intl')} value={fmtPct(inst.intl_share ?? null, 0)} />
          <KpiCard icon="building" label={sx('in.col.partners')} value={fmtInt(inst.partners ?? null)} sub={sx('in.kpiTopics', { n: fmtInt(inst.topics ?? null) })} />
        </KpiRow>
        {years.length || topics.length ? (
          <DashGrid>
            {years.length ? (
              <Section id="years" span={topics.length ? 6 : 12} title={sx('in.years.h')}>
                <ColumnChart
                  items={years.map((y) => ({ key: String(y.year), value: y.articles }))}
                  format={fmtInt}
                  label={x('xv.yr.label', { a: years[0].year, b: years[years.length - 1].year, values: years.map((y) => fmtInt(y.articles)).join(', ') })}
                />
              </Section>
            ) : null}
            {topics.length ? (
              <Section id="topics" span={years.length ? 6 : 12} title={sx('in.topics.h')} intro={x('xv.mix.how', { n: MIX_TOP })}>
                <MixBar parts={mix} label={x('xv.mix.label', { parts: mixText })} />
                {signals.length ? (
                  <>
                    <p className="card-h3">{sx('in.emerging')}</p>
                    <ul className="opp-list">
                      {signals.map((tp) => (
                        <li key={tp.id}><TopicLink topic={tp} showStatus /></li>
                      ))}
                    </ul>
                  </>
                ) : null}
              </Section>
            ) : null}
          </DashGrid>
        ) : null}
        {partners.length || countries.length || suggested.length ? (
          <DashGrid>
            {partners.length ? (
              <Section id="partners" span={4} title={sx('in.partners.h')}>
                <BarRank rows={partnerBars.rows} href={(row) => (row.id ? `/institutions/${row.id}` : null)} value={(row) => fmtInt(row.count)} label={x('xv.ptn.label')} />
              </Section>
            ) : null}
            {countries.length ? (
              <Section id="abroad" span={4} title={sx('in.countries.h')}>
                <BarRank rows={countryBars.rows} value={(row) => fmtInt(row.count)} label={x('xv.ctry.label')} />
              </Section>
            ) : null}
            {suggested.length ? (
              <Section id="suggested" span={4} title={sx('in.suggest.h')} intro={sx('in.suggest.intro', { x: instName(byId.get(suggested[0].id) as InstitutionSummary, lang).text, a: w.start, b: w.end })}>
                <RankRows
                  numbered={false}
                  label={sx('in.suggest.h')}
                  rows={suggested.map((sg) => {
                    const n = instName(byId.get(sg.id) as InstitutionSummary, lang)
                    const shared = (sg.topics ?? []).map((tid) => topicOf(tid)).filter((tp): tp is Topic => tp !== undefined).map((tp) => name(tp))
                    return { key: sg.id, to: `/institutions/${sg.id}`, name: n.text, nameLang: n.lang ?? undefined, meta: shared.length ? <span className="rise-sub">{shared.join(' · ')}</span> : undefined }
                  })}
                />
              </Section>
            ) : null}
          </DashGrid>
        ) : null}
        {detailFile.status === 'loading' ? <p className="loading" role="status">{t('loading')}</p> : null}
      </div>
    </>
  )
}
