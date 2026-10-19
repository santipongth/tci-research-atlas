import type { ReactNode } from 'react'
import { useI18n } from '../lib/i18n'
import type { View } from '../lib/urlState'
import { Tabs } from './Tabs'

/** Civic figure: "แผนภูมิ n: title", legend, chart ⇄ table tabs, and the "ที่มา:" source line. */
export function Figure({ id, number, title, source, view, onView, legend, chart, table, note }: {
  id: string
  number: number
  title: string
  source: string
  view: View
  onView: (v: View) => void
  legend?: ReactNode
  chart: ReactNode
  table: ReactNode
  note?: ReactNode
}) {
  const { t } = useI18n()
  const heading = t('figure.n', { n: number, title })
  return (
    <figure className="fig" aria-labelledby={`${id}-title`}>
      <Tabs id={id} label={t('view.label')} items={[{ id: 'chart', label: t('view.chart') }, { id: 'table', label: t('view.table') }]} value={view} onChange={(v) => onView(v === 'table' ? 'table' : 'chart')}>
        <p className={view === 'chart' ? 'figtitle' : 'figtitle sr-only'} id={`${id}-title`}>{heading}</p>
        {view === 'chart' ? (
          <>
            {legend}
            <div className="chart-box">{chart}</div>
          </>
        ) : (
          table
        )}
        {note}
        <p className="source">{source}</p>
      </Tabs>
    </figure>
  )
}
