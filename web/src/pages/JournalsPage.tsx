import type { ScatterPoint } from '../charts/editorLayout'
import { BarRank } from '../charts/BarRank'
import { rankBars } from '../charts/infographic'
import { JournalScatter } from '../charts/JournalScatter'
import { Card, DashGrid, DashStack } from '../components/dashboard/Card'
import { KpiCard, KpiRow } from '../components/dashboard/KpiCard'
import { MoreRows, RankRows } from '../components/dashboard/RankRows'
import { PageBar } from '../components/dashboard/PageBar'
import { Segmented } from '../components/dashboard/Segmented'
import { ModuleFile } from '../components/ModuleFile'
import { RequireRelease } from '../components/RequireRelease'
import { StatusChip } from '../components/StatusGlyph'
import { useReleaseFile } from '../data/atlasContext'
import { groupName, hasModule, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { JournalSummary, JournalsFile, MethodsFile, ReferencesFile, Topic } from '../data/types'
import { fmtInt, fmtNum, fmtPct } from '../lib/format'
import { useI18n, useStrings } from '../lib/i18n'
import { journalName } from '../lib/journals'
import { sortBy } from '../lib/sort'
import { statusName } from '../lib/topicText'
import { usePaged } from '../lib/usePaged'
import { journalsCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import { dashPages } from '../strings/dashPages'
import { editorViz } from '../strings/editorViz'
import { journals } from '../strings/journals'

export default function JournalsPage() {
  const sj = useStrings(journals)
  return (
    <RequireRelease title={sj('jr.title')}>
      {(release) => (
        <ModuleFile<JournalsFile> release={release} module="journals" path={MODULE_FILES.journals} title={sj('jr.title')}>
          {(file) => <Journals release={release} file={file} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

/** The journals at a glance: KPIs, completeness × own-institution authors, tiers, every journal, openings, methods, citations. */
function Journals({ release, file }: { release: AtlasRelease; file: JournalsFile }) {
  const sj = useStrings(journals)
  const s = useStrings(dashPages)
  const w = file.window
  const active = file.journals.filter((j) => j.articles_window > 0)
  const articles = active.reduce((n, j) => n + j.articles_window, 0)
  const complete = active.filter((j) => j.completeness != null)
  const meanComplete = complete.length ? complete.reduce((n, j) => n + (j.completeness ?? 0), 0) / complete.length : null
  const tier1 = file.journals.filter((j) => j.tci_tier === 1).length
  const methods = hasModule(release, 'methods')
  const refs = hasModule(release, 'references')
  return (
    <>
      <PageBar
        title={sj('jr.title')}
        sub={s('jr.sub', { n: fmtInt(file.journals.length), a: w.start, b: w.end })}
        info={sj('jr.lede', { release: release.overview.release, n: fmtInt(file.journals.length), a: w.start, b: w.end })}
      />
      <div className="dash">
        <KpiRow>
          <KpiCard icon="journals" label={s('jr.k.journals')} value={fmtInt(file.journals.length)} />
          <KpiCard icon="articles" label={s('jr.k.articles', { a: w.start, b: w.end })} value={fmtInt(articles)} />
          {meanComplete !== null ? <KpiCard icon="layers" label={s('jr.k.complete')} value={fmtNum(meanComplete, 0)} sub={s('jr.k.of100')} /> : null}
          {tier1 ? <KpiCard icon="goals" label={s('jr.k.tier1')} value={fmtInt(tier1)} /> : null}
        </KpiRow>
        <DashGrid>
          <ScatterCard file={file} />
          <DashStack span={4}>
            <TiersCard file={file} />
            <SpecialIssueCard release={release} file={file} />
          </DashStack>
        </DashGrid>
        <DashGrid>
          <ListCard release={release} file={file} span={methods ? 7 : 12} />
          {methods ? <MethodsCard /> : null}
        </DashGrid>
        {refs ? (
          <DashGrid>
            <CitedCard release={release} />
          </DashGrid>
        ) : null}
      </div>
    </>
  )
}

/** Record completeness (x) against authors from the journal's own institution (y), one dot per journal. */
function ScatterCard({ file }: { file: JournalsFile }) {
  const { lang } = useI18n()
  const s = useStrings(dashPages)
  const e = useStrings(editorViz)
  const plotted = file.journals.filter((j) => j.completeness != null && j.inhouse_share != null)
  if (!plotted.length) return null
  const flagAt = file.inhouse_flag_share ?? null
  const byId = new Map(plotted.map((j) => [j.id, j]))
  const points: ScatterPoint[] = plotted.map((j) => ({ id: j.id, label: journalName(j, lang).text, x: j.completeness as number, y: j.inhouse_share as number, weight: j.articles_window, inferred: j.owner_source === 'inferred' }))
  return (
    <Card span={8} title={e('js.fig')} info={s('jr.scatterInfo')}>
      <JournalScatter
        points={points}
        yRef={flagAt}
        text={{ x: e('js.x'), y: e('js.y'), zone: flagAt != null ? e('js.zone', { p: fmtPct(flagAt, 0) }) : '', owner: e('js.owner'), inferred: e('js.inferred') }}
        label={e('js.label', { n: fmtInt(points.length) })}
        pct={(v, d) => fmtPct(v, d)}
        describe={(p) => {
          const j = byId.get(p.id) as JournalSummary
          return e('js.tip', { j: p.label, c: fmtNum(p.x, 1), p: fmtPct(p.y, 0), n: fmtInt(j.articles_window) })
        }}
      />
    </Card>
  )
}

/** Journals per TCI tier. */
function TiersCard({ file }: { file: JournalsFile }) {
  const s = useStrings(dashPages)
  const counts = new Map<string, number>()
  for (const j of file.journals) {
    const k = j.tci_tier ? String(j.tci_tier) : 'none'
    counts.set(k, (counts.get(k) ?? 0) + 1)
  }
  const order = ['1', '2', '3', 'none'].filter((k) => counts.has(k))
  if (!order.length) return null
  const max = Math.max(...order.map((k) => counts.get(k) ?? 0))
  const rows = order.map((k) => ({ key: k === 'none' ? s('jr.tier.none') : s('jr.tier.n', { n: k }), id: k, count: counts.get(k) ?? 0, frac: max ? (counts.get(k) ?? 0) / max : 0 }))
  return (
    <Card span={12} title={s('jr.tiers')} info={s('jr.tiersInfo')}>
      <BarRank rows={rows} value={(r) => fmtInt(r.count)} label={s('jr.tiers')} />
    </Card>
  )
}

/** Every journal, ten at a time, by articles or by record completeness. */
function ListCard({ release, file, span }: { release: AtlasRelease; file: JournalsFile; span: 7 | 12 }) {
  const { lang } = useI18n()
  const s = useStrings(dashPages)
  const [state, update] = useUrlState(journalsCodec)
  const ranked = state.by === 'complete' ? sortBy(sortBy(file.journals, (j) => j.articles_window, 'desc'), (j) => j.completeness ?? -1, 'desc') : sortBy(file.journals, (j) => j.articles_window, 'desc')
  const page = usePaged(ranked, 10, state.by)
  return (
    <Card span={span} title={s('jr.list')} info={s('jr.listInfo')}>
      <Segmented label={s('jr.by')} value={state.by} onChange={(by) => update({ by })} options={[{ id: 'articles', label: s('jr.by.articles') }, { id: 'complete', label: s('jr.by.complete') }]} />
      <RankRows
        label={s('jr.list')}
        rows={page.shown.map((j) => {
          const n = journalName(j, lang)
          const tier = j.tci_tier ? s('jr.tier.n', { n: j.tci_tier }) : null
          const field = j.group ? groupName(release, j.group, lang) : null
          return {
            key: j.id,
            to: `/journals/${j.id}`,
            name: n.text,
            nameLang: n.lang ?? undefined,
            meta: <span className="rise-sub">{[tier, field].filter(Boolean).join(' · ')}</span>,
            value: state.by === 'complete' && j.completeness != null ? <b className="rise-a">{s('jr.complete', { c: fmtNum(j.completeness, 0) })}</b> : <b className="rise-a">{fmtInt(j.articles_window)}</b>,
          }
        })}
      />
      <MoreRows {...page.more} />
    </Card>
  )
}

/** Growing topics only a few journals carry: an opening for a special issue. */
function SpecialIssueCard({ release, file }: { release: AtlasRelease; file: JournalsFile }) {
  const { t, name } = useI18n()
  const sj = useStrings(journals)
  const s = useStrings(dashPages)
  const rows = sortBy(sortBy((file.special_issue ?? []).filter((x) => release.topicById.has(x.topic)), (x) => x.articles_recent, 'desc'), (x) => x.hosts, 'asc')
  const page = usePaged(rows, 8)
  if (!rows.length) return null
  const r = file.recent
  return (
    <Card
      span={12}
      title={s('jr.si')}
      info={sj('jr.si.intro', {
        topic: name(release.topicById.get(rows[0].topic) as Topic), h: fmtInt(rows[0].hosts),
        statuses: (file.special_issue_statuses ?? []).map((st) => statusName(t, st)).join(' / '),
        max: fmtInt(file.special_issue_max_hosts ?? 0), a: r.start, b: r.end,
      }) + ' ' + sj('jr.si.how', { min: fmtInt(file.special_issue_min_host_articles ?? 1) })}
    >
      <RankRows
        label={s('jr.si')}
        rows={page.shown.map((x) => {
          const tp = release.topicById.get(x.topic) as Topic
          return { key: x.topic, to: `/topics/${tp.id}`, name: name(tp), meta: <StatusChip status={tp.status} label={statusName(t, tp.status)} small />, value: <b className="rise-a">{s('jr.siN', { n: fmtInt(x.hosts) })}</b> }
        })}
      />
      <MoreRows {...page.more} />
    </Card>
  )
}

/** The research methods used most across the corpus (share of articles). */
function MethodsCard() {
  const { lang } = useI18n()
  const s = useStrings(dashPages)
  const file = useReleaseFile<MethodsFile>(MODULE_FILES.methods)
  if (file.status !== 'ready') return null
  const names = new Map(file.data.methods.map((m) => [m.key, lang === 'en' ? m.en : m.th]))
  const bars = rankBars(file.data.corpus.map((m) => ({ key: names.get(m.method) ?? m.method, id: m.method, count: m.share })), 8)
  if (!bars.rows.length) return null
  return (
    <Card span={5} title={s('jr.methods')} info={s('jr.methodsInfo', { a: file.data.window.start, b: file.data.window.end })}>
      <BarRank rows={bars.rows} value={(r) => fmtPct(r.count, 0)} label={s('jr.methods')} />
    </Card>
  )
}

/** The articles cited most by other articles in TCI journals (references.json, when the matches are there). */
function CitedCard({ release }: { release: AtlasRelease }) {
  const { lang } = useI18n()
  const s = useStrings(dashPages)
  const file = useReleaseFile<ReferencesFile>(MODULE_FILES.references)
  const top = file.status === 'ready' ? (file.data.internal?.top_articles ?? []) : []
  const page = usePaged(top, 6)
  if (!top.length) return null
  return (
    <Card span={12} title={s('jr.cited')} info={s('jr.citedInfo')}>
      <RankRows
        label={s('jr.cited')}
        rows={page.shown.map((a) => {
          const tp = a.topic ? release.topicById.get(a.topic) : undefined
          const title = lang === 'en' && a.title_en ? a.title_en : a.title
          return {
            key: a.article_id,
            to: tp ? `/topics/${tp.id}` : null,
            name: title,
            meta: <span className="rise-sub">{[a.journal, a.year].filter(Boolean).join(' · ')}</span>,
            value: <b className="rise-a">{s('jr.citedN', { n: fmtInt(a.count) })}</b>,
          }
        })}
      />
      <MoreRows {...page.more} />
    </Card>
  )
}
