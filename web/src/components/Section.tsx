import type { ReactNode } from 'react'
import { InfoPop } from './Term'
import { Icon } from './dashboard/Icon'
import type { Span } from './dashboard/Card'
import { useI18n } from '../lib/i18n'

/**
 * A page section as a dashboard card with an id (a scroll target) and an h2; its intro moves behind the (i) beside the
 * title. Inside a `DashGrid` give it a `span`; outside one it runs the width of the page. Render it only when its data
 * exists (self-hiding).
 */
export function Section({ id, title, intro, span, action, children }: {
  id: string
  title: string
  intro?: ReactNode
  span?: Span
  action?: ReactNode
  children: ReactNode
}) {
  const { t } = useI18n()
  return (
    <section className={`sec card${span ? ` span-${span}` : ''}`} id={id} aria-labelledby={`${id}-h`}>
      <div className="card-head">
        <div className="card-titles">
          <h2 className="card-title" id={`${id}-h`} tabIndex={-1}>{title}</h2>
          {intro ? (
            <InfoPop
              className="card-info"
              label={
                <>
                  <Icon name="info" size={16} />
                  <span className="sr-only">{t('dash.about', { title })}</span>
                </>
              }
            >
              {intro}
            </InfoPop>
          ) : null}
        </div>
        {action ? <div className="card-tools">{action}</div> : null}
      </div>
      {children}
    </section>
  )
}
