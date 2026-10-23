import type { Lang } from './i18n'

/** A name as shown: in the UI language when it has one, else in the other language, else a fallback (an id, an OJS path). */
export interface ShownName {
  text: string
  /** language of `text` when it differs from the UI language (for a lang attribute); null = same, or not a name */
  lang: Lang | null
  /** no name in either language: `text` is the fallback */
  fallback: boolean
}

/** The name in the UI language, else in the other language, else `fallback` (never an empty title). */
export function shownName(th: string | null | undefined, en: string | null | undefined, lang: Lang, fallback: string): ShownName {
  const own = lang === 'en' ? en : th
  const other = lang === 'en' ? th : en
  if (own) return { text: own, lang: null, fallback: false }
  if (other) return { text: other, lang: lang === 'en' ? 'th' : 'en', fallback: false }
  return { text: fallback, lang: null, fallback: true }
}

/** The name in the other language when both exist and differ (shown under a title). */
export function otherName(th: string | null | undefined, en: string | null | undefined, lang: Lang): string {
  const own = lang === 'en' ? en : th
  const other = lang === 'en' ? th : en
  return own && other && own !== other ? other : ''
}
