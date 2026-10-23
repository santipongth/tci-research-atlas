import { Link } from 'react-router'
import { BRAND, PARTNERS } from '../brand/brand'
import { useRelease } from '../data/atlasContext'
import { useI18n } from '../lib/i18n'
import type { StrKey } from '../strings'

/** Four plain next steps. "Cite" opens /about and scrolls to its cite section (route state, never href="#id"). */
const NEXT: readonly { to: string; state?: { section: string }; key: StrKey; hint: StrKey }[] = [
  { to: '/about', state: { section: 'cite' }, key: 'footer.cite', hint: 'footer.citeHint' },
  { to: '/data', key: 'footer.download', hint: 'footer.downloadHint' },
  { to: '/changes', key: 'footer.prev', hint: 'footer.prevHint' },
  { to: '/about', key: 'footer.read', hint: 'footer.readHint' },
]

export function Footer() {
  const { t, lang } = useI18n()
  const release = useRelease()
  return (
    <footer className="ftr">
      <div className="container">
        <h2>{t('footer.nextH')}</h2>
        <ul className="ftr-next">
          {NEXT.map((n) => (
            <li key={n.key}>
              <Link to={n.to} state={n.state}>{t(n.key)}</Link>
              <span>{t(n.hint)}</span>
            </li>
          ))}
        </ul>
        <div className="ftr-about">
          <p>{t('footer.about')}</p>
          {release ? (
            <p className="small">
              {t('footer.release', { release: release.overview.release, year: release.overview.last_complete_year, v: release.definitionVersion })}
            </p>
          ) : null}
        </div>
      </div>
      <div className="container">
        <div className="ftr-partners">
          <p>{t('footer.partners')}</p>
          {PARTNERS.map((p) => (
            <img key={p.alt.en} src={p.src} alt={p.alt[lang]} width={p.width} height={p.height} loading="lazy" decoding="async" />
          ))}
        </div>
        <div className="licence">
          <span>{t('footer.licence')}</span>
          <span>{t('footer.privacy')}</span>
          {BRAND.temporary ? <span>{t('wordmarkNote')}</span> : null}
        </div>
      </div>
    </footer>
  )
}
