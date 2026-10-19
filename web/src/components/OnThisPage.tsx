import { useI18n } from '../lib/i18n'
import { scrollToId } from '../lib/scroll'

/** "ในหน้านี้" rail: buttons, because in-page href="#…" would change the HashRouter route. */
export function OnThisPage({ items }: { items: readonly { id: string; label: string }[] }) {
  const { t } = useI18n()
  if (items.length === 0) return null
  return (
    <nav className="toc" aria-labelledby="toc-h">
      <h2 id="toc-h">{t('onThisPage')}</h2>
      <ol>
        {items.map((it) => (
          <li key={it.id}>
            <button type="button" className="linkbtn" onClick={() => scrollToId(it.id)}>{it.label}</button>
          </li>
        ))}
      </ol>
    </nav>
  )
}
