import { TopicName } from '../components/TopicName'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { CiWhisker } from '../components/CiWhisker'
import { StatusGlyph } from '../components/StatusGlyph'
import type { Topic } from '../data/types'
import { DEFINITION } from '../lib/definition'
import { fmtInt, fmtSignedPct } from '../lib/format'
import { hasCi } from '../lib/forest'
import { useI18n } from '../lib/i18n'
import type { SignalStatus } from '../lib/status'
import { useElementSize } from '../lib/useElementSize'
import { dataDomain, linear, niceTicks } from './scale'

export interface ForestGroup {
  status: SignalStatus
  title: string
  rule?: string
  note?: ReactNode
  rows: readonly Topic[]
  total: number
  /** topics of this status without a confidence interval (drawn as text rows when shown) */
  noCi?: number
  more?: { to: string; label: string }
}

/** Growth-axis limits: a share cannot fall faster than −100 %/yr; an interval beyond +300 %/yr runs to the edge as an arrow (its numbers are beside it). */
const CAP: readonly [number, number] = [-1, 3]

/**
 * CI forest plot (Editorial signature): one row per topic — name | interval on a shared axis | value —
 * grouped by status, with a dashed line at the EMERGING bar and a solid line at zero. Rows are links.
 * The axis covers every interval shown (plus zero and the bar) unless a `domain` is given.
 */
export function ForestPlot({ groups, axisLabel, refLabel, subtitle, level, base, domain, refValue = DEFINITION.emergingMinGrowthLo, wide = false }: {
  groups: readonly ForestGroup[]
  axisLabel: string
  refLabel: string
  subtitle: (t: Topic) => string
  /** interval level in percent (90), for the row's spoken name */
  level: number
  /** the baseline years ("2016–2020"), for "new — none in …" */
  base: string
  domain?: readonly [number, number]
  refValue?: number
  /** a full-width page (/emerging): narrower name and value columns, a taller whisker */
  wide?: boolean
}) {
  const [plotRef, { width }] = useElementSize<HTMLDivElement>()
  const { t, name } = useI18n()
  const dom = domain ?? dataDomain(groups.flatMap((g) => g.rows.flatMap((tp) => [tp.metrics.share_growth_lo, tp.metrics.share_growth_hi, tp.metrics.share_growth])), [0, refValue], CAP)
  const x = linear(dom[0], dom[1], 6, Math.max(width, 12) - 6)
  const ticks = niceTicks(dom[0], dom[1], width < 420 ? 4 : 6).filter((v) => v >= dom[0] && v <= dom[1])
  return (
    <div className={wide ? 'forest is-wide' : 'forest'}>
      <div className="fr-axis" aria-hidden="true">
        <div className="fr-axislabel">{axisLabel}</div>
        <div className="fr-axis-plot" ref={plotRef}>
          {width > 0 ? (
            <svg width={width} height={34} viewBox={`0 0 ${width} 34`}>
              <text x={x(refValue)} y={10} textAnchor="middle" className="ax-ref">{refLabel}</text>
              {ticks.map((v) => (
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
              <small>
                {t('ov.forest.shown', { a: g.rows.length, b: g.total })}
                {g.noCi ? ` · ${t('ov.forest.noCi', { n: fmtInt(g.noCi) })}` : ''}
              </small>
            </h3>
            {g.rule ? <p className="fr-grule">{g.rule}</p> : null}
          </div>
          {g.note}
          <ul className="fr-list">
            {g.rows.map((tp) => {
              const ci = hasCi(tp)
              return (
                <li key={tp.id}>
                  <Link
                    className="fr-row"
                    to={`/topics/${tp.id}`}
                    aria-label={[name(tp), subtitle(tp), `${fmtSignedPct(tp.metrics.share_growth)}${tp.metrics.no_baseline ? ` (${t('noBaseline', { base })})` : ''}`, ci ? t('ciRange', { level, lo: fmtSignedPct(tp.metrics.share_growth_lo), hi: fmtSignedPct(tp.metrics.share_growth_hi) }) : t('noCi')].join(', ')}
                  >
                    <span className="fr-name">
                      <b><TopicName topic={tp} /></b>
                      {tp.metrics.no_baseline ? <span className="fr-new">{t('noBaseline', { base: base.replace(/\u2013/g, '\u2013\u2060') /* keep the year range on one line */ })}</span> : null}
                      <span>{subtitle(tp)}</span>
                    </span>
                    <span className="fr-plot">
                      {ci ? (
                        <CiWhisker status={tp.status} value={tp.metrics.share_growth} lo={tp.metrics.share_growth_lo} hi={tp.metrics.share_growth_hi} domain={dom} refValue={refValue} width={width} height={wide ? 30 : 26} r={wide ? 5 : 4} />
                      ) : (
                        <span className="fr-noci">{t('noCi')}</span>
                      )}
                    </span>
                    <span className="fr-val">
                      <b>{fmtSignedPct(tp.metrics.share_growth)}</b>
                      {ci ? <span>{fmtSignedPct(tp.metrics.share_growth_lo)} {t('to')} {fmtSignedPct(tp.metrics.share_growth_hi)}</span> : null}
                    </span>
                  </Link>
                </li>
              )
            })}
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
