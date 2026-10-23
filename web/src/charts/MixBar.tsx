import type { ReactNode } from 'react'
import type { MixSegment } from './execLayout'

export interface MixPart extends MixSegment {
  name: ReactNode
  /** the value as printed ("30%") */
  text: string
}

/**
 * One 100 % bar split into parts (largest first, the remainder last as "อื่น ๆ"): one blue hue from dark to light in
 * list order, a 2 px paper gap between parts, and the key under the bar repeating every part with its number, so
 * nothing is read from colour alone.
 */
export function MixBar({ parts, label }: { parts: readonly MixPart[]; label: string }) {
  const shade = (p: MixPart, i: number) => (p.other ? 'mx-other' : `mx-${Math.min(i, 3)}`)
  return (
    <div className="mx">
      <div className="mx-bar" role="img" aria-label={label}>
        {parts.map((p, i) => (
          <span key={p.key} className={`mx-seg ${shade(p, i)}`} style={{ width: `${p.frac * 100}%` }} />
        ))}
      </div>
      <ol className="mx-key">
        {parts.map((p, i) => (
          <li key={p.key}>
            <span className={`mx-sw ${shade(p, i)}`} aria-hidden="true" />
            <span className="mx-name">{p.name}</span>
            <span className="mx-val">{p.text}</span>
          </li>
        ))}
      </ol>
    </div>
  )
}

/**
 * The largest source against everything else as one 100 % bar, with a dashed marker at the threshold: the dark part
 * past the marker means "relies on one source". The share is printed beside the bar.
 */
export function SplitBar({ frac, marker, text, label }: { frac: number; marker: number; text: string; label: string }) {
  const f = Math.max(0, Math.min(1, frac))
  return (
    <span className="sb">
      <span className="sb-bar" role="img" aria-label={label}>
        <span className="sb-top" style={{ width: `${f * 100}%` }} />
        <span className="sb-mark" style={{ left: `${Math.max(0, Math.min(1, marker)) * 100}%` }} />
      </span>
      <span className="sb-val">{text}</span>
    </span>
  )
}
