import type { Topic } from '../data/types'
import type { StrKey } from '../strings'
import { DEFINITION } from './definition'
import { fmtInt, fmtPct } from './format'
import type { Vars } from './i18n'

export type BreadthReason =
  | { kind: 'journals'; n: number; min: number }
  | { kind: 'orgs'; n: number; min: number }
  | { kind: 'newShare'; share: number; max: number }

/**
 * The breadth tests (pipeline emerging.py) a topic fails, against DEFINITION: at least `minJournals` journals,
 * at least `minOrgs` institutions (skipped when institutions are unverified) and a new-journal share below the maximum.
 */
export function breadthReasons(topic: Topic): BreadthReason[] {
  const m = topic.metrics
  const out: BreadthReason[] = []
  if (m.n_journals_R < DEFINITION.minJournals) out.push({ kind: 'journals', n: m.n_journals_R, min: DEFINITION.minJournals })
  if (!m.orgs_unverified && m.n_orgs_R < DEFINITION.minOrgs) out.push({ kind: 'orgs', n: m.n_orgs_R, min: DEFINITION.minOrgs })
  if (m.new_journal_share >= DEFINITION.maxNewJournalShare) out.push({ kind: 'newShare', share: m.new_journal_share, max: DEFINITION.maxNewJournalShare })
  return out
}

type T = (key: StrKey, vars?: Vars) => string

/** One sentence fragment per failed test, joined with " · "; a generic line when none can be shown. */
export function breadthText(t: T, topic: Topic): string {
  const parts = breadthReasons(topic).map((r) => {
    if (r.kind === 'journals') return t('breadth.journals', { n: fmtInt(r.n), min: r.min })
    if (r.kind === 'orgs') return t('breadth.orgs', { n: fmtInt(r.n), min: r.min })
    return t('breadth.newShare', { p: fmtPct(r.share, 0), max: fmtPct(r.max, 0) })
  })
  return parts.length ? parts.join(' · ') : t('breadth.generic')
}
