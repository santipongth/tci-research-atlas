import { lazy, Suspense } from 'react'
import { useLocation } from 'react-router'
import { BRAND } from '../brand/brand'
import { PageHeader } from '../components/PageHeader'
import { Section } from '../components/Section'
import { DashGrid } from '../components/dashboard/Card'
import { StatusGlyph } from '../components/StatusGlyph'
import { METHOD } from '../content/method'
import { useRelease } from '../data/atlasContext'
import { DEFINITION, fmtWindow, ruleVars, windows } from '../lib/definition'
import { ciPct } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { STATUSES } from '../lib/status'
import { statusName } from '../lib/topicText'

// "Cite this atlas" (text + BibTeX with copy buttons) loads on demand: this page is in the entry chunk.
const CiteAtlas = lazy(() => import('./about/CiteAtlas'))
// the four-step diagram and the status decision path load on demand too
const PipelineSteps = lazy(() => import('./about/PipelineSteps'))
const StatusDecision = lazy(() => import('./about/StatusDecision'))

/**
 * How the atlas works, then the method in six short cards (the technical detail behind each card's (i)), then what each
 * status means (the decision path and one tile per status), then privacy and the citation. Works without data.
 */
export default function AboutPage() {
  const { t, lang, pick } = useI18n()
  const release = useRelease()
  const location = useLocation()
  // the footer's "cite" link arrives with route state { section: 'cite' }: open the citation straight away
  const citeOpen = (location.state as { section?: unknown } | null)?.section === 'cite'
  const version = release?.definitionVersion ?? DEFINITION.version
  const level = release ? ciPct(release.ciLevel) : 90
  const w = release ? windows(release.overview.last_complete_year) : null
  const vars: Record<string, string> = w
    ? { R: fmtWindow(w.R), B: fmtWindow(w.B), W: fmtWindow(w.W) }
    : { R: t('about.generic.R'), B: t('about.generic.B'), W: t('about.generic.W') }
  const fill = (s: string) => s.replace(/\{(\w+)\}/g, (m, k: string) => vars[k] ?? m)
  return (
    <div className="container">
      <PageHeader title={t('about.title')} lede={t('about.lede')} />
      <div className="prose about">
        <Section id="flow" title={t('about.flow.h')}>
          <Suspense fallback={null}>
            <PipelineSteps release={release} />
          </Suspense>
        </Section>
        <DashGrid>
          {METHOD.map((m) => (
            <Section key={m.id} id={`m-${m.id}`} span={4} title={pick(m.h.th, m.h.en)} intro={m.how ? fill(lang === 'en' ? m.how.en : m.how.th) : undefined}>
              {m.body.map((p, i) => (
                <p key={i}>{fill(lang === 'en' ? p.en : p.th)}</p>
              ))}
            </Section>
          ))}
        </DashGrid>
        <Section id="definition" title={t('about.def.h')} intro={t('about.def.intro', { v: version, level })}>
          <Suspense fallback={null}>
            <StatusDecision level={level} topics={release?.topics ?? []} />
          </Suspense>
          <dl className="defs">
            {STATUSES.map((st) => (
              <div key={st}>
                <dt>
                  <StatusGlyph status={st} size={14} />
                  <span>{statusName(t, st)}</span>
                </dt>
                <dd>{t(`rule.${st}` as const, ruleVars(level))}</dd>
              </div>
            ))}
          </dl>
          <p className="note">{t('rule.how', { level })} {t('about.def.order')}</p>
        </Section>
        <DashGrid>
          <Section id="privacy" span={8} title={t('about.privacy.h')}>
            <p>{t('about.privacy.body')}</p>
            {BRAND.temporary ? <p className="note">{t('wordmarkNote')}</p> : null}
          </Section>
          <Section id="cite" span={4} title={t('about.cite.h')}>
            <details className="how cite-fold" open={citeOpen || undefined}>
              <summary>{t('about.cite.show')}</summary>
              <div>
                <Suspense fallback={<p className="loading" role="status">{t('loading')}</p>}>
                  <CiteAtlas release={release} />
                </Suspense>
              </div>
            </details>
          </Section>
        </DashGrid>
      </div>
    </div>
  )
}
