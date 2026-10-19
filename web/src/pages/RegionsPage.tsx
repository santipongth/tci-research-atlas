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
import { DASH, fmtInt, fmtNum, fmtPct } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { REGION_METRICS, regionsCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import type { StrKey } from '../strings'

export default function RegionsPage() {
  const { t } = useI18n()
  return (
    <RequireRelease title={t('rg.title')}>
      {(release) => (
        <ModuleFile<RegionsFile> release={release} module="regions" path={MODULE_FILES.regions} title={t('rg.title')}>
          {(file) => <Regions release={release} file={file} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

function Regions({ release, file }: { release: AtlasRelease; file: RegionsFile }) {
  const { t, lang } = useI18n()
  const [state, update] = useUrlState(regionsCodec)
  const instFile = useReleaseFile<InstitutionsFile>(hasModule(release, 'institutions') ? MODULE_FILES.institutions : null)
  const insts = new Map(instFile.status === 'ready' ? instFile.data.institutions.map((i) => [i.id, i]) : [])
  const hasPop = file.provinces.some((p) => p.per_100k != null)
  const metric = hasPop ? state.m : 'articles'
  const valueOf = (p: ProvinceStat): number | null => (metric === 'per100k' ? (p.per_100k ?? null) : p.articles)
  const format = (v: number) => (metric === 'per100k' ? fmtNum(v, 1) : fmtInt(v))
  const measure = t(metric === 'per100k' ? 'rg.metric.per100k' : 'rg.metric.articles')
  const pname = (p: ProvinceStat) => (lang === 'en' ? p.name_en : p.name_th)
  const maxShare = Math.max(0.0001, ...file.provinces.map((p) => p.share ?? 0))
  const w = file.window
  const rel = release.overview.release
  const columns: Column<ProvinceStat>[] = [
    { key: 'name', csvHeader: 'province', header: t('in.col.province'), rowHeader: true, cell: pname, sortValue: pname, csv: (p) => p.code },
    { key: 'region', csvHeader: 'region', header: t('rg.col.region'), cell: (p) => t(`rg.region.${p.region}` as StrKey), sortValue: (p) => p.region, csv: (p) => p.region },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (p) => fmtInt(p.articles), sortValue: (p) => p.articles },
    { key: 'share', csvHeader: 'share', header: t('rg.col.share'), numeric: true, cell: (p) => <ShareBar value={p.share} digits={1} max={maxShare} />, sortValue: (p) => p.share ?? null },
    { key: 'recent', csvHeader: 'articles_recent', header: t('in.col.recent'), numeric: true, cell: (p) => fmtInt(p.articles_recent ?? 0), sortValue: (p) => p.articles_recent ?? 0 },
    { key: 'institutions', csvHeader: 'institutions', header: t('rg.col.institutions'), numeric: true, cell: (p) => fmtInt(p.institutions ?? 0), sortValue: (p) => p.institutions ?? 0 },
    ...(hasPop ? [{ key: 'per100k', csvHeader: 'per_100k', header: t('rg.col.per100k'), numeric: true, cell: (p: ProvinceStat) => fmtNum(p.per_100k ?? null, 1), sortValue: (p: ProvinceStat) => p.per_100k ?? null }] : []),
    {
      key: 'top', csvHeader: 'top_institutions', header: t('rg.col.top'),
      cell: (p) => {
        const top = (p.top ?? []).map((id) => insts.get(id)).filter((i) => i !== undefined)
        return top.length ? <span className="pair">{top.map((i) => <InstitutionLink key={i.id} inst={i} />)}</span> : DASH
      },
      csv: (p) => (p.top ?? []).join(';'),
    },
  ]
  const regionColumns: Column<RegionStat>[] = [
    { key: 'name', csvHeader: 'region', header: t('rg.col.region'), rowHeader: true, cell: (r) => t(`rg.region.${r.key}` as StrKey), csv: (r) => r.key },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (r) => fmtInt(r.articles), sortValue: (r) => r.articles },
    { key: 'share', csvHeader: 'share', header: t('rg.col.share'), numeric: true, cell: (r) => fmtPct(r.share ?? null, 1), sortValue: (r) => r.share ?? null },
  ]
  return (
    <div className="container">
      <PageHeader title={t('rg.title')} lede={t('rg.lede', { a: w.start, b: w.end, p: fmtPct(file.coverage ?? null, 0) })} />
      <Section id="map" title={t('rg.provinces.h')}>
        {hasPop ? (
          <fieldset className="metric-switch">
            <legend>{t('rg.metric')}</legend>
            {REGION_METRICS.map((m) => (
              <label key={m}>
                <input type="radio" name="rg-metric" value={m} checked={metric === m} onChange={() => update({ m })} />
                {t(m === 'per100k' ? 'rg.metric.per100k' : 'rg.metric.articles')}
              </label>
            ))}
          </fieldset>
        ) : null}
        <Figure
          id="fig-regions"
          number={1}
          title={t('rg.fig', { m: measure })}
          source={t('rg.source', { release: rel })}
          view={state.view}
          onView={(v) => update({ view: v })}
          chart={
            <ProvinceMap
              values={new Map(file.provinces.map((p) => [p.code, valueOf(p)]))}
              format={format}
              label={t('rg.map', { m: measure, n: fmtInt(file.provinces.filter((p) => valueOf(p) !== null).length) })}
              noData={t('rg.noData')}
              range={(a, b) => t('rg.range', { a, b })}
            />
          }
          table={
            <DataTable
              caption={t('table.n', { n: 1, title: t('rg.table') })}
              rows={file.provinces}
              columns={columns}
              rowKey={(p) => p.code}
              defaultSort={{ key: metric === 'per100k' ? 'per100k' : 'articles', dir: 'desc' }}
              csvFilename={`atlas-${rel}-provinces.csv`}
            />
          }
          note={hasPop ? <p className="note">{t('rg.popNote', { y: file.population_year ?? DASH })}</p> : undefined}
        />
      </Section>
      {file.regions.length ? (
        <Section id="by-region" title={t('rg.regions.h')}>
          <DataTable caption={t('table.n', { n: 2, title: t('rg.regions.table') })} rows={file.regions} columns={regionColumns} rowKey={(r) => r.key} stack={false} defaultSort={{ key: 'articles', dir: 'desc' }} csvFilename={`atlas-${rel}-regions.csv`} />
        </Section>
      ) : null}
    </div>
  )
}
