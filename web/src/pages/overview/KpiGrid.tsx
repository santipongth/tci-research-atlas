import type { AtlasRelease } from '../../data/release'
import type { Kpis } from '../../data/types'
import { fmtInt, fmtNum, kpiDelta, kpiDir } from '../../lib/format'
import { useI18n } from '../../lib/i18n'
import type { StrKey } from '../../strings'

const KPIS: readonly { key: keyof Kpis; label: StrKey; unit: 'count' | 'pct' }[] = [
  { key: 'articles', label: 'kpi.articles', unit: 'count' },
  { key: 'topics', label: 'kpi.topics', unit: 'count' },
  { key: 'groups', label: 'kpi.groups', unit: 'count' },
  { key: 'journals', label: 'kpi.journals', unit: 'count' },
  { key: 'institutions', label: 'kpi.institutions', unit: 'count' },
  { key: 'pct_abstract_en', label: 'kpi.abstractEn', unit: 'pct' },
]

/** E1: KPI tiles; Δ only when the previous release's overview is on the site. */
export function KpiGrid({ release }: { release: AtlasRelease }) {
  const { t, lang } = useI18n()
  const now = release.overview.kpis
  const prev = release.previousOverview
  return (
    <dl className="kpis">
      {KPIS.map((k) => {
        const value = now[k.key]
        const before = prev ? prev.kpis[k.key] : null
        const delta = kpiDelta(value, before, k.unit, lang)
        // the arrow follows the change as printed: no arrow beside "±0.0"
        const dir = kpiDir(value, before, k.unit)
        return (
          <div className="kpi" key={k.key}>
            <dt>{t(k.label)}</dt>
            <dd>
              <span className="v">{k.unit === 'pct' ? `${fmtNum(value, 1)}%` : fmtInt(value)}</span>
              {delta && prev ? (
                <span className={dir < 0 ? 'd is-down' : 'd'}>
                  {dir !== 0 ? (
                    <svg viewBox="0 0 10 10" aria-hidden="true" focusable="false">
                      <path d={dir > 0 ? 'M5 1.5L9 7.5H1z' : 'M5 8.5L9 2.5H1z'} fill="currentColor" />
                    </svg>
                  ) : null}
                  <span>{delta}</span>
                  <span className="d-ref">{t('delta', { prev: prev.release })}</span>
                </span>
              ) : null}
            </dd>
          </div>
        )
      })}
    </dl>
  )
}
