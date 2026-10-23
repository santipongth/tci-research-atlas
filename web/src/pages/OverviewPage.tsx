import { lazy, Suspense } from 'react'
import { Card, DashGrid, type Span } from '../components/dashboard/Card'
import { Icon } from '../components/dashboard/Icon'
import { Segmented } from '../components/dashboard/Segmented'
import { KpiCard, KpiRow } from '../components/dashboard/KpiCard'
import { PageBar } from '../components/dashboard/PageBar'
import { EmptyState } from '../components/EmptyState'
import { RequireRelease } from '../components/RequireRelease'
import { hasModule, type AtlasRelease } from '../data/release'
import type { Kpis } from '../data/types'
import { fmtDate, fmtInt, fmtNum, kpiDelta, kpiDir } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { pickRisers } from '../lib/story'
import { useMediaQuery } from '../lib/useMediaQuery'
import { overviewCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import type { StrKey } from '../strings'
import type { IconName } from '../components/dashboard/Icon'
import { MovesCard, RisingChartCard } from './overview/RisingCards'
import { StatusCard } from './overview/StatusCard'

// The province map (its outlines) and the institutions list load on demand: neither is needed for the first paint.
const PlacesCards = lazy(() => import('./overview/PlacesCards'))

interface Kpi {
  key: keyof Kpis
  label: StrKey
  unit: 'count' | 'pct'
  icon: IconName
}

/** The four figures every reader needs first, as KPI cards. */
const PRIMARY: readonly Kpi[] = [
  { key: 'articles', label: 'kpi.articles', unit: 'count', icon: 'articles' },
  { key: 'topics', label: 'kpi.topics', unit: 'count', icon: 'layers' },
  { key: 'journals', label: 'kpi.journals', unit: 'count', icon: 'journals' },
  { key: 'institutions', label: 'kpi.institutions', unit: 'count', icon: 'building' },
]
/** The rest of the release's figures, listed in one card. */
const MORE: readonly Omit<Kpi, 'icon'>[] = [
  { key: 'groups', label: 'kpi.groups', unit: 'count' },
  { key: 'provinces', label: 'kpi.provinces', unit: 'count' },
  { key: 'pct_international', label: 'kpi.international', unit: 'pct' },
  { key: 'pct_abstract_en', label: 'kpi.abstractEn', unit: 'pct' },
]

const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null)

export default function OverviewPage() {
  const { t } = useI18n()
  return <RequireRelease title={t('nav.overview')}>{(release) => <Overview release={release} />}</RequireRelease>
}

/**
 * The national picture on one screen (it is also the executive brief: "พิมพ์ / บันทึก PDF" prints it): KPIs, what is
 * rising or falling, the status mix, where the work happens, the release's findings and its notes for policy makers.
 */
