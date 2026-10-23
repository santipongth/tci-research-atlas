import type { AtlasRelease } from '../../data/release'
import { fmtWindow, windows } from '../../lib/definition'
import { fmtInt } from '../../lib/format'
import { useI18n, useStrings } from '../../lib/i18n'
import { glyphPath, STATUSES } from '../../lib/status'
import { openViz } from '../../strings/openViz'

function ArticlesArt() {
  return (
    <svg width="72" height="56" viewBox="0 0 72 56" focusable="false">
      {[0, 1, 2].map((i) => <rect key={i} x={10 + i * 9} y={14 - i * 5} width="30" height="38" rx="3" className="pa-sheet" />)}
      {[22, 29, 36, 43].map((y) => <line key={y} x1="34" x2="52" y1={y} y2={y} className="pa-line" />)}
    </svg>
  )
}

function GroupArt() {
  const a = [[16, 22], [24, 15], [27, 27], [14, 32], [21, 28]]
  const b = [[50, 22], [58, 31], [47, 35], [60, 18], [53, 28]]
  return (
    <svg width="72" height="56" viewBox="0 0 72 56" focusable="false">
      <circle cx="21" cy="25" r="15" className="pa-ring" />
      <circle cx="53" cy="27" r="15" className="pa-ring" />
      {[...a, ...b].map(([x, y]) => <circle key={`${x}-${y}`} cx={x} cy={y} r="3" className="pa-dot" />)}
    </svg>
  )
}

function TopicsArt() {
  return (
    <svg width="72" height="56" viewBox="0 0 72 56" focusable="false">
      {[0, 1, 2].map((i) => (
        <g key={i} transform={`translate(${8 + (i % 2) * 6},${8 + i * 14})`}>
          <rect width="50" height="10" rx="5" className="pa-tag" />
          <circle cx="7" cy="5" r="2" className="pa-tagdot" />
        </g>
      ))}
    </svg>
  )
}

function StatusArt() {
  return (
    <svg width="96" height="56" viewBox="0 0 96 56" focusable="false">
      <line x1="6" x2="90" y1="46" y2="46" className="pa-base" />
      <path d="M8 42 L28 38 L46 30 L64 22 L86 8" className="pa-trend" />
      {(['EMERGING', 'WATCH', 'HOT', 'DECLINING'] as const).map((st, i) => <path key={st} className={`mk mk-${st}`} transform={`translate(${16 + i * 22},18)`} d={glyphPath(st, 6)} />)}
    </svg>
  )
}

function PublishArt() {
  return (
    <svg width="72" height="56" viewBox="0 0 72 56" focusable="false">
      <rect x="6" y="8" width="44" height="32" rx="4" className="pa-sheet" />
      <line x1="6" x2="50" y1="15" y2="15" className="pa-line" />
      <path d="M14 34 L22 26 L30 30 L42 20" className="pa-trend" />
      <rect x="44" y="26" width="22" height="26" rx="3" className="pa-sheet" />
      <path d="M55 31v12 M50 39l5 5 5-5" className="pa-down" />
    </svg>
  )
}

/**
 * "Atlas ทำงานอย่างไร": five stations joined by arrows — articles → grouped by content → topics → six statuses →
 * the site and open files every three months — each with this release's number when there is one. Loaded on demand
 * (/about, /data).
 */
export default function PipelineSteps({ release }: { release: AtlasRelease | null }) {
  const s = useStrings(openViz)
  const { t } = useI18n()
  const ov = release?.overview
  const w = release ? windows(release.overview.last_complete_year) : null
  const R = w ? fmtWindow(w.R) : t('about.generic.R')
  const B = w ? fmtWindow(w.B) : t('about.generic.B')
  const stations = [
    { art: <ArticlesArt />, num: ov ? s('ab.n.articles', { n: fmtInt(ov.kpis.articles) }) : null, title: s('ab.1t'), body: ov ? s('ab.1b', { n: fmtInt(ov.kpis.articles) }) : s('ab.1bGeneric') },
    { art: <GroupArt />, num: ov?.kpis.assigned_articles != null ? s('ab.n.assigned', { n: fmtInt(ov.kpis.assigned_articles) }) : null, title: s('ab.2t'), body: s('ab.2b') },
    { art: <TopicsArt />, num: ov ? s('ab.n.topics', { n: fmtInt(ov.kpis.topics) }) : null, title: s('ab.3tTopics'), body: s('ab.3bTopics') },
    { art: <StatusArt />, num: s('ab.n.status', { n: STATUSES.length }), title: s('ab.4t'), body: s('ab.3b', { R, B }) },
    { art: <PublishArt />, num: s('ab.n.publish'), title: s('ab.5t'), body: s('ab.5b') },
  ]
  return (
    <ol className="afl" aria-label={s('ab.flow.label')}>
      {stations.map((st, i) => (
        <li key={i} className="afl-st">
          <div className="afl-art" aria-hidden="true">{st.art}</div>
          {st.num ? <p className="afl-num">{st.num}</p> : null}
          <p className="afl-t">{st.title}</p>
          <p className="afl-b">{st.body}</p>
        </li>
      ))}
    </ol>
  )
}
