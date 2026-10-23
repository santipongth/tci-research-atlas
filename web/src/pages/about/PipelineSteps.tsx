import { Steps } from '../../components/Steps'
import type { AtlasRelease } from '../../data/release'
import { fmtWindow, windows } from '../../lib/definition'
import { fmtInt } from '../../lib/format'
import { useI18n, useStrings } from '../../lib/i18n'
import { glyphPath, SIGNAL_STATUSES } from '../../lib/status'
import { openViz } from '../../strings/openViz'

function ArticlesArt() {
  return (
    <svg width="56" height="40" viewBox="0 0 56 40" focusable="false">
      {[0, 1, 2].map((i) => <rect key={i} x={6 + i * 7} y={10 - i * 4} width="24" height="28" className="pa-sheet" />)}
      {[14, 20, 26].map((y) => <line key={y} x1="24" x2="40" y1={y} y2={y} className="pa-line" />)}
    </svg>
  )
}

function GroupArt() {
  const a = [[12, 14], [18, 9], [20, 19], [11, 23]]
  const b = [[38, 16], [44, 24], [36, 27], [46, 13]]
  return (
    <svg width="56" height="40" viewBox="0 0 56 40" focusable="false">
      <circle cx="16" cy="17" r="12" className="pa-ring" />
      <circle cx="41" cy="20" r="12" className="pa-ring" />
      {[...a, ...b].map(([x, y]) => <circle key={`${x}-${y}`} cx={x} cy={y} r="2.6" className="pa-dot" />)}
    </svg>
  )
}

function GrowthArt() {
  return (
    <svg width="56" height="40" viewBox="0 0 56 40" focusable="false">
      <line x1="4" x2="52" y1="34" y2="34" className="pa-base" />
      <path d="M6 30 L16 28 L26 25 L36 18 L48 8" className="pa-trend" />
      <circle cx="48" cy="8" r="3" className="pa-end" />
    </svg>
  )
}

function StatusArt() {
  return (
    <svg width="96" height="40" viewBox="0 0 96 40" focusable="false">
      {SIGNAL_STATUSES.map((st, i) => <path key={st} className={`mk mk-${st}`} transform={`translate(${12 + i * 24},20)`} d={glyphPath(st, 7)} />)}
    </svg>
  )
}

/** /about's lead: articles → topics → growth → status, four steps with small drawings. Loaded on demand. */
export default function PipelineSteps({ release }: { release: AtlasRelease | null }) {
  const s = useStrings(openViz)
  const { t } = useI18n()
  const w = release ? windows(release.overview.last_complete_year) : null
  const R = w ? fmtWindow(w.R) : t('about.generic.R')
  const B = w ? fmtWindow(w.B) : t('about.generic.B')
  return (
    <div className="ab-flow">
      <Steps
        label={s('ab.flow.label')}
        items={[
          { title: s('ab.1t'), body: release ? s('ab.1b', { n: fmtInt(release.overview.kpis.articles) }) : s('ab.1bGeneric'), art: <ArticlesArt /> },
          { title: s('ab.2t'), body: s('ab.2b'), art: <GroupArt /> },
          { title: s('ab.3t'), body: s('ab.3b', { R, B }), art: <GrowthArt /> },
          { title: s('ab.4t'), body: s('ab.4b'), art: <StatusArt /> },
        ]}
      />
    </div>
  )
}
