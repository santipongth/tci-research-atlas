import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { CiWhisker } from '../components/CiWhisker'
import { StatusGlyph } from '../components/StatusGlyph'
import type { Topic } from '../data/types'
import { DEFINITION } from '../lib/definition'
import { fmtSignedPct } from '../lib/format'
import { useI18n } from '../lib/i18n'
import type { SignalStatus } from '../lib/status'
import { useElementSize } from '../lib/useElementSize'
import { FOREST_DOMAIN } from '../pages/topicColumns'
import { linear } from './scale'

export interface ForestGroup {
  status: SignalStatus
  title: string
  rule?: string
  note?: ReactNode
  rows: readonly Topic[]
  total: number
  more?: { to: string; label: string }
}

const TICKS = [-0.2, 0, 0.2, 0.4, 0.6, 0.8, 1.0]

/**
 * CI forest plot (Editorial signature): one row per topic — name | interval on a shared axis | value —
 * grouped by status, with a dashed line at the EMERGING bar and a solid line at zero. Rows are links.
 */
export function ForestPlot({ groups, axisLabel, refLabel, subtitle, domain = FOREST_DOMAIN, refValue = DEFINITION.emergingMinGrowthLo }: {
  groups: readonly ForestGroup[]
  axisLabel: string
  refLabel: string
  subtitle: (t: Topic) => string
  domain?: readonly [number, number]
  refValue?: number
}) {
  const [plotRef, { width }] = useElementSize<HTMLDivElement>()
  const { t, name } = useI18n()
  const x = linear(domain[0], domain[1], 6, Math.max(width, 12) - 6)
  return (
    <div className="forest">
      <div className="fr-axis" aria-hidden="true">
        <div className="fr-axislabel">{axisLabel}</div>
        <div className="fr-axis-plot" ref={plotRef}>
          {width > 0 ? (
            <svg width={width} height={34} viewBox={`0 0 ${width} 34`}>
              <text x={x(refValue)} y={10} textAnchor="middle" className="ax-ref">{refLabel}</text>
              {TICKS.filter((v) => v >= domain[0] && v <= domain[1]).map((v) => (
                <text key={v} x={x(v)} y={28} textAnchor="middle" className="ax-tick">{v === 0 ? '0%' : fmtSignedPct(v, 0)}</text>
              ))}
            </svg>
          ) : null}
        </div>
        <div />
      </div>
      {groups.map((g) => (
        <div className="fr-group" key={g.status}>
          <div className="fr-ghead">
            <h3 className="fr-gname">
              <StatusGlyph status={g.status} size={16} />
              <span>{g.title}</span>
              <small>{t('ov.forest.shown', { a: g.rows.length, b: g.total })}</small>
            </h3>
            {g.rule ? <p className="fr-grule">{g.rule}</p> : null}
          </div>
          {g.note}
          <ul className="fr-list">
            {g.rows.map((tp) => (
              <li key={tp.id}>
                <Link className="fr-row" to={`/topics/${tp.id}`}>
                  <span className="fr-name">
                    <b>{name(tp)}</b>
                    <span>{subtitle(tp)}</span>
                  </span>
                  <span className="fr-plot">
                    <CiWhisker status={tp.status} value={tp.metrics.share_growth} lo={tp.metrics.share_growth_lo} hi={tp.metrics.share_growth_hi} domain={domain} refValue={refValue} width={width} height={26} />
                  </span>
                  <span className="fr-val">
                    <b>{fmtSignedPct(tp.metrics.share_growth)}</b>
                    <span>{fmtSignedPct(tp.metrics.share_growth_lo, 0)} {t('to')} {fmtSignedPct(tp.metrics.share_growth_hi, 0)}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
          {g.more ? (
            <p className="fr-more">
              <Link to={g.more.to}>{g.more.label}</Link>
            </p>
          ) : null}
        </div>
      ))}
    </div>
  )
}
