import { useEffect, useRef } from 'react'
import { MoreRows } from '../../components/dashboard/RankRows'
import { Segmented } from '../../components/dashboard/Segmented'
import { StatusGlyph } from '../../components/StatusGlyph'
import { groupName, type AtlasRelease } from '../../data/release'
import type { Topic } from '../../data/types'
import { fmtInt, fmtSignedPct } from '../../lib/format'
import { useI18n, useStrings } from '../../lib/i18n'
import { sortBy } from '../../lib/sort'
import type { StatusId } from '../../lib/status'
import { keepSelected } from '../../lib/useCapped'
import { usePaged } from '../../lib/usePaged'
import { atlas } from '../../strings/atlas'

/** Rows the list shows before "แสดงเพิ่ม" (a real release has ~1,500 topics). */
const STEP = 30

/**
 * The map in words, beside the map: every topic of the statuses on show, ranked by growth or by size, each with its
 * field and its grid square. A row is a button: it selects the topic and pans the map to it; a topic picked on the map
 * is pressed here and scrolled into view. Replaces the separate "ดัชนีหัวข้อ" (topic index) below the map.
 */
export function TopicList({ release, refOf, shown, by, onBy, selected, onPick }: {
  release: AtlasRelease
  refOf: ReadonlyMap<string, string>
  /** statuses whose topics are on the map */
  shown: ReadonlySet<StatusId>
  by: 'growth' | 'size'
  onBy: (by: 'growth' | 'size') => void
  selected: string | null
  onPick: (id: string) => void
}) {
  const { t, name, lang } = useI18n()
  const sa = useStrings(atlas)
  const list = release.topics.filter((tp) => shown.has(tp.status))
  const ranked: Topic[] =
    by === 'growth'
      ? sortBy(sortBy(list, (tp) => tp.metrics.share_recent, 'desc'), (tp) => tp.metrics.share_growth ?? -Infinity, 'desc')
      : sortBy(list, (tp) => tp.metrics.share_recent, 'desc')
  const page = usePaged(ranked, STEP, `${by}:${[...shown].sort().join(',')}`)
  const rows = keepSelected(page.shown, ranked, (tp) => tp.id === selected)
  const box = useRef<HTMLDivElement>(null)
  // a topic picked on the map: bring its row into the list's view (DOM only, no state)
  useEffect(() => {
    if (!selected) return
    const row = box.current?.querySelector<HTMLElement>(`[data-id="${selected}"]`)
    row?.scrollIntoView({ block: 'nearest' })
  }, [selected])
  return (
    <div className="ab-list">
      <div className="ab-list-head">
        <p className="ab-list-h">
          {sa('map.list.h')} <span>{sa('map.list.n', { n: fmtInt(list.length) })}</span>
        </p>
        <Segmented label={sa('map.by')} value={by} onChange={onBy} options={[{ id: 'growth', label: sa('map.by.growth') }, { id: 'size', label: sa('map.by.size') }]} />
      </div>
      <div className="ab-scroll" ref={box}>
        {rows.length ? (
          <ul className="ab-rows" aria-label={sa('map.list.h')}>
            {rows.map((tp) => {
              const g = tp.metrics.share_growth
              return (
                <li key={tp.id}>
                  <button type="button" className="ab-row" data-id={tp.id} aria-pressed={tp.id === selected} onClick={() => onPick(tp.id)}>
                    <StatusGlyph status={tp.status} size={12} />
                    <span className="ab-row-main">
                      <span className="ab-row-name">{name(tp)}</span>
                      <span className="ab-row-sub">{groupName(release, tp.group, lang)} · {sa('map.grid')} {refOf.get(tp.id) ?? ''}</span>
                    </span>
                    <span className={g != null && g < 0 ? 'ab-row-v is-down' : 'ab-row-v'}>
                      {g == null ? '' : `${fmtSignedPct(g, 0)} ${t('perYear')}`}
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        ) : (
          <p className="card-empty">{sa('map.list.none')}</p>
        )}
        <MoreRows {...page.more} />
      </div>
    </div>
  )
}
