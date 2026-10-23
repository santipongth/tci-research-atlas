import { describe, expect, it } from 'vitest'
import type { Column } from '../components/DataTable'
import { toCsv } from './csv'
import { countLine, PHONE_ROW_LIMIT, rowLimit, tableView } from './tableRows'
import { tableCsvColumns } from './tableCsv'

interface Row {
  id: string
  n: number
}
const rows: Row[] = Array.from({ length: 120 }, (_, i) => ({ id: `r${i}`, n: (i * 37) % 120 }))
const columns: Column<Row>[] = [
  { key: 'id', header: 'id', rowHeader: true, cell: (r) => r.id, csv: (r) => r.id },
  { key: 'n', header: 'n', numeric: true, cell: (r) => String(r.n), sortValue: (r) => r.n },
]

describe('rowLimit', () => {
  it('caps the limit while rows are stacked phone cards, and leaves wide tables and unlimited tables alone', () => {
    expect(rowLimit(50, false)).toBe(50)
    expect(rowLimit(50, true)).toBe(PHONE_ROW_LIMIT)
    expect(rowLimit(5, true)).toBe(5)
    expect(rowLimit(undefined, true)).toBeUndefined()
    expect(rowLimit(0, false)).toBeUndefined()
  })
})

describe('countLine', () => {
  it('says the table shows only the first rows when more rows match than it shows', () => {
    expect(countLine(30, 10000, 50)).toBe('count')
    expect(countLine(800, 10000, 50)).toBe('countCut')
    expect(countLine(10000, 10000, 50)).toBe('countAllCut')
    expect(countLine(10000, 10000, undefined)).toBe('count')
  })
})

describe('tableView', () => {
  it('shows the first `limit` rows in the sorted order but its CSV has every row', () => {
    const v = tableView(rows, columns, { key: 'n', dir: 'desc' }, 50, false)
    expect(v.cut).toBe(true)
    expect(v.visible).toHaveLength(50)
    expect(v.visible[0].n).toBe(119)
    const csv = toCsv(v.sorted, tableCsvColumns(columns)).trim().split(/\r?\n/)
    expect(csv).toHaveLength(rows.length + 1)
  })

  it('shows every row when asked, or when there are no more rows than the limit', () => {
    expect(tableView(rows, columns, null, 50, true).visible).toHaveLength(120)
    expect(tableView(rows.slice(0, 10), columns, null, PHONE_ROW_LIMIT, false).cut).toBe(false)
  })
})
