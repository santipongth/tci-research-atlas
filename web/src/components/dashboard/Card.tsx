import { useId, type ReactNode } from 'react'
import { Link } from 'react-router'
import { useI18n } from '../../lib/i18n'
import { InfoPop } from '../Term'
import { Icon } from './Icon'

export type Span = 3 | 4 | 5 | 6 | 7 | 8 | 12

/** "ดูทั้งหมด": a link to the page with everything, or a button that opens the full list in a drawer. */
export function SeeAll({ to, onClick, label, describedBy }: { to?: string; onClick?: () => void; label: string; describedBy?: string }) {
  const inner = (
    <>
      {label}
      <Icon name="arrow" size={16} />
    </>
  )
  if (to) return <Link className="see-all" to={to} aria-describedby={describedBy}>{inner}</Link>
  return (
    <button type="button" className="see-all" onClick={onClick} aria-describedby={describedBy}>
      {inner}
    </button>
  )
}

/**
 * A white dashboard card on the canvas: a title row (h2, an (i) button holding what the card counts and how, an action
 * such as "ดูทั้งหมด") and its content. No explanation sits on the card itself. `span` is the card's share of the
 * 12-column grid on wide screens; phones stack every card.
 */
export function Card({ title, info, action, span = 4, children, className, titleId }: {
  title: string
  /** what the card counts, its years, how to read it: opens from the (i) beside the title (click/tap, never hover-only) */
  info?: ReactNode
  action?: ReactNode
  span?: Span
  children: ReactNode
  className?: string
  titleId?: string
}) {
  const { t } = useI18n()
  const own = useId()
  const id = titleId ?? own
  return (
    <section className={`card span-${span}${className ? ` ${className}` : ''}`} aria-labelledby={id}>
      <div className="card-head">
        <div className="card-titles">
          <h2 className="card-title" id={id}>{title}</h2>
          {info ? (
            <InfoPop
              className="card-info"
              label={
                <>
                  <Icon name="info" size={16} />
                  <span className="sr-only">{t('dash.about', { title })}</span>
                </>
              }
            >
              {info}
            </InfoPop>
          ) : null}
        </div>
        {action ? <div className="card-tools">{action}</div> : null}
      </div>
      {children}
    </section>
  )
}

/** Cards stacked in one column of the grid (e.g. two short cards beside a tall one); the last one takes the rest. */
export function DashStack({ span, children }: { span: Span; children: ReactNode }) {
  return <div className={`dstack span-${span}`}>{children}</div>
}

/** The 12-column card grid (one column under 760 px). */
export function DashGrid({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={`dgrid${className ? ` ${className}` : ''}`}>{children}</div>
}
