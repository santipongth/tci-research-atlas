import { useId, useState, type ReactNode } from 'react'
import { FigureContext } from '../lib/figureContext'
import { useI18n } from '../lib/i18n'
import type { FigureCsv } from '../lib/tableCsv'
import type { View } from '../lib/urlState'
import { CsvButton } from './CsvButton'
import { SourceMore } from './SourceLine'
import { TabList } from './Tabs'

/**
 * Civic figure. One caption row: "แผนภูมิ n: title" (or the table's "ตาราง n: …" in the table view) on the left;
 * the chart ⇄ table switch, a "วิธีอ่าน" disclosure and a small CSV button on the right. Then the legend and chart
 * (or the table), and the "ที่มา:" source line with its details behind a popover.
 * `toggle="buttons"` uses a pressed-button pair instead of tabs — for a figure inside another tab panel (no nested tablists).
 */
export function Figure({ id, number, title, tableTitle, source, view, onView, legend, chart, table, note, how, csv, toggle = 'tabs' }: {
  id: string
  number: number
  title: string
  /** the table's numbered caption ("ตาราง n: …"), shown in the caption row in the table view */
  tableTitle?: string
  source: ReactNode
  view: View
  onView: (v: View) => void
  legend?: ReactNode
  chart: ReactNode
  table: ReactNode
  note?: ReactNode
  /** "วิธีอ่าน": how to read the chart, in words (opens under the caption row) */
  how?: ReactNode
  csv?: FigureCsv
  toggle?: 'tabs' | 'buttons'
}) {
  const { t } = useI18n()
  const [howOpen, setHowOpen] = useState(false)
  const howId = useId()
  const heading = view === 'table' && tableTitle ? tableTitle : t('figure.n', { n: number, title })
  const views = [{ id: 'chart', label: t('view.chart') }, { id: 'table', label: t('view.table') }] as const
  const pick = (v: string) => onView(v === 'table' ? 'table' : 'chart')
  const body = (
    <FigureContext.Provider value={{ titled: Boolean(tableTitle), csv: Boolean(csv) }}>
      {view === 'chart' ? (
        <>
          {legend}
          <div className="chart-box">{chart}</div>
        </>
      ) : (
        table
      )}
      {note}
    </FigureContext.Provider>
  )
  return (
    <figure className="fig" aria-labelledby={`${id}-title`}>
      <div className="fig-head">
        <p className="figtitle" id={`${id}-title`}>{heading}</p>
        <div className="fig-tools">
          {toggle === 'tabs' ? (
            <TabList id={id} label={t('view.label')} items={views} value={view} onChange={pick} />
          ) : (
            <div className="viewsw" role="group" aria-label={t('view.label')}>
              {views.map((v) => (
                <button key={v.id} type="button" aria-pressed={view === v.id} aria-controls={`${id}-panel`} onClick={() => pick(v.id)}>
                  {v.label}
                </button>
              ))}
            </div>
          )}
          {how ? (
            <button type="button" className="fig-howbtn" aria-expanded={howOpen} aria-controls={howId} onClick={() => setHowOpen((o) => !o)}>
              {t('view.how')}
              <svg viewBox="0 0 10 6" width="10" height="6" aria-hidden="true" focusable="false">
                <path d={howOpen ? 'M1 5l4-4 4 4' : 'M1 1l4 4 4-4'} fill="none" stroke="currentColor" strokeWidth="1.6" />
              </svg>
            </button>
          ) : null}
          {csv ? <CsvButton filename={csv.filename} text={csv.text} /> : null}
        </div>
      </div>
      {how ? (
        <div id={howId} className="fig-how" hidden={!howOpen}>
          {how}
        </div>
      ) : null}
      {toggle === 'tabs' ? (
        <div className="fig-panel" role="tabpanel" id={`${id}-panel`} aria-labelledby={`${id}-tab-${view}`} tabIndex={0}>
          {body}
        </div>
      ) : (
        <div className="fig-panel" id={`${id}-panel`}>
          {body}
        </div>
      )}
      <p className="source">
        {source}
        <SourceMore />
      </p>
    </figure>
  )
}
