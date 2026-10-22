import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { DataBanner } from '../components/DataBanner'
import { useAtlas } from '../data/atlasContext'
import type { AtlasRelease } from '../data/release'
import { useI18n, useStrings } from '../lib/i18n'
import { embed } from '../strings/embed'

/**
 * The frame of an embeddable widget: no header, navigation or footer — only the widget, the sample-data label when
 * the release is synthetic and a small attribution line whose link opens the full page in a new tab.
 * Loading and data errors are shown in place (never a white frame).
 */
export function EmbedFrame({ full, children }: { full: (release: AtlasRelease | null) => string; children: (release: AtlasRelease) => ReactNode }) {
  const state = useAtlas()
  const s = useStrings(embed)
  const { t, lang } = useI18n()
  const release = state.status === 'ready' ? state.release : null
  const path = full(release)
  const to = `${path}${path.includes('?') ? '&' : '?'}lang=${lang}`
  return (
    <div className="embed">
      {release?.sample ? (
        <p className="embed-sample">
          <strong className="phase-tag is-sample">{t('sample.tag')}</strong>
          <span>{t('sample.text')}</span>
        </p>
      ) : null}
      <main id="main" className="embed-main">
        {release ? (
          children(release)
        ) : state.status === 'loading' ? (
          <p className="loading" role="status">{t('loading')}</p>
        ) : (
          <>
            <h1 className="embed-h">{s('attr.link')}</h1>
            <DataBanner />
          </>
        )}
      </main>
      <p className="embed-attr">
        <Link to={to} target="_blank" rel="noopener noreferrer" className="embed-brand">
          {s('attr.link')}
          <span className="sr-only"> {t('newTab')}</span>
        </Link>
        {release ? <span>{s('attr.release', { release: release.overview.release })}</span> : null}
      </p>
    </div>
  )
}
