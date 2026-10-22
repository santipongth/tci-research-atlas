import { Link } from 'react-router'
import { DataTable, type Column } from '../components/DataTable'
import { EmptyState } from '../components/EmptyState'
import { FeedLink } from '../embed/EmbedTools'
import { JournalLink } from '../components/JournalLink'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { StatusChip } from '../components/StatusGlyph'
import { TopicLink } from '../components/TopicLink'
import { useReleaseFile } from '../data/atlasContext'
import { hasModule, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { DiffFile, JournalsFile, KpiChange, Mover, StatusChange, Topic } from '../data/types'
import { fmtInt, fmtPct, fmtPp, kpiDelta } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { STATUSES } from '../lib/status'
import { statusName } from '../lib/topicText'
import type { StrKey } from '../strings'

export default function ChangesPage() {
  const { t } = useI18n()
  return (
    <RequireRelease title={t('ch.title')}>
      {(release) =>
        !hasModule(release, 'diff') && !release.overview.previous_release ? (
          <div className="container">
            <PageHeader title={t('ch.title')}>
              <FeedLink release={release} kind="releases" />
            </PageHeader>
            <EmptyState title={t('ch.noPrevious')}><p>{t('ch.noPreviousBody')}</p></EmptyState>
          </div>
        ) : (
          <ModuleFile<DiffFile> release={release} module="diff" path={MODULE_FILES.diff} title={t('ch.title')}>
            {(diff) => <Changes release={release} diff={diff} />}
          </ModuleFile>
        )
      }
    </RequireRelease>
  )
}

function Changes({ release, diff }: { release: AtlasRelease; diff: DiffFile }) {
  const { t, lang } = useI18n()
  const rel = release.overview.release
  const topicOf = (id: string) => release.topicById.get(id)
  const known = (id: string): boolean => release.topicById.has(id)
  const order = (s: string) => STATUSES.indexOf(s as (typeof STATUSES)[number])
  const retiredName = (id: string): string | null => {
    const r = diff.retired.find((x) => x.topic === id)
    return r ? (lang === 'en' ? r.en || r.th : r.th || r.en) || null : null
  }
  /** A parent is a current topic (link), a retired one (its old name) or just an id. */
  const parentNode = (p: string) => {
    const parent = topicOf(p)
    return parent ? <TopicLink topic={parent} /> : <span>{retiredName(p) ?? p}</span>
  }
  const kpiColumns: Column<KpiChange>[] = [
    { key: 'key', csvHeader: 'kpi', header: t('col.kpi'), rowHeader: true, cell: (k) => t(`kpi.${k.key}` as StrKey), csv: (k) => k.key },
    { key: 'previous', csvHeader: 'previous', header: t('col.previous'), numeric: true, cell: (k) => fmtInt(k.previous), csv: (k) => k.previous },
    { key: 'current', csvHeader: 'current', header: t('col.current'), numeric: true, cell: (k) => fmtInt(k.current), csv: (k) => k.current },
    { key: 'change', header: t('col.change'), numeric: true, cell: (k) => kpiDelta(k.current, k.previous, 'count', lang) ?? '' },
  ]
  const statusRows = diff.status_changes.filter((c) => known(c.topic))
  const statusColumns: Column<StatusChange>[] = [
    { key: 'topic', csvHeader: 'topic_id', header: t('col.topic'), rowHeader: true, cell: (c) => <TopicLink topic={topicOf(c.topic) as Topic} />, sortValue: (c) => c.topic, csv: (c) => c.topic },
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
    { key: 'topic', csvHeader: 'topic_id', header: t('col.topic'), rowHeader: true, cell: (m) => <TopicLink topic={topicOf(m.topic) as Topic} showStatus />, sortValue: (m) => m.topic, csv: (m) => m.topic },
    { key: 'previous', csvHeader: 'share_previous', header: t('col.previous'), numeric: true, cell: (m) => fmtPct(m.share_previous, 2), sortValue: (m) => m.share_previous },
    { key: 'current', csvHeader: 'share_current', header: t('col.current'), numeric: true, cell: (m) => fmtPct(m.share_current, 2), sortValue: (m) => m.share_current },
    { key: 'change', header: t('col.change'), numeric: true, cell: (m) => fmtPp((m.share_current - m.share_previous) * 100, lang), sortValue: (m) => Math.abs(m.share_current - m.share_previous) },
  ]
  const fresh = diff.new_topics.filter((n) => known(n.topic))
  const restructured = (diff.restructured ?? []).filter((n) => known(n.topic))
  const journalsLinked = hasModule(release, 'journals')
  const jf = useReleaseFile<JournalsFile>(journalsLinked ? MODULE_FILES.journals : null)
  const journalById = new Map((jf.status === 'ready' ? jf.data.journals : []).map((j) => [j.id, j]))
  return (
    <div className="container">
      <PageHeader title={t('ch.title')} lede={t('ch.lede', { release: diff.release, prev: diff.previous_release })}>
        {diff.previous_source === 'output' ? <p className="note">{t('ch.fromOutput', { prev: diff.previous_release })}</p> : null}
        <FeedLink release={release} kind="releases" />
      </PageHeader>
      {diff.kpis.length ? (
        <Section id="kpis" title={t('ch.kpi.h')}>
          <DataTable caption={t('table.n', { n: 1, title: t('ch.kpi.table') })} rows={diff.kpis} columns={kpiColumns} rowKey={(k) => k.key} stack={false} csvFilename={`atlas-${rel}-changes-totals.csv`} />
        </Section>
      ) : null}
      <Section id="status" title={t('ch.status.h')}>
        <DataTable caption={t('table.n', { n: 2, title: t('ch.status.table') })} rows={statusRows} columns={statusColumns} rowKey={(c) => c.topic} defaultSort={{ key: 'change', dir: 'asc' }} empty={t('ch.status.none')} csvFilename={`atlas-${rel}-status-changes.csv`} />
      </Section>
      {fresh.length ? (
        <Section id="new" title={t('ch.new.h')}>
          <ul className="new-list">
            {fresh.map((n) => (
              <li key={n.topic}>
                <TopicLink topic={topicOf(n.topic) as Topic} showStatus />
                <span className="topic-sub">
                  {t(n.event === 'split' ? 'ch.new.split' : n.event === 'merge' ? 'ch.new.merge' : 'ch.new.new')}
                  {(n.parents ?? []).map((p, i) => <span key={p}>{i ? ', ' : ' '}{parentNode(p)}</span>)}
                </span>
              </li>
            ))}
          </ul>
        </Section>
      ) : null}
      {restructured.length ? (
        <Section id="restructured" title={t('ch.restructured.h')} intro={t('ch.restructured.intro')}>
          <ul className="new-list">
            {restructured.map((n) => (
              <li key={n.topic}>
                <TopicLink topic={topicOf(n.topic) as Topic} showStatus />
                <span className="topic-sub">
                  {t(n.event === 'split' ? 'ch.restructured.split' : 'ch.restructured.merge')}
                  {(n.parents ?? []).map((p, i) => <span key={p}>{i ? ', ' : ' '}{parentNode(p)}</span>)}
                </span>
              </li>
            ))}
          </ul>
        </Section>
      ) : null}
      {diff.retired.length ? (
        <Section id="retired" title={t('ch.retired.h')} intro={t('ch.retired.intro')}>
          <ul className="new-list">
            {diff.retired.map((r) => {
              const into = r.merged_into ? topicOf(r.merged_into) : undefined
              return (
                <li key={r.topic}>
                  <span lang={lang === 'en' && !r.en ? 'th' : undefined}>{(lang === 'en' ? r.en || r.th : r.th || r.en) || r.topic}</span>
                  <span className="topic-sub">
                    {r.merged_into
                      ? <>{t('ch.retired.into')} {into ? <TopicLink topic={into} /> : r.merged_into}</>
                      : t('ch.retired.ended')}
                    {' · '}{r.topic}
                  </span>
                </li>
              )
            })}
          </ul>
        </Section>
      ) : null}
      {movers.length ? (
        <Section id="movers" title={t('ch.movers.h')} intro={t('ch.movers.intro')}>
          <DataTable caption={t('table.n', { n: 3, title: t('ch.movers.table') })} rows={movers} columns={moverColumns} rowKey={(m) => m.topic} defaultSort={{ key: 'change', dir: 'desc' }} csvFilename={`atlas-${rel}-movers.csv`} />
        </Section>
      ) : null}
      {diff.journals_compared && (diff.new_journals ?? []).length ? (
        <Section id="journals" title={t('ch.journals.h')}>
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
