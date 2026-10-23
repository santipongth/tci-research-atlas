import { sortBy, type SortDir } from './sort'
import { useMediaQuery } from './useMediaQuery'

/** Under this width `table.t.stack` rows turn into label/value cards (components.css) — the same breakpoint. */
export const STACKED_TABLE = '(max-width: 640px)'
/** Rows a stacked (phone) table shows before "แสดงทั้งหมด": each card is ~280 px tall, so 50 rows would be a 15,000 px page. */
export const PHONE_ROW_LIMIT = 10

/** The row limit in force: `limit`, capped at PHONE_ROW_LIMIT while the rows are stacked cards. */
export function rowLimit(limit: number | undefined, stacked: boolean): number | undefined {
  if (limit === undefined || limit <= 0) return undefined
  return stacked ? Math.min(limit, PHONE_ROW_LIMIT) : limit
}

/** The row limit of a DataTable on this screen (SSR-safe: wide until the media query says otherwise; follows rotation). */
export function useRowLimit(limit: number | undefined, stack = true): number | undefined {
  const phone = useMediaQuery(STACKED_TABLE)
  return rowLimit(limit, stack && phone)
}

/**
 * Which filter-count sentence a list page shows above a limited table: "แสดง n จาก total" when every match is on
 * screen, else how many match and that the table shows the first `limit` ("ตรงเงื่อนไข … · ตารางแสดง 50 แรก").
 */
export function countLine(matches: number, total: number, limit: number | undefined): 'count' | 'countCut' | 'countAllCut' {
  if (limit === undefined || matches <= limit) return 'count'
  return matches < total ? 'countCut' : 'countAllCut'
}

interface ViewColumn<R> {
  key: string
  sortValue?: (row: R) => number | string | null | undefined
}

/**
 * What a DataTable holds: every row in the current order (`sorted`, which is also what its CSV exports) and the rows
 * on screen (`visible`, the first `limit` unless the reader asked for all).
 */
export function tableView<R>(rows: readonly R[], columns: readonly ViewColumn<R>[], active: { key: string; dir: SortDir } | null, limit: number | undefined, showAll: boolean) {
  const col = active ? columns.find((c) => c.key === active.key) : undefined
  const sorted = active && col?.sortValue ? sortBy(rows, col.sortValue, active.dir) : [...rows]
  const cut = limit !== undefined && limit > 0 && sorted.length > limit
  return { sorted, cut, visible: cut && !showAll ? sorted.slice(0, limit) : sorted }
}