function Overview({ release }: { release: AtlasRelease }) {
  const { t, lang } = useI18n()
  const [state, update] = useUrlState(overviewCodec)
  const ov = release.overview
  const prev = release.previousOverview
  const risers = pickRisers(release.topics, 5)
  // phones skip the line chart: the ranked list beside it carries the same topics with their trend lines
  const phone = useMediaQuery('(max-width: 760px)')
  const exec = ov.executive ? ((lang === 'en' ? ov.executive.bullets_en : ov.executive.bullets_th) ?? []) : []
  const finds = ov.brief ? ((lang === 'en' ? ov.brief.bullets_en : ov.brief.bullets_th) ?? []) : []
  const pt = !finds.length ? 'policy' : !exec.length ? 'find' : state.pt
  const points = (pt === 'find' ? finds : exec).slice(0, 4)
  // the printed brief carries both lists: the one not shown on screen is print-only
  const other = (pt === 'find' ? exec : finds).slice(0, 4)
  const listName = (which: 'find' | 'policy') => t(which === 'find' ? 'ov.d.find' : 'ov.d.policy')
  const regions = hasModule(release, 'regions')
  const institutions = hasModule(release, 'institutions')
  const row3 = 1 + Number(regions) + Number(institutions)
  const span: Span = row3 === 3 ? 4 : row3 === 2 ? 6 : 12
  const trimmed = release.manifest.trimmed_years ?? []
  const value = (k: Pick<Kpi, 'key' | 'unit'>) => {
    const v = num(ov.kpis[k.key])
    return v === null ? null : k.unit === 'pct' ? `${fmtNum(v, 1)}%` : fmtInt(v)
  }
  const delta = (k: Pick<Kpi, 'key' | 'unit'>) => {
    const v = num(ov.kpis[k.key])
    const before = prev ? num(prev.kpis?.[k.key]) : null
    const text = v === null ? null : kpiDelta(v, before, k.unit, lang)
    // the arrow follows the change as printed: no arrow beside "±0.0"
    return v !== null && text && prev ? { text, dir: kpiDir(v, before, k.unit), ref: t('delta', { prev: prev.release }) } : null
  }
  const more = MORE.filter((k) => value(k) !== null)
  return (
    <>
      <PageBar
        title={t('nav.overview')}
        sub={t(prev ? 'ov.d.subPrev' : 'ov.d.sub', { year: ov.last_complete_year, date: fmtDate(ov.generated_at, lang), prev: prev?.release ?? '' })}
        actions={
          <button type="button" className="btn-quiet no-print" onClick={() => window.print()}>
            <Icon name="download" size={18} />
            {t('ov.d.print')}
          </button>
        }
      />
      <div className="dash">
        <KpiRow>
          {PRIMARY.map((k) => {
            const v = value(k)
            return v === null ? null : <KpiCard key={k.key} icon={k.icon} label={t(k.label)} value={v} delta={delta(k)} sub={prev ? undefined : t('firstRelease')} />
          })}
        </KpiRow>
        {release.topics.length ? (
          <>
            <DashGrid>
              {phone ? null : <RisingChartCard release={release} risers={risers} />}
              <MovesCard release={release} risers={risers} move={state.mv} onMove={(mv) => update({ mv })} />
            </DashGrid>
            <DashGrid>
              <StatusCard release={release} span={span} />
              {regions || institutions ? (
                <Suspense fallback={<PendingCards n={row3 - 1} span={span} />}>
                  <PlacesCards regions={regions} institutions={institutions} span={span} />
                </Suspense>
              ) : null}
            </DashGrid>
          </>
        ) : (
          <EmptyState title={t('empty.topics')} />
        )}
        <DashGrid>
          {points.length ? (
            <Card span={more.length ? 8 : 12} title={t('ov.d.points')} info={t('brief.execNote')}>
              {finds.length && exec.length ? (
                <Segmented
                  label={t('ov.d.pointsSwitch')}
                  value={pt}
                  onChange={(v) => update({ pt: v })}
                  options={[{ id: 'find', label: t('ov.d.find') }, { id: 'policy', label: t('ov.d.policy') }]}
                />
              ) : null}
              {other.length ? <p className="card-h3 print-only">{listName(pt)}</p> : null}
              <ol className="pol">
                {points.map((b, i) => (
                  <li key={i}>
                    <span className="pol-n" aria-hidden="true">{i + 1}</span>
                    <p>{b}</p>
                  </li>
                ))}
              </ol>
              {other.length ? (
                <div className="print-only">
                  <p className="card-h3">{listName(pt === 'find' ? 'policy' : 'find')}</p>
                  <ol className="pol">
                    {other.map((b, i) => (
                      <li key={i}>
                        <span className="pol-n" aria-hidden="true">{i + 1}</span>
                        <p>{b}</p>
                      </li>
                    ))}
                  </ol>
                </div>
              ) : null}
            </Card>
          ) : null}
          {more.length ? (
            <Card span={points.length ? 4 : 12} title={t('ov.d.facts')} info={trimmed.length ? t('ov.trimmed', { years: trimmed.join(', ') }) : undefined}>
              <dl className="facts">
                {more.map((k) => {
                  const d = delta(k)
                  return (
                    <div key={k.key}>
                      <dt>{t(k.label)}</dt>
                      <dd>
                        <b>{value(k)}</b>
                        {d ? <span className={d.dir < 0 ? 'facts-d is-down' : 'facts-d'}>{d.text}</span> : null}
                      </dd>
                    </div>
                  )
                })}
              </dl>
            </Card>
          ) : null}
        </DashGrid>
      </div>
    </>
  )
}

function PendingCards({ n, span }: { n: number; span: Span }) {
  const { t } = useI18n()
  return (
    <>
      {Array.from({ length: n }, (_, i) => (
        <div key={i} className={`card span-${span}`}>
          <p className="loading" role="status">{t('loading')}</p>
        </div>
      ))}
    </>
  )
}
