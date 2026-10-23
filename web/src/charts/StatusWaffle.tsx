import type { ReactNode } from 'react'
import { useNavigate } from 'react-router'
import { StatusGlyph } from '../components/StatusGlyph'
import type { Topic } from '../data/types'
import { fmtInt } from '../lib/format'
import type { StatusId } from '../lib/status'
import { useTooltip } from '../lib/tooltip'
import { percentOf, waffleCells, waffleCounts, type WaffleGroup } from './infographic'

/**
 * Status waffle (unit chart): one row per status — glyph, name, count and share of all topics in text — then one
 * square per topic in that status's colour (low data: a dashed outline); with many topics one square stands for about
 * `unit` topics (waffleCounts). The squares are decorative (the counts are
 * written beside them and the figure's table has every number); pointing at one shows the topic, pressing it opens it.
 */
export function StatusWaffle({ groups, total, unit = 1, statusLabel, meaning, tipFor, compact = false }: {
  groups: readonly WaffleGroup[]
  total: number
  /** topics per square: 1 = a square for every topic; more when the release has too many topics to draw one each */
  unit?: number
  statusLabel: (s: StatusId) => string
  /** the status in everyday words, under its name */
  meaning?: (s: StatusId) => string
  /** the tooltip of a square: its strongest topic, and how many more topics the square stands for */
  tipFor?: (tp: Topic, more: number) => ReactNode
  /** smaller squares, no meanings (the printed brief) */
  compact?: boolean
}) {
  const navigate = useNavigate()
  const tip = useTooltip()
  const squares = waffleCounts(groups.map((g) => g.topics.length), unit)
  return (
    <div className={compact ? 'wf is-compact' : 'wf'}>
      {groups.map((g, gi) => (
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
            {waffleCells(g.topics, squares[gi]).map((cell) => (
              <span
                key={cell[0].id}
                className={`wf-cell wf-${g.status}`}
                onPointerEnter={tipFor ? (e) => tip.show(tipFor(cell[0], cell.length - 1), e.clientX, e.clientY) : undefined}
                onPointerLeave={tipFor ? () => tip.hide() : undefined}
                onClick={() => {
                  tip.hide()
                  // a square for one topic opens it; once squares stand for several topics, every square (even one
                  // left holding a single topic) opens the list of that status
                  navigate(unit <= 1 ? `/topics/${cell[0].id}` : `/emerging?status=${g.status}`)
                }}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
