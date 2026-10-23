import { useI18n } from '../lib/i18n'
import { scrollToId } from '../lib/scroll'
import { COMPACT_CHROME, useMediaQuery } from '../lib/useMediaQuery'

/** "ในหน้านี้" rail: buttons, because in-page href="#…" would change the HashRouter route.
 * Under 900 px the rail sits above the content, so the list folds into one closed disclosure row. */
export function OnThisPage({ items }: { items: readonly { id: string; label: string }[] }) {
  const { t } = useI18n()
  const compact = useMediaQuery(COMPACT_CHROME)
  if (items.length === 0) return null
  const list = (
    <ol>
      {items.map((it) => (
        <li key={it.id}>
          <button type="button" className="linkbtn" onClick={() => scrollToId(it.id)}>{it.label}</button>
        </li>
      ))}
    </ol>
  )
  if (compact) {
    return (
      <nav className="toc" aria-label={t('onThisPage')}>
        <details className="toc-d">
          <summary>
            <span>{t('onThisPage')}</span>
            <svg viewBox="0 0 12 8" aria-hidden="true" focusable="false">
              <path d="M1 1.5l5 5 5-5" fill="none" stroke="currentColor" strokeWidth="1.8" />
            </svg>
          </summary>
          {list}
        </details>
      </nav>
    )
  }
  return (
    <nav className="toc" aria-labelledby="toc-h">
      <h2 id="toc-h">{t('onThisPage')}</h2>
      {list}
    </nav>
  )
}
