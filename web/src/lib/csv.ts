export interface CsvColumn<R> {
  header: string
  value: (row: R) => string | number | boolean | null | undefined
}

/** One CSV cell: raw numbers, quoted text when needed, and text starting with = + - @ prefixed with ' (formula injection). */
export function csvCell(v: string | number | boolean | null | undefined): string {
  if (v === null || v === undefined) return ''
  if (typeof v === 'number') return Number.isFinite(v) ? String(v) : ''
  if (typeof v === 'boolean') return String(v)
  const safe = /^[=+\-@\t\r]/.test(v) ? `'${v}` : v
  return /[",\r\n]/.test(safe) ? `"${safe.replace(/"/g, '""')}"` : safe
}

/** UTF-8 BOM (so Excel shows Thai), header row, CRLF line ends. */
export function toCsv<R>(rows: readonly R[], columns: readonly CsvColumn<R>[]): string {
  const lines = [columns.map((c) => csvCell(c.header)).join(','), ...rows.map((r) => columns.map((c) => csvCell(c.value(r))).join(','))]
  return `\uFEFF${lines.join('\r\n')}\r\n`
}

/** Save text as a file — works on Pages and in the offline file:// edition (no server involved). */
export function downloadText(filename: string, text: string, mime = 'text/csv;charset=utf-8'): void {
  const url = URL.createObjectURL(new Blob([text], { type: mime }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.append(a)
  a.click()
  a.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
