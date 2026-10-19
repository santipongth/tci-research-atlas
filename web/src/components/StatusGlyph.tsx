import { glyphPath, type StatusId } from '../lib/status'

/** Decorative status glyph; the status name is always written next to it. */
export function StatusGlyph({ status, size = 14 }: { status: StatusId; size?: number }) {
  return (
    <svg className={`st-icon st-${status}`} width={size} height={size} viewBox="-8 -8 16 16" aria-hidden="true" focusable="false">
      <path className="st-mark" d={glyphPath(status, 5.6)} />
    </svg>
  )
}

/** Status tag: glyph + tinted background + the status name (never colour alone). */
export function StatusChip({ status, label, small = false }: { status: StatusId; label: string; small?: boolean }) {
  return (
    <span className={`chip chip-${status}${small ? ' chip-sm' : ''}`}>
      <StatusGlyph status={status} size={small ? 11 : 12} />
      <span>{label}</span>
    </span>
  )
}
