import { useAtlas } from '../data/atlasContext'
import type { DataErrorKind } from '../data/source'
import { useI18n } from '../lib/i18n'
import type { StrKey } from '../strings'

const TITLE: Record<DataErrorKind, StrKey> = { missing: 'error.missing.title', network: 'error.network.title', parse: 'error.parse.title', schema: 'error.schema.title' }
const BODY: Record<Exclude<DataErrorKind, 'schema'>, StrKey> = { missing: 'error.missing.body', network: 'error.network.body', parse: 'error.parse.body' }

/** "No white page": every data failure becomes a banner that says why and what to do. */
export function DataBanner() {
  const state = useAtlas()
  const { t } = useI18n()
  if (state.status !== 'error') return null
  const { kind, detail } = state.error
  return (
    <div className="container">
      <div className="banner" role="alert">
        <h2>{t(TITLE[kind])}</h2>
        <p>{kind === 'schema' ? t('error.schema.body', { found: detail }) : t(BODY[kind])}</p>
        {kind === 'schema' ? null : <p className="detail">{t('error.detail', { detail })}</p>}
        <p className="mt-2">
          <button type="button" className="linkbtn" onClick={() => window.location.reload()}>
            {t('reload')}
          </button>
        </p>
      </div>
    </div>
  )
}
