import { linear } from '../charts/scale'
import { glyphPath, type StatusId } from '../lib/status'

/**
 * One forest-plot row: the interval (capped, or an arrow where it runs off the axis), the estimate as the status glyph,
 * a solid zero line and a dashed reference line (+10 %/yr for EMERGING). Decorative: the numbers are written beside it.
 */
export function CiWhisker({ status, value, lo, hi, domain, refValue, width, height = 18, r = 4 }: {
  status: StatusId
  value: number | null | undefined
  lo: number | null | undefined
  hi: number | null | undefined
  domain: readonly [number, number]
  refValue?: number
  width: number
  height?: number
  r?: number
}) {
  if (lo === null || lo === undefined || hi === null || hi === undefined || width <= 12) return null
  const [d0, d1] = domain
  const x = linear(d0, d1, 6, width - 6)
  const cy = height / 2
  const a = Math.max(d0, Math.min(d1, lo))
  const b = Math.max(d0, Math.min(d1, hi))
  const v = value === null || value === undefined ? null : Math.max(d0, Math.min(d1, value))
  const cls = `wh-cap wh-${status}`
  return (
    <svg className="whisker" width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden="true" focusable="false">
      {d0 < 0 && d1 > 0 ? <line className="wh-zero" x1={x(0)} x2={x(0)} y1={0} y2={height} /> : null}
      {refValue !== undefined && refValue > d0 && refValue < d1 ? <line className="wh-ref" x1={x(refValue)} x2={x(refValue)} y1={2} y2={height - 2} /> : null}
      <line className={`wh-ci wh-${status}`} x1={x(a)} x2={x(b)} y1={cy} y2={cy} />
      {lo < d0 ? <path className={cls} fill="none" d={`M${x(a) + 5},${cy - 4}L${x(a)},${cy}L${x(a) + 5},${cy + 4}`} /> : <line className={cls} x1={x(a)} x2={x(a)} y1={cy - 4} y2={cy + 4} />}
      {hi > d1 ? <path className={cls} fill="none" d={`M${x(b) - 5},${cy - 4}L${x(b)},${cy}L${x(b) - 5},${cy + 4}`} /> : <line className={cls} x1={x(b)} x2={x(b)} y1={cy - 4} y2={cy + 4} />}
      {v !== null ? <path className={`mk mk-${status}`} transform={`translate(${x(v)},${cy})`} d={glyphPath(status, r)} /> : null}
    </svg>
  )
}
