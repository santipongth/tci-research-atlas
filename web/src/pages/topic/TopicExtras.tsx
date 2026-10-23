import { THAI } from '../../lib/script'
import { Link } from 'react-router'
import { BarRank } from '../../charts/BarRank'
import { rankBars } from '../../charts/infographic'
import { DataTable, type Column } from '../../components/DataTable'
import { Figure } from '../../components/Figure'
import { useReleaseFile } from '../../data/atlasContext'
import { hasModule, MODULE_FILES, type AtlasRelease } from '../../data/release'
import type { CountItem, RepresentativeArticle, SdgFile } from '../../data/types'
import { toBibtex, toRis, type CiteRecord } from '../../lib/citation'
import { downloadText } from '../../lib/csv'
import { fmtInt } from '../../lib/format'
import { useI18n, useStrings } from '../../lib/i18n'
import { figureCsv } from '../../lib/tableCsv'
import type { View } from '../../lib/urlState'
import { topicExtra } from '../../strings/topicExtra'

/*
 * Topic-page parts loaded on demand (TopicPage is in the entry chunk): the SDG chips, which read goal names from
 * sdg.json, the RIS/BibTeX export of the representative articles (lib/citation), and the journal / institution rankings.
 */

/** "Related goals: SDG 3 Good health …" — one link per goal to /sdg; names from sdg.json when the release has it. */
export function TopicSdg({ release, goals }: { release: AtlasRelease; goals: readonly number[] }) {
  const s = useStrings(topicExtra)
  const { name } = useI18n()
  const sdg = useReleaseFile<SdgFile>(hasModule(release, 'sdg') ? MODULE_FILES.sdg : null)
  const goalName = (n: number) => {
    const g = sdg.status === 'ready' ? sdg.data.goals.find((x) => x.framework === 'sdg' && x.number === n) : undefined
    return g ? name(g) : ''
  }
  const sorted = [...new Set(goals)].sort((a, b) => a - b)
  return (
    <p className="tp-sdg">
      <span className="tp-sdg-label">{s('sdg.label')}</span>
      {sorted.map((n) => {
        const nm = goalName(n)
        return (
          <Link key={n} to="/sdg" className="tp-sdg-chip" aria-label={nm ? s('sdg.link', { n, name: nm }) : undefined}>
            <strong>{s('sdg.chip', { n })}</strong>
            {nm ? <span>{nm}</span> : null}
          </Link>
        )
      })}
    </p>
  )
}


const cite = (a: RepresentativeArticle): CiteRecord => {
  const thaiMain = THAI.test(a.title) || !a.title_en
  return {
    id: a.article_id,
    titleTh: thaiMain ? a.title : (a.title_en ?? ''),
    titleEn: thaiMain ? (a.title_en ?? '') : a.title,
    journal: a.journal ?? '',
    year: a.year ?? null,
    doi: a.doi || null,
    url: a.url || null,
  }
}

/** RIS / BibTeX of the topic's representative articles (no authors: the Atlas publishes no person names). */
export function ArticleCite({ release, topicId, articles }: { release: AtlasRelease; topicId: string; articles: readonly RepresentativeArticle[] }) {
  const s = useStrings(topicExtra)
  const rel = release.overview.release
  const base = `atlas-${rel}-${topicId}-articles`
  const records = articles.map(cite)
  const formats = [
    { key: 'x.ris' as const, run: () => downloadText(`${base}.ris`, toRis(records, rel), 'application/x-research-info-systems;charset=utf-8') },
    { key: 'x.bib' as const, run: () => downloadText(`${base}.bib`, toBibtex(records, rel), 'application/x-bibtex;charset=utf-8') },
  ]
  return (
    <div className="srch-x tp-cite" role="group" aria-labelledby="tp-cite-h">
      <p id="tp-cite-h" className="srch-x-h">{s('x.h')}</p>
      <div className="srch-x-btns">
        {formats.map((f) => (
          <button key={f.key} type="button" className="btn-secondary" aria-label={s('x.label', { n: fmtInt(articles.length), format: s(f.key) })} onClick={f.run}>{s(f.key)}</button>
        ))}
      </div>
      <p className="hint">{s('x.note')}</p>
    </div>
  )
}

const TOP = 5

/**
 * The journals or institutions with most articles on the topic: the top five as a mini bar ranking (chart view) and the
 * full list as a sortable table (table view, with the CSV of every row).
 */
export function TopicRanking({ release, topicId, kind, rows, number, tableNo, view, onView }: {
  release: AtlasRelease
  topicId: string
  kind: 'journals' | 'institutions'
  rows: readonly CountItem[]
  number: number
  tableNo: number
  view: View
  onView: (v: View) => void
}) {
  const s = useStrings(topicExtra)
  const { t } = useI18n()
  const { rows: top, rest } = rankBars(rows, TOP)
  const base = kind === 'journals' ? '/journals' : '/institutions'
  const isJr = kind === 'journals'
  const tableTitle = t('table.n', { n: tableNo, title: t(isJr ? 'tp.journals.table' : 'tp.orgs.table') })
  const columns: Column<CountItem>[] = [
    { key: 'key', csvHeader: 'name', header: t(isJr ? 'col.journal' : 'col.institution'), rowHeader: true, cell: (r) => (r.id ? <Link to={`${base}/${r.id}`}>{r.key}</Link> : r.key), sortValue: (r) => r.key },
    { key: 'count', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (r) => fmtInt(r.count), sortValue: (r) => r.count },
  ]
  const filename = `atlas-${release.overview.release}-${topicId}-${kind}.csv`
  return (
    <Figure
      id={`fig-${kind}`}
      number={number}
      title={s(isJr ? 'rk.jr.title' : 'rk.org.title', { n: top.length })}
      tableTitle={tableTitle}
      csv={figureCsv(filename, rows, columns)}
      how={<p>{s('rk.how')}</p>}
      source={t('source.line', { release: release.overview.release })}
      view={view}
      onView={onView}
      chart={
        <>
          <BarRank rows={top} href={(r) => (r.id ? `${base}/${r.id}` : null)} value={(r) => fmtInt(r.count)} label={s(isJr ? 'rk.jr.label' : 'rk.org.label')} />
          {rest > 0 ? <p className="br-more">{s('rk.more', { n: fmtInt(rest) })}</p> : null}
        </>
      }
      table={<DataTable caption={tableTitle} rows={rows} rowKey={(r) => r.key} stack={false} columns={columns} limit={25} />}
    />
  )
}
