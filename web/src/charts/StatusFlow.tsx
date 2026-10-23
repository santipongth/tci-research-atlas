import { useState } from 'react'
import { StatusGlyph } from '../components/StatusGlyph'
import type { StatusId } from '../lib/status'
import { useTooltip } from '../lib/tooltip'
import { useElementSize } from '../lib/useElementSize'
import { bandPath, statusFlow, type FlowLink, type FlowNode } from './execLayout'

const UNIT = 26
const MIN_H = 48
const GAP = 14
const BAR = 6

/**
 * Status transitions between two releases: the previous status on the left, the current one on the right (glyph +
 * name + count on both sides), one band per transition whose thickness is its topic count, tinted with the new status.
 * Pointing at a band names its topics; the figure's table view lists every change.
 */
export function StatusFlow({ changes, statusLabel, topicName, heads, label, bandTitle }: {
  changes: readonly { topic: string; previous: string; current: string }[]
  statusLabel: (s: StatusId) => string
  topicName: (id: string) => string
  heads: { left: string; right: string }
  label: string
  bandTitle: (l: FlowLink) => string
}) {
  const [ref, { width: W }] = useElementSize<HTMLDivElement>()
  const [hot, setHot] = useState<string | null>(null)
  const tip = useTooltip()
  const L = statusFlow(changes, { unit: UNIT, minH: MIN_H, gap: GAP })
  if (L.links.length === 0) return null
  const key = (l: FlowLink) => `${l.from}>${l.to}`
  const side = (nodes: FlowNode[], where: 'l' | 'r') => (
    <ul className={`sf-col sf-${where}`} style={{ height: L.height }}>
      {nodes.map((n) => (
        <li key={n.status} className="sf-node" style={{ top: n.y, height: n.h }}>
          <StatusGlyph status={n.status} size={14} />
          <span className="sf-name">{statusLabel(n.status)}</span>
          <b className="sf-n">{n.count}</b>
        </li>
      ))}
    </ul>
  )
  return (
    <div className="sf">
      <div className="sf-heads" aria-hidden="true">
        <span>{heads.left}</span>
        <span>{heads.right}</span>
      </div>
      <div className="sf-body">
        {side(L.left, 'l')}
        <div ref={ref} className="sf-mid">
          {W > 0 ? (
            <svg width={W} height={L.height} viewBox={`0 0 ${W} ${L.height}`} role="img" aria-label={label}>
              {L.links.map((l) => (
                <path
                  key={key(l)}
                  d={bandPath(l, BAR, W - BAR)}
                  className={`sf-band sf-to-${l.to}${hot === key(l) ? ' is-hot' : ''}`}
                  onPointerEnter={(e) => {
                    setHot(key(l))
                    tip.show(
                      <>
                        <div className="tip-title">{bandTitle(l)}</div>
                        {l.topics.map((id) => <div key={id}>{topicName(id)}</div>)}
                      </>,
                      e.clientX,
                      e.clientY,
                    )
                  }}
                  onPointerLeave={() => {
                    setHot(null)
                    tip.hide()
                  }}
                >
                  <title>{bandTitle(l)}</title>
                </path>
              ))}
              {L.left.map((n) => <rect key={`l${n.status}`} x={0} y={n.y} width={BAR} height={n.h} className={`sf-bar sf-to-${n.status}`} />)}
              {L.right.map((n) => <rect key={`r${n.status}`} x={W - BAR} y={n.y} width={BAR} height={n.h} className={`sf-bar sf-to-${n.status}`} />)}
            </svg>
          ) : null}
        </div>
        {side(L.right, 'r')}
      </div>
    </div>
  )
}
