import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { DataTable, type Column } from '../components/DataTable'
import { EmptyState } from '../components/EmptyState'
import { Figure } from '../components/Figure'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { StatusGlyph } from '../components/StatusGlyph'
import { TopicSearch } from '../components/TopicSearch'
import { MultiLineChart, type LineSeries } from '../charts/MultiLineChart'
import { assignSlots, SERIES_DASHES } from '../charts/series'
import { groupName, seriesOf, type AtlasRelease } from '../data/release'
import type { Topic } from '../data/types'
import { ciPct, fmtCompact, fmtInt, fmtPct } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { sortBy } from '../lib/sort'
import { compareCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import { ciColumn, growthColumn, idColumn, journalsColumn, orgsColumn, shareColumn, statusColumn, topicColumn, type ColumnContext } from './topicColumns'

export default function ComparePage() {
  const { t } = useI18n()
  return <RequireRelease title={t('cmp.title')}>{(release) => <Compare release={release} />}</RequireRelease>
}

interface YearRow {
  year: number
  values: (number | null)[]
}

function Swatch({ slot }: { slot: number }) {
  return (
    <svg className="cmp-swatch" width="28" height="10" aria-hidden="true" focusable="false">
      <line x1="0" x2="28" y1="5" y2="5" style={{ stroke: `var(--series-${slot + 1})` }} strokeWidth="3" strokeDasharray={SERIES_DASHES[slot]} />
    </svg>
  )
}

function Compare({ release }: { release: AtlasRelease }) {
  const { t, name, lang } = useI18n()
  const [state, update] = useUrlState(compareCodec)
  // slots the visitor has already seen, so removing a topic never repaints the others
  const [seenSlots, setSeenSlots] = useState<Record<string, number>>({})
  const chosen = state.ids.map((id) => release.topicById.get(id)).filter((tp): tp is Topic => tp !== undefined)
  const slots = assignSlots(chosen.map((tp) => tp.id), seenSlots)
  const years = release.series.years
  const totals = release.series.corpus_total
  const share = state.metric === 'share'
  const series: LineSeries[] = chosen.map((tp) => {
    const counts = seriesOf(release, tp.id)
    return {
      id: tp.id,
      label: name(tp),
      slot: slots[tp.id],
      // no series for the topic → a gap, never a line of zeros
      values: years.map((_, i) => (counts === null ? null : share ? (totals[i] ? (counts[i] ?? 0) / totals[i] : null) : (counts[i] ?? null))),
    }
  })
  const format = (v: number) => (share ? fmtPct(v, 2) : fmtInt(v))
  const axisFormat = (v: number) => (share ? fmtPct(v, v > 0 && v < 0.01 ? 1 : 0) : fmtCompact(v))
  const setIds = (ids: string[]) => {
    setSeenSlots(assignSlots(ids, slots))
    update({ ids })
  }
  const known = state.ids.filter((id) => release.topicById.has(id))
  // Where keyboard focus goes once the changed chip list has rendered (the focused control may be unmounted or disabled).
  const focusNext = useRef<number | 'hint' | null>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const hintRef = useRef<HTMLParagraphElement>(null)
  const add = (id: string) => {
    const next = [...known.filter((x) => x !== id), id].slice(0, 4)
    if (next.length >= 4) focusNext.current = 'hint'
    setIds(next)
  }
  const remove = (id: string) => {
    const left = known.filter((x) => x !== id)
    focusNext.current = Math.min(known.indexOf(id), left.length - 1)
    setIds(left)
  }
  const idsKey = state.ids.join(',')
  useEffect(() => {
    const target = focusNext.current
    if (target === null) return
    focusNext.current = null
    if (target === 'hint') hintRef.current?.focus()
    else if (target < 0) document.getElementById('cmp-search')?.focus()
    else listRef.current?.querySelectorAll<HTMLButtonElement>('.cmp-remove')[target]?.focus()
  }, [idsKey])
  const suggestions = sortBy(release.topics.filter((tp) => (tp.status === 'EMERGING' || tp.status === 'HOT') && !state.ids.includes(tp.id)), (tp) => tp.score, 'desc').slice(0, 3)
  const ctx: ColumnContext = { t, name, groupName: (g) => groupName(release, g, lang) }
  const rows: YearRow[] = years.map((year, i) => ({ year, values: series.map((s) => s.values[i] ?? null) }))
  const yearColumns: Column<YearRow>[] = [
    { key: 'year', header: t('col.year'), rowHeader: true, cell: (r) => String(r.year), csv: (r) => r.year },
    ...series.map((s, k) => ({ key: s.id, header: s.label, numeric: true, cell: (r: YearRow) => (r.values[k] === null ? '–' : format(r.values[k] as number)), csv: (r: YearRow) => r.values[k] })),
  ]
  const figTitle = t(share ? 'cmp.fig.share' : 'cmp.fig.count', { a: years[0] ?? '', b: years[years.length - 1] ?? '' })
  return (
    <div className="container">
      <PageHeader title={t('cmp.title')} lede={t('cmp.lede')} />
      <div className="cmp-picker">
        <TopicSearch id="cmp-search" label={t('cmp.add')} onPick={add} exclude={state.ids} disabled={chosen.length >= 4} />
        {chosen.length >= 4 ? <p className="hint" ref={hintRef} tabIndex={-1}>{t('cmp.max')}</p> : null}
        {chosen.length ? (
          <ul className="cmp-chips" ref={listRef} aria-label={t('cmp.chosen')}>
            {chosen.map((tp) => (
              <li key={tp.id} className="cmp-chip">
                <Swatch slot={slots[tp.id]} />
                <StatusGlyph status={tp.status} size={12} />
                <Link to={`/topics/${tp.id}`}>{name(tp)}</Link>
                <button type="button" className="cmp-remove" aria-label={t('cmp.remove', { n: name(tp) })} onClick={() => remove(tp.id)}>
                  <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" focusable="false"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="2" /></svg>
                </button>
              </li>
            ))}
          </ul>
        ) : null}
        <fieldset className="cmp-metric">
          <legend>{t('cmp.metric')}</legend>
          <label>
            <input type="radio" name="cmp-metric" checked={share} onChange={() => update({ metric: 'share' })} />
            <span>{t('cmp.metric.share')}</span>
          </label>
          <label>
            <input type="radio" name="cmp-metric" checked={!share} onChange={() => update({ metric: 'count' })} />
            <span>{t('cmp.metric.count')}</span>
          </label>
        </fieldset>
      </div>
      {chosen.length < 2 ? (
        <EmptyState title={t('cmp.needTwo')}>
          {suggestions.length ? (
            <>
              <p>{t('cmp.try')}</p>
              <ul className="cmp-suggest">
                {suggestions.map((tp) => (
                  <li key={tp.id}>
                    <button type="button" className="btn-secondary" onClick={() => add(tp.id)}>
                      <StatusGlyph status={tp.status} size={12} />
                      {name(tp)}
                    </button>
                  </li>
                ))}
              </ul>
            </>
          ) : null}
        </EmptyState>
      ) : (
        <>
          <Section id="cmp-trend" title={t('cmp.chart.h')}>
            <Figure
              id="fig-cmp"
              number={1}
              title={figTitle}
              source={t('source.line', { release: release.overview.release, v: release.definitionVersion })}
              view={state.view}
              onView={(view) => update({ view })}
              legend={
                <div className="legend">
                  {series.map((s, k) => (
                    <span key={s.id}>
                      <Swatch slot={s.slot ?? k} />
                      {s.label}
                    </span>
                  ))}
                </div>
              }
              chart={<MultiLineChart years={years} series={series} format={format} axisFormat={axisFormat} label={figTitle} />}
              table={
                <DataTable
                  caption={t('table.n', { n: 1, title: t('cmp.table') })}
                  rows={rows}
                  columns={yearColumns}
                  rowKey={(r) => String(r.year)}
                  stack={false}
                  csvFilename={`atlas-${release.overview.release}-compare-${state.metric}.csv`}
                />
              }
              note={<p className="note">{t('cmp.how')}</p>}
            />
          </Section>
          <Section id="cmp-figures" title={t('cmp.metrics.h')}>
            <DataTable
              caption={t('table.n', { n: 2, title: t('cmp.metrics.table') })}
              rows={chosen}
              columns={[idColumn(), topicColumn(ctx), statusColumn(ctx), shareColumn(ctx), growthColumn(ctx), ciColumn(ctx, ciPct(release.ciLevel)), journalsColumn(ctx), orgsColumn(ctx)]}
              rowKey={(r) => r.id}
              csvFilename={`atlas-${release.overview.release}-compare-figures.csv`}
            />
          </Section>
        </>
      )}
    </div>
  )
}
