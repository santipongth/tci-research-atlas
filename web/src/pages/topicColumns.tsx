import { Link } from 'react-router'
import { CiWhisker } from '../components/CiWhisker'
import type { Column } from '../components/DataTable'
import { StatusChip } from '../components/StatusGlyph'
import type { Topic } from '../data/types'
import { DEFINITION } from '../lib/definition'
import { DASH, fmtInt, fmtNum, fmtPct, fmtSignedPct } from '../lib/format'
import type { I18n } from '../lib/i18n'
import { lowDataText, ratioText, statusName } from '../lib/topicText'

export interface ColumnContext {
  t: I18n['t']
  name: I18n['name']
  groupName: (groupId: string) => string
}

/** Share-growth axis of every CI whisker (fractions); values outside are drawn as arrows. */
export const FOREST_DOMAIN: readonly [number, number] = [-0.3, 1.0]

export function idColumn(): Column<Topic> {
  return { key: 'id', header: 'id', cell: () => null, csv: (r) => r.id, csvOnly: true }
}

export function topicColumn(ctx: ColumnContext, sub?: (r: Topic) => string): Column<Topic> {
  return {
    key: 'name',
    header: ctx.t('col.topic'),
    rowHeader: true,
    cell: (r) => (
      <>
        <Link to={`/topics/${r.id}`} className="topic-link">{ctx.name(r)}</Link>
        <span className="topic-sub">{sub ? sub(r) : ctx.groupName(r.group)}</span>
      </>
    ),
    sortValue: (r) => ctx.name(r),
  }
}

export function statusColumn(ctx: ColumnContext): Column<Topic> {
  return { key: 'status', header: ctx.t('col.status'), cell: (r) => <StatusChip status={r.status} label={statusName(ctx.t, r.status)} small />, csv: (r) => r.status }
}

export function shareColumn(ctx: ColumnContext): Column<Topic> {
  return { key: 'share', header: ctx.t('col.share'), numeric: true, cell: (r) => fmtPct(r.metrics.share_recent, 2), sortValue: (r) => r.metrics.share_recent }
}

export function growthColumn(ctx: ColumnContext): Column<Topic> {
  return { key: 'growth', header: ctx.t('col.growth'), numeric: true, cell: (r) => fmtSignedPct(r.metrics.share_growth), sortValue: (r) => r.metrics.share_growth }
}

export function ciColumn(ctx: ColumnContext, levelPct: number): Column<Topic> {
  return {
    key: 'lo',
    header: `${ctx.t('col.ci')} ${levelPct}%`,
    className: 'ci',
    firstDir: 'desc',
    cell: (r) =>
      r.metrics.share_growth_lo === null || r.metrics.share_growth_lo === undefined ? (
        DASH
      ) : (
        <div className="ci-cell">
          <CiWhisker status={r.status} value={r.metrics.share_growth} lo={r.metrics.share_growth_lo} hi={r.metrics.share_growth_hi} domain={FOREST_DOMAIN} refValue={DEFINITION.emergingMinGrowthLo} width={150} />
          <span>{fmtSignedPct(r.metrics.share_growth_lo)} {ctx.t('to')} {fmtSignedPct(r.metrics.share_growth_hi)}</span>
        </div>
      ),
    sortValue: (r) => r.metrics.share_growth_lo,
  }
}

export function ciHighColumn(): Column<Topic> {
  return { key: 'hi', header: 'share_growth_hi', cell: () => null, csv: (r) => r.metrics.share_growth_hi, csvOnly: true }
}

export function ratioColumn(ctx: ColumnContext): Column<Topic> {
  return {
    key: 'ratio',
    header: ctx.t('col.ratio'),
    numeric: true,
    cell: (r) => ratioText(ctx.t, r.metrics),
    sortValue: (r) => (r.metrics.no_baseline ? 1e9 : r.metrics.share_ratio),
    csv: (r) => r.metrics.share_ratio,
  }
}

export function journalsColumn(ctx: ColumnContext): Column<Topic> {
  return { key: 'journals', header: ctx.t('col.journals'), numeric: true, cell: (r) => fmtInt(r.metrics.n_journals_R), sortValue: (r) => r.metrics.n_journals_R }
}

export function orgsColumn(ctx: ColumnContext): Column<Topic> {
  return {
    key: 'orgs',
    header: ctx.t('col.orgs'),
    numeric: true,
    cell: (r) => (
      <>
        {fmtInt(r.metrics.n_orgs_R)}
        {r.metrics.orgs_unverified ? (
          <span className="flag" aria-hidden="true"> †</span>
        ) : null}
        {r.metrics.orgs_unverified ? <span className="sr-only"> ({ctx.t('orgsUnverified')})</span> : null}
      </>
    ),
    sortValue: (r) => r.metrics.n_orgs_R,
    csv: (r) => r.metrics.n_orgs_R,
  }
}

export function scoreColumn(ctx: ColumnContext): Column<Topic> {
  return { key: 'score', header: ctx.t('col.score'), numeric: true, cell: (r) => fmtNum(r.score, 0), sortValue: (r) => r.score }
}

export function articlesColumn(ctx: ColumnContext): Column<Topic> {
  return { key: 'articles', header: ctx.t('col.articlesR'), numeric: true, cell: (r) => fmtInt(r.metrics.count_recent), sortValue: (r) => r.metrics.count_recent }
}

export function reasonColumn(ctx: ColumnContext): Column<Topic> {
  return { key: 'reason', header: ctx.t('col.reason'), cell: (r) => lowDataText(ctx.t, r.metrics) ?? DASH, csv: (r) => r.metrics.low_data_reason ?? '' }
}
