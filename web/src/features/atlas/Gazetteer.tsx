import { useMemo } from 'react'
import { CiWhisker } from '../../components/CiWhisker'
import { StatusGlyph } from '../../components/StatusGlyph'
import { groupName, type AtlasRelease } from '../../data/release'
import type { Topic } from '../../data/types'
import { breadthText } from '../../lib/breadth'
import { DEFINITION } from '../../lib/definition'
import { ciPct, fmtInt, fmtSignedPct } from '../../lib/format'
import { useI18n } from '../../lib/i18n'
import { buildSearchIndex, searchTopics } from '../../lib/search'
import { sortBy } from '../../lib/sort'
import { SIGNAL_STATUSES } from '../../lib/status'
import { statusName } from '../../lib/topicText'
import { FOREST_DOMAIN } from '../../pages/topicColumns'
import { gridRef, type MapPoint } from './mapSpace'

/** The map in text: every signal topic by status with its grid reference and CI, plus a search over all topics. */
export function Gazetteer({ release, points, query, onQuery, onPick, selected }: {
  release: AtlasRelease
  points: readonly MapPoint[]
  query: string
  onQuery: (q: string) => void
  onPick: (id: string) => void
  selected: string | null
}) {
  const { t, name, lang } = useI18n()
  const level = ciPct(release.ciLevel)
  const refOf = useMemo(() => new Map(points.map((p) => [p.id, gridRef(p.x, p.y)])), [points])
  const index = useMemo(() => buildSearchIndex(release.topics.map((tp) => ({ id: tp.id, th: tp.th, en: tp.en, keywords: tp.keywords ?? [], size: tp.size }))), [release])
  const q = query.trim()
  const hits = q
    ? searchTopics(index, q, 20)
        .map((h) => release.topicById.get(h.id))
        .filter((tp): tp is Topic => tp !== undefined)
    : []
  return (
    <>
      <div className="gaz-search">
        <label htmlFor="gaz-q" className="search-label">{t('map.gaz.search')}</label>
        <input id="gaz-q" type="search" className="gaz-input" value={query} autoComplete="off" spellCheck={false} onChange={(e) => onQuery(e.target.value)} />
        <div className="sr-only" role="status" aria-live="polite">
          {q ? (hits.length ? t('map.gaz.results', { n: hits.length }) : t('map.gaz.none', { q })) : ''}
        </div>
        {q && hits.length ? (
          <ul className="gaz-hits">
            {hits.map((tp) => (
              <li key={tp.id}>
                <button type="button" className="grow" aria-pressed={tp.id === selected} onClick={() => onPick(tp.id)}>
                  <span className="g-name">
                    <StatusGlyph status={tp.status} size={12} />
                    {name(tp)}
                  </span>
                  <span className="g-ref">{refOf.get(tp.id) ?? ''}</span>
                  <span className="g-sub">{statusName(t, tp.status)} · {groupName(release, tp.group, lang)}</span>
                </button>
              </li>
            ))}
          </ul>
        ) : null}
        {q && !hits.length ? <p className="search-none">{t('map.gaz.none', { q })}</p> : null}
      </div>
      <div className="gaz">
        {SIGNAL_STATUSES.map((st) => {
          const list = sortBy(release.topics.filter((tp) => tp.status === st), (tp) => tp.metrics.share_growth, st === 'DECLINING' ? 'asc' : 'desc')
          return (
            <div className="gcol" key={st}>
              <h3 className="gcol-h">
                <StatusGlyph status={st} size={16} />
                <span>{statusName(t, st)}</span>
                <small>{fmtInt(list.length)}</small>
              </h3>
              <ul className="glist">
                {list.map((tp) => (
                  <li key={tp.id}>
                    <button type="button" className="grow" aria-pressed={tp.id === selected} onClick={() => onPick(tp.id)}>
                      <span className="g-name">{name(tp)}</span>
                      <span className="g-ref">{refOf.get(tp.id) ?? ''}</span>
                      <span className="g-meta">
                        <span className="g-wh">
                          <CiWhisker status={tp.status} value={tp.metrics.share_growth} lo={tp.metrics.share_growth_lo} hi={tp.metrics.share_growth_hi} domain={FOREST_DOMAIN} refValue={DEFINITION.emergingMinGrowthLo} width={140} />
                        </span>
                        <span className="g-val">{fmtSignedPct(tp.metrics.share_growth)}</span>
                      </span>
                      <span className="g-sub">
                        {groupName(release, tp.group, lang)}
                        {tp.metrics.journal_driven ? ` · ${t('journalDriven')}: ${breadthText(t, tp)}` : ''}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </div>
      <p className="note">{t('map.gaz.foot', { level, bar: fmtSignedPct(DEFINITION.emergingMinGrowthLo, 0) })}</p>
    </>
  )
}
