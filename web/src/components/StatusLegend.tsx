import type { ReactNode } from 'react'
import { useI18n } from '../lib/i18n'
import type { StatusId } from '../lib/status'
import { statusName } from '../lib/topicText'
import { StatusGlyph } from './StatusGlyph'

export function StatusLegend({ statuses, extra }: { statuses: readonly StatusId[]; extra?: ReactNode }) {
  const { t } = useI18n()
  return (
    <div className="legend">
      {statuses.map((st) => (
        <span key={st}>
          <StatusGlyph status={st} size={14} />
          {statusName(t, st)}
        </span>
      ))}
      {extra}
    </div>
  )
}
