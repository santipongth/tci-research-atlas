import type { Lang } from './i18n'

/** Both languages use Arabic digits with en-US grouping, the true minus sign and Gregorian years (DESIGN.md). */
export const MINUS = '−'
export const DASH = '–'

const formatters = new Map<number, Intl.NumberFormat>()
function nf(digits: number): Intl.NumberFormat {
  let f = formatters.get(digits)
  if (!f) {
    f = new Intl.NumberFormat('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
    formatters.set(digits, f)
  }
  return f
}

const finite = (x: number | null | undefined): x is number => typeof x === 'number' && Number.isFinite(x)

export function fmtNum(x: number | null | undefined, digits: number): string {
  if (!finite(x)) return DASH
  // a value that rounds to zero is "0", never "−0"
  const v = Number(x.toFixed(digits)) === 0 ? 0 : x
  return nf(digits).format(v).replace('-', MINUS)
}

export function fmtInt(n: number | null | undefined): string {
  return finite(n) ? fmtNum(Math.round(n), 0) : DASH
}

/** 0.0123 → "1.23%" (the contract stores shares and growth as fractions). */
export function fmtPct(fraction: number | null | undefined, digits = 1): string {
  return finite(fraction) ? `${fmtNum(fraction * 100, digits)}%` : DASH
}

/** +0.152 → "+15.2%", −0.05 → "−5.0%", values that round to zero → "±0.0%". */
export function fmtSignedPct(fraction: number | null | undefined, digits = 1): string {
  if (!finite(fraction)) return DASH
  const v = Number((fraction * 100).toFixed(digits))
  if (v === 0) return `±${nf(digits).format(0)}%`
  return `${v > 0 ? '+' : MINUS}${nf(digits).format(Math.abs(v))}%`
}

export function fmtSignedInt(n: number | null | undefined): string {
  if (!finite(n)) return DASH
  const v = Math.round(n)
  if (v === 0) return '±0'
  return `${v > 0 ? '+' : MINUS}${nf(0).format(Math.abs(v))}`
}

/** A change between two percentages, in percentage points: "+0.6 จุด" / "+0.6 pp". */
export function fmtPp(points: number, lang: Lang): string {
  const v = Number(points.toFixed(1))
  const unit = lang === 'en' ? 'pp' : 'จุด'
  if (v === 0) return `±0.0 ${unit}`
  return `${v > 0 ? '+' : MINUS}${nf(1).format(Math.abs(v))} ${unit}`
}

export function fmtRatio(x: number | null | undefined): string {
  return finite(x) ? `${fmtNum(x, 1)}×` : DASH
}

/** Axis ticks: 950, 1.5K, 13K, 2.4M. */
export function fmtCompact(n: number): string {
  const a = Math.abs(n)
  const body = (): string => {
    if (a >= 1e6) return `${a >= 1e7 ? Math.round(a / 1e6) : Number((a / 1e6).toFixed(1))}M`
    if (a >= 1e3) {
      const k = a >= 1e4 ? Math.round(a / 1e3) : Number((a / 1e3).toFixed(1))
      return k >= 1000 ? '1M' : `${k}K`
    }
    const r = Math.round(a)
    return r >= 1000 ? '1K' : String(r)
  }
  const b = body()
  return n < 0 && b !== '0' ? `${MINUS}${b}` : b
}

export function fmtDate(iso: string, lang: Lang): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return new Intl.DateTimeFormat(lang === 'th' ? 'th-TH-u-ca-gregory' : 'en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' }).format(d)
}

/** manifest.ci_level 0.9 → 90 */
export function ciPct(level: number): number {
  return Math.round(level * 100)
}

/** "+6,140 (+2.5%)" for counts, "+0.6 จุด" for percentages; null when there is nothing to compare with. */
/** Direction of a KPI change as printed by kpiDelta (pct to 0.1 point, counts to 1), so a change shown as ±0 gets no arrow. */
export function kpiDir(value: number, prev: number | null | undefined, unit: 'count' | 'pct'): -1 | 0 | 1 {
  if (!finite(prev) || !finite(value)) return 0
  const d = unit === 'pct' ? Number((value - prev).toFixed(1)) : Math.round(value - prev)
  return d > 0 ? 1 : d < 0 ? -1 : 0
}

export function kpiDelta(value: number, prev: number | null | undefined, unit: 'count' | 'pct', lang: Lang): string | null {
  if (!finite(prev) || !finite(value)) return null
  if (unit === 'pct') return fmtPp(value - prev, lang)
  const d = value - prev
  return prev > 0 ? `${fmtSignedInt(d)} (${fmtSignedPct(d / prev, 1)})` : fmtSignedInt(d)
}

/** "2026Q4" → { y: 2026, q: 4 }; null for any other shape. */
export function releaseQuarter(release: string): { y: number; q: number } | null {
  const m = /^(\d{4})Q([1-4])$/.exec(release)
  return m ? { y: Number(m[1]), q: Number(m[2]) } : null
}
