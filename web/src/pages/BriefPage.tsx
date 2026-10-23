import { useState } from 'react'
import { Wordmark } from '../brand/Wordmark'
import { DataTable } from '../components/DataTable'
import { Figure } from '../components/Figure'
import { SegmentText } from '../components/SegmentText'
import { DotPlot } from '../charts/DotPlot'
import { topMovers } from '../charts/infographic'
import { useAtlas } from '../data/atlasContext'
import { groupName, type AtlasRelease } from '../data/release'
import { DEFINITION } from '../lib/definition'
import { pickFindings } from '../lib/findings'
import { ciPct, fmtDate, fmtInt, fmtSignedPct } from '../lib/format'
import { segmentHeadline } from '../lib/highlight'
import { useI18n } from '../lib/i18n'
import { hasCi } from '../lib/forest'
import { useDocumentTitle } from '../lib/useDocumentTitle'
import type { View } from '../lib/urlState'
import { FindingCards } from './overview/FindingCards'
import { KpiGrid } from './overview/KpiGrid'
import { StatusMix } from './overview/StatusMix'
import { ciColumn, growthColumn, statusColumn, topicColumn, columnContext } from './topicColumns'

const UP = 4
const DOWN = 3

/**
 * E4: a one-page A4 infographic brief (two pages at most; printed to PDF by `npm run brief:pdf`): headline, four key
 * figures, three findings, every topic by status, the top movers as a dot plot, the policy notes and the source.
 * Every number comes from the release. On screen it is an ordinary page of the site (inside the layout, which shows
 * the data banner when the release cannot load); printing hides the site chrome and shows the brief's own wordmark.
 */
export default function BriefPage() {
  const state = useAtlas()
  const { t } = useI18n()
  useDocumentTitle(t('nav.brief'))
  if (state.status === 'ready') return <Brief release={state.release} />
  return (
    <div className="container brief">
      <h1>{t('nav.brief')}</h1>
      {state.status === 'loading' ? <p className="loading" role="status">{t('loading')}</p> : null}
    </div>
  )
}

