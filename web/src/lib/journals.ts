import type { JournalSummary } from '../data/types'
import type { Lang } from './i18n'
import { otherName, shownName, type ShownName } from './names'
import { foldText } from './search'

type Named = Pick<JournalSummary, 'name_th' | 'name_en' | 'path'>

/** The registry name in the UI language, else the other language, else the OJS path (`fallback`: no registry name). */
export function journalName(j: Named, lang: Lang): ShownName {
  return shownName(j.name_th, j.name_en, lang, j.path)
}

/** The name in the other language when both exist and differ (shown under the title). */
export function otherJournalName(j: Named, lang: Lang): string {
  return otherName(j.name_th, j.name_en, lang)
}

/** In-house share above journals.inhouse_flag_share (published in journals.json; null = no mark). Only a registry owner
 *  may be marked: an owner inferred from the articles is never judged against the bar. */
export function inhouseFlag(j: Pick<JournalSummary, 'inhouse_share' | 'owner_source'>, threshold: number | null | undefined): boolean {
  if (j.owner_source !== undefined && j.owner_source !== 'registry') return false
  return threshold !== null && threshold !== undefined && j.inhouse_share !== null && j.inhouse_share !== undefined && j.inhouse_share > threshold
}

type Gaps = Pick<JournalSummary, 'low_data' | 'owner' | 'owner_matched' | 'inhouse_share'>

/** Why a journal's in-house share is empty: too few articles, or an owner that does not appear among the authors. */
export function inhouseGap(j: Gaps): 'low_data' | 'owner_not_found' | 'unknown' {
  if (j.low_data) return 'low_data'
  if (j.inhouse_share == null && j.owner && !(j.owner_matched ?? false)) return 'owner_not_found'
  return 'unknown'
}

export type TierFilter = 'all' | '1' | '2' | '3' | 'none'

/** Journals whose names, OJS path, key or ISSN contain the query (Thai folded, tone marks ignored) and match the tier. */
export function filterJournals(journals: readonly JournalSummary[], query: string, tier: TierFilter): JournalSummary[] {
  const q = foldText(query)
  return journals.filter((j) => {
    if (tier === 'none' ? j.tci_tier != null : tier !== 'all' && j.tci_tier !== Number(tier)) return false
    if (!q) return true
    return [j.name_th, j.name_en, j.path, j.key, j.issn, j.eissn].some((v) => v && foldText(v).includes(q))
  })
}
