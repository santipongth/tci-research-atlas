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
  return finite(x) ? nf(digits).format(x).replace('-', MINUS) : DASH
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
  const sign = n < 0 ? MINUS : ''
  if (a >= 1e6) return `${sign}${(a / 1e6).toFixed(a >= 1e7 ? 0 : 1).replace(/\.0$/, '')}M`
  if (a >= 1e4) return `${sign}${Math.round(a / 1e3)}K`
  if (a >= 1e3) return `${sign}${(a / 1e3).toFixed(1).replace(/\.0$/, '')}K`
  return `${sign}${Math.round(a)}`
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
export function kpiDelta(value: number, prev: number | null | undefined, unit: 'count' | 'pct', lang: Lang): string | null {
  if (!finite(prev) || !finite(value)) return null
  if (unit === 'pct') return fmtPp(value - prev, lang)
  const d = value - prev
  return prev > 0 ? `${fmtSignedInt(d)} (${fmtSignedPct(d / prev, 1)})` : fmtSignedInt(d)
}
