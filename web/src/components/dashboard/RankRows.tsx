import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { fmtInt } from '../../lib/format'
import { useI18n } from '../../lib/i18n'
import { Sparkline } from '../StatTile'

export interface RankRow {
  key: string
  /** the row's own page */
  to?: string | null
  name: string
  nameLang?: string
  /** a status chip, a field name … under the name */
  meta?: ReactNode
  /** the row's number, right-aligned */
  value?: ReactNode
  /** articles a year: a small trend line at the end of the row (decorative; the number carries the fact) */
  trend?: readonly (number | null)[]
}

/**
 * The dashboard's ranked list: a rank badge (the first in TCI blue), the name linking to its page (one line, the full
 * name in its title), a meta line, the number and an optional trend line. `start` numbers a later page of the list.
 */
export function RankRows({ rows, label, numbered = true, start = 0 }: { rows: readonly RankRow[]; label: string; numbered?: boolean; start?: number }) {
  return (
    <ol className={`rise${numbered ? '' : ' is-plain'}`} aria-label={label} start={start + 1}>
      {rows.map((r, i) => (
        <li key={r.key}>
          {numbered ? <span className="rise-n" aria-hidden="true">{start + i + 1}</span> : null}
          <span className="rise-main">
            {r.to ? (
              <Link className="rise-name" to={r.to} title={r.name} lang={r.nameLang}>{r.name}</Link>
            ) : (
              <span className="rise-name" title={r.name} lang={r.nameLang}>{r.name}</span>
            )}
            {r.meta ? <span className="rise-meta">{r.meta}</span> : null}
          </span>
          {r.value !== undefined || r.trend ? (
            <span className="rise-end">
              {r.value !== undefined ? <span className="rise-v">{r.value}</span> : null}
              {r.trend ? <Sparkline values={r.trend} width={56} height={24} /> : null}
            </span>
          ) : null}
        </li>
      ))}
    </ol>
  )
}

/** "แสดงเพิ่ม" under a long list: the next `step` rows each press, then "แสดงน้อยลง" once every row shows. */
export function MoreRows({ total, shown, step, onMore, onReset }: { total: number; shown: number; step: number; onMore: () => void; onReset: () => void }) {
  const { t } = useI18n()
  if (total <= step) return null
  const left = total - shown
  return (
    <p className="more-rows">
      {left > 0 ? (
        <button type="button" className="see-all" onClick={onMore}>
          {t('dash.more', { k: fmtInt(Math.min(step, left)), n: fmtInt(left) })}
        </button>
      ) : (
        <button type="button" className="see-all" onClick={onReset}>
          {t('dash.fewer')}
        </button>
      )}
    </p>
  )
}
