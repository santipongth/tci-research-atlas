import { BarRank } from '../../charts/BarRank'
import { rankBars } from '../../charts/infographic'
import { Card, SeeAll, type Span } from '../../components/dashboard/Card'
import { ProvinceMap } from '../../components/ProvinceMap'
import { useRelease, useReleaseFile } from '../../data/atlasContext'
import { MODULE_FILES } from '../../data/release'
import type { InstitutionsFile, ProvinceStat, RegionsFile } from '../../data/types'
import { instName } from '../../lib/executive'
import { fmtInt } from '../../lib/format'
import { useI18n, useStrings } from '../../lib/i18n'
import { execPages } from '../../strings/execPages'

/** The overview's "where" cards (lazy: the province outlines and both module files stay out of the entry chunk). */
export default function PlacesCards({ regions, institutions, span }: { regions: boolean; institutions: boolean; span: Span }) {
  return (
    <>
      {regions ? <ProvincesCard span={span} /> : null}
      {institutions ? <InstitutionsCard span={span} /> : null}
    </>
  )
}

function Pending({ span, title }: { span: Span; title: string }) {
  const { t } = useI18n()
  return (
    <section className={`card span-${span}`} aria-label={title}>
      <p className="loading" role="status">{t('loading')}</p>
    </section>
  )
}

function ProvincesCard({ span }: { span: Span }) {
  const { t } = useI18n()
  const file = useReleaseFile<RegionsFile>(MODULE_FILES.regions)
  if (file.status === 'loading') return <Pending span={span} title={t('ov.d.prov')} />
  if (file.status !== 'ready') return null
  return <Provinces file={file.data} span={span} />
}

/** Card: a small choropleth of articles by province beside the five provinces with the most articles. */
function Provinces({ file, span }: { file: RegionsFile; span: Span }) {
  const { t, lang } = useI18n()
  const sx = useStrings(execPages)
  const pname = (p: ProvinceStat) => (lang === 'en' ? p.name_en : p.name_th)
  const top = rankBars(file.provinces.map((p) => ({ key: pname(p), id: p.code, count: p.articles })), 5)
  const located = file.provinces.filter((p) => p.articles > 0).length
  return (
    <Card span={span} title={t('ov.d.prov')} info={t('ov.d.provSub', { n: fmtInt(located), a: file.window.start, b: file.window.end })} action={<SeeAll to="/places" label={t('dash.seeAll')} />}>
      <div className="pv-mini">
        <div className="pv-mini-map">
          <ProvinceMap
            values={new Map(file.provinces.map((p) => [p.code, p.articles]))}
            format={(v) => fmtInt(v)}
            label={sx('rg.map', { m: sx('rg.metric.articles'), n: fmtInt(located) })}
            noData={sx('rg.noData')}
            range={(a, b) => sx('rg.range', { a, b })}
          />
        </div>
        <div className="pv-mini-top">
          <BarRank rows={top.rows} href={(r) => (r.id ? `/province/${r.id}` : null)} value={(r) => fmtInt(r.count)} label={t('ov.d.provTop')} />
        </div>
      </div>
    </Card>
  )
}

function InstitutionsCard({ span }: { span: Span }) {
  const { t } = useI18n()
  const file = useReleaseFile<InstitutionsFile>(MODULE_FILES.institutions)
  if (file.status === 'loading') return <Pending span={span} title={t('ov.d.inst')} />
  if (file.status !== 'ready' || !file.data.institutions.length) return null
  return <Institutions file={file.data} span={span} />
}

/** Card: the six institutions with the most articles as a bar list (every bar has its number). */
function Institutions({ file, span }: { file: InstitutionsFile; span: Span }) {
  const { t, lang } = useI18n()
  const total = useRelease()?.overview.kpis.institutions ?? file.institutions.length
  const top = rankBars(file.institutions.map((i) => ({ key: instName(i, lang).text, id: i.id, count: i.articles })), 6)
  return (
    <Card span={span} title={t('ov.d.inst')} info={t('ov.d.instSub', { n: fmtInt(total), k: fmtInt(file.min_articles), a: file.window.start, b: file.window.end })} action={<SeeAll to="/places" label={t('dash.seeAll')} />}>
      <BarRank rows={top.rows} href={(r) => (r.id ? `/institutions/${r.id}` : null)} value={(r) => fmtInt(r.count)} label={t('ov.d.inst')} />
    </Card>
  )
}
