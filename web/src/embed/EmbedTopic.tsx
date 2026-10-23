import { useState } from 'react'
import { useParams } from 'react-router'
import { TrendChart } from '../charts/TrendChart'
import { DataTable } from '../components/DataTable'
import { Figure } from '../components/Figure'
import { StatusChip } from '../components/StatusGlyph'
import { seriesOf, type AtlasRelease } from '../data/release'
import type { Topic } from '../data/types'
import { forecastView } from '../lib/forecast'
import { DASH, fmtInt, fmtShare } from '../lib/format'
import { useDocumentTitle } from '../lib/useDocumentTitle'
import { useI18n, useStrings } from '../lib/i18n'
import { growthText, statusName } from '../lib/topicText'
import type { View } from '../lib/urlState'
import { embed } from '../strings/embed'
import { EmbedFrame } from './EmbedFrame'

/** /embed/topic/:id — one topic's title, status (glyph + colour + name) and yearly trend, for an <iframe>. */
export default function EmbedTopic() {
  const { id = '' } = useParams()
  return (
    <EmbedFrame full={(release) => (release?.topicById.has(id) ? `/topics/${id}` : '/overview')}>
      {(release) => {
        const topic = release.topicById.get(id)
        return topic ? <TopicWidget key={topic.id} release={release} topic={topic} /> : <NotFound id={id} />
      }}
    </EmbedFrame>
  )
}

function NotFound({ id }: { id: string }) {
  const s = useStrings(embed)
  const title = id ? s('nf.title', { id }) : s('nf.page')
  useDocumentTitle(title)
  return (
    <div className="embed-nf">
      <h1 className="embed-h">{title}</h1>
      {id ? <p>{s('nf.body')}</p> : null}
    </div>
  )
}

interface Row {
  year: number
  forecast: boolean
  articles: number | null
  share: number | null
  mean: number | null
}

function TopicWidget({ release, topic }: { release: AtlasRelease; topic: Topic }) {
  const { t, name, lang } = useI18n()
  const [view, setView] = useState<View>('chart')
  useDocumentTitle(name(topic))
  const years = release.series.years
  const counts = seriesOf(release, topic.id) ?? []
  const fc = forecastView(topic.status, topic.forecast ?? null) === 'show' ? (topic.forecast ?? null) : null
  const nowcast = topic.nowcast ?? null
  const title = years.length ? t('tp.trend.title', { a: years[0], b: years[years.length - 1] }) : t('tp.trend.h')
  const rows: Row[] = [
    ...years.map((year, i) => ({
      year, forecast: false, articles: counts[i] ?? 0,
      share: release.series.corpus_total[i] ? (counts[i] ?? 0) / release.series.corpus_total[i] : null, mean: null,
    })),
    ...(fc ? fc.years.map((year, i) => ({ year, forecast: true, articles: null, share: null, mean: fc.mean[i] })) : []),
  ]
  return (
    <article className="embed-topic">
      <h1 className="embed-h" lang={lang === 'en' && !topic.en ? 'th' : undefined}>{name(topic)}</h1>
      <p className="embed-status">
        <StatusChip status={topic.status} label={statusName(t, topic.status)} />
        <span>{growthText(t, topic.metrics)}</span>
      </p>
      {counts.length ? (
        <Figure
          id="embed-trend"
          number={1}
          title={title}
          source={t('source.line', { release: release.overview.release })}
          view={view}
          onView={setView}
          legend={
            <div className="legend">
              <span><i className="lg-line" aria-hidden="true" />{t('actual')}</span>
              {fc ? <span><i className="lg-line is-dashed" aria-hidden="true" />{t('forecast')}</span> : null}
              {fc ? <span><i className="lg-band" aria-hidden="true" />{t('tp.legend.band')}</span> : null}
            </div>
          }
          chart={
            <TrendChart
              status={topic.status}
              years={years}
              counts={counts}
              forecast={fc}
              nowcast={nowcast}
              labels={{ name: `${title} · ${name(topic)}`, forecast: t('forecast'), articles: t('col.articles'), range80: (lo, hi) => t('tp.range80', { lo, hi }) }}
            />
          }
          table={
            <DataTable
              caption={t('table.n', { n: 1, title: t('tp.trend.table') })}
              rows={rows}
              rowKey={(r) => `${r.forecast ? 'f' : 'a'}-${r.year}`}
              stack={false}
              csvFilename={`atlas-${release.overview.release}-${topic.id}-trend.csv`}
              columns={[
                { key: 'year', csvHeader: 'year', header: t('col.year'), rowHeader: true, cell: (r) => (r.forecast ? t('tp.forecastYear', { year: r.year }) : String(r.year)), csv: (r) => r.year },
                { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (r) => (r.articles === null ? DASH : fmtInt(r.articles)), csv: (r) => r.articles },
                { key: 'share', csvHeader: 'share_of_year', header: t('tp.col.shareOfYear'), numeric: true, cell: (r) => (r.share === null ? DASH : fmtShare(r.share, 2)), csv: (r) => r.share },
                ...(fc ? [{ key: 'mean', csvHeader: 'forecast_mean', header: t('forecast'), numeric: true, cell: (r: Row) => (r.mean === null ? DASH : fmtInt(r.mean)), csv: (r: Row) => r.mean }] : []),
              ]}
            />
          }
        />
      ) : (
        <p className="note">{t('tp.noSeries')}</p>
      )}
    </article>
  )
}
