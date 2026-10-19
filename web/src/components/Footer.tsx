import { Link } from 'react-router'
import { BRAND } from '../brand/brand'
import { useI18n } from '../lib/i18n'

export function Footer() {
  const { t } = useI18n()
  return (
    <footer className="ftr">
      <div className="container ftr-grid">
        <div>
          <h2>{t('footer.aboutH')}</h2>
          <p>{t('footer.about')}</p>
        </div>
        <div>
          <h2>{t('footer.moreH')}</h2>
          <ul>
            <li><Link to="/about">{t('nav.about')}</Link></li>
            <li><Link to="/data">{t('nav.data')}</Link></li>
          </ul>
        </div>
      </div>
      <div className="container licence">
        <span>{t('footer.licence')}</span>
        <span>{t('footer.privacy')}</span>
        {BRAND.temporary ? <span>{t('wordmarkNote')}</span> : null}
      </div>
    </footer>
  )
}
