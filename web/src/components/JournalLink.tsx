import { Link } from 'react-router'
import type { JournalSummary } from '../data/types'
import { useI18n, useStrings } from '../lib/i18n'
import { journalName } from '../lib/journals'
import { journals } from '../strings/journals'

/** A journal's name linking to /journals/:id, with its OJS name (or "no full name yet") underneath. */
export function JournalLink({ journal }: { journal: Pick<JournalSummary, 'id' | 'name_th' | 'name_en' | 'path'> }) {
  const { lang } = useI18n()
  const sj = useStrings(journals)
  const n = journalName(journal, lang)
  return (
    <>
      <Link to={`/journals/${journal.id}`} className="topic-link">
        <span lang={n.lang ?? undefined}>{n.text}</span>
      </Link>
      <span className="j-path">{n.fallback ? sj('jr.noName') : sj('jr.ojs', { path: journal.path })}</span>
    </>
  )
}
