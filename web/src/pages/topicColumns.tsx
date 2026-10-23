import { TopicName } from '../components/TopicName'
import { Link } from 'react-router'
import { CiWhisker } from '../components/CiWhisker'
import type { Column } from '../components/DataTable'
import { StatusChip } from '../components/StatusGlyph'
import { groupName, type AtlasRelease } from '../data/release'
import type { Topic } from '../data/types'
import { DEFINITION, fmtWindow, windows } from '../lib/definition'
import { DASH, fmtInt, fmtNum, fmtSignedPct, fmtShare } from '../lib/format'
import type { I18n } from '../lib/i18n'
import { lowDataText, ratioText, statusName } from '../lib/topicText'

export interface ColumnContext {
  t: I18n['t']
  name: I18n['name']
  groupName: (groupId: string) => string
  /** the release's windows as printed years ("2016–2020"): baseline B and recent R */
  base: string
  recent: string
}

/** The context every topic column needs, from the release and the current language. */
export function columnContext(release: AtlasRelease, i18n: Pick<I18n, 't' | 'name' | 'lang'>): ColumnContext {
  const w = windows(release.overview.last_complete_year)
  return { t: i18n.t, name: i18n.name, groupName: (g) => groupName(release, g, i18n.lang), base: fmtWindow(w.B), recent: fmtWindow(w.R) }
}

/** Share-growth axis of every CI whisker (fractions); values outside are drawn as arrows. */
export const FOREST_DOMAIN: readonly [number, number] = [-0.3, 1.0]
/** The whisker under the interval text in a table cell (text first; the whisker only illustrates it). */
const CI_CELL_WHISKER = 128

export function idColumn(): Column<Topic> {
  return { key: 'id', header: 'id', csvHeader: 'topic_id', cell: () => null, csv: (r) => r.id, csvOnly: true }
}

export function topicColumn(ctx: ColumnContext, sub?: (r: Topic) => string): Column<Topic> {
  return {
    key: 'name',
    header: ctx.t('col.topic'),
    rowHeader: true,
    cell: (r) => (
      <>
        <Link to={`/topics/${r.id}`} className="topic-link"><TopicName topic={r} /></Link>
        <span className="topic-sub">{sub ? sub(r) : ctx.groupName(r.group)}</span>
      </>
    ),
    sortValue: (r) => ctx.name(r),
    csvCols: [
      { header: 'name_th', value: (r) => r.th },
      { header: 'name_en', value: (r) => r.en },
    ],
  }
}

export function statusColumn(ctx: ColumnContext): Column<Topic> {
  return { key: 'status', csvHeader: 'status', header: ctx.t('col.status'), cell: (r) => <StatusChip status={r.status} label={statusName(ctx.t, r.status)} small />, csv: (r) => r.status }
}

export function shareColumn(ctx: ColumnContext): Column<Topic> {
  return { key: 'share', csvHeader: 'share_recent', header: ctx.t('col.share'), unit: ctx.t('unit.pct'), numeric: true, cell: (r) => fmtShare(r.metrics.share_recent, 2), sortValue: (r) => r.metrics.share_recent }
}

export function growthColumn(ctx: ColumnContext): Column<Topic> {
  return { key: 'growth', csvHeader: 'share_growth', header: ctx.t('col.growth'), unit: ctx.t('unit.pct'), numeric: true, cell: (r) => fmtSignedPct(r.metrics.share_growth), sortValue: (r) => r.metrics.share_growth }
}

export function ciColumn(ctx: ColumnContext): Column<Topic> {
  return {
    key: 'lo',
    csvHeader: 'share_growth_lo',
    header: ctx.t('col.ci'),
    className: 'ci',
    firstDir: 'desc',
    cell: (r) =>
      r.metrics.share_growth_lo === null || r.metrics.share_growth_lo === undefined ? (
        DASH
      ) : (
        <div className="ci-cell">
          <span>{fmtSignedPct(r.metrics.share_growth_lo)} {ctx.t('to')} {fmtSignedPct(r.metrics.share_growth_hi)}</span>
          <CiWhisker status={r.status} value={r.metrics.share_growth} lo={r.metrics.share_growth_lo} hi={r.metrics.share_growth_hi} domain={FOREST_DOMAIN} refValue={DEFINITION.emergingMinGrowthLo} width={CI_CELL_WHISKER} />
        </div>
      ),
    sortValue: (r) => r.metrics.share_growth_lo,
  }
}

export function ciHighColumn(): Column<Topic> {
  return { key: 'hi', header: 'share_growth_hi', csvHeader: 'share_growth_hi', cell: () => null, csv: (r) => r.metrics.share_growth_hi, csvOnly: true }
}

export function ratioColumn(ctx: ColumnContext): Column<Topic> {
  return {
    key: 'ratio',
    header: ctx.t('col.ratio', { base: ctx.base }),
    numeric: true,
    cell: (r) => ratioText(ctx.t, r.metrics, ctx.base),
    sortValue: (r) => (r.metrics.no_baseline ? 1e9 : r.metrics.share_ratio),
    csvCols: [
      { header: 'share_ratio', value: (r) => r.metrics.share_ratio },
      { header: 'no_baseline', value: (r) => r.metrics.no_baseline ?? false },
    ],
  }
}

export function journalsColumn(ctx: ColumnContext): Column<Topic> {
  return { key: 'journals', csvHeader: 'n_journals_R', header: ctx.t('col.journals'), numeric: true, cell: (r) => fmtInt(r.metrics.n_journals_R), sortValue: (r) => r.metrics.n_journals_R }
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
    csvCols: [
      { header: 'n_orgs_R', value: (r) => r.metrics.n_orgs_R },
      { header: 'orgs_unverified', value: (r) => r.metrics.orgs_unverified ?? false },
    ],
  }
}

export function scoreColumn(ctx: ColumnContext): Column<Topic> {
  return { key: 'score', csvHeader: 'score', header: ctx.t('col.score'), unit: '0–100', numeric: true, cell: (r) => fmtNum(r.score, 0), sortValue: (r) => r.score }
}

export function articlesColumn(ctx: ColumnContext): Column<Topic> {
  return { key: 'articles', csvHeader: 'count_recent', header: ctx.t('col.articlesR', { r: ctx.recent }), numeric: true, cell: (r) => fmtInt(r.metrics.count_recent), sortValue: (r) => r.metrics.count_recent }
}

export function reasonColumn(ctx: ColumnContext): Column<Topic> {
  return { key: 'reason', csvHeader: 'low_data_reason', header: ctx.t('col.reason'), cell: (r) => lowDataText(ctx.t, r.metrics) ?? DASH, csv: (r) => r.metrics.low_data_reason ?? '' }
}
