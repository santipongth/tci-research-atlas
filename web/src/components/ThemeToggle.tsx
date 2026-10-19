import { useI18n } from '../lib/i18n'
import { setTheme, useTheme } from '../lib/theme'

/** A toggle button: the label stays "Dark mode", aria-pressed says whether it is on. */
export function ThemeToggle() {
  const theme = useTheme()
  const { t } = useI18n()
  const dark = theme === 'dark'
  return (
    <button type="button" className="themebtn" aria-pressed={dark} onClick={() => setTheme(dark ? 'light' : 'dark')}>
      <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
        <path d="M8 1.5a6.5 6.5 0 1 0 0 13 5 5 0 0 1 0-13z" fill="currentColor" />
        <circle cx="8" cy="8" r="6.25" fill="none" stroke="currentColor" strokeWidth="1.5" />
      </svg>
      <span>{t('theme.dark')}</span>
    </button>
  )
}
