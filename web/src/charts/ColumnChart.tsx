import { useTooltip } from '../lib/tooltip'
import { useElementSize } from '../lib/useElementSize'
import { columnAxis } from './execLayout'

export interface ColumnItem {
  key: string
  value: number
}

/**
 * Columns on a zero baseline (one per year): ink-2 bars, recessive gridlines, numbers on the first, the latest and the
 * largest column only; every column shows its figure on hover (the table view has them all). Placed in percent, so it reflows and prints.
 * Under ~40 px per column every other label is dropped (the latest always stays).
 */
export function ColumnChart({ items, format, label }: { items: readonly ColumnItem[]; format: (v: number) => string; label: string }) {
  const [ref, { width: W }] = useElementSize<HTMLDivElement>()
  const tip = useTooltip()
  const { max, ticks } = columnAxis(items.map((c) => c.value))
  const peak = items.reduce((m, c, i) => (c.value > items[m].value ? i : m), 0)
  const marked = new Set([0, items.length - 1, peak])
  const sparse = W > 0 && (W - 48) / Math.max(1, items.length) < 40
  const pct = (v: number) => `${(Math.max(0, v) / max) * 100}%`
  return (
    <div ref={ref} className="cc" role="img" aria-label={label}>
      <div className="cc-plot" aria-hidden="true">
        {ticks.map((v) => (
          <span key={v} className={v === 0 ? 'cc-gl is-base' : 'cc-gl'} style={{ bottom: pct(v) }}>
            <span className="cc-tk">{format(v)}</span>
          </span>
        ))}
        <ol className="cc-cols">
          {items.map((c, i) => (
            <li
              key={c.key}
              className="cc-col"
              onPointerEnter={(e) => tip.showAt(<><div className="tip-title">{c.key}</div><div>{format(c.value)}</div></>, e.currentTarget)}
              onPointerLeave={() => tip.hide()}
            >
              <span className="cc-bar" style={{ height: pct(c.value) }}>
                {marked.has(i) ? <span className="cc-v">{format(c.value)}</span> : null}
              </span>
            </li>
          ))}
        </ol>
      </div>
      <ol className="cc-x" aria-hidden="true">
        {items.map((c, i) => (
          <li key={c.key} className={sparse && i % 2 !== (items.length - 1) % 2 ? 'is-skip' : undefined}>{c.key}</li>
        ))}
      </ol>
    </div>
  )
}
