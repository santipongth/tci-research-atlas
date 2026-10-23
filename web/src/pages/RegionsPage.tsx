import { BarRank } from '../charts/BarRank'
import { rankBars } from '../charts/infographic'
import { DataTable, type Column } from '../components/DataTable'
import { Figure } from '../components/Figure'
import { InstitutionLink } from '../components/InstitutionLink'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { ProvinceMap } from '../components/ProvinceMap'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { ShareBar } from '../components/ShareBar'
import { useReleaseFile } from '../data/atlasContext'
import { hasModule, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { InstitutionsFile, ProvinceStat, RegionStat, RegionsFile } from '../data/types'
import { fmtWindow, windows } from '../lib/definition'
import { DASH, fmtInt, fmtNum, fmtPct, fmtShare } from '../lib/format'
import { useI18n, useStrings } from '../lib/i18n'
import { figureCsv } from '../lib/tableCsv'
import { REGION_METRICS, regionsCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import { execViz } from '../strings/execViz'
import { execPages } from '../strings/execPages'

/** Provinces listed beside the map. */
const TOP_N = 10

export default function RegionsPage() {
  const sx = useStrings(execPages)
  return (
    <RequireRelease title={sx('rg.title')}>
      {(release) => (
        <ModuleFile<RegionsFile> release={release} module="regions" path={MODULE_FILES.regions} title={sx('rg.title')}>
          {(file) => <Regions release={release} file={file} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

function Regions({ release, file }: { release: AtlasRelease; file: RegionsFile }) {
  const { t, lang } = useI18n()
  const sx = useStrings(execPages)
  const x = useStrings(execViz)
  const [state, update] = useUrlState(regionsCodec)
  const instFile = useReleaseFile<InstitutionsFile>(hasModule(release, 'institutions') ? MODULE_FILES.institutions : null)
  const insts = new Map(instFile.status === 'ready' ? instFile.data.institutions.map((i) => [i.id, i]) : [])
  const hasPop = file.provinces.some((p) => p.per_100k != null)
  const metric = hasPop ? state.m : 'articles'
  const valueOf = (p: ProvinceStat): number | null => (metric === 'per100k' ? (p.per_100k ?? null) : p.articles)
  const format = (v: number) => (metric === 'per100k' ? fmtNum(v, 1) : fmtInt(v))
  const measure = sx(metric === 'per100k' ? 'rg.metric.per100k' : 'rg.metric.articles')
  const pname = (p: ProvinceStat) => (lang === 'en' ? p.name_en : p.name_th)
  const maxShare = Math.max(0.0001, ...file.provinces.map((p) => p.share ?? 0))
  const w = file.window
  const topProv = file.provinces.reduce<ProvinceStat | null>((m, p) => (m === null || p.articles > m.articles ? p : m), null)
  const rel = release.overview.release
  const columns: Column<ProvinceStat>[] = [
    { key: 'name', csvHeader: 'province', header: sx('in.col.province'), rowHeader: true, cell: pname, sortValue: pname, csv: (p) => p.code },
    { key: 'region', csvHeader: 'region', header: sx('rg.col.region'), cell: (p) => sx(`rg.region.${p.region}` as keyof typeof execPages), sortValue: (p) => p.region, csv: (p) => p.region },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (p) => fmtInt(p.articles), sortValue: (p) => p.articles },
    { key: 'share', csvHeader: 'share', header: sx('rg.col.share'), numeric: true, cell: (p) => <ShareBar value={p.share} digits={1} max={maxShare} />, sortValue: (p) => p.share ?? null },
    { key: 'recent', csvHeader: 'articles_recent', header: sx('in.col.recent', { r: fmtWindow(windows(release.overview.last_complete_year).R) }), numeric: true, cell: (p) => fmtInt(p.articles_recent ?? null), sortValue: (p) => p.articles_recent ?? null },
    { key: 'institutions', csvHeader: 'institutions', header: sx('rg.col.institutions'), numeric: true, cell: (p) => fmtInt(p.institutions ?? null), sortValue: (p) => p.institutions ?? null },
    ...(hasPop ? [{ key: 'per100k', csvHeader: 'per_100k', header: sx('rg.col.per100k'), numeric: true, cell: (p: ProvinceStat) => fmtNum(p.per_100k ?? null, 1), sortValue: (p: ProvinceStat) => p.per_100k ?? null }] : []),
    {
      key: 'top', csvHeader: 'top_institutions', header: sx('rg.col.top'),
      cell: (p) => {
        const top = (p.top ?? []).map((id) => insts.get(id)).filter((i) => i !== undefined)
        return top.length ? <span className="pair">{top.map((i) => <InstitutionLink key={i.id} inst={i} />)}</span> : DASH
      },
      csv: (p) => (p.top ?? []).join(';'),
    },
  ]
  const regionColumns: Column<RegionStat>[] = [
    { key: 'name', csvHeader: 'region', header: sx('rg.col.region'), rowHeader: true, cell: (r) => sx(`rg.region.${r.key}` as keyof typeof execPages), csv: (r) => r.key },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (r) => fmtInt(r.articles), sortValue: (r) => r.articles },
    { key: 'share', csvHeader: 'share', header: sx('rg.col.share'), numeric: true, cell: (r) => fmtShare(r.share ?? null, 1), sortValue: (r) => r.share ?? null },
  ]
  const top = rankBars(
    file.provinces.map((p) => ({ key: pname(p), id: p.code, count: valueOf(p) ?? Number.NaN })),
    TOP_N,
  )
  const regionName = (key: string) => sx(`rg.region.${key}` as keyof typeof execPages)
  const regionShare = new Map<string, number | null>(file.regions.map((r) => [r.key, r.share ?? null]))
  const regionBars = rankBars(file.regions.map((r) => ({ key: regionName(r.key), id: r.key, count: r.articles })), file.regions.length)
  const regionsTitle = t('table.n', { n: 2, title: sx('rg.regions.table') })
  return (
    <div className="container">
      <PageHeader title={x('q.rg')} lede={sx('rg.lede', { release: rel, n: fmtInt(file.provinces.filter((p) => p.articles > 0).length), a: w.start, b: w.end })} />
      <Section id="map" title={sx('rg.provinces.h')} intro={topProv && topProv.articles > 0 ? sx('ex.most', { x: pname(topProv), k: fmtInt(topProv.articles) }) : undefined}>
        {hasPop ? (
          <fieldset className="metric-switch">
            <legend>{sx('rg.metric')}</legend>
            {REGION_METRICS.map((m) => (
              <label key={m}>
                <input type="radio" name="rg-metric" value={m} checked={metric === m} onChange={() => update({ m })} />
                {sx(m === 'per100k' ? 'rg.metric.per100k' : 'rg.metric.articles')}
              </label>
            ))}
          </fieldset>
        ) : null}
        <Figure
          id="fig-regions"
          number={1}
          title={sx('rg.fig', { m: measure })}
          tableTitle={t('table.n', { n: 1, title: sx('rg.table') })}
          csv={figureCsv(`atlas-${rel}-provinces.csv`, file.provinces, columns)}
          source={sx('rg.source', { release: rel })}
          view={state.view}
          onView={(v) => update({ view: v })}
          chart={
            <div className="rg-map">
              <div className="rg-map-c">
                <ProvinceMap
                  values={new Map(file.provinces.map((p) => [p.code, valueOf(p)]))}
                  format={format}
                  label={sx('rg.map', { m: measure, n: fmtInt(file.provinces.filter((p) => valueOf(p) !== null).length) })}
                  noData={sx('rg.noData')}
                  range={(a, b) => sx('rg.range', { a, b })}
                />
              </div>
              {top.rows.length ? (
                <div className="rg-top">
                  <p className="rg-top-h">{x('xv.top.title', { m: measure })}</p>
                  <BarRank rows={top.rows} value={(r) => format(r.count)} label={x('xv.top.label', { m: measure })} />
                </div>
              ) : null}
            </div>
          }
          table={
            <DataTable
              caption={t('table.n', { n: 1, title: sx('rg.table') })}
              rows={file.provinces}
              columns={columns}
              rowKey={(p) => p.code}
              defaultSort={{ key: metric === 'per100k' ? 'per100k' : 'articles', dir: 'desc' }}
            />
          }
          how={
            <>
              <p>{x('xv.map.how', { n: TOP_N })}</p>
              <p>{sx('rg.how', { p: fmtPct(file.coverage ?? null, 0) })}</p>
              {hasPop ? <p>{sx('rg.popNote', { y: file.population_year ?? DASH })}</p> : null}
            </>
          }
        />
      </Section>
      {file.regions.length ? (
        <Section id="by-region" title={sx('rg.regions.h')}>
          <Figure
            id="fig-by-region"
            number={2}
            title={x('xv.rg.title')}
            tableTitle={regionsTitle}
            csv={figureCsv(`atlas-${rel}-regions.csv`, file.regions, regionColumns)}
            how={<p>{x('xv.rg.how')}</p>}
            source={t('source.line', { release: rel })}
            view={state.rv}
            onView={(v) => update({ rv: v })}
            chart={<BarRank rows={regionBars.rows} value={(r) => `${fmtInt(r.count)} · ${fmtPct(regionShare.get(r.id ?? '') ?? null, 0)}`} label={x('xv.rg.label')} />}
            table={<DataTable caption={regionsTitle} rows={file.regions} columns={regionColumns} rowKey={(r) => r.key} stack={false} defaultSort={{ key: 'articles', dir: 'desc' }} />}
          />
        </Section>
      ) : null}
    </div>
  )
}
