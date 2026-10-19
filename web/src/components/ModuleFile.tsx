import type { ReactNode } from 'react'
import { useReleaseFile } from '../data/atlasContext'
import { hasModule, type AtlasRelease, type ModuleName } from '../data/release'
import { useI18n } from '../lib/i18n'
import { EmptyState } from './EmptyState'
import { PageHeader } from './PageHeader'

/**
 * A page built on one optional module file (contract 2.1). Renders `children(data)` when the file is loaded;
 * otherwise the page h1 and why there is nothing to show (module absent, left out of the offline file, failed).
 * Like RequireRelease: put hooks in a component rendered by the children function, never in the function itself.
 */
export function ModuleFile<T>({ release, module, path, title, children }: {
  release: AtlasRelease
  module: ModuleName
  path: string
  title: string
  children: (data: T) => ReactNode
}) {
  const { t } = useI18n()
  const present = hasModule(release, module)
  const file = useReleaseFile<T>(present ? path : null)
  if (present && file.status === 'ready') return <>{children(file.data)}</>
  return (
    <div className="container">
      <PageHeader title={title} />
      {!present ? (
        <EmptyState title={t('mod.absent')}><p>{t('mod.absentBody')}</p></EmptyState>
      ) : file.status === 'loading' ? (
        <p className="loading" role="status">{t('loading')}</p>
      ) : file.status === 'missing' ? (
        release.source === 'embedded' ? (
          <EmptyState title={t('mod.offline')}><p>{t('mod.offlineBody')}</p></EmptyState>
        ) : (
          <EmptyState title={t('mod.missingFile')} />
        )
      ) : (
        <p className="note">{t('mod.error')}</p>
      )}
    </div>
  )
}
