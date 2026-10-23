import type { ReactNode } from 'react'
import type { FigureCsv } from '../lib/tableCsv'
import type { View } from '../lib/urlState'

/**
 * A chart with its plain title, legend and note — nothing else (owner 2026-10-24: no chart ⇄ table tabs, no
 * "วิธีอ่าน", no CSV, no source line on the page). Charts print their numbers as labels and lists, and the full
 * figures live on the detail pages. The older props (table, how, csv, source, view …) are accepted and not shown.
 */
export function Figure({ id, title, legend, chart, note }: {
  id: string
  number?: number
  title: string
  tableTitle?: string
  source?: ReactNode
  view?: View
  onView?: (v: View) => void
  legend?: ReactNode
  chart: ReactNode
  table?: ReactNode
  note?: ReactNode
  how?: ReactNode
  csv?: FigureCsv
  toggle?: 'tabs' | 'buttons'
}) {
  return (
    <figure className="fig" aria-labelledby={`${id}-title`}>
      <p className="figtitle" id={`${id}-title`}>{title}</p>
      {legend}
      <div className="chart-box">{chart}</div>
      {note}
    </figure>
  )
}
