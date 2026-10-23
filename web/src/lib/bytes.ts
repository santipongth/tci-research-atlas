import { fmtNum } from './format'

/** A file size for people: "< 1 KB", "12 KB" (whole kilobytes under 1 MB), "1.4 MB" (one decimal). */
export function fmtBytes(bytes: number | null | undefined): string {
  if (typeof bytes !== 'number' || !Number.isFinite(bytes) || bytes < 0) return '–'
  if (bytes < 1024) return '< 1 KB'
  if (bytes < 1024 * 1024) return `${fmtNum(Math.round(bytes / 1024), 0)} KB`
  return `${fmtNum(bytes / (1024 * 1024), 1)} MB`
}

/** Bytes of a text once saved as UTF-8 (what a CSV download weighs). */
export function utf8Bytes(text: string): number {
  return new TextEncoder().encode(text).length
}
