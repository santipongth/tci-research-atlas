import type { ReactNode } from 'react'
import { useNavigate } from 'react-router'
import { StatusGlyph } from '../components/StatusGlyph'
import type { Topic } from '../data/types'
import { fmtInt } from '../lib/format'
import type { StatusId } from '../lib/status'
import { useTooltip } from '../lib/tooltip'
import { percentOf, type WaffleGroup } from './infographic'

/**
 * Status waffle (unit chart): one row per status — glyph, name, count and share of all topics in text — then one
 * square per topic in that status's colour (low data: a dashed outline). The squares are decorative (the counts are
 * written beside them and the figure's table has every number); pointing at one shows the topic, pressing it opens it.
 */
export function StatusWaffle({ groups, total, statusLabel, meaning, tipFor, compact = false }: {
  groups: readonly WaffleGroup[]
  total: number
  statusLabel: (s: StatusId) => string
  /** the status in everyday words, under its name */
  meaning?: (s: StatusId) => string
  tipFor?: (tp: Topic) => ReactNode
  /** smaller squares, no meanings (the printed brief) */
  compact?: boolean
}) {
  const navigate = useNavigate()
  const tip = useTooltip()
  return (
    <div className={compact ? 'wf is-compact' : 'wf'}>
      {groups.map((g) => (
        <div className="wf-row" key={g.status}>
          <div className="wf-label">
            <p className="wf-name">
              <StatusGlyph status={g.status} size={16} />
              <b>{statusLabel(g.status)}</b>
              <span className="wf-n">{fmtInt(g.topics.length)}</span>
              <span className="wf-pct">{percentOf(g.topics.length, total)}%</span>
            </p>
            {meaning && !compact ? <p className="wf-mean">{meaning(g.status)}</p> : null}
          </div>
          <div className="wf-cells" aria-hidden="true">
            {g.topics.map((tp) => (
              <span
                key={tp.id}
                className={`wf-cell wf-${g.status}`}
                onPointerEnter={tipFor ? (e) => tip.show(tipFor(tp), e.clientX, e.clientY) : undefined}
                onPointerLeave={tipFor ? () => tip.hide() : undefined}
                onClick={() => {
                  tip.hide()
                  navigate(`/topics/${tp.id}`)
                }}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
