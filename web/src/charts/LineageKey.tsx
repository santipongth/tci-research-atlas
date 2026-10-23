export type LineageKind = 'new' | 'merge' | 'split' | 'gone'

export interface LineageItem {
  kind: LineageKind
  title: string
  body: string
  /** how many topics of this release did this ("3 หัวข้อ"), or null to leave it out */
  count: string | null
}

/** Before → after as ink dots: nothing → one (new), two → one (merge), one → two (split), one → nothing (gone). */
function Art({ kind }: { kind: LineageKind }) {
  const dot = (cx: number, cy: number, faint = false) => <circle cx={cx} cy={cy} r={6} className={faint ? 'lk-dot is-faint' : 'lk-dot'} />
  const line = (x1: number, y1: number, x2: number, y2: number) => <line x1={x1} y1={y1} x2={x2} y2={y2} className="lk-line" />
  return (
    <svg viewBox="0 0 88 36" width="88" height="36" aria-hidden="true" focusable="false">
      {kind === 'new' ? <>{dot(12, 18, true)}{line(20, 18, 62, 18)}{dot(72, 18)}</> : null}
      {kind === 'merge' ? <>{dot(12, 8)}{dot(12, 28)}{line(19, 10, 64, 17)}{line(19, 26, 64, 19)}{dot(72, 18)}</> : null}
      {kind === 'split' ? <>{dot(12, 18)}{line(20, 17, 65, 10)}{line(20, 19, 65, 26)}{dot(72, 8)}{dot(72, 28)}</> : null}
      {kind === 'gone' ? <>{dot(12, 18)}{line(20, 18, 62, 18)}{dot(72, 18, true)}</> : null}
    </svg>
  )
}

/** The four ways a topic changes between releases, as a small key: drawing, name, one-line meaning, this release's count. */
export function LineageKey({ items, label }: { items: readonly LineageItem[]; label: string }) {
  return (
    <ul className="lk" aria-label={label}>
      {items.map((it) => (
        <li key={it.kind} className="lk-item">
          <Art kind={it.kind} />
          <span className="lk-t">{it.title}</span>
          <span className="lk-b">{it.body}</span>
          {it.count ? <span className="lk-n">{it.count}</span> : null}
        </li>
      ))}
    </ul>
  )
}
