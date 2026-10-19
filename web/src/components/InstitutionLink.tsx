import { Link } from 'react-router'
import type { InstitutionSummary } from '../data/types'
import { instName } from '../lib/executive'
import { useI18n } from '../lib/i18n'

/** An institution's name linking to /institutions/:id (the other language's name carries its lang attribute). */
export function InstitutionLink({ inst }: { inst: Pick<InstitutionSummary, 'id' | 'name_th' | 'name_en'> }) {
  const { lang } = useI18n()
  const n = instName(inst, lang)
  return (
    <Link to={`/institutions/${inst.id}`} className="topic-link">
      <span lang={n.lang ?? undefined}>{n.text}</span>
    </Link>
  )
}
