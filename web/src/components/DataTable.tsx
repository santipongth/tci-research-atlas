import { useId, useMemo, useState, type ReactNode } from 'react'
import { toCsv, type CsvColumn } from '../lib/csv'
import { useFigureFrame } from '../lib/figureContext'
import { tableCsvColumns } from '../lib/tableCsv'
import { useI18n } from '../lib/i18n'
import { nextSort, sortBy, type SortDir } from '../lib/sort'
import { CsvButton } from './CsvButton'

export interface Column<R> {
  key: string
  header: string
  /** the unit, printed after the header ("สัดส่วน (%)") and in the phone card label */
  unit?: string
  /**
   * a main column: when any column of a table is primary, only the primary ones (and the row header) show by default,
   * with a "แสดงทุกคอลัมน์" toggle; on phones the other fields open per row. CSV always has every column.
   */
  primary?: boolean
  cell: (row: R) => ReactNode
  sortValue?: (row: R) => number | string | null | undefined
  /** language-independent CSV header (contract field name); defaults to `key`, never to the on-screen header */
  csvHeader?: string
  /** replaces the single CSV column with several (e.g. name_th + name_en) */
  csvCols?: CsvColumn<R>[]
  csv?: (row: R) => string | number | boolean | null | undefined
  numeric?: boolean
  rowHeader?: boolean
  className?: string
  /** direction of the first click; default: numeric columns descending, text columns ascending */
  firstDir?: SortDir
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

const headText = <R,>(c: Column<R>) => (c.unit ? `${c.header} (${c.unit})` : c.header)

/**
 * Civic table: numbered caption, sortable headers with aria-sort, numbers right-aligned, a CSV button,
 * and (stack) label/value cards under 640 px. Sort is controlled (URL state) when `sort`/`onSort` are given.
 * Inside a `Figure` the caption row carries the numbered title and the CSV button, so the table leaves them out.
 */
export function DataTable<R>({ caption, rows, columns, rowKey, sort, onSort, defaultSort, csvFilename, stack = true, wide = false, selectedKey = null, empty, footnote, limit }: {
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
  /** a note under the table (e.g. what † means) */
  footnote?: string
  /** show only the first `limit` rows (in the current order) with a "แสดงทั้งหมด" button; the CSV always has every row */
  limit?: number
}) {
  const { t } = useI18n()
  const frame = useFigureFrame()
  const tableId = useId()
  const [own, setOwn] = useState<SortState | null>(defaultSort ?? null)
  const [all, setAll] = useState(false)
  const [allRows, setAllRows] = useState(false)
  const [openRows, setOpenRows] = useState<ReadonlySet<string>>(() => new Set())
  const active = sort !== undefined ? sort : own
  const sorted = useMemo(() => {
    const col = active ? columns.find((c) => c.key === active.key) : undefined
    return active && col?.sortValue ? sortBy(rows, col.sortValue, active.dir) : [...rows]
  }, [rows, columns, active])
  const shown = columns.filter((c) => !c.csvOnly)
  // the column the table is sorted by always shows, so a shared link sorted by a secondary column still makes sense
  const isExtra = (c: Column<R>) => !c.primary && !c.rowHeader && c.key !== active?.key
  const nExtra = shown.some((c) => c.primary) ? shown.filter(isExtra).length : 0
  const collapsed = nExtra > 0 && !all
  const rowToggle = collapsed && stack
  const csvColumns = tableCsvColumns(columns)
  const choose = (key: string) => {
    const col = columns.find((c) => c.key === key)
    const next = nextSort(active, key, col?.firstDir ?? (col?.numeric ? 'desc' : 'asc'))
    if (onSort) onSort(next)
    else setOwn(next)
  }
  const flip = (k: string) =>
    setOpenRows((s) => {
      const n = new Set(s)
      if (n.has(k)) n.delete(k)
      else n.add(k)
      return n
    })
  const cellClass = (c: Column<R>, base?: string) => [base ?? '', c.numeric ? 'num' : '', c.className ?? '', nExtra && isExtra(c) ? 'col-extra' : ''].join(' ').trim() || undefined
  const showCsv = Boolean(csvFilename) && rows.length > 0 && !frame.csv
  const cut = limit !== undefined && limit > 0 && sorted.length > limit
  const visible = cut && !allRows ? sorted.slice(0, limit) : sorted
  return (
    <div className="tbl">
      {showCsv || nExtra ? (
        <div className="tbl-tools">
          {nExtra ? (
            <button type="button" className="linkbtn tbl-cols" aria-expanded={all} aria-controls={tableId} onClick={() => setAll((a) => !a)}>
              {all ? t('table.fewCols') : t('table.allCols', { n: shown.length })}
            </button>
          ) : null}
          {showCsv && csvFilename ? <CsvButton filename={csvFilename} text={() => toCsv(sorted, csvColumns)} /> : null}
        </div>
      ) : null}
      <div className="tscroll">
        <table id={tableId} className={`t${stack ? ' stack' : ''}${wide && !collapsed ? ' wide' : ''}${collapsed ? ' is-collapsed' : ''}`}>
          <caption className={frame.titled ? 'sr-only' : undefined}>{caption}</caption>
          <thead>
            <tr>
              {shown.map((c) => {
                const dir = active?.key === c.key ? active.dir : null
                const label = (
                  <>
                    <span>{c.header}</span>
                    {c.unit ? <span className="th-unit"> ({c.unit})</span> : null}
                  </>
                )
                return (
                  <th key={c.key} scope="col" className={cellClass(c)} aria-sort={c.sortValue ? (dir === 'asc' ? 'ascending' : dir === 'desc' ? 'descending' : 'none') : undefined}>
                    {c.sortValue ? (
                      <button type="button" className="sortbtn" onClick={() => choose(c.key)}>
                        <span className="sortbtn-text">{label}</span>
                        <SortGlyph dir={dir} />
                      </button>
                    ) : (
                      label
                    )}
                  </th>
                )
              })}
              {rowToggle ? <td className="row-more" aria-hidden="true" /> : null}
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr>
                <td colSpan={shown.length + (rowToggle ? 1 : 0)} className="empty">{empty ?? t('table.empty')}</td>
              </tr>
            ) : (
              visible.map((r) => {
                const k = rowKey(r)
                const open = openRows.has(k)
                return (
                  <tr key={k} className={[k === selectedKey ? 'is-selected' : '', rowToggle && open ? 'is-open' : ''].join(' ').trim() || undefined} aria-current={k === selectedKey ? 'true' : undefined}>
                    {shown.map((c) =>
                      c.rowHeader ? (
                        <th key={c.key} scope="row" className={c.className}>{c.cell(r)}</th>
                      ) : (
                        <td key={c.key} className={cellClass(c)} data-label={headText(c)}>
                          {c.cell(r)}
                        </td>
                      ),
                    )}
                    {rowToggle ? (
                      <td className="row-more">
                        <button type="button" className="linkbtn" aria-expanded={open} onClick={() => flip(k)}>
                          {open ? t('table.rowLess') : t('table.rowMore')}
                        </button>
                      </td>
                    ) : null}
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
      {cut ? (
        <p className="tbl-rows">
          <button type="button" className="btn-secondary" aria-expanded={allRows} aria-controls={tableId} onClick={() => setAllRows((a) => !a)}>
            {allRows ? t('table.firstRows', { n: limit }) : t('table.allRows', { n: sorted.length })}
          </button>
        </p>
      ) : null}
      {footnote ? <p className="note tbl-foot">{footnote}</p> : null}
    </div>
  )
}
