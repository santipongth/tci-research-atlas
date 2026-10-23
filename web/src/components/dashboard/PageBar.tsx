import type { ReactNode } from 'react'
import { useRelease } from '../../data/atlasContext'
import { useI18n } from '../../lib/i18n'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import { useMediaQuery, WIDE_SHELL } from '../../lib/useMediaQuery'
import { LangSwitch } from '../LangSwitch'
import { InfoPop } from '../Term'
import { Icon } from './Icon'

/**
 * The white page bar every page opens with: the h1 (an (i) beside it holds what the page is about), one short line under
 * it, the page's own actions, and the release chip with the beta / sample-data tag (its full text opens under it).
 */
export function PageBar({ title, titleLang, sub, info, actions }: {
  title: string
  titleLang?: string
  sub?: ReactNode
  /** what the page shows and how, behind the (i) beside the title (click/tap) */
  info?: ReactNode
  actions?: ReactNode
}) {
  useDocumentTitle(title)
  const { t } = useI18n()
  const release = useRelease()
  const sample = release?.sample === true
  // phones have the switch in their top bar
  const wide = useMediaQuery(WIDE_SHELL)
  return (
    <div className="pbar">
      <div className="pbar-in">
        <div className="pbar-titles">
          <div className="pbar-h">
            <h1 lang={titleLang}>{title}</h1>
            {info ? (
              <InfoPop
                className="card-info"
                label={
                  <>
                    <Icon name="info" size={18} />
                    <span className="sr-only">{t('dash.about', { title })}</span>
                  </>
                }
              >
                {info}
              </InfoPop>
            ) : null}
          </div>
          {sub ? <p className="pbar-sub">{sub}</p> : null}
        </div>
        <div className="pbar-tools">
          {actions}
          {release ? (
            <details className="pbar-notice">
              <summary>
                <span className="rel-chip">{t('dash.release', { release: release.overview.release })}</span>
                <span className={sample ? 'phase-tag is-sample' : 'phase-tag'}>{t(sample ? 'sample.tag' : 'phase.tag')}</span>
              </summary>
              <div className="pbar-pop">
                <p>{t(sample ? 'notice.shortSample' : 'notice.short')}</p>
                <p>{t('phase.text')}</p>
                {sample ? <p>{t('sample.text')}</p> : null}
              </div>
            </details>
          ) : null}
          {wide ? <LangSwitch /> : null}
        </div>
      </div>
    </div>
  )
}