function Brief({ release }: { release: AtlasRelease }) {
  const { t, lang, name } = useI18n()
  const [views, setViews] = useState<{ wf: View; mv: View }>({ wf: 'chart', mv: 'chart' })
  const ov = release.overview
  const level = ciPct(release.ciLevel)
  const bar = fmtSignedPct(DEFINITION.emergingMinGrowthLo, 0)
  const brief = ov.brief
  const headline = brief ? (lang === 'en' ? brief.headline_en : brief.headline_th) : ''
  const bullets = brief ? ((lang === 'en' ? brief.bullets_en : brief.bullets_th) ?? []) : []
  const exec = ov.executive ? ((lang === 'en' ? ov.executive.bullets_en : ov.executive.bullets_th) ?? []) : []
  const findings = pickFindings(release.topics)
  const movers = topMovers(release.topics, UP, DOWN)
  const nUp = movers.filter((tp) => (tp.metrics.share_growth ?? 0) > 0).length
  const watch = ov.status_counts.WATCH ?? 0
  const ctx = columnContext(release, { t, name, lang })
  const moverCols = [topicColumn(ctx), statusColumn(ctx), growthColumn(ctx), ciColumn(ctx)]
  const moversTable = t('table.n', { n: 2, title: t('brief.movers.table') })
  const source = t('source.line', { release: ov.release })
  return (
    <div className="container brief" data-brief-ready="true">
      <header className="brief-head">
        <Wordmark sub={t('brandSub')} lang={lang} />
        <p className="brief-meta">{t('brief.sub', { year: ov.last_complete_year, date: fmtDate(ov.generated_at, lang) })}</p>
      </header>
      <h1>{t('brief.title', { release: ov.release })}</h1>
      <p className="brief-acts no-print">
        <button type="button" className="btn-secondary" onClick={() => window.print()}>
          <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">
            <path d="M4 6V1.5h8V6 M4 12H2.5V6h11v6H12 M4 9.5h8v5H4z" fill="none" stroke="currentColor" strokeWidth="1.4" />
          </svg>
          {t('brief.print')}
        </button>
      </p>
      {release.sample ? (
        <p className="brief-sample">
          <strong>{t('sample.tag')}</strong> {t('sample.text')}
        </p>
      ) : null}
      {headline ? (
        <p className="headline brief-headline">
          <SegmentText segments={segmentHeadline(headline, release.topics)} links={false} />
        </p>
      ) : null}
      <section aria-labelledby="brief-kpi">
        <h2 id="brief-kpi">{t('brief.kpi')}</h2>
        {release.previousMissing ? <p className="note">{t('prev.missing', { prev: release.previousMissing })}</p> : null}
        <KpiGrid release={release} more={false} />
      </section>
      {findings.length ? (
        <section aria-labelledby="brief-find">
          <h2 id="brief-find">{findings.length === 3 ? t('ov.fc.h3') : t('ov.findings.h')}</h2>
          <FindingCards release={release} findings={findings} />
        </section>
      ) : null}
      {bullets.length ? (
        <section aria-labelledby="brief-points">
          <h2 id="brief-points">{t('brief.points')}</h2>
          <ul className="brief-points">
            {bullets.map((b, i) => (
              <li key={i}><SegmentText segments={segmentHeadline(b, release.topics, { figures: false })} mark={false} links={false} /></li>
            ))}
          </ul>
        </section>
      ) : null}
      {release.topics.length ? (
        <section aria-labelledby="brief-status" className="brief-p2">
          <h2 id="brief-status">{t('brief.status')}</h2>
          <StatusMix release={release} number={1} tableNo={1} view={views.wf} onView={(wf) => setViews((v) => ({ ...v, wf }))} compact />
          {watch > 0 ? <p className="note">{t('brief.watch', { n: fmtInt(watch) })}</p> : null}
          {movers.length ? (
            <Figure
              id="fig-movers"
              number={2}
              title={t('brief.movers.title', { up: nUp, down: movers.length - nUp })}
              tableTitle={moversTable}
              how={<p>{t('brief.movers.how', { bar, level })}</p>}
              source={source}
              view={views.mv}
              onView={(mv) => setViews((v) => ({ ...v, mv }))}
              chart={
                <DotPlot
                  rows={movers.map((tp) => ({
                    id: tp.id,
                    label: name(tp),
                    sub: groupName(release, tp.group, lang),
                    status: tp.status,
                    value: tp.metrics.share_growth ?? 0,
                    text: `${fmtSignedPct(tp.metrics.share_growth, 0)} ${t('perYear')}`,
                    ci: hasCi(tp) ? t('ciRange', { lo: fmtSignedPct(tp.metrics.share_growth_lo, 0), hi: fmtSignedPct(tp.metrics.share_growth_hi, 0) }) : null,
                    href: `/topics/${tp.id}`,
                  }))}
                  axisLabel={t('ov.forest.axis')}
                  tick={(v) => (v === 0 ? '0%' : fmtSignedPct(v, 0))}
                  refValue={DEFINITION.emergingMinGrowthLo}
                  refLabel={t('ov.forest.bar', { v: bar })}
                />
              }
              table={<DataTable caption={moversTable} rows={movers} columns={moverCols} rowKey={(r) => r.id} stack={false} />}
            />
          ) : null}
        </section>
      ) : null}
      {exec.length ? (
        <section aria-labelledby="brief-exec">
          <h2 id="brief-exec">{t('brief.exec')}</h2>
          <ol className="policy-list">
            {exec.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ol>
          <p className="policy-note">{t('brief.execNote')}</p>
        </section>
      ) : null}
      <footer className="brief-foot">
        <p>{t('brief.def', { v: release.definitionVersion, level, bar })}</p>
        <p>{source} · {t('source.def', { v: release.definitionVersion })}</p>
        <p>{t('brief.more')} · {t('footer.licence')}</p>
      </footer>
    </div>
  )
}
