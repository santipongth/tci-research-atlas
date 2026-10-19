import { Link } from 'react-router'
import { BRAND } from '../brand/brand'
import { useRelease } from '../data/atlasContext'
import { useI18n } from '../lib/i18n'

export function Footer() {
  const { t } = useI18n()
  const release = useRelease()
  return (
    <footer className="ftr">
      <div className="container ftr-grid">
        <div>
          <h2>{t('footer.aboutH')}</h2>
          <p>{t('footer.about')}</p>
          {release ? (
            <p className="small">
              {t('footer.release', { release: release.overview.release, year: release.overview.last_complete_year, v: release.definitionVersion })}
            </p>
          ) : null}
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
