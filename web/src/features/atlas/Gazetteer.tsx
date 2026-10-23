import { ListMore } from '../../components/ListMore'
import { useMemo } from 'react'
import { StatusGlyph } from '../../components/StatusGlyph'
import { groupName, type AtlasRelease } from '../../data/release'
import { DASH, fmtInt, fmtSignedPct } from '../../lib/format'
import { useI18n } from '../../lib/i18n'
import { sortBy } from '../../lib/sort'
import { SIGNAL_STATUSES, type SignalStatus } from '../../lib/status'
import { statusName } from '../../lib/topicText'
import { keepSelected, useCapped } from '../../lib/useCapped'
import { gridRef, type MapPoint } from './mapSpace'

/** The map in text: every signal topic by status with its grid reference (no search box: owner 2026-10-24). */
export function Gazetteer({ release, points, onPick, selected }: {
  release: AtlasRelease
  points: readonly MapPoint[]
  onPick: (id: string) => void
  selected: string | null
}) {
  const refOf = useMemo(() => new Map(points.map((p) => [p.id, gridRef(p.x, p.y)])), [points])
  return (
    <>
      <div className="gaz">
        {SIGNAL_STATUSES.map((st) => (
          <GazColumn key={st} release={release} status={st} refOf={refOf} onPick={onPick} selected={selected} />
        ))}
      </div>
    </>
  )
}

/** Topics listed per status before "show all": the gazetteer is a way in, the topic pages carry the rest. */
const COLUMN_ROWS = 20

function GazColumn({ release, status, refOf, onPick, selected }: {
  release: AtlasRelease
  status: SignalStatus
  refOf: ReadonlyMap<string, string>
  onPick: (id: string) => void
  selected: string | null
}) {
  const { t, name, lang } = useI18n()
  const list = useMemo(() => sortBy(release.topics.filter((tp) => tp.status === status), (tp) => tp.metrics.share_growth, status === 'DECLINING' ? 'asc' : 'desc'), [release, status])
  const capped = useCapped(list, COLUMN_ROWS)
  return (
    <div className="gcol">
      <h3 className="gcol-h">
        <StatusGlyph status={status} size={16} />
        <span>{statusName(t, status)}</span>
        <small>{fmtInt(list.length)}</small>
      </h3>
      {status === 'WATCH' && list.length ? <p className="gcol-note">{t('journalDriven')}</p> : null}
      <ul className="glist">
        {keepSelected(capped.shown, list, (tp) => tp.id === selected).map((tp) => (
          <li key={tp.id}>
            <button type="button" className="grow" aria-pressed={tp.id === selected} onClick={() => onPick(tp.id)}>
              <span className="g-name">{name(tp)}</span>
              <span className="g-ref">{refOf.get(tp.id) ?? ''}</span>
              <span className="g-meta">
                <span className="g-val">{tp.metrics.share_growth === null || tp.metrics.share_growth === undefined ? DASH : `${fmtSignedPct(tp.metrics.share_growth, 0)} ${t('perYear')}`}</span>
              </span>
              <span className="g-sub">
                {groupName(release, tp.group, lang)}
              </span>
            </button>
          </li>
        ))}
      </ul>
      <ListMore {...capped.more} />
    </div>
  )
}
