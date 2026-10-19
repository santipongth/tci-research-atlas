import { useSyncExternalStore } from 'react'

export type Theme = 'light' | 'dark'

const KEY = 'atlas-theme'
const listeners = new Set<() => void>()
const media = typeof window !== 'undefined' && typeof window.matchMedia === 'function' ? window.matchMedia('(prefers-color-scheme: dark)') : null
media?.addEventListener('change', () => listeners.forEach((l) => l()))

/** The explicit choice (data-theme, set before first paint by index.html) or else the OS preference. */
export function currentTheme(): Theme {
  const chosen = typeof document !== 'undefined' ? document.documentElement.getAttribute('data-theme') : null
  if (chosen === 'light' || chosen === 'dark') return chosen
  return media?.matches ? 'dark' : 'light'
}

export function setTheme(theme: Theme): void {
  document.documentElement.setAttribute('data-theme', theme)
  try {
    window.localStorage.setItem(KEY, theme)
  } catch {
    /* storage blocked: the choice lasts for this page view */
  }
  listeners.forEach((l) => l())
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function useTheme(): Theme {
  return useSyncExternalStore(subscribe, currentTheme, (): Theme => 'light')
}
