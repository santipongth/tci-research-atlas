import type { ReactNode } from 'react'
import { useI18n } from '../lib/i18n'
import type { StatusId } from '../lib/status'
import { statusMeaning, statusName } from '../lib/topicText'
import { StatusGlyph } from './StatusGlyph'

/**
 * Status key: glyph + name for every status shown. `plain` adds the one-line meaning in everyday words
 * ("▲ กำลังเกิดใหม่ — เล็กแต่โตเร็ว"); the exact rules stay on /emerging and /about.
 */
export function StatusLegend({ statuses, extra, plain = false }: { statuses: readonly StatusId[]; extra?: ReactNode; plain?: boolean }) {
  const { t } = useI18n()
  if (plain) {
    return (
      <ul className="legend legend-plain">
        {statuses.map((st) => (
          <li key={st}>
            <b className="legend-name">
              <StatusGlyph status={st} size={14} />
              {statusName(t, st)}
            </b>{' '}
            <span>— {statusMeaning(t, st)}</span>
          </li>
        ))}
        {extra ? <li>{extra}</li> : null}
      </ul>
    )
  }
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
