import { useMemo, useState, type ReactNode } from 'react'
import { toCsv, downloadText, type CsvColumn } from '../lib/csv'
import { useI18n } from '../lib/i18n'
import { sortBy, type SortDir } from '../lib/sort'

export interface Column<R> {
  key: string
  header: string
  cell: (row: R) => ReactNode
  sortValue?: (row: R) => number | string | null | undefined
  csv?: (row: R) => string | number | boolean | null | undefined
  numeric?: boolean
  rowHeader?: boolean
  className?: string
  /** exported to CSV only (e.g. the topic id), not shown */
  csvOnly?: boolean
}

export interface SortState {
  key: string
  dir: SortDir
}

function SortGlyph({ dir }: { dir: SortDir | null }) {
  return (
    <svg viewBox="0 0 10 12" width="10" height="12" aria-hidden="true" focusable="false">
      <path d="M5 1L9 5H1z" fill="currentColor" opacity={dir === 'asc' ? 1 : 0.35} />
      <path d="M5 11L9 7H1z" fill="currentColor" opacity={dir === 'desc' ? 1 : 0.35} />
    </svg>
  )
}

/**
 * Civic table: numbered caption, sortable headers with aria-sort, numbers right-aligned, a CSV button,
 * and (stack) label/value cards under 640 px. Sort is controlled (URL state) when `sort`/`onSort` are given.
 */
export function DataTable<R>({ caption, rows, columns, rowKey, sort, onSort, defaultSort, csvFilename, stack = true, wide = false, selectedKey = null, empty }: {
  caption: string
  rows: readonly R[]
  columns: readonly Column<R>[]
  rowKey: (row: R) => string
  sort?: SortState | null
  onSort?: (s: SortState) => void
  defaultSort?: SortState
  csvFilename?: string
  stack?: boolean
  wide?: boolean
  selectedKey?: string | null
  empty?: string
}) {
  const { t } = useI18n()
  const [own, setOwn] = useState<SortState | null>(defaultSort ?? null)
  const active = sort !== undefined ? sort : own
  const sorted = useMemo(() => {
    const col = active ? columns.find((c) => c.key === active.key) : undefined
    return active && col?.sortValue ? sortBy(rows, col.sortValue, active.dir) : [...rows]
  }, [rows, columns, active])
  const shown = columns.filter((c) => !c.csvOnly)
  const csvColumns: CsvColumn<R>[] = columns
    .filter((c) => c.csv || c.sortValue)
    .map((c) => ({ header: c.header, value: (r: R) => (c.csv ? c.csv(r) : (c.sortValue?.(r) ?? null)) }))
  const choose = (key: string) => {
    const next: SortState = { key, dir: active?.key === key && active.dir === 'desc' ? 'asc' : 'desc' }
    if (onSort) onSort(next)
    else setOwn(next)
  }
  return (
    <div className="tbl">
      {csvFilename && rows.length > 0 ? (
        <div className="tbl-tools">
          <button type="button" className="btn-secondary" onClick={() => downloadText(csvFilename, toCsv(sorted, csvColumns))}>
            {t('csv.download')}
          </button>
        </div>
      ) : null}
      <div className="tscroll">
        <table className={`t${stack ? ' stack' : ''}${wide ? ' wide' : ''}`}>
          <caption>{caption}</caption>
          <thead>
            <tr>
              {shown.map((c) => {
                const dir = active?.key === c.key ? active.dir : null
                return (
                  <th key={c.key} scope="col" className={c.numeric ? 'num' : undefined} aria-sort={c.sortValue ? (dir === 'asc' ? 'ascending' : dir === 'desc' ? 'descending' : 'none') : undefined}>
                    {c.sortValue ? (
                      <button type="button" className="sortbtn" onClick={() => choose(c.key)}>
                        <span>{c.header}</span>
                        <SortGlyph dir={dir} />
                      </button>
                    ) : (
                      c.header
                    )}
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr>
                <td colSpan={shown.length} className="empty">{empty ?? t('table.empty')}</td>
              </tr>
            ) : (
              sorted.map((r) => {
                const k = rowKey(r)
                return (
                  <tr key={k} className={k === selectedKey ? 'is-selected' : undefined}>
                    {shown.map((c) =>
                      c.rowHeader ? (
                        <th key={c.key} scope="row" className={c.className}>{c.cell(r)}</th>
                      ) : (
                        <td key={c.key} className={[c.numeric ? 'num' : '', c.className ?? ''].join(' ').trim() || undefined} data-label={c.header}>
                          {c.cell(r)}
                        </td>
                      ),
                    )}
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
