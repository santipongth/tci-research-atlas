import { DataTable, type Column } from '../components/DataTable'
import { HowNote } from '../components/HowNote'
import { InstitutionLink } from '../components/InstitutionLink'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { ShareBar } from '../components/ShareBar'
import { groupName, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { CollabEdge, CountryCount, InstitutionSummary, InstitutionsFile } from '../data/types'
import { filterInstitutions, instName } from '../lib/executive'
import { DASH, fmtInt, fmtPct } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { INST_SORTS, INST_TYPE_FILTERS, institutionsCodec, type InstSort } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import type { StrKey } from '../strings'

export default function InstitutionsPage() {
  const { t } = useI18n()
  return (
    <RequireRelease title={t('in.title')}>
      {(release) => (
        <ModuleFile<InstitutionsFile> release={release} module="institutions" path={MODULE_FILES.institutions} title={t('in.title')}>
          {(file) => <Institutions release={release} file={file} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

const isSort = (v: string): v is InstSort => (INST_SORTS as readonly string[]).includes(v)

function Institutions({ release, file }: { release: AtlasRelease; file: InstitutionsFile }) {
  const { t, lang } = useI18n()
  const [state, update] = useUrlState(institutionsCodec)
  const w = file.window
  const rw = `${file.recent.start}–${file.recent.end}`
  const rows = filterInstitutions(file.institutions, state.q, state.type)
  const byId = new Map(file.institutions.map((i) => [i.id, i]))
  const provinces = new Map((file.province_names ?? []).map((p) => [p.code, p]))
  const place = (i: InstitutionSummary): string => {
    if (i.province) {
      const p = provinces.get(i.province)
      return p ? (lang === 'en' ? p.name_en : p.name_th) : i.province
    }
    return i.country && i.country !== 'TH' ? t('in.abroad', { c: i.country }) : t('in.unplaced')
  }
  const columns: Column<InstitutionSummary>[] = [
    { key: 'id', header: 'id', csvHeader: 'institution_id', cell: () => null, csv: (i) => i.id, csvOnly: true },
    {
      key: 'name', header: t('col.institution'), rowHeader: true, cell: (i) => <InstitutionLink inst={i} />, sortValue: (i) => instName(i, lang).text,
      csvCols: [{ header: 'name_th', value: (i) => i.name_th ?? '' }, { header: 'name_en', value: (i) => i.name_en ?? '' }],
    },
    { key: 'type', csvHeader: 'type', header: t('in.col.type'), cell: (i) => t(`in.type.${i.type ?? 'other'}` as StrKey), csv: (i) => i.type ?? 'other' },
    { key: 'province', csvHeader: 'province', header: t('in.col.province'), cell: place, sortValue: place, csv: (i) => i.province ?? '' },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (i) => fmtInt(i.articles), sortValue: (i) => i.articles },
    { key: 'recent', csvHeader: 'articles_recent', header: t('in.col.recent', { r: rw }), numeric: true, cell: (i) => fmtInt(i.articles_recent ?? 0), sortValue: (i) => i.articles_recent ?? 0 },
    { key: 'intl', csvHeader: 'intl_share', header: t('in.col.intl'), numeric: true, cell: (i) => <ShareBar value={i.intl_share} />, sortValue: (i) => i.intl_share ?? null },
    { key: 'partners', csvHeader: 'partners', header: t('in.col.partners'), numeric: true, cell: (i) => fmtInt(i.partners ?? 0), sortValue: (i) => i.partners ?? 0 },
    { key: 'group', csvHeader: 'group', header: t('col.field'), cell: (i) => (i.group ? groupName(release, i.group, lang) : DASH), csv: (i) => i.group ?? '' },
  ]
  const valid = columns.some((c) => c.key === state.sort && c.sortValue)
  const edges = (file.edges ?? []).filter((e) => byId.has(e.a) && byId.has(e.b))
  const edgeColumns: Column<CollabEdge>[] = [
    {
      key: 'pair', csvHeader: 'institution_a', header: t('in.col.pair'), rowHeader: true,
      cell: (e) => (
        <span className="pair">
          <InstitutionLink inst={byId.get(e.a) as InstitutionSummary} />
          <InstitutionLink inst={byId.get(e.b) as InstitutionSummary} />
        </span>
      ),
      csvCols: [{ header: 'institution_a', value: (e) => e.a }, { header: 'institution_b', value: (e) => e.b }],
    },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (e) => fmtInt(e.articles), sortValue: (e) => e.articles },
  ]
  const countries = file.countries ?? []
  // the examples: the largest institution, the strongest partnership, the main partner country
  const topInst = file.institutions.reduce<InstitutionSummary | null>((m, i) => (m === null || i.articles > m.articles ? i : m), null)
  const topEdge = edges.reduce<CollabEdge | null>((m, e) => (m === null || e.articles > m.articles ? e : m), null)
  const topCountry = countries.reduce<CountryCount | null>((m, c) => (m === null || c.articles > m.articles ? c : m), null)
  const iname = (id: string) => instName(byId.get(id) as InstitutionSummary, lang).text
  const countryColumns: Column<CountryCount>[] = [
    { key: 'name', csvHeader: 'country', header: t('in.col.country'), rowHeader: true, cell: (c) => (lang === 'en' ? c.name_en : c.name_th), sortValue: (c) => (lang === 'en' ? c.name_en : c.name_th), csv: (c) => c.code },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (c) => fmtInt(c.articles), sortValue: (c) => c.articles },
  ]
  const rel = release.overview.release
  return (
    <div className="container">
      <PageHeader title={t('in.title')} lede={t('in.lede', { n: fmtInt(file.min_articles), a: w.start, b: w.end })} />
      <Section id="glance" title={t('in.kpi.h')} intro={topInst ? t('ex.most', { x: instName(topInst, lang).text, k: fmtInt(topInst.articles) }) : undefined}>
        <dl className="summary">
          <div>
            <dt>{t('in.kpi.shown')}</dt>
            <dd>{fmtInt(file.institutions.length)}<small>{t('in.kpi.shownSub', { n: fmtInt(file.min_articles), a: w.start, b: w.end })}</small></dd>
          </div>
          <div>
            <dt>{t('in.kpi.intl')}</dt>
            <dd>{fmtPct(file.pct_international ?? null, 1)}<small>{t('in.kpi.intlSub', { n: fmtInt(file.articles_with_org) })}</small></dd>
          </div>
          <div>
            <dt>{t('in.kpi.multi')}</dt>
            <dd>{fmtPct(file.pct_multi_institution ?? null, 1)}</dd>
          </div>
        </dl>
      </Section>
      <div className="j-tools">
        <label>
          {t('in.search')}
          <input type="search" value={state.q} onChange={(e) => update({ q: e.target.value })} />
        </label>
        <label>
          {t('in.type')}
          <select value={state.type} onChange={(e) => update({ type: (INST_TYPE_FILTERS as readonly string[]).includes(e.target.value) ? (e.target.value as (typeof INST_TYPE_FILTERS)[number]) : 'all' })}>
            {INST_TYPE_FILTERS.map((ty) => (
              <option key={ty} value={ty}>{t(`in.type.${ty}` as StrKey)}</option>
            ))}
          </select>
        </label>
        <p className="hint" role="status">{t('in.count', { n: fmtInt(rows.length), total: fmtInt(file.institutions.length) })}</p>
      </div>
      <Section id="institutions" title={t('in.table', { a: w.start, b: w.end })}>
        <DataTable
          caption={t('table.n', { n: 1, title: t('in.table', { a: w.start, b: w.end }) })}
          rows={rows}
          columns={columns}
          rowKey={(i) => i.id}
          sort={valid ? { key: state.sort, dir: state.dir } : { key: 'articles', dir: 'desc' }}
          onSort={(s) => update({ sort: isSort(s.key) ? s.key : 'articles', dir: s.dir })}
          csvFilename={`atlas-${rel}-institutions.csv`}
          empty={t('in.none')}
        />
        <HowNote>
          <p>{t('in.foot')}</p>
        </HowNote>
      </Section>
      {edges.length ? (
        <Section id="partnerships" title={t('in.pairs.h')} intro={topEdge ? t('in.pairs.intro', { x: iname(topEdge.a), y: iname(topEdge.b), k: fmtInt(topEdge.articles), a: w.start, b: w.end, n: fmtInt(file.network_min_articles) }) : undefined}>
          <DataTable caption={t('table.n', { n: 2, title: t('in.pairs.table') })} rows={edges} columns={edgeColumns} rowKey={(e) => `${e.a}~${e.b}`} defaultSort={{ key: 'articles', dir: 'desc' }} csvFilename={`atlas-${rel}-partnerships.csv`} />
        </Section>
      ) : null}
      {countries.length ? (
        <Section id="countries" title={t('in.countries.h')} intro={topCountry ? t('in.countries.intro', { c: lang === 'en' ? topCountry.name_en : topCountry.name_th, k: fmtInt(topCountry.articles), a: w.start, b: w.end }) : undefined}>
          <DataTable caption={t('table.n', { n: 3, title: t('in.countries.table') })} rows={countries} columns={countryColumns} rowKey={(c) => c.code} defaultSort={{ key: 'articles', dir: 'desc' }} csvFilename={`atlas-${rel}-partner-countries.csv`} />
        </Section>
      ) : null}
    </div>
  )
}
