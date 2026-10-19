import { useMemo, useSyncExternalStore } from 'react'
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

export function translate(lang: Lang, key: StrKey, vars?: Vars): string {
  const entry: Entry = STR[key]
  const s = entry[lang]
  return vars ? s.replace(/\{(\w+)\}/g, (m, v: string) => (vars[v] != null ? String(vars[v]) : m)) : s
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
      name: (o) => (lang === 'en' ? o.en || o.th : o.th || o.en),
      other: (o) => (lang === 'en' ? o.th : o.en),
      setLang,
    }),
    [lang],
  )
}
