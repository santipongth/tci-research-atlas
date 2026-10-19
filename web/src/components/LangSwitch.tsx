import { useI18n } from '../lib/i18n'

export function LangSwitch() {
  const { lang, setLang, t } = useI18n()
  return (
    <div className="langsw" role="group" aria-label={t('langGroup')}>
      <button type="button" lang="th" aria-pressed={lang === 'th'} onClick={() => setLang('th')}>
        ไทย
      </button>
      <button type="button" lang="en" aria-pressed={lang === 'en'} onClick={() => setLang('en')}>
        English
      </button>
    </div>
  )
}
