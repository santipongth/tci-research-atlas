import type { TopicMetrics } from '../data/types'
import { DEFINITION } from './definition'
import { ciPct, DASH, fmtRatio, fmtSignedPct } from './format'
import type { I18n } from './i18n'
import type { StatusId } from './status'

type T = I18n['t']

export function statusName(t: T, status: StatusId): string {
  return t(`status.${status}` as const)
}

/** The status in everyday words, one line ("เล็กแต่โตเร็ว"); the rule with its thresholds is `rule.<status>`. */
export function statusMeaning(t: T, status: StatusId): string {
  return t(`stat.mean.${status}` as const)
}

export function growthText(t: T, m: TopicMetrics): string {
  return m.share_growth === null || m.share_growth === undefined ? DASH : `${fmtSignedPct(m.share_growth, 0)} ${t('perYear')}`
}

export function ciText(t: T, m: TopicMetrics, ciLevel: number): string | null {
  if (m.share_growth_lo === null || m.share_growth_lo === undefined || m.share_growth_hi === null || m.share_growth_hi === undefined) return null
  return t('ciRange', { level: ciPct(ciLevel), lo: fmtSignedPct(m.share_growth_lo), hi: fmtSignedPct(m.share_growth_hi) })
}

/** share_recent / share_baseline, or "new — none in {base}" when the baseline window (its years: `base`) had no articles. */
export function ratioText(t: T, m: TopicMetrics, base: string): string {
  if (m.no_baseline || m.share_ratio === null || m.share_ratio === undefined) return t('noBaseline', { base })
  return fmtRatio(m.share_ratio)
}

export function lowDataText(t: T, m: TopicMetrics): string | null {
  if (m.low_data_reason === 'few_articles') return t('lowData.few_articles', { n: DEFINITION.minArticlesRecent, ry: DEFINITION.recentYears })
  if (m.low_data_reason === 'not_estimable') return t('lowData.not_estimable')
  return null
}
