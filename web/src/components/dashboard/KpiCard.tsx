import type { ReactNode } from 'react'
import { useI18n } from '../../lib/i18n'
import type { StatDelta } from '../StatTile'
import { InfoPop } from '../Term'
import { Icon, type IconName } from './Icon'

/** A row of KPI cards (a description list; each card is one dt/dd pair). What the changes are compared with is said
 *  once, in the page bar. */
export function KpiRow({ children }: { children: ReactNode }) {
  return <dl className="kpi-row">{children}</dl>
}

/**
 * One key figure as a card: a drawn icon in a soft-tinted circle, the label, the value, and the change since the last
 * release (an arrow only when the printed change is not zero).
 */
export function KpiCard({ icon, label, value, delta, sub, info }: {
  icon: IconName
  label: string
  value: ReactNode
  delta?: StatDelta | null
  /** one short line under the value */
  sub?: ReactNode
  /** what the figure counts, behind an (i) beside the label */
  info?: ReactNode
}) {
  const { t } = useI18n()
  return (
    <div className="kpi">
      <span className="kpi-ico" aria-hidden="true">
        <Icon name={icon} size={22} />
      </span>
      <dt className="kpi-label">
        {label}
        {info ? (
          <InfoPop className="card-info" label={<><Icon name="info" size={14} /><span className="sr-only">{t('dash.about', { title: label })}</span></>}>
            {info}
          </InfoPop>
        ) : null}
      </dt>
      <dd className="kpi-body">
        <span className="kpi-v">{value}</span>
        {delta ? (
          <span className={delta.dir < 0 ? 'kpi-d is-down' : 'kpi-d'}>
            {delta.dir !== 0 ? (
              <svg viewBox="0 0 10 10" aria-hidden="true" focusable="false">
                <path d={delta.dir > 0 ? 'M5 1.5L9 7.5H1z' : 'M5 8.5L9 2.5H1z'} fill="currentColor" />
              </svg>
            ) : null}
            <span>{delta.text}</span>
            <span className="sr-only">{delta.ref}</span>
          </span>
        ) : sub ? (
          <span className="kpi-sub">{sub}</span>
        ) : null}
      </dd>
    </div>
  )
}
