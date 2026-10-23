import { useCallback, useMemo, useSyncExternalStore } from 'react'
import { STR, type StrKey } from '../strings'
import type { Entry } from '../strings/define'

export type Lang = 'th' | 'en'
export type Vars = Record<string, string | number>

const KEY = 'atlas-lang'
const listeners = new Set<() => void>()
let current: Lang = detectLang()

/** ?lang= inside the hash (shared links, the PDF brief) → the visitor's last choice → Thai. */
function detectLang(): Lang {
  if (typeof window === 'undefined') return 'th'
  const fromUrl = new URLSearchParams(window.location.hash.split('?')[1] ?? '').get('lang')
  if (fromUrl === 'th' || fromUrl === 'en') return fromUrl
  try {
    const saved = window.localStorage.getItem(KEY)
    if (saved === 'th' || saved === 'en') return saved
  } catch {
    /* storage blocked: keep the default */
  }
  return 'th'
}

export function getLang(): Lang {
  return current
}

export function syncDocumentLang(): void {
  if (typeof document !== 'undefined') document.documentElement.lang = current
}

export function setLang(lang: Lang): void {
  if (lang === current) return
  current = lang
  try {
    window.localStorage.setItem(KEY, lang)
  } catch {
    /* storage blocked: the choice lasts for this page view */
  }
  syncDocumentLang()
  listeners.forEach((l) => l())
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

/** {name} placeholders filled from vars; unknown ones stay visible. */
export function fillVars(s: string, vars?: Vars): string {
  return vars ? s.replace(/\{(\w+)\}/g, (m, v: string) => (vars[v] != null ? String(vars[v]) : m)) : s
}

export function translate(lang: Lang, key: StrKey, vars?: Vars): string {
  // a key missing from the dictionary (an enum value the strings do not know) shows the key, never a white page
  const entry = (STR as Record<string, Entry | undefined>)[key]
  return entry ? fillVars(entry[lang], vars) : key
}

/** A bilingual name in the UI language, falling back to the other language when one is empty. */
export function nameIn(o: { th?: string | null; en?: string | null }, lang: Lang): string {
  return (lang === 'en' ? o.en || o.th : o.th || o.en) || ''
}

export interface I18n {
  lang: Lang
  otherLang: Lang
  t: (key: StrKey, vars?: Vars) => string
  pick: (th: string, en: string) => string
  name: (o: Entry) => string
  other: (o: Entry) => string
  setLang: (lang: Lang) => void
}

export function useI18n(): I18n {
  const lang = useSyncExternalStore(subscribe, getLang, (): Lang => 'th')
  return useMemo<I18n>(
    () => ({
      lang,
      otherLang: lang === 'th' ? 'en' : 'th',
      t: (key, vars) => translate(lang, key, vars),
      pick: (th, en) => (lang === 'en' ? en : th),
      name: (o) => nameIn(o, lang),
      other: (o) => (lang === 'en' ? o.th : o.en),
      setLang,
    }),
    [lang],
  )
}

/** A translator over a page's own strings file (lazy pages keep their strings out of the entry chunk). */
export function useStrings<K extends string>(dict: Record<K, Entry>): (key: K, vars?: Vars) => string {
  const { lang } = useI18n()
  return useCallback((key: K, vars?: Vars) => (dict[key] ? fillVars(dict[key][lang], vars) : key), [dict, lang])
}
