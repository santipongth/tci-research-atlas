import type { Column } from '../components/DataTable'
import type { CsvColumn } from './csv'

/**
 * The CSV columns of a table. Headers are the language-independent `csvHeader` (contract field names), falling back
 * to the column `key` — never the on-screen header, so one table gives one CSV in Thai and in English.
 * A column may expand to several CSV columns with `csvCols` (e.g. name_th + name_en).
 */
export function tableCsvColumns<R>(columns: readonly Column<R>[]): CsvColumn<R>[] {
  return columns.flatMap((c): CsvColumn<R>[] => {
    if (c.csvCols) return c.csvCols
    if (!c.csv && !c.sortValue) return []
    return [{ header: c.csvHeader ?? c.key, value: (r: R) => (c.csv ? c.csv(r) : (c.sortValue?.(r) ?? null)) }]
  })
}
