import type { Column } from '../components/DataTable'

/** Mark the main columns of a table (shown by default; the rest behind "แสดงทุกคอลัมน์"). */
export function withPrimary<R>(columns: readonly Column<R>[], keys: readonly string[]): Column<R>[] {
  return columns.map((c) => (keys.includes(c.key) ? { ...c, primary: true } : c))
}
