export type SortDir = 'asc' | 'desc'

const collator = new Intl.Collator('th')

/** A sorted copy; missing values (null, undefined, NaN) always go last whatever the direction. */
export function sortBy<R>(rows: readonly R[], value: (row: R) => number | string | null | undefined, dir: SortDir): R[] {
  const sign = dir === 'asc' ? 1 : -1
  const missing = (v: number | string | null | undefined) => v === null || v === undefined || (typeof v === 'number' && !Number.isFinite(v))
  return [...rows].sort((a, b) => {
    const va = value(a)
    const vb = value(b)
    const ma = missing(va)
    const mb = missing(vb)
    if (ma || mb) return ma === mb ? 0 : ma ? 1 : -1
    if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * sign
    return collator.compare(String(va), String(vb)) * sign
  })
}

export interface SortSpec {
  key: string
  dir: SortDir
}

/** Next sort when a header is chosen: a new column starts in `first` (text asc, numbers desc); the same column flips. */
export function nextSort(current: SortSpec | null, key: string, first: SortDir): SortSpec {
  if (current && current.key === key) return { key, dir: current.dir === 'asc' ? 'desc' : 'asc' }
  return { key, dir: first }
}
