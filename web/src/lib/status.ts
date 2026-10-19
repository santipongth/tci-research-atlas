/** The six statuses of the Emerging definition, in display order, and their glyph shapes. */
export const STATUSES = ['EMERGING', 'WATCH', 'HOT', 'DECLINING', 'STABLE', 'LOW_DATA'] as const
export type StatusId = (typeof STATUSES)[number]
/** Statuses that carry a signal (they get CI whiskers, map markers and forecast attention). */
export const SIGNAL_STATUSES = ['EMERGING', 'WATCH', 'HOT', 'DECLINING'] as const
export type SignalStatus = (typeof SIGNAL_STATUSES)[number]

export function isStatus(v: unknown): v is StatusId {
  return typeof v === 'string' && (STATUSES as readonly string[]).includes(v)
}

export function isSignal(s: StatusId): s is SignalStatus {
  return (SIGNAL_STATUSES as readonly string[]).includes(s)
}

const f = (n: number) => Number(n.toFixed(2))

/** SVG path of a status glyph centred on 0,0: ▲ EMERGING, ◆ WATCH, ● HOT, ▼ DECLINING, ■ STABLE, ○ LOW_DATA (dashed in CSS). */
export function glyphPath(status: StatusId, r: number): string {
  const a = r * 1.25
  switch (status) {
    case 'EMERGING':
      return `M0,${f(-a)}L${f(a * 0.93)},${f(a * 0.62)}L${f(-a * 0.93)},${f(a * 0.62)}Z`
    case 'DECLINING':
      return `M0,${f(a)}L${f(a * 0.93)},${f(-a * 0.62)}L${f(-a * 0.93)},${f(-a * 0.62)}Z`
    case 'WATCH':
      return `M0,${f(-a)}L${f(a)},0L0,${f(a)}L${f(-a)},0Z`
    case 'STABLE': {
      const q = f(r * 0.86)
      return `M${-q},${-q}H${q}V${q}H${-q}Z`
    }
    default:
      return `M${f(-r)},0A${f(r)},${f(r)} 0 1,0 ${f(r)},0A${f(r)},${f(r)} 0 1,0 ${f(-r)},0Z`
  }
}

/** The nowcast marker: a neutral ink cross (centred path) — status glyphs and colours are reserved for statuses. */
export const NOWCAST_MARK = 'M-4.5,-4.5L4.5,4.5M4.5,-4.5L-4.5,4.5'
