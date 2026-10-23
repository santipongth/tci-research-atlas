import { Link } from 'react-router'
import { StatusChip } from '../components/StatusGlyph'
import { TopicName } from '../components/TopicName'
import type { AtlasRelease } from '../data/release'
import type { Topic } from '../data/types'
import { fmtInt } from '../lib/format'
import { useDocumentTitle } from '../lib/useDocumentTitle'
import { useI18n, useStrings } from '../lib/i18n'
import { growthText, statusName } from '../lib/topicText'
import { embed } from '../strings/embed'
import { EmbedFrame } from './EmbedFrame'

const TOP = 10
const ORDER = ['EMERGING', 'WATCH'] as const

/** EMERGING first, then WATCH; within a status the highest score first (no score last), then the larger growth. */
function topSignals(topics: readonly Topic[], n = TOP): Topic[] {
  const rank = (tp: Topic) => ORDER.indexOf(tp.status as (typeof ORDER)[number])
  return topics
    .filter((tp) => rank(tp) >= 0)
    .sort((a, b) => rank(a) - rank(b) || (b.score ?? -Infinity) - (a.score ?? -Infinity) || (b.metrics.share_growth ?? -Infinity) - (a.metrics.share_growth ?? -Infinity) || a.id.localeCompare(b.id))
    .slice(0, n)
}

/** /embed/emerging — the top 10 EMERGING / WATCH topics of the latest release, for an <iframe>. */
export default function EmbedEmerging() {
  return <EmbedFrame full={() => '/topics'}>{(release) => <EmergingWidget release={release} />}</EmbedFrame>
}

function EmergingWidget({ release }: { release: AtlasRelease }) {
  const s = useStrings(embed)
  const { t, lang } = useI18n()
  useDocumentTitle(s('em.title'))
  const all = release.topics.filter((tp) => tp.status === 'EMERGING' || tp.status === 'WATCH')
  const rows = topSignals(release.topics)
  return (
    <section className="embed-em" aria-labelledby="embed-em-h">
      <h1 id="embed-em-h" className="embed-h">{s('em.title')}</h1>
      {rows.length ? (
        <>
          <p className="embed-sub">{s('em.sub', { n: fmtInt(rows.length) })}</p>
          <ol className="embed-list">
            {rows.map((tp) => (
              <li key={tp.id}>
                <div className="embed-row">
                  <Link to={`/topics/${tp.id}?lang=${lang}`} target="_blank" rel="noopener noreferrer" className="embed-topic-link">
                    <TopicName topic={tp} />
                    <span className="sr-only"> {t('newTab')}</span>
                  </Link>
                  <span className="embed-meta">
                    <StatusChip status={tp.status} label={statusName(t, tp.status)} small />
                    <span>{growthText(t, tp.metrics)}</span>
                  </span>
                </div>
              </li>
            ))}
          </ol>
          {all.length > rows.length ? (
            <p className="embed-more">
              <Link to={`/topics?lang=${lang}`} target="_blank" rel="noopener noreferrer">
                {s('em.more')}
                <span className="sr-only"> {t('newTab')}</span>
              </Link>
            </p>
          ) : null}
        </>
      ) : (
        <p className="note">{s('em.none')}</p>
      )}
      <p className="source">{t('source.line', { release: release.overview.release })} · {t('source.def', { v: release.definitionVersion })}</p>
    </section>
  )
}
