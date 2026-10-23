import type { InstitutionSummary } from '../data/types'
import type { Lang } from './i18n'
import { otherName, shownName, type ShownName } from './names'
import { foldText } from './search'

type Named = Pick<InstitutionSummary, 'id' | 'name_th' | 'name_en'>

/** The institution's name in the UI language, else in the other language, else its id (never an empty title). */
export function instName(i: Named, lang: Lang): ShownName {
  return shownName(i.name_th, i.name_en, lang, i.id)
}

/** The name in the other language when both exist and differ. */
export function otherInstName(i: Named, lang: Lang): string {
  return otherName(i.name_th, i.name_en, lang)
}

export const INST_TYPES = ['university', 'rajabhat', 'rajamangala', 'hospital', 'government', 'research', 'company', 'other'] as const
export type InstType = (typeof INST_TYPES)[number]
export type TypeFilter = 'all' | InstType

/** Institutions whose names or id contain the query (Thai folded, tone marks ignored) and match the type. */
export function filterInstitutions(list: readonly InstitutionSummary[], query: string, type: TypeFilter): InstitutionSummary[] {
  const q = foldText(query)
  return list.filter((i) => (type === 'all' || (i.type ?? 'other') === type) && (!q || [i.name_th, i.name_en, i.id].some((v) => v && foldText(v).includes(q))))
}

/** Upper bounds of k quantile classes (ascending, without repeats) — a choropleth's classes. */
export function quantileBreaks(values: readonly number[], k = 5): number[] {
  const v = values.filter((x) => Number.isFinite(x)).slice().sort((a, b) => a - b)
  const out: number[] = []
  for (let c = 1; c <= k && v.length; c++) {
    const b = v[Math.min(v.length - 1, Math.ceil((c * v.length) / k) - 1)]
    if (!out.length || b > out[out.length - 1]) out.push(b)
  }
  return out
}

/** Class of a value (0 = lowest); -1 = no data. */
export function bucketOf(value: number | null | undefined, breaks: readonly number[]): number {
  if (value === null || value === undefined || !Number.isFinite(value) || breaks.length === 0) return -1
  const i = breaks.findIndex((b) => value <= b)
  return i < 0 ? breaks.length - 1 : i
}
