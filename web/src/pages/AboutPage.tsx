import { BRAND } from '../brand/brand'
import { OnThisPage } from '../components/OnThisPage'
import { PageHeader } from '../components/PageHeader'
import { Section } from '../components/Section'
import { StatusGlyph } from '../components/StatusGlyph'
import { CHANGELOG } from '../content/changelog'
import { METHOD } from '../content/method'
import { useRelease } from '../data/atlasContext'
import { DEFINITION, fmtWindow, windows } from '../lib/definition'
import { ciPct, fmtNum, fmtSignedPct } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { STATUSES } from '../lib/status'
import { statusName } from '../lib/topicText'

/** Plain-language method, the status definition, the forecast rule, privacy and the definition changelog. Works without data. */
export default function AboutPage() {
  const { t, lang, pick } = useI18n()
  const release = useRelease()
  const version = release?.definitionVersion ?? Math.max(...CHANGELOG.map((c) => c.version))
  const level = release ? ciPct(release.ciLevel) : 90
  const w = release ? windows(release.overview.last_complete_year) : null
  const vars: Record<string, string> = w
    ? { R: fmtWindow(w.R), B: fmtWindow(w.B), W: fmtWindow(w.W) }
    : { R: t('about.generic.R'), B: t('about.generic.B'), W: t('about.generic.W') }
  const fill = (s: string) => s.replace(/\{(\w+)\}/g, (m, k: string) => vars[k] ?? m)
  const ruleVars = {
    level,
    bar: fmtSignedPct(DEFINITION.emergingMinGrowthLo, 0),
    ratio: fmtNum(DEFINITION.emergingMinShareRatio, 1),
    dratio: fmtNum(DEFINITION.decliningMaxShareRatio, 1),
    j: DEFINITION.minJournals,
    o: DEFINITION.minOrgs,
    n: DEFINITION.minArticlesRecent,
    y: DEFINITION.recentYears,
  }
  const changes = CHANGELOG.filter((c) => c.version <= version).sort((a, b) => b.version - a.version)
  const toc = [
    ...METHOD.map((m) => ({ id: `m-${m.id}`, label: pick(m.h.th, m.h.en) })),
    { id: 'definition', label: t('about.def.h') },
    { id: 'privacy', label: t('about.privacy.h') },
    { id: 'changelog', label: t('about.log.h') },
  ]
  return (
    <div className="container">
      <PageHeader title={t('about.title')} lede={t('about.lede')} />
      <div className="layout">
        <div className="main-col prose">
          {METHOD.map((m) => (
            <Section key={m.id} id={`m-${m.id}`} title={pick(m.h.th, m.h.en)}>
              {m.body.map((p, i) => (
                <p key={i}>{fill(lang === 'en' ? p.en : p.th)}</p>
              ))}
            </Section>
          ))}
          <Section id="definition" title={t('about.def.h')} intro={t('about.def.intro', { v: version, level })}>
            <dl className="defs">
              {STATUSES.map((st) => (
                <div key={st}>
                  <dt>
                    <StatusGlyph status={st} size={16} />
                    <span>{statusName(t, st)}</span>
                    <code>{st}</code>
                  </dt>
                  <dd>{t(`rule.${st}` as const, ruleVars)}</dd>
                </div>
              ))}
            </dl>
            <p className="note">{t('about.def.order')}</p>
          </Section>
          <Section id="privacy" title={t('about.privacy.h')}>
            <p>{t('about.privacy.body')}</p>
            {BRAND.temporary ? <p className="note">{t('wordmarkNote')}</p> : null}
          </Section>
          <Section id="changelog" title={t('about.log.h')} intro={t('about.log.intro')}>
            <ol className="changelog">
              {changes.map((c) => (
                <li key={c.version}>
                  <p className="log-h">{t('about.log.version', { v: c.version, date: c.date })}</p>
                  <p>{lang === 'en' ? c.en : c.th}</p>
                </li>
              ))}
            </ol>
          </Section>
        </div>
        <aside className="rail" aria-label={t('onThisPage')}>
          <OnThisPage items={toc} />
        </aside>
      </div>
    </div>
  )
}
