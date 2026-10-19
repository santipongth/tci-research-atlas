import { Wordmark } from '../brand/Wordmark'
import { DataBanner } from '../components/DataBanner'
import { SegmentText } from '../components/SegmentText'
import { StatusGlyph } from '../components/StatusGlyph'
import { useAtlas } from '../data/atlasContext'
import type { AtlasRelease } from '../data/release'
import type { Kpis, Topic } from '../data/types'
import { DEFINITION } from '../lib/definition'
import { ciPct, fmtDate, fmtInt, fmtNum, fmtPct, fmtSignedPct, kpiDelta } from '../lib/format'
import { segmentHeadline } from '../lib/highlight'
import { useI18n } from '../lib/i18n'
import { sortBy } from '../lib/sort'
import { STATUSES, type SignalStatus } from '../lib/status'
import { statusName } from '../lib/topicText'
import { useDocumentTitle } from '../lib/useDocumentTitle'
import type { StrKey } from '../strings'

const KPIS: readonly { key: keyof Kpis; label: StrKey; unit: 'count' | 'pct' }[] = [
  { key: 'articles', label: 'kpi.articles', unit: 'count' },
  { key: 'topics', label: 'kpi.topics', unit: 'count' },
  { key: 'journals', label: 'kpi.journals', unit: 'count' },
  { key: 'institutions', label: 'kpi.institutions', unit: 'count' },
  { key: 'pct_abstract_en', label: 'kpi.abstractEn', unit: 'pct' },
]
const TOP = 5

/** E4: one- to two-page A4 executive brief (printed to PDF by `npm run brief:pdf`); every number comes from the release. */
export default function BriefPage() {
  const state = useAtlas()
  const { t } = useI18n()
  useDocumentTitle(t('nav.brief'))
  if (state.status === 'ready') return <Brief release={state.release} />
  return (
    <main id="main" className="brief">
      <h1>{t('nav.brief')}</h1>
      {state.status === 'loading' ? <p className="loading" role="status">{t('loading')}</p> : <DataBanner />}
    </main>
  )
}

function Brief({ release }: { release: AtlasRelease }) {
  const { t, lang, name } = useI18n()
  const ov = release.overview
  const level = ciPct(release.ciLevel)
  const brief = ov.brief
  const headline = brief ? (lang === 'en' ? brief.headline_en : brief.headline_th) : ''
  const bullets = brief ? ((lang === 'en' ? brief.bullets_en : brief.bullets_th) ?? []) : []
  const prev = release.previousOverview
  const top = (st: SignalStatus): Topic[] =>
    sortBy(release.topics.filter((tp) => tp.status === st && tp.metrics.share_growth != null), (tp) => tp.metrics.share_growth, st === 'DECLINING' ? 'asc' : 'desc').slice(0, TOP)
  const tables = (['EMERGING', 'HOT', 'DECLINING'] as const).map((st) => ({ st, rows: top(st) })).filter((g) => g.rows.length > 0)
  const watch = ov.status_counts.WATCH ?? 0
  return (
    <main id="main" className="brief" data-brief-ready="true">
      <header className="brief-head">
        <Wordmark sub={t('brandSub')} lang={lang} />
        <p className="brief-meta">{t('brief.sub', { year: ov.last_complete_year, date: fmtDate(ov.generated_at, lang) })}</p>
      </header>
      <h1>{t('brief.title', { release: ov.release })}</h1>
      {release.sample ? (
        <p className="brief-sample">
          <strong>{t('sample.tag')}</strong> {t('sample.text')}
        </p>
      ) : null}
      {headline ? (
        <p className="headline brief-headline">
          <SegmentText segments={segmentHeadline(headline, release.topics)} />
        </p>
      ) : null}
      <section aria-labelledby="brief-kpi">
        <h2 id="brief-kpi">{t('brief.kpi')}</h2>
        {release.previousMissing ? <p className="note">{t('prev.missing', { prev: release.previousMissing })}</p> : null}
        <table className="t brief-t">
          <thead>
            <tr>
              <th scope="col">{t('brief.kpi')}</th>
              <th scope="col" className="num">{ov.release}</th>
              {prev ? <th scope="col" className="num">{t('delta', { prev: prev.release })}</th> : null}
            </tr>
          </thead>
          <tbody>
            {KPIS.map((k) => (
              <tr key={k.key}>
                <th scope="row">{t(k.label)}</th>
                <td className="num">{k.unit === 'pct' ? `${fmtNum(ov.kpis[k.key], 1)}%` : fmtInt(ov.kpis[k.key])}</td>
                {prev ? <td className="num">{kpiDelta(ov.kpis[k.key], prev.kpis[k.key], k.unit, lang) ?? ''}</td> : null}
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      {bullets.length ? (
        <section aria-labelledby="brief-points">
          <h2 id="brief-points">{t('brief.points')}</h2>
          <ul className="brief-points">
            {bullets.map((b, i) => (
              <li key={i}><SegmentText segments={segmentHeadline(b, release.topics, { figures: false })} mark={false} /></li>
            ))}
          </ul>
        </section>
      ) : null}
      <section aria-labelledby="brief-status">
        <h2 id="brief-status">{t('brief.status')}</h2>
        <p className="brief-counts">
          {STATUSES.map((st) => (
            <span key={st}>
              <StatusGlyph status={st} size={12} /> {statusName(t, st)} {fmtInt(ov.status_counts[st] ?? 0)}
            </span>
          ))}
        </p>
        {watch > 0 ? <p className="note">{t('brief.watch', { n: fmtInt(watch) })}</p> : null}
        {tables.map(({ st, rows }) => (
          <table key={st} className="t brief-t">
            <caption>
              <StatusGlyph status={st} size={12} /> {t('brief.top', { status: statusName(t, st), n: rows.length })}
            </caption>
            <thead>
              <tr>
                <th scope="col">{t('col.topic')}</th>
                <th scope="col" className="num">{t('col.share')}</th>
                <th scope="col" className="num">{t('col.growth')}</th>
                <th scope="col" className="num">{t('ciShort', { level })}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((tp) => (
                <tr key={tp.id}>
                  <th scope="row">{name(tp)}</th>
                  <td className="num">{fmtPct(tp.metrics.share_recent, 2)}</td>
                  <td className="num">{fmtSignedPct(tp.metrics.share_growth)}</td>
                  <td className="num">{fmtSignedPct(tp.metrics.share_growth_lo, 0)} {t('to')} {fmtSignedPct(tp.metrics.share_growth_hi, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ))}
      </section>
      <footer className="brief-foot">
        <p>{t('brief.def', { v: release.definitionVersion, level, bar: fmtSignedPct(DEFINITION.emergingMinGrowthLo, 0) })}</p>
        <p>{t('source.line', { release: ov.release, v: release.definitionVersion })}</p>
        <p>{t('brief.more')} · {t('footer.licence')}</p>
      </footer>
      <p className="no-print mt-6">
        <button type="button" className="btn" onClick={() => window.print()}>{t('brief.print')}</button>
      </p>
    </main>
  )
}
