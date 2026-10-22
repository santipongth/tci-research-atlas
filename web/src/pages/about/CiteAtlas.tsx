import type { AtlasRelease } from '../../data/release'
import { CopyField } from '../../embed/EmbedTools'
import { siteUrl } from '../../embed/embedUrl'
import { atlasBibtex, atlasCitation } from '../../lib/citation'
import { useI18n, useStrings } from '../../lib/i18n'
import { embed } from '../../strings/embed'

const CFF = 'https://github.com/santipongth/tci-research-atlas/blob/main/CITATION.cff'

/** "Cite this atlas" on /about (Ruling 10): APA-like text and BibTeX @misc for the current release, with copy buttons.
 *  The author is the organisation; no person is named. Loaded on demand (the about page is in the entry chunk). */
export default function CiteAtlas({ release }: { release: AtlasRelease | null }) {
  const s = useStrings(embed)
  const { t } = useI18n()
  const url = siteUrl()
  const software = (
    <p className="hint">
      <a href={CFF} target="_blank" rel="noopener noreferrer">{s('cite.software')}<span className="sr-only"> {t('newTab')}</span></a>
    </p>
  )
  if (!release) {
    return (
      <div className="cite-atlas">
        <p>{s('cite.intro')}</p>
        <p className="note">{s('cite.noRelease')}</p>
        {software}
      </div>
    )
  }
  const rel = release.overview.release
  const year = Number(String(release.manifest.generated_at ?? '').slice(0, 4)) || new Date().getFullYear()
  const apa = atlasCitation({ org: s('cite.org'), title: s('cite.title'), version: s('cite.version', { release: rel }), kind: s('cite.kind'), year, url })
  return (
    <div className="cite-atlas">
      <p>{s('cite.intro')}</p>
      <CopyField id="cite-apa" label={s('cite.apa')} text={apa} rows={3} />
      <CopyField id="cite-bib" label={s('cite.bib')} text={atlasBibtex(rel, year, url, release.definitionVersion)} rows={9} />
      {software}
    </div>
  )
}
