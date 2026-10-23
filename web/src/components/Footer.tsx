import { BRAND, PARTNERS } from '../brand/brand'
import { useI18n } from '../lib/i18n'

/** The site footer: who produces the Atlas (the partner logos, centred) and one licence line. The release itself is
 *  named at the top of each page, so the footer does not repeat it. */
export function Footer() {
  const { t, lang } = useI18n()
  return (
    <footer className="ftr">
      <div className="container">
        <div className="ftr-partners">
          <p>{t('footer.partners')}</p>
          <div className="ftr-logos">
            {PARTNERS.map((p) => (
              <img key={p.alt.en} src={p.src} alt={p.alt[lang]} width={p.width} height={p.height} loading="lazy" decoding="async" />
            ))}
          </div>
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
