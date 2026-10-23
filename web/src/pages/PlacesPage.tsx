import { Link } from 'react-router'
import { ArcNetwork } from '../charts/ArcNetwork'
import { BarRank } from '../charts/BarRank'
import { networkNodes } from '../charts/execLayout'
import { rankBars } from '../charts/infographic'
import { Card, DashGrid, DashStack } from '../components/dashboard/Card'
import { KpiCard, KpiRow } from '../components/dashboard/KpiCard'
import { MoreRows, RankRows } from '../components/dashboard/RankRows'
import { PageBar } from '../components/dashboard/PageBar'
import { Segmented } from '../components/dashboard/Segmented'
import { EmptyState } from '../components/EmptyState'
import { InstitutionLink } from '../components/InstitutionLink'
import { ProvinceMap } from '../components/ProvinceMap'
import { RequireRelease } from '../components/RequireRelease'
import { useReleaseFile } from '../data/atlasContext'
import { hasModule, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { InstitutionsFile, InstitutionSummary, ProvinceStat, RegionsFile } from '../data/types'
import { instName } from '../lib/executive'
import { fmtInt, fmtNum, fmtPct } from '../lib/format'
import { useI18n, useStrings } from '../lib/i18n'
import { sortBy } from '../lib/sort'
import { usePaged } from '../lib/usePaged'
import { placesCodec, REGION_METRICS } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import { dashPages } from '../strings/dashPages'
import { execPages } from '../strings/execPages'
import { execViz } from '../strings/execViz'

/** Institutions drawn in the partnership arcs. */
const NET_NODES = 8
const REGION_ORDER = ['bangkok', 'central', 'north', 'northeast', 'south'] as const

export default function PlacesPage() {
  const s = useStrings(dashPages)
  return <RequireRelease title={s('pl.title')}>{(release) => <PlacesLoad release={release} />}</RequireRelease>
}

/** Both module files are optional: each card shows when its file is there; with neither the page says why. */
function PlacesLoad({ release }: { release: AtlasRelease }) {
  const { t } = useI18n()
  const s = useStrings(dashPages)
  const regionsOn = hasModule(release, 'regions')
  const instOn = hasModule(release, 'institutions')
  const regions = useReleaseFile<RegionsFile>(regionsOn ? MODULE_FILES.regions : null)
  const inst = useReleaseFile<InstitutionsFile>(instOn ? MODULE_FILES.institutions : null)
  if (!regionsOn && !instOn) {
    return (
      <>
        <PageBar title={s('pl.title')} />
        <div className="dash"><EmptyState title={t('mod.absent')}><p>{t('mod.absentBody')}</p></EmptyState></div>
      </>
    )
  }
  if ((regionsOn && regions.status === 'loading') || (instOn && inst.status === 'loading')) {
    return (
      <>
        <PageBar title={s('pl.title')} />
        <div className="dash"><p className="loading" role="status">{t('loading')}</p></div>
      </>
    )
  }
  return <Places release={release} regions={regions.status === 'ready' ? regions.data : null} inst={inst.status === 'ready' ? inst.data : null} />
}

function Places({ release, regions, inst }: { release: AtlasRelease; regions: RegionsFile | null; inst: InstitutionsFile | null }) {
  const s = useStrings(dashPages)
  const kpis = release.overview.kpis
  const w = inst?.window ?? regions?.window ?? null
  const provincesWith = regions ? regions.provinces.filter((p) => p.articles > 0).length : (kpis.provinces ?? null)
  return (
    <>
      <PageBar
        title={s('pl.title')}
        sub={w ? s('pl.sub', { a: w.start, b: w.end }) : undefined}
        info={inst ? s('pl.info', { n: fmtInt(inst.min_articles) }) : undefined}
      />
      <div className="dash">
        <KpiRow>
          {inst ? <KpiCard icon="building" label={s('pl.k.inst')} value={fmtInt(inst.institutions.length)} /> : null}
          {provincesWith !== null ? <KpiCard icon="places" label={s('pl.k.prov')} value={fmtInt(provincesWith)} /> : null}
          {inst?.pct_multi_institution != null ? <KpiCard icon="layers" label={s('pl.k.multi')} value={fmtPct(inst.pct_multi_institution, 1)} /> : null}
          {inst?.pct_international != null ? <KpiCard icon="goals" label={s('pl.k.intl')} value={fmtPct(inst.pct_international, 1)} /> : null}
        </KpiRow>
        {regions ? (
          <DashGrid>
            <MapCard file={regions} />
            <DashStack span={5}>
              <RegionsCard file={regions} />
              {inst?.countries?.length ? <CountriesCard file={inst} /> : null}
            </DashStack>
          </DashGrid>
        ) : null}
        {inst ? (
          <DashGrid>
            <InstitutionsCard file={inst} />
            <NetworkCard file={inst} />
          </DashGrid>
        ) : null}
        {regions ? (
          <DashGrid>
            <AllProvincesCard file={regions} />
          </DashGrid>
        ) : inst?.countries?.length ? (
          <DashGrid>
            <CountriesCard file={inst} />
          </DashGrid>
        ) : null}
      </div>
    </>
  )
}

/** The choropleth beside the ten provinces with the most articles (or per 100,000 people when the release can say). */
function MapCard({ file }: { file: RegionsFile }) {
  const { lang } = useI18n()
  const s = useStrings(dashPages)
  const sx = useStrings(execPages)
  const [state, update] = useUrlState(placesCodec)
  const hasPop = file.provinces.some((p) => p.per_100k != null)
  const metric = hasPop ? state.m : 'articles'
  const valueOf = (p: ProvinceStat): number | null => (metric === 'per100k' ? (p.per_100k ?? null) : p.articles)
  const format = (v: number) => (metric === 'per100k' ? fmtNum(v, 1) : fmtInt(v))
  const measure = sx(metric === 'per100k' ? 'rg.metric.per100k' : 'rg.metric.articles')
  const pname = (p: ProvinceStat) => (lang === 'en' ? p.name_en : p.name_th)
  const top = rankBars(file.provinces.map((p) => ({ key: pname(p), id: p.code, count: valueOf(p) ?? Number.NaN })), 10)
  return (
    <Card span={7} title={s('pl.map')} info={s('pl.mapInfo', { m: measure })}>
      {hasPop ? (
        <Segmented
          label={s('pl.metric')}
          value={metric}
          onChange={(m) => update({ m })}
          options={REGION_METRICS.map((m) => ({ id: m, label: sx(m === 'per100k' ? 'rg.metric.per100k' : 'rg.metric.articles') }))}
        />
      ) : null}
      <div className="pv-big">
        <div className="pv-mini-map">
          <ProvinceMap
            values={new Map(file.provinces.map((p) => [p.code, valueOf(p)]))}
            format={format}
            label={sx('rg.map', { m: measure, n: fmtInt(file.provinces.filter((p) => valueOf(p) !== null).length) })}
            noData={sx('rg.noData')}
            range={(a, b) => sx('rg.range', { a, b })}
          />
        </div>
        <div className="pv-mini-top">
          <BarRank rows={top.rows} href={(r) => (r.id ? `/province/${r.id}` : null)} value={(r) => format(r.count)} label={s('pl.top')} />
        </div>
      </div>
    </Card>
  )
}

/** Articles by region (five regions, bars with their numbers). */
function RegionsCard({ file }: { file: RegionsFile }) {
  const s = useStrings(dashPages)
  const sx = useStrings(execPages)
  const bars = rankBars(file.regions.map((r) => ({ key: sx(`rg.region.${r.key}` as keyof typeof execPages), id: r.key, count: r.articles })), file.regions.length)
  if (!bars.rows.length) return null
  return (
    <Card span={12} title={s('pl.regions')} info={s('pl.regionsInfo', { a: file.window.start, b: file.window.end })}>
      <BarRank rows={bars.rows} value={(r) => fmtInt(r.count)} label={s('pl.regions')} />
    </Card>
  )
}

/** Institutions by articles, ten at a time, each with its type and province. */
function InstitutionsCard({ file }: { file: InstitutionsFile }) {
  const { lang } = useI18n()
  const s = useStrings(dashPages)
  const sx = useStrings(execPages)
  const provinces = new Map((file.province_names ?? []).map((p) => [p.code, lang === 'en' ? p.name_en : p.name_th]))
  const ranked = sortBy(file.institutions, (i) => i.articles, 'desc')
  const page = usePaged(ranked, 10)
  if (!ranked.length) return null
  return (
    <Card span={5} title={s('pl.inst')} info={s('pl.instInfo', { a: file.window.start, b: file.window.end })}>
      <RankRows
        label={s('pl.inst')}
        rows={page.shown.map((i) => {
          const n = instName(i, lang)
          const place = i.province ? (provinces.get(i.province) ?? i.province) : i.country && i.country !== 'TH' ? sx('in.abroad', { c: i.country }) : null
          return {
            key: i.id,
            to: `/institutions/${i.id}`,
            name: n.text,
            nameLang: n.lang ?? undefined,
            meta: <span className="rise-sub">{[sx(`in.type.${i.type ?? 'other'}` as keyof typeof execPages), place].filter(Boolean).join(' · ')}</span>,
            value: <b className="rise-a">{fmtInt(i.articles)}</b>,
          }
        })}
      />
      <MoreRows {...page.more} />
    </Card>
  )
}

/** The partnership arcs between the institutions with the strongest joint output. */
function NetworkCard({ file }: { file: InstitutionsFile }) {
  const { lang } = useI18n()
  const s = useStrings(dashPages)
  const x = useStrings(execViz)
  const byId = new Map(file.institutions.map((i) => [i.id, i]))
  const edges = (file.edges ?? []).filter((e) => byId.has(e.a) && byId.has(e.b))
  if (!edges.length) return null
  const net = networkNodes(edges, NET_NODES)
  const rows = net.ids.map((id) => byId.get(id) as InstitutionSummary)
  return (
    <Card span={7} title={s('pl.net')} info={s('pl.netInfo', { n: fmtInt(rows.length) })}>
      <ArcNetwork
        rows={rows.map((i) => ({ id: i.id, name: <InstitutionLink inst={i} />, text: instName(i, lang).text, weight: i.articles, sub: x('xv.articles', { k: fmtInt(i.articles) }) }))}
        links={net.links.map((e) => ({ a: e.a, b: e.b, value: e.articles }))}
        label={x('xv.net.label', { n: fmtInt(edges.length) })}
        pairTitle={(a, b, k) => x('xv.net.pair', { a, b, k: fmtInt(k) })}
        maxNodes={NET_NODES}
      />
    </Card>
  )
}

/** The countries Thai authors write with most. */
function CountriesCard({ file }: { file: InstitutionsFile }) {
  const { lang } = useI18n()
  const s = useStrings(dashPages)
  const bars = rankBars((file.countries ?? []).map((c) => ({ key: lang === 'en' ? c.name_en : c.name_th, id: c.code, count: c.articles })), 8)
  return (
    <Card span={12} title={s('pl.ctry')} info={s('pl.ctryInfo', { a: file.window.start, b: file.window.end })}>
      <BarRank rows={bars.rows} value={(r) => fmtInt(r.count)} label={s('pl.ctry')} />
    </Card>
  )
}

/** Every province grouped by region in columns, each with the number the map is coloured by: the way into a province
 *  page (no search box), and the map's figures in words for every province, not only the top 10. */
function AllProvincesCard({ file }: { file: RegionsFile }) {
  const { lang } = useI18n()
  const s = useStrings(dashPages)
  const sx = useStrings(execPages)
  const [state] = useUrlState(placesCodec)
  const metric = file.provinces.some((p) => p.per_100k != null) ? state.m : 'articles'
  const valueOf = (p: ProvinceStat): number | null => (metric === 'per100k' ? (p.per_100k ?? null) : p.articles)
  const pname = (p: ProvinceStat) => (lang === 'en' ? p.name_en : p.name_th)
  const cols = REGION_ORDER.map((r) => ({ r, list: sortBy(file.provinces.filter((p) => p.region === r), (p) => valueOf(p) ?? -1, 'desc') })).filter((c) => c.list.length)
  if (!cols.length) return null
  return (
    <Card span={12} title={s('pl.all')} info={s('pl.allInfo')}>
      <div className="prov-cols">
        {cols.map(({ r, list }) => (
          <div key={r}>
            <p className="card-h3">{sx(`rg.region.${r}` as keyof typeof execPages)}</p>
            <ul>
              {list.map((p) => (
                <li key={p.code}>
                  <Link to={`/province/${p.code}`}>{pname(p)}</Link>
                  <span>{metric === 'per100k' ? fmtNum(valueOf(p), 1) : fmtInt(p.articles)}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </Card>
  )
}
