import type { AtlasRelease } from '../data/release'
import type { StrKey } from '../strings'
import { fmtWindow, windows } from './definition'
import { ciPct } from './format'
import type { Vars } from './i18n'

/** Terms the `Term` popover can explain: `g.<term>.term` (strings/glossary.ts) and `g.<term>.def` (strings/glossaryDefs.ts). */
export const GLOSSARY = ['ci', 'baseline', 'recent', 'shareGrowth', 'score', 'hhi', 'jaccard', 'jsd', 'cosine', 'activity', 'metadata', 'embedding'] as const
export type GlossaryTerm = (typeof GLOSSARY)[number]

export const termKey = (term: GlossaryTerm): StrKey => `g.${term}.term` as StrKey
export const defKey = (term: GlossaryTerm) => `g.${term}.def` as const

/** The figures a definition quotes, from the release: interval level and the baseline / recent windows. */
export function glossaryVars(release: AtlasRelease | null): Vars {
  if (!release) return { level: 90, b: '', r: '' }
  const w = windows(release.overview.last_complete_year)
  return { level: ciPct(release.ciLevel), b: fmtWindow(w.B), r: fmtWindow(w.R) }
}
