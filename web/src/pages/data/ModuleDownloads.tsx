import { useState } from 'react'
import { useAtlas } from '../../data/atlasContext'
import { hasModule, MODULE_FILES, type AtlasRelease, type ModuleName } from '../../data/release'
import { dataUrl } from '../../data/source'
import { downloadText } from '../../lib/csv'
import { fmtNum } from '../../lib/format'
import { useI18n } from '../../lib/i18n'
import type { StrKey } from '../../strings'

const INFO: Record<ModuleName, StrKey> = {
  journals: 'data.file.journals',
  methods: 'data.file.methods',
  diff: 'data.file.diff',
  match: 'data.file.match',
  institutions: 'data.file.institutions',
  regions: 'data.file.regions',
  sdg: 'data.file.sdg',
  global: 'data.file.global',
  gaps: 'data.file.gaps',
  references: 'data.file.references',
  search: 'data.file.search',
  galaxy: 'data.file.galaxy',
  kwtrends: 'data.file.kwtrends',
}

/** Files of the optional modules (a sub-part of /data's developers section): direct links on the web; on the offline file, rebuilt from the embedded data. */
export function ModuleDownloads({ release }: { release: AtlasRelease }) {
  const { t } = useI18n()
  const atlas = useAtlas()
  const load = atlas.status === 'ready' ? atlas.file : null
  const [absent, setAbsent] = useState<ReadonlySet<string>>(new Set())
  const rel = release.overview.release
  const sizes = new Map((release.manifest.files ?? []).map((f) => [f.path, f.bytes]))
  const present = (Object.keys(MODULE_FILES) as ModuleName[]).filter((m) => hasModule(release, m))
  if (present.length === 0) return null
  return (
    <div className="dev-sub" id="modules">
      <h3 tabIndex={-1}>{t('data.mod.h')}</h3>
      <p className="intro">{t('data.mod.intro')}</p>
      <ul className="dl-list">
        {present.map((m) => {
          const path = MODULE_FILES[m]
          const name = `atlas-${rel}-${path}`
          return (
            <li key={m}>
              <div>
                <code>{path}</code>
                <span className="dl-note">{t(INFO[m])}{sizes.has(path) ? ` · ${fmtNum((sizes.get(path) ?? 0) / 1024, 0)} KB` : ''}</span>
              </div>
              {absent.has(path) ? (
                <span className="dl-note">{t('mod.offline')}</span>
              ) : release.source === 'http' ? (
                <a className="btn-secondary" href={dataUrl(import.meta.env.BASE_URL, `${rel}/${path}`)} download={name} aria-label={`${t('data.dl.json')}: ${name}`}>{t('data.dl.json')}</a>
              ) : (
                <button
                  type="button"
                  className="btn-secondary"
                  aria-label={`${t('data.dl.json')}: ${name}`}
                  onClick={() => {
                    void load?.(path).then((v) => {
                      if (v) downloadText(name, JSON.stringify(v), 'application/json')
                      else setAbsent((prev) => new Set(prev).add(path))     // e.g. match.json, left out of the offline file
                    })
                  }}
                >
                  {t('data.dl.json')}
                </button>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
