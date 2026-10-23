import { OpportunityQuadrant } from '../charts/OpportunityQuadrant'
import { DataTable, type Column } from '../components/DataTable'
import { Figure } from '../components/Figure'
import { HowNote } from '../components/HowNote'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { Term } from '../components/Term'
import { TopicLink } from '../components/TopicLink'
import { groupName, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { GlobalFile, SubfieldBench, Topic } from '../data/types'
import { DASH, fmtInt, fmtNum, fmtRatio, fmtShare, yearSpan } from '../lib/format'
import { useI18n, useStrings } from '../lib/i18n'
import { withPrimary } from '../lib/columns'
import { figureCsv } from '../lib/tableCsv'
import { globalCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import { execViz } from '../strings/execViz'
import { execPages } from '../strings/execPages'

export default function GlobalPage() {
  const sx = useStrings(execPages)
  return (
    <RequireRelease title={sx('gl.title')}>
      {(release) => (
        <ModuleFile<GlobalFile> release={release} module="global" path={MODULE_FILES.global} title={sx('gl.title')}>
          {(file) => <Global release={release} file={file} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

function Global({ release, file }: { release: AtlasRelease; file: GlobalFile }) {
  const { t, lang } = useI18n()
  const sx = useStrings(execPages)
  const x = useStrings(execViz)
  const [state, update] = useUrlState(globalCodec)
  const opp = file.subfields.filter((s) => s.opportunity)
  const r = yearSpan(file.recent.start, file.recent.end)
  const b = yearSpan(file.baseline.start, file.baseline.end)
  // the strongest opportunity (fastest world growth) is the page's example
  const top = opp.reduce<SubfieldBench | null>((m, s) => ((s.world_ratio ?? 0) > (m?.world_ratio ?? -1) ? s : m), null)
  const topicsOf = (s: SubfieldBench): Topic[] => (s.topics ?? []).map((id) => release.topicById.get(id)).filter((tp): tp is Topic => tp !== undefined)
  const columns = (mark: boolean): Column<SubfieldBench>[] => withPrimary<SubfieldBench>([
    {
      key: 'subfield', header: sx('gl.col.subfield'), rowHeader: true, sortValue: (s) => s.en,
      cell: (s) => (
        <>
          <span lang="en">{s.en}</span>
          {mark && s.opportunity ? <span className="flag">{sx('gl.opp')}</span> : null}
        </>
      ),
      csvCols: [{ header: 'subfield_id', value: (s) => s.id }, { header: 'subfield_en', value: (s) => s.en }],
    },
    { key: 'field', csvHeader: 'group', header: t('col.field'), cell: (s) => (release.groupById.has(s.group) ? groupName(release, s.group, lang) : DASH), csv: (s) => s.group },
    { key: 'ratio', csvHeader: 'world_ratio', header: sx('gl.col.ratio'), numeric: true, cell: (s) => fmtRatio(s.world_ratio ?? null), sortValue: (s) => s.world_ratio ?? null },
    { key: 'ai', csvHeader: 'activity_index', header: sx('gl.col.ai'), numeric: true, cell: (s) => fmtNum(s.activity_index ?? null, 2), sortValue: (s) => s.activity_index ?? null },
    { key: 'share', csvHeader: 'country_share', header: sx('gl.col.share'), numeric: true, cell: (s) => fmtShare(s.country_share ?? null, 2), sortValue: (s) => s.country_share ?? null },
    { key: 'country', csvHeader: 'country_recent', header: sx('gl.col.country', { r }), numeric: true, cell: (s) => fmtInt(s.country_recent), sortValue: (s) => s.country_recent },
    { key: 'world', csvHeader: 'world_recent', header: sx('gl.col.world', { r }), numeric: true, cell: (s) => fmtInt(s.world_recent), sortValue: (s) => s.world_recent },
    { key: 'tci', csvHeader: 'tci_recent', header: sx('gl.col.tci'), numeric: true, cell: (s) => fmtInt(s.tci_recent ?? null), sortValue: (s) => s.tci_recent ?? null },
    {
      key: 'topics', csvHeader: 'topic_ids', header: sx('gl.col.topics'),
      cell: (s) => {
        const tl = topicsOf(s).slice(0, 3)
        return tl.length ? <span className="sdg-ex">{tl.map((tp) => <TopicLink key={tp.id} topic={tp} showStatus />)}</span> : DASH
      },
      csv: (s) => (s.topics ?? []).join(';'),
    },
  ], ['ratio', 'ai', 'country', 'topics'])
  const country = file.country === 'TH' ? sx('gl.thailand') : file.country
  const rel = release.overview.release
  const points = file.subfields
    .filter((s) => typeof s.activity_index === 'number' && typeof s.world_ratio === 'number')
    .map((s) => ({ id: s.id, label: s.en, x: s.activity_index as number, y: s.world_ratio as number, hot: Boolean(s.opportunity) }))
  const oppTitle = t('table.n', { n: 1, title: sx('gl.opp.table') })
  const oppColumns = columns(false)
  return (
    <div className="container">
      <PageHeader
        title={sx('gl.title')}
        lede={sx('gl.lede', { c: country, r, b })}
      >
        <HowNote>
          <p>{sx('gl.def', { c: country, r, b })}</p>
          <p className="how-terms">
            <span>{t('glossary.terms')}:</span>
            <Term term="activity" />
          </p>
        </HowNote>
      </PageHeader>
      {opp.length ? (
        <Section id="opportunities" title={sx('gl.opp.h')} intro={top ? sx('gl.example', { x: top.en, wr: fmtNum(top.world_ratio ?? null, 1), ai: fmtNum(top.activity_index ?? null, 2) }) : undefined}>
          <Figure
            id="fig-quadrant"
            number={1}
            title={x('xv.q.title')}
            tableTitle={oppTitle}
            csv={figureCsv(`atlas-${rel}-opportunities.csv`, opp, oppColumns)}
            how={<p>{x('xv.q.how', { r: fmtNum(file.min_world_ratio, 1), n: fmtInt(file.min_world_works), ai: fmtNum(file.max_activity_index, 1) })}</p>}
            source={sx('gl.source', { v: file.source })}
            view={state.view}
            onView={(v) => update({ view: v })}
            chart={
              <OpportunityQuadrant
                points={points}
                xMax={file.max_activity_index}
                yMin={file.min_world_ratio}
                text={{ x: sx('gl.col.ai'), y: sx('gl.col.ratio'), zone: sx('gl.opp'), same: x('xv.q.same'), flat: x('xv.q.flat'), opp: x('xv.q.key.opp'), other: x('xv.q.key.other') }}
                label={x('xv.q.label', { n: fmtInt(points.length), k: fmtInt(opp.length) })}
                describe={(p) => x('xv.q.point', { x: p.label, wr: fmtNum(p.y, 2), ai: fmtNum(p.x, 2) })}
                labelLang="en"
              />
            }
            table={<DataTable caption={oppTitle} rows={opp} columns={oppColumns} rowKey={(s) => s.id} defaultSort={{ key: 'ratio', dir: 'desc' }} limit={25} />}
          />
        </Section>
      ) : null}
      <Section id="all" title={sx('gl.all.h')}>
        <DataTable caption={t('table.n', { n: 2, title: sx('gl.all.table') })} rows={file.subfields} columns={columns(true)} rowKey={(s) => s.id} defaultSort={{ key: 'world', dir: 'desc' }} csvFilename={`atlas-${rel}-global.csv`} limit={50} />
      </Section>
      <p className="source">{sx('gl.source', { v: file.source })}</p>
    </div>
  )
}
