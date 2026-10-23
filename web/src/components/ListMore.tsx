import { fmtInt } from '../lib/format'
import { useI18n } from '../lib/i18n'

/** The "show all (n)" switch under a list that is cut to its first `limit` items (the table view and CSV keep every row). */
export function ListMore({ total, limit, expanded, onToggle }: { total: number; limit: number; expanded: boolean; onToggle: () => void }) {
  const { t } = useI18n()
  if (total <= limit) return null
  return (
    <p className="tbl-rows">
      <button type="button" className="btn-secondary" aria-expanded={expanded} onClick={onToggle}>
        {expanded ? t('list.fewer', { n: limit }) : t('list.all', { n: fmtInt(total) })}
      </button>
    </p>
  )
}
