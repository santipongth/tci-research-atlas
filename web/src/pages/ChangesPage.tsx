import { Link } from 'react-router'
import { LineageKey } from '../charts/LineageKey'
import { StatusFlow } from '../charts/StatusFlow'
import { CsvButton } from '../components/CsvButton'
import { DataTable, type Column } from '../components/DataTable'
import { EmptyState } from '../components/EmptyState'
import { Figure } from '../components/Figure'
import { FeedLink } from '../embed/EmbedTools'
import { JournalLink } from '../components/JournalLink'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { StatGrid, StatTile } from '../components/StatTile'
import { StatusChip } from '../components/StatusGlyph'
import { TopicLink } from '../components/TopicLink'
import { useReleaseFile } from '../data/atlasContext'
import { hasModule, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { DiffFile, JournalsFile, KpiChange, Mover, StatusChange, Topic } from '../data/types'
import { fmtInt, fmtPp, kpiDelta, kpiDir, fmtShare } from '../lib/format'
import { useI18n, useStrings, nameIn } from '../lib/i18n'
import { STATUSES } from '../lib/status'
import { figureCsv } from '../lib/tableCsv'
import { statusName } from '../lib/topicText'
import { changesCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import type { StrKey } from '../strings'
import { execViz } from '../strings/execViz'
import { changes } from '../strings/changes'

export default function ChangesPage() {
  const sc = useStrings(changes)
  return (
    <RequireRelease title={sc('ch.title')}>
      {(release) =>
        !hasModule(release, 'diff') && !release.overview.previous_release ? (
          <div className="container">
            <PageHeader title={sc('ch.title')}>
              <FeedLink release={release} kind="releases" />
            </PageHeader>
            <EmptyState title={sc('ch.noPrevious')}><p>{sc('ch.noPreviousBody')}</p></EmptyState>
          </div>
        ) : (
          <ModuleFile<DiffFile> release={release} module="diff" path={MODULE_FILES.diff} title={sc('ch.title')}>
            {(diff) => <Changes release={release} diff={diff} />}
          </ModuleFile>
        )
      }
    </RequireRelease>
  )
}

function Changes({ release, diff }: { release: AtlasRelease; diff: DiffFile }) {
  const { t, lang, name } = useI18n()
  const sc = useStrings(changes)
  const x = useStrings(execViz)
  const [state, update] = useUrlState(changesCodec)
  const rel = release.overview.release
  const topicOf = (id: string) => release.topicById.get(id)
  const known = (id: string): boolean => release.topicById.has(id)
  const order = (s: string) => STATUSES.indexOf(s as (typeof STATUSES)[number])
  const retiredName = (id: string): string | null => {
    const r = diff.retired.find((x) => x.topic === id)
    return r ? nameIn(r, lang) || null : null
  }
  /** A parent is a current topic (link), a retired one (its old name) or just an id. */
  const parentNode = (p: string) => {
    const parent = topicOf(p)
    return parent ? <TopicLink topic={parent} /> : <span>{retiredName(p) ?? p}</span>
  }
  const kpiColumns: Column<KpiChange>[] = [
    { key: 'key', csvHeader: 'kpi', header: sc('col.kpi'), rowHeader: true, cell: (k) => t(`kpi.${k.key}` as StrKey), csv: (k) => k.key },
    { key: 'previous', csvHeader: 'previous', header: sc('col.previous'), numeric: true, cell: (k) => fmtInt(k.previous), csv: (k) => k.previous },
    { key: 'current', csvHeader: 'current', header: sc('col.current'), numeric: true, cell: (k) => fmtInt(k.current), csv: (k) => k.current },
    { key: 'change', header: sc('col.change'), numeric: true, cell: (k) => kpiDelta(k.current, k.previous, 'count', lang) ?? '' },
  ]
  const statusRows = diff.status_changes.filter((c) => known(c.topic))
  const statusColumns: Column<StatusChange>[] = [
    { key: 'topic', csvHeader: 'topic_id', header: t('col.topic'), rowHeader: true, cell: (c) => <TopicLink topic={topicOf(c.topic) as Topic} />, sortValue: (c) => name(topicOf(c.topic) as Topic), csv: (c) => c.topic },
    {
      key: 'change', header: t('col.status'), sortValue: (c) => order(c.current) * 10 + order(c.previous),
      cell: (c) => (
        <span className="st-change">
          <StatusChip status={c.previous} label={statusName(t, c.previous)} small />
          <span aria-hidden="true">→</span>
          <span className="sr-only">{t('to')}</span>
          <StatusChip status={c.current} label={statusName(t, c.current)} small />
        </span>
      ),
      csvCols: [{ header: 'previous', value: (c) => c.previous }, { header: 'current', value: (c) => c.current }],
    },
  ]
  const movers = diff.movers.filter((m) => known(m.topic))
  const moverColumns: Column<Mover>[] = [
    { key: 'topic', csvHeader: 'topic_id', header: t('col.topic'), rowHeader: true, cell: (m) => <TopicLink topic={topicOf(m.topic) as Topic} showStatus />, sortValue: (m) => name(topicOf(m.topic) as Topic), csv: (m) => m.topic },
    { key: 'previous', csvHeader: 'share_previous', header: sc('col.previous'), numeric: true, cell: (m) => fmtShare(m.share_previous, 2), sortValue: (m) => m.share_previous },
    { key: 'current', csvHeader: 'share_current', header: sc('col.current'), numeric: true, cell: (m) => fmtShare(m.share_current, 2), sortValue: (m) => m.share_current },
    { key: 'change', header: sc('col.change'), numeric: true, cell: (m) => fmtPp((m.share_current - m.share_previous) * 100, lang), sortValue: (m) => Math.abs(m.share_current - m.share_previous) },
  ]
  // examples for the intros: the first status change listed, and the biggest mover
  const firstChange = statusRows[0]
  const bigMover = movers.length ? movers.reduce((a, b) => (Math.abs(b.share_current - b.share_previous) > Math.abs(a.share_current - a.share_previous) ? b : a)) : null
  const fresh = diff.new_topics.filter((n) => known(n.topic))
  const restructured = (diff.restructured ?? []).filter((n) => known(n.topic))
  const journalsLinked = hasModule(release, 'journals')
  const jf = useReleaseFile<JournalsFile>(journalsLinked ? MODULE_FILES.journals : null)
  const journalById = new Map((jf.status === 'ready' ? jf.data.journals : []).map((j) => [j.id, j]))
  const unchanged = Math.max(0, release.topics.length - fresh.length - statusRows.length)
  const events = [...fresh, ...restructured]
  const lineage = [
    { kind: 'new' as const, title: x('xv.lin.new'), body: x('xv.lin.newB'), n: fresh.filter((n) => n.event !== 'split' && n.event !== 'merge').length },
    { kind: 'merge' as const, title: x('xv.lin.merge'), body: x('xv.lin.mergeB'), n: events.filter((n) => n.event === 'merge').length },
    { kind: 'split' as const, title: x('xv.lin.split'), body: x('xv.lin.splitB'), n: events.filter((n) => n.event === 'split').length },
    { kind: 'gone' as const, title: x('xv.lin.gone'), body: x('xv.lin.goneB'), n: diff.retired.length },
  ].map((l) => ({ kind: l.kind, title: l.title, body: l.body, count: x('xv.lin.n', { n: fmtInt(l.n) }) }))
  const statusTitle = t('table.n', { n: 1, title: sc('ch.status.table') })
  return (
    <div className="container">
      <PageHeader title={sc('ch.title')} lede={sc('ch.lede', { release: diff.release, prev: diff.previous_release })}>
        {diff.previous_source === 'output' ? <p className="note">{sc('ch.fromOutput', { prev: diff.previous_release })}</p> : null}
        <p className="ch-lead">
          <span className="ch-lead-k">{x('xv.ch.lead')}</span>
          <span><b>+{fmtInt(fresh.length)}</b> {x('xv.ch.new')}</span>
          <span><b>{fmtInt(statusRows.length)}</b> {x('xv.ch.changed')}</span>
          <span><b>{fmtInt(diff.retired.length)}</b> {x('xv.ch.gone')}</span>
        </p>
        <FeedLink release={release} kind="releases" />
      </PageHeader>
      {diff.kpis.length ? (
        <Section id="kpis" title={sc('ch.kpi.h')}>
          <div className="ch-kpi-tools">
            <CsvButton {...figureCsv(`atlas-${rel}-changes-totals.csv`, diff.kpis, kpiColumns)} />
          </div>
          <StatGrid cols={diff.kpis.length === 4 ? 4 : diff.kpis.length < 3 ? 2 : 3}>
            {diff.kpis.map((k, i) => {
              const d = kpiDelta(k.current, k.previous, 'count', lang)
              return (
                <StatTile
                  key={k.key}
                  label={t(`kpi.${k.key}` as StrKey)}
                  value={fmtInt(k.current)}
                  delta={d ? { text: d, dir: kpiDir(k.current, k.previous, 'count'), ref: t('delta', { prev: diff.previous_release }) } : null}
                  sub={`${sc('col.previous')}: ${fmtInt(k.previous)}`}
                  wide={diff.kpis.length > 4 && diff.kpis.length % 3 === 2 && i === diff.kpis.length - 1}
                />
              )
            })}
          </StatGrid>
        </Section>
      ) : null}
      <Section
        id="status"
        title={sc('ch.status.h')}
        intro={firstChange ? sc('ch.status.intro', { topic: name(topicOf(firstChange.topic) as Topic), from: statusName(t, firstChange.previous), to: statusName(t, firstChange.current) }) : undefined}
      >
        {statusRows.length ? (
          <Figure
            id="fig-flow"
            number={1}
            title={x('xv.fl.title')}
            tableTitle={statusTitle}
            csv={figureCsv(`atlas-${rel}-status-changes.csv`, statusRows, statusColumns)}
            how={<p>{x('xv.fl.how')}</p>}
            source={t('source.line', { release: rel })}
            view={state.flow}
            onView={(v) => update({ flow: v })}
            chart={
              <>
                <StatusFlow
                  changes={statusRows}
                  statusLabel={(st) => statusName(t, st)}
                  topicName={(id) => { const tp = topicOf(id); return tp ? name(tp) : id }}
                  heads={{ left: x('xv.fl.prev', { r: diff.previous_release }), right: x('xv.fl.cur', { r: diff.release }) }}
                  label={x('xv.fl.label', { n: fmtInt(statusRows.length) })}
                  bandTitle={(l) => x('xv.fl.band', { from: statusName(t, l.from), to: statusName(t, l.to), n: fmtInt(l.count) })}
                  moreText={(n) => x('xv.fl.more', { n: fmtInt(n) })}
                />
                {unchanged > 0 ? <p className="br-more">{x('xv.fl.same', { n: fmtInt(unchanged) })}</p> : null}
              </>
            }
            table={<DataTable caption={statusTitle} rows={statusRows} columns={statusColumns} rowKey={(c) => c.topic} defaultSort={{ key: 'change', dir: 'asc' }} limit={25} />}
          />
        ) : (
          <p className="note">{sc('ch.status.none')}</p>
        )}
      </Section>
      {fresh.length || restructured.length || diff.retired.length ? (
        <Section id="lineage" title={x('xv.lin.h')}>
          <LineageKey items={lineage} label={x('xv.lin.label')} />
        </Section>
      ) : null}
      {fresh.length ? (
        <Section id="new" title={sc('ch.new.h')}>
          <ul className="new-list">
            {fresh.map((n) => (
              <li key={n.topic}>
                <TopicLink topic={topicOf(n.topic) as Topic} showStatus />
                <span className="topic-sub">
                  {sc(n.event === 'split' ? 'ch.new.split' : n.event === 'merge' ? 'ch.new.merge' : 'ch.new.new')}
                  {(n.parents ?? []).map((p, i) => <span key={p}>{i ? ', ' : ' '}{parentNode(p)}</span>)}
                </span>
              </li>
            ))}
          </ul>
        </Section>
      ) : null}
      {restructured.length ? (
        <Section id="restructured" title={sc('ch.restructured.h')} intro={sc('ch.restructured.intro')}>
          <ul className="new-list">
            {restructured.map((n) => (
              <li key={n.topic}>
                <TopicLink topic={topicOf(n.topic) as Topic} showStatus />
                <span className="topic-sub">
                  {sc(n.event === 'split' ? 'ch.restructured.split' : 'ch.restructured.merge')}
                  {(n.parents ?? []).map((p, i) => <span key={p}>{i ? ', ' : ' '}{parentNode(p)}</span>)}
                </span>
              </li>
            ))}
          </ul>
        </Section>
      ) : null}
      {diff.retired.length ? (
        <Section id="retired" title={sc('ch.retired.h')} intro={sc('ch.retired.intro')}>
          <ul className="new-list">
            {diff.retired.map((r) => {
              const into = r.merged_into ? topicOf(r.merged_into) : undefined
              return (
                <li key={r.topic}>
                  <span lang={lang === 'en' && !r.en ? 'th' : undefined}>{nameIn(r, lang) || r.topic}</span>
                  <span className="topic-sub">
                    {r.merged_into
                      ? <>{sc('ch.retired.into')} {into ? <TopicLink topic={into} /> : r.merged_into}</>
                      : sc('ch.retired.ended')}
                    {' · '}{r.topic}
                  </span>
                </li>
              )
            })}
          </ul>
        </Section>
      ) : null}
      {movers.length ? (
        <Section id="movers" title={sc('ch.movers.h')} intro={bigMover ? sc('ch.movers.intro', { topic: name(topicOf(bigMover.topic) as Topic), a: fmtShare(bigMover.share_previous, 2), b: fmtShare(bigMover.share_current, 2) }) : undefined}>
          <DataTable caption={t('table.n', { n: 2, title: sc('ch.movers.table') })} rows={movers} columns={moverColumns} rowKey={(m) => m.topic} defaultSort={{ key: 'change', dir: 'desc' }} csvFilename={`atlas-${rel}-movers.csv`} limit={25} />
        </Section>
      ) : null}
      {diff.journals_compared && (diff.new_journals ?? []).length ? (
        <Section id="journals" title={sc('ch.journals.h')}>
          <ul className="kw-list">
            {(diff.new_journals ?? []).map((id) => {
              const j = journalById.get(id)
              return <li key={id}>{j ? <JournalLink journal={j} /> : journalsLinked ? <Link to={`/journals/${id}`}>{id}</Link> : id}</li>
            })}
          </ul>
        </Section>
      ) : null}
    </div>
  )
}
