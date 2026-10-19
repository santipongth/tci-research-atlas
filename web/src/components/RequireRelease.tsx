import type { ReactNode } from 'react'
import { useAtlas } from '../data/atlasContext'
import type { AtlasRelease } from '../data/release'
import { useI18n } from '../lib/i18n'
import { PageHeader } from './PageHeader'

/**
 * Renders `children(release)` once data is ready; otherwise the page h1 plus "loading" or a pointer to the banner.
 * Put hooks in a component rendered by the children function, never in the function itself.
 */
export function RequireRelease({ title, children }: { title: string; children: (release: AtlasRelease) => ReactNode }) {
  const state = useAtlas()
  const { t } = useI18n()
  if (state.status === 'ready') return <>{children(state.release)}</>
  return (
    <div className="container">
      <PageHeader title={title} />
      {state.status === 'loading' ? (
        <p className="loading" role="status">{t('loading')}</p>
      ) : (
        <p className="loading">{t('noData.body')}</p>
      )}
    </div>
  )
}
