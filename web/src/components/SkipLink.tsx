import { useI18n } from '../lib/i18n'
import { scrollToId } from '../lib/scroll'

/** A button, not href="#main": under HashRouter an in-page anchor would change the route. */
export function SkipLink() {
  const { t } = useI18n()
  return (
    <button type="button" className="skip" onClick={() => scrollToId('main')}>
      {t('skip')}
    </button>
  )
}
