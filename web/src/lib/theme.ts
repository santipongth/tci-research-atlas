export type Theme = 'light' | 'dark'

/** The site has one light theme (owner's ruling 2026-10-23). Canvas code still asks, so a theme can return later. */
export function useTheme(): Theme {
  return 'light'
}
