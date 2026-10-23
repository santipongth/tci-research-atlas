import { Link } from 'react-router'
import { useReleaseFile } from '../../data/atlasContext'
import { hasModule, MODULE_FILES, type AtlasRelease } from '../../data/release'
import type { SdgFile } from '../../data/types'
import { useI18n, useStrings } from '../../lib/i18n'
import { topicExtra } from '../../strings/topicExtra'

/* The topic page's SDG chips, loaded on demand: they read the goal names from sdg.json. */

/** "Related goals: SDG 3 Good health …" — one link per goal to /goals; names from sdg.json when the release has it. */
export function TopicSdg({ release, goals }: { release: AtlasRelease; goals: readonly number[] }) {
  const s = useStrings(topicExtra)
  const { name } = useI18n()
  const sdg = useReleaseFile<SdgFile>(hasModule(release, 'sdg') ? MODULE_FILES.sdg : null)
  const goalName = (n: number) => {
    const g = sdg.status === 'ready' ? sdg.data.goals.find((x) => x.framework === 'sdg' && x.number === n) : undefined
    return g ? name(g) : ''
  }
  const sorted = [...new Set(goals)].sort((a, b) => a - b)
  return (
    <p className="tp-sdg">
      <span className="tp-sdg-label">{s('sdg.label')}</span>
      {sorted.map((n) => {
        const nm = goalName(n)
        return (
          <Link key={n} to="/goals" className="tp-sdg-chip" aria-label={nm ? s('sdg.link', { n, name: nm }) : undefined}>
            <strong>{s('sdg.chip', { n })}</strong>
            {nm ? <span>{nm}</span> : null}
          </Link>
        )
      })}
    </p>
  )
}


