import { useDeferredValue, useMemo } from 'react'
import { ArcNetwork } from '../charts/ArcNetwork'
import { BarRank } from '../charts/BarRank'
import { networkNodes } from '../charts/execLayout'
import { rankBars } from '../charts/infographic'
import { DataTable, type Column } from '../components/DataTable'
import { Figure } from '../components/Figure'
import { HowNote } from '../components/HowNote'
import { InstitutionLink } from '../components/InstitutionLink'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { ShareBar } from '../components/ShareBar'
import { StatGrid, StatTile } from '../components/StatTile'
import { groupName, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { CollabEdge, CountryCount, InstitutionSummary, InstitutionsFile } from '../data/types'
import { filterInstitutions, instName } from '../lib/executive'
import { DASH, fmtInt, fmtPct, yearSpan } from '../lib/format'
import { useI18n, useStrings } from '../lib/i18n'
import { figureCsv } from '../lib/tableCsv'
import { countLine, useRowLimit } from '../lib/tableRows'
import { INST_SORTS, INST_TYPE_FILTERS, institutionsCodec, type InstSort } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import { execViz } from '../strings/execViz'
import { execPages } from '../strings/execPages'

export default function InstitutionsPage() {
  const sx = useStrings(execPages)
  return (
    <RequireRelease title={sx('in.title')}>
      {(release) => (
        <ModuleFile<InstitutionsFile> release={release} module="institutions" path={MODULE_FILES.institutions} title={sx('in.title')}>
          {(file) => <Institutions release={release} file={file} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

/** Institutions drawn in the collaboration arcs (the largest with a partnership). */
const NET_NODES = 10
/** Rows of the institutions table before "แสดงทั้งหมด" (fewer on phones, see useRowLimit). */
const TABLE_ROWS = 50

const isSort = (v: string): v is InstSort => (INST_SORTS as readonly string[]).includes(v)

function Institutions({ release, file }: { release: AtlasRelease; file: InstitutionsFile }) {
  const { t, lang } = useI18n()
  const sx = useStrings(execPages)
  const x = useStrings(execViz)
  const [state, update] = useUrlState(institutionsCodec)
  const tableRows = useRowLimit(TABLE_ROWS)
  const w = file.window
  const rw = yearSpan(file.recent.start, file.recent.end)
  // typing stays responsive: the table filters on the deferred text while the box shows every keystroke at once
  const q = useDeferredValue(state.q)
  const rows = useMemo(() => filterInstitutions(file.institutions, q, state.type), [file.institutions, q, state.type])
  const byId = useMemo(() => new Map(file.institutions.map((i) => [i.id, i])), [file.institutions])
  // memoised (columns, province names): a new columns array on every keystroke would re-sort ~10,000 rows each time
  const provinces = useMemo(() => new Map((file.province_names ?? []).map((p) => [p.code, p])), [file.province_names])
  const columns = useMemo((): Column<InstitutionSummary>[] => {
    const place = (i: InstitutionSummary): string => {
      if (i.province) {
        const p = provinces.get(i.province)
        return p ? (lang === 'en' ? p.name_en : p.name_th) : i.province
      }
      return i.country && i.country !== 'TH' ? sx('in.abroad', { c: i.country }) : sx('in.unplaced')
    }
    return [
      { key: 'id', header: 'id', csvHeader: 'institution_id', cell: () => null, csv: (i) => i.id, csvOnly: true },
      {
        key: 'name', header: t('col.institution'), rowHeader: true, cell: (i) => <InstitutionLink inst={i} />, sortValue: (i) => instName(i, lang).text,
        csvCols: [{ header: 'name_th', value: (i) => i.name_th ?? '' }, { header: 'name_en', value: (i) => i.name_en ?? '' }],
      },
      { key: 'type', csvHeader: 'type', header: sx('in.col.type'), cell: (i) => sx(`in.type.${i.type ?? 'other'}` as keyof typeof execPages), csv: (i) => i.type ?? 'other' },
      { key: 'province', csvHeader: 'province', header: sx('in.col.province'), cell: place, sortValue: place, csv: (i) => i.province ?? '' },
      { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (i) => fmtInt(i.articles), sortValue: (i) => i.articles },
      { key: 'recent', csvHeader: 'articles_recent', header: sx('in.col.recent', { r: rw }), numeric: true, cell: (i) => fmtInt(i.articles_recent ?? null), sortValue: (i) => i.articles_recent ?? null },
      { key: 'intl', csvHeader: 'intl_share', header: sx('in.col.intl'), numeric: true, cell: (i) => <ShareBar value={i.intl_share} />, sortValue: (i) => i.intl_share ?? null },
      { key: 'partners', csvHeader: 'partners', header: sx('in.col.partners'), numeric: true, cell: (i) => fmtInt(i.partners ?? null), sortValue: (i) => i.partners ?? null },
      { key: 'group', csvHeader: 'group', header: t('col.field'), cell: (i) => (i.group ? groupName(release, i.group, lang) : DASH), csv: (i) => i.group ?? '' },
    ]
  }, [provinces, lang, t, sx, rw, release])
  const valid = columns.some((c) => c.key === state.sort && c.sortValue)
  const edges = useMemo(() => (file.edges ?? []).filter((e) => byId.has(e.a) && byId.has(e.b)), [file.edges, byId])
  const edgeColumns: Column<CollabEdge>[] = [
    {
      key: 'pair', csvHeader: 'institution_a', header: sx('in.col.pair'), rowHeader: true,
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
    { key: 'name', csvHeader: 'country', header: sx('in.col.country'), rowHeader: true, cell: (c) => (lang === 'en' ? c.name_en : c.name_th), sortValue: (c) => (lang === 'en' ? c.name_en : c.name_th), csv: (c) => c.code },
    { key: 'articles', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (c) => fmtInt(c.articles), sortValue: (c) => c.articles },
  ]
  const rel = release.overview.release
  const pairsTitle = t('table.n', { n: 1, title: sx('in.pairs.table') })
  const countriesTitle = t('table.n', { n: 2, title: sx('in.countries.table') })
  const countryBars = rankBars(countries.map((c) => ({ key: lang === 'en' ? c.name_en : c.name_th, id: c.code, count: c.articles })), 8)
  // the arc rows: the institutions of the strongest partnerships first (so the pair the intro names is always drawn),
  // largest first; with ~10,000 institutions every other pair stays in the table
  const { netRows, netLinks, hiddenPairs } = useMemo(() => {
    const net = networkNodes(edges, NET_NODES)
    const top = net.ids.map((id) => byId.get(id) as InstitutionSummary)
    return { netRows: top, netLinks: net.links, hiddenPairs: edges.length - net.links.length }
  }, [edges, byId])
  return (
    <div className="container">
      <PageHeader title={x('q.in')} lede={sx('in.lede', { release: rel, k: fmtInt(file.institutions.length), n: fmtInt(file.min_articles), a: w.start, b: w.end })} />
      <Section id="glance" title={sx('in.kpi.h')} intro={topInst ? sx('ex.most', { x: instName(topInst, lang).text, k: fmtInt(topInst.articles) }) : undefined}>
        <StatGrid cols={2}>
          <StatTile label={sx('in.kpi.multi')} value={fmtPct(file.pct_multi_institution ?? null, 1)} sub={sx('in.kpi.intlSub', { n: fmtInt(file.articles_with_org) })} />
          <StatTile label={sx('in.kpi.intl')} value={fmtPct(file.pct_international ?? null, 1)} sub={sx('in.kpi.intlSub', { n: fmtInt(file.articles_with_org) })} wide="phone" />
        </StatGrid>
      </Section>
      {edges.length ? (
        <Section id="partnerships" title={sx('in.pairs.h')} intro={topEdge ? sx('in.pairs.intro', { x: iname(topEdge.a), y: iname(topEdge.b), k: fmtInt(topEdge.articles), a: w.start, b: w.end, n: fmtInt(file.network_min_articles) }) : undefined}>
          <Figure
            id="fig-pairs"
            number={1}
            title={x('xv.net.title')}
            tableTitle={pairsTitle}
            csv={figureCsv(`atlas-${rel}-partnerships.csv`, edges, edgeColumns)}
            how={<p>{x('xv.net.how')}</p>}
            source={t('source.line', { release: rel })}
            view={state.net}
            onView={(v) => update({ net: v })}
            chart={
              <>
                <ArcNetwork
                  rows={netRows.map((i) => ({ id: i.id, name: <InstitutionLink inst={i} />, text: instName(i, lang).text, weight: i.articles, sub: x('xv.articles', { k: fmtInt(i.articles) }) }))}
                  links={netLinks.map((e) => ({ a: e.a, b: e.b, value: e.articles }))}
                  label={x('xv.net.label', { n: fmtInt(edges.length) })}
                  pairTitle={(a, b, k) => x('xv.net.pair', { a, b, k: fmtInt(k) })}
                  maxNodes={NET_NODES}
                />
                {hiddenPairs > 0 ? <p className="br-more">{x('xv.net.more', { n: fmtInt(hiddenPairs) })}</p> : null}
              </>
            }
            table={<DataTable caption={pairsTitle} rows={edges} columns={edgeColumns} rowKey={(e) => `${e.a}~${e.b}`} defaultSort={{ key: 'articles', dir: 'desc' }} limit={25} />}
          />
        </Section>
      ) : null}
      {countries.length ? (
        <Section id="countries" title={sx('in.countries.h')} intro={topCountry ? sx('in.countries.intro', { c: lang === 'en' ? topCountry.name_en : topCountry.name_th, k: fmtInt(topCountry.articles), a: w.start, b: w.end }) : undefined}>
          <Figure
            id="fig-countries"
            number={2}
            title={x('xv.ctry.title')}
            tableTitle={countriesTitle}
            csv={figureCsv(`atlas-${rel}-partner-countries.csv`, countries, countryColumns)}
            how={<p>{x('xv.bar.how')}</p>}
            source={t('source.line', { release: rel })}
            view={state.ctry}
            onView={(v) => update({ ctry: v })}
            chart={
              <>
                <BarRank rows={countryBars.rows} value={(r) => fmtInt(r.count)} label={x('xv.ctry.label')} />
                {countryBars.rest > 0 ? <p className="br-more">{x('xv.more', { n: fmtInt(countryBars.rest) })}</p> : null}
              </>
            }
            table={<DataTable caption={countriesTitle} rows={countries} columns={countryColumns} rowKey={(c) => c.code} stack={false} defaultSort={{ key: 'articles', dir: 'desc' }} limit={25} />}
          />
        </Section>
      ) : null}
      <Section id="institutions" title={sx('in.table', { a: w.start, b: w.end })}>
        <div className="j-tools">
          <label>
            {sx('in.search')}
            <input type="search" value={state.q} onChange={(e) => update({ q: e.target.value })} />
          </label>
          <label>
            {sx('in.type')}
            <select value={state.type} onChange={(e) => update({ type: (INST_TYPE_FILTERS as readonly string[]).includes(e.target.value) ? (e.target.value as (typeof INST_TYPE_FILTERS)[number]) : 'all' })}>
              {INST_TYPE_FILTERS.map((ty) => (
                <option key={ty} value={ty}>{sx(`in.type.${ty}` as keyof typeof execPages)}</option>
              ))}
            </select>
          </label>
          <p className="hint" role="status">{sx(`in.${countLine(rows.length, file.institutions.length, tableRows)}` as const, { n: fmtInt(rows.length), total: fmtInt(file.institutions.length), k: fmtInt(tableRows ?? 0) })}</p>
        </div>
        <DataTable
          caption={t('table.n', { n: 3, title: sx('in.table', { a: w.start, b: w.end }) })}
          rows={rows}
          columns={columns}
          rowKey={(i) => i.id}
          limit={TABLE_ROWS}
          sort={valid ? { key: state.sort, dir: state.dir } : { key: 'articles', dir: 'desc' }}
          onSort={(s) => update({ sort: isSort(s.key) ? s.key : 'articles', dir: s.dir })}
          csvFilename={`atlas-${rel}-institutions.csv`}
          empty={sx('in.none')}
        />
        <HowNote>
          <p>{sx('in.foot')}</p>
        </HowNote>
      </Section>
    </div>
  )
}
