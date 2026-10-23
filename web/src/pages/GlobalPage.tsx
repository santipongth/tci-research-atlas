import { DataTable, type Column } from '../components/DataTable'
import { HowNote } from '../components/HowNote'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { Term } from '../components/Term'
import { TopicLink } from '../components/TopicLink'
import { groupName, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { GlobalFile, SubfieldBench, Topic } from '../data/types'
import { DASH, fmtInt, fmtNum, fmtPct, fmtRatio } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { withPrimary } from '../lib/columns'

export default function GlobalPage() {
  const { t } = useI18n()
  return (
    <RequireRelease title={t('gl.title')}>
      {(release) => (
        <ModuleFile<GlobalFile> release={release} module="global" path={MODULE_FILES.global} title={t('gl.title')}>
          {(file) => <Global release={release} file={file} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

function Global({ release, file }: { release: AtlasRelease; file: GlobalFile }) {
  const { t, lang } = useI18n()
  const opp = file.subfields.filter((s) => s.opportunity)
  const r = `${file.recent.start}–${file.recent.end}`
  const b = `${file.baseline.start}–${file.baseline.end}`
  // the strongest opportunity (fastest world growth) is the page's example
  const top = opp.reduce<SubfieldBench | null>((m, s) => ((s.world_ratio ?? 0) > (m?.world_ratio ?? -1) ? s : m), null)
  const topicsOf = (s: SubfieldBench): Topic[] => (s.topics ?? []).map((id) => release.topicById.get(id)).filter((tp): tp is Topic => tp !== undefined)
  const columns = (mark: boolean): Column<SubfieldBench>[] => withPrimary<SubfieldBench>([
    {
      key: 'subfield', header: t('gl.col.subfield'), rowHeader: true, sortValue: (s) => s.en,
      cell: (s) => (
        <>
          <span lang="en">{s.en}</span>
          {mark && s.opportunity ? <span className="flag">{t('gl.opp')}</span> : null}
        </>
      ),
      csvCols: [{ header: 'subfield_id', value: (s) => s.id }, { header: 'subfield_en', value: (s) => s.en }],
    },
    { key: 'field', csvHeader: 'group', header: t('col.field'), cell: (s) => (release.groupById.has(s.group) ? groupName(release, s.group, lang) : DASH), csv: (s) => s.group },
    { key: 'ratio', csvHeader: 'world_ratio', header: t('gl.col.ratio'), numeric: true, cell: (s) => fmtRatio(s.world_ratio ?? null), sortValue: (s) => s.world_ratio ?? null },
    { key: 'ai', csvHeader: 'activity_index', header: t('gl.col.ai'), numeric: true, cell: (s) => fmtNum(s.activity_index ?? null, 2), sortValue: (s) => s.activity_index ?? null },
    { key: 'share', csvHeader: 'country_share', header: t('gl.col.share'), numeric: true, cell: (s) => fmtPct(s.country_share ?? null, 2), sortValue: (s) => s.country_share ?? null },
    { key: 'country', csvHeader: 'country_recent', header: t('gl.col.country', { r }), numeric: true, cell: (s) => fmtInt(s.country_recent), sortValue: (s) => s.country_recent },
    { key: 'world', csvHeader: 'world_recent', header: t('gl.col.world', { r }), numeric: true, cell: (s) => fmtInt(s.world_recent), sortValue: (s) => s.world_recent },
    { key: 'tci', csvHeader: 'tci_recent', header: t('gl.col.tci'), numeric: true, cell: (s) => fmtInt(s.tci_recent ?? 0), sortValue: (s) => s.tci_recent ?? 0 },
    {
      key: 'topics', csvHeader: 'topic_ids', header: t('gl.col.topics'),
      cell: (s) => {
        const tl = topicsOf(s).slice(0, 3)
        return tl.length ? <span className="sdg-ex">{tl.map((tp) => <TopicLink key={tp.id} topic={tp} showStatus />)}</span> : DASH
      },
      csv: (s) => (s.topics ?? []).join(';'),
    },
  ], ['ratio', 'ai', 'country', 'topics'])
  const country = file.country === 'TH' ? t('gl.thailand') : file.country
  const rel = release.overview.release
  return (
    <div className="container">
      <PageHeader
        title={t('gl.title')}
        lede={t('gl.lede', { c: country, r, b })}
      >
        <HowNote>
          <p>{t('gl.def', { c: country, r, b })}</p>
          <p className="how-terms">
            <span>{t('glossary.terms')}:</span>
            <Term term="activity" />
          </p>
        </HowNote>
      </PageHeader>
      {opp.length ? (
        <Section id="opportunities" title={t('gl.opp.h')} intro={top ? t('gl.example', { x: top.en, wr: fmtNum(top.world_ratio ?? null, 1), ai: fmtNum(top.activity_index ?? null, 2) }) : undefined}>
          <HowNote>
            <p>{t('gl.opp.intro', { r: fmtNum(file.min_world_ratio, 1), n: fmtInt(file.min_world_works), ai: fmtNum(file.max_activity_index, 1) })}</p>
          </HowNote>
          <DataTable caption={t('table.n', { n: 1, title: t('gl.opp.table') })} rows={opp} columns={columns(false)} rowKey={(s) => s.id} defaultSort={{ key: 'ratio', dir: 'desc' }} csvFilename={`atlas-${rel}-opportunities.csv`} />
        </Section>
      ) : null}
      <Section id="all" title={t('gl.all.h')}>
        <DataTable caption={t('table.n', { n: 2, title: t('gl.all.table') })} rows={file.subfields} columns={columns(true)} rowKey={(s) => s.id} defaultSort={{ key: 'world', dir: 'desc' }} csvFilename={`atlas-${rel}-global.csv`} />
      </Section>
      <p className="source">{t('gl.source', { v: file.source })}</p>
    </div>
  )
}
