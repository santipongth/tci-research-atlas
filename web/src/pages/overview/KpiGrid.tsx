import { StatGrid, StatTile } from '../../components/StatTile'
import type { AtlasRelease } from '../../data/release'
import type { Kpis } from '../../data/types'
import { fmtInt, fmtNum, kpiDelta, kpiDir } from '../../lib/format'
import { useI18n } from '../../lib/i18n'
import type { StrKey } from '../../strings'

interface Kpi {
  key: keyof Kpis
  label: StrKey
  unit: 'count' | 'pct'
}

/** The four figures every reader needs first; the rest open under "ดูตัวเลขเพิ่ม". */
const PRIMARY: readonly Kpi[] = [
  { key: 'articles', label: 'kpi.articles', unit: 'count' },
  { key: 'topics', label: 'kpi.topics', unit: 'count' },
  { key: 'journals', label: 'kpi.journals', unit: 'count' },
  { key: 'institutions', label: 'kpi.institutions', unit: 'count' },
]
const MORE: readonly Kpi[] = [
  { key: 'groups', label: 'kpi.groups', unit: 'count' },
  { key: 'pct_abstract_en', label: 'kpi.abstractEn', unit: 'pct' },
  { key: 'pct_international', label: 'kpi.international', unit: 'pct' },
  { key: 'provinces', label: 'kpi.provinces', unit: 'count' },
]

const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null)

/** E1: KPI tiles — a KPI the release does not carry (e.g. P3 KPIs of an older release) is left out; Δ only when the
 *  previous release's overview carries it too. The article tile carries the yearly article count as a sparkline. */
export function KpiGrid({ release, more: showMore = true }: { release: AtlasRelease; more?: boolean }) {
  const { t, lang } = useI18n()
  const now = release.overview.kpis
  const prev = release.previousOverview
  const tile = (k: Kpi) => {
    const value = num(now[k.key])
    if (value === null) return null
    const before = prev ? num(prev.kpis?.[k.key]) : null
    const delta = kpiDelta(value, before, k.unit, lang)
    return (
      <StatTile
        key={k.key}
        label={t(k.label)}
        value={k.unit === 'pct' ? `${fmtNum(value, 1)}%` : fmtInt(value)}
        // the arrow follows the change as printed: no arrow beside "±0.0"
        delta={delta && prev ? { text: delta, dir: kpiDir(value, before, k.unit), ref: t('delta', { prev: prev.release }) } : null}
      />
    )
  }
  const more = MORE.filter((k) => num(now[k.key]) !== null)
  return (
    <>
      <StatGrid cols={4}>{PRIMARY.map(tile)}</StatGrid>
      {showMore && more.length ? (
        <details className="stats-more">
          <summary>{t('stat.more', { n: more.length })}</summary>
          <StatGrid cols={4}>{more.map(tile)}</StatGrid>
        </details>
      ) : null}
    </>
  )
}
