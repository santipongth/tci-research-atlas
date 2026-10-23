import { PortfolioMatrix } from '../charts/PortfolioMatrix'
import { BarRank } from '../charts/BarRank'
import { rankBars } from '../charts/infographic'
import { Card, DashGrid, SeeAll } from '../components/dashboard/Card'
import { MoreRows, RankRows, type RankRow } from '../components/dashboard/RankRows'
import { PageBar } from '../components/dashboard/PageBar'
import { Segmented } from '../components/dashboard/Segmented'
import { EmptyState } from '../components/EmptyState'
import { FeedLink } from '../embed/EmbedTools'
import { RequireRelease } from '../components/RequireRelease'
import { StatusChip, StatusGlyph } from '../components/StatusGlyph'
import { StatusLegend } from '../components/StatusLegend'
import { useReleaseFile } from '../data/atlasContext'
import { groupName, hasModule, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { DiffFile, GapsFile, Topic } from '../data/types'
import { DEFINITION, largeShareThreshold, quadrantOf, ruleVars, windows, fmtWindow, QUADRANTS, type Quadrant } from '../lib/definition'
import { ciPct, fmtInt, fmtPct, fmtSignedPct } from '../lib/format'
import { useI18n, useStrings } from '../lib/i18n'
import { sortBy } from '../lib/sort'
import { STATUSES, type StatusId } from '../lib/status'
import { statusMeaning, statusName } from '../lib/topicText'
import { usePaged } from '../lib/usePaged'
import { topicsCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import { dashPages } from '../strings/dashPages'

/** Topic rows shown at a time in the status list. */
const STEP = 10

export default function TopicsPage() {
  const s = useStrings(dashPages)
  return <RequireRelease title={s('tp.title')}>{(release) => <Topics release={release} />}</RequireRelease>
}

const seriesOf = (release: AtlasRelease, tp: Topic) => (release.series.topics[tp.id] ?? []).map((v) => (Number.isFinite(v) ? v : null))

/** What is rising, what is falling: the topics by status, what changed since the last release, and where the openings are. */
function Topics({ release }: { release: AtlasRelease }) {
  const { t, lang } = useI18n()
  const s = useStrings(dashPages)
  const [state, update] = useUrlState(topicsCodec)
  const ov = release.overview
  if (!release.topics.length) {
    return (
      <>
        <PageBar title={s('tp.title')} />
        <div className="dash"><EmptyState title={t('empty.topics')} /></div>
      </>
    )
  }
  return (
    <>
      <PageBar
        title={s('tp.title')}
        sub={s('tp.sub', { n: fmtInt(release.topics.length), g: fmtInt(release.groupById.size), year: ov.last_complete_year })}
        info={s('tp.info')}
        actions={
          <>
            <FeedLink release={release} kind="releases" />
            <SeeAll to="/atlas" label={s('tp.atlas')} />
          </>
        }
      />
      <div className="dash">
        <StatusPicker release={release} value={state.status} onChange={(status) => update({ status })} />
        <DashGrid>
          <StatusList release={release} status={state.status} by={state.status === 'LOW_DATA' ? 'size' : state.by} onBy={(by) => update({ by })} />
          {hasModule(release, 'diff') && ov.previous_release ? <ChangesCard release={release} /> : <KeywordsCard release={release} span={4} />}
        </DashGrid>
        <DashGrid>
          <PortfolioCard release={release} />
          {hasModule(release, 'diff') && ov.previous_release ? <KeywordsCard release={release} span={4} /> : <GroupsCard release={release} span={4} lang={lang} />}
        </DashGrid>
        <DashGrid>
          {hasModule(release, 'gaps') ? <GapsCard release={release} /> : null}
          {hasModule(release, 'diff') && ov.previous_release ? <GroupsCard release={release} span={hasModule(release, 'gaps') ? 6 : 12} lang={lang} /> : null}
        </DashGrid>
      </div>
    </>
  )
}

/** Six status buttons with their counts: the page's filter (glyph + colour + name, never colour alone). */
function StatusPicker({ release, value, onChange }: { release: AtlasRelease; value: StatusId; onChange: (s: StatusId) => void }) {
  const { t } = useI18n()
  const s = useStrings(dashPages)
  return (
    <div className="st-pick" role="group" aria-label={s('tp.pick')}>
      {STATUSES.map((st) => {
        const n = release.topics.filter((tp) => tp.status === st).length
        return (
          <button key={st} type="button" className={`st-pick-b is-${st}`} aria-pressed={value === st} onClick={() => onChange(st)}>
            <span className="st-pick-name">
              <StatusGlyph status={st} size={13} />
              {statusName(t, st)}
            </span>
            <span className="st-pick-n">{fmtInt(n)}</span>
            <span className="st-pick-m">{statusMeaning(t, st)}</span>
          </button>
        )
      })}
    </div>
  )
}

/** The topics of the chosen status, ranked by growth or by size, ten at a time. */
function StatusList({ release, status, by, onBy }: { release: AtlasRelease; status: StatusId; by: 'growth' | 'size'; onBy: (b: 'growth' | 'size') => void }) {
  const { t, name, lang } = useI18n()
  const s = useStrings(dashPages)
  const level = ciPct(release.ciLevel)
  const all = release.topics.filter((tp) => tp.status === status)
  const ranked = by === 'growth' ? sortBy(sortBy(all, (tp) => tp.metrics.share_recent, 'desc'), (tp) => tp.metrics.share_growth, 'desc') : sortBy(all, (tp) => tp.metrics.count_recent, 'desc')
  const page = usePaged(ranked, STEP, `${status}:${by}`)
  const rows: RankRow[] = page.shown.map((tp) => ({
    key: tp.id,
    to: `/topics/${tp.id}`,
    name: name(tp),
    meta: <span className="rise-sub">{groupName(release, tp.group, lang)}</span>,
    value:
      by === 'growth' && tp.metrics.share_growth != null ? (
        <b className={tp.metrics.share_growth < 0 ? 'rise-g is-down' : 'rise-g'}>{s('tp.perYear', { g: fmtSignedPct(tp.metrics.share_growth, 0) })}</b>
      ) : (
        <b className="rise-a">{s('tp.articles', { n: fmtInt(tp.metrics.count_recent) })}</b>
      ),
    trend: seriesOf(release, tp),
  }))
  return (
    <Card
      span={8}
      title={s('tp.list', { status: statusName(t, status), n: fmtInt(all.length) })}
      info={<>{statusMeaning(t, status)} — {t(`rule.${status}` as const, ruleVars(level))}</>}
    >
      {status !== 'LOW_DATA' && all.length > 1 ? (
        <Segmented label={s('tp.by')} value={by} onChange={onBy} options={[{ id: 'growth', label: s('tp.by.growth') }, { id: 'size', label: s('tp.by.size') }]} />
      ) : null}
      {rows.length ? <RankRows rows={rows} label={s('tp.list', { status: statusName(t, status), n: fmtInt(all.length) })} /> : <p className="card-empty">{s('tp.none')}</p>}
      <MoreRows {...page.more} />
    </Card>
  )
}

/** What changed since the last release: three counts, then the topics whose status moved (old → new). */
function ChangesCard({ release }: { release: AtlasRelease }) {
  const { t, name } = useI18n()
  const s = useStrings(dashPages)
  const file = useReleaseFile<DiffFile>(MODULE_FILES.diff)
  const prev = release.overview.previous_release ?? ''
  if (file.status === 'loading') return <Card span={4} title={s('tp.changes', { prev })}><p className="loading" role="status">{t('loading')}</p></Card>
  if (file.status !== 'ready') return null
  const d = file.data
  const changes = d.status_changes
    .map((c) => ({ c, tp: release.topicById.get(c.topic) }))
    .filter((x): x is { c: (typeof d.status_changes)[number]; tp: Topic } => x.tp !== undefined)
  // the moves that matter first: into a rising status, then the rest
  const rank = (st: string) => (st === 'EMERGING' || st === 'HOT' ? 0 : st === 'WATCH' ? 1 : st === 'DECLINING' ? 2 : 3)
  const top = sortBy(changes, (x) => rank(x.c.current), 'asc').slice(0, 5)
  return (
    <Card span={4} title={s('tp.changes', { prev })} info={s('tp.changesInfo')}>
      <dl className="mini-stats">
        <div><dt>{s('tp.ch.new')}</dt><dd>{fmtInt(d.new_topics.length)}</dd></div>
        <div><dt>{s('tp.ch.moved')}</dt><dd>{fmtInt(d.status_changes.length)}</dd></div>
        <div><dt>{s('tp.ch.gone')}</dt><dd>{fmtInt(d.retired.length)}</dd></div>
      </dl>
      {top.length ? (
        <>
          <p className="card-h3">{s('tp.ch.list')}</p>
          <RankRows
            numbered={false}
            label={s('tp.ch.list')}
            rows={top.map(({ c, tp }) => ({
              key: tp.id,
              to: `/topics/${tp.id}`,
              name: name(tp),
              meta: (
                <span className="moved">
                  <StatusChip status={c.previous as StatusId} label={statusName(t, c.previous as StatusId)} small />
                  <span aria-hidden="true">→</span>
                  <StatusChip status={c.current as StatusId} label={statusName(t, c.current as StatusId)} small />
                </span>
              ),
            }))}
          />
        </>
      ) : null}
    </Card>
  )
}

/** Size × growth of every topic (the four portfolio corners), the chart from the old overview. */
function PortfolioCard({ release }: { release: AtlasRelease }) {
  const { t } = useI18n()
  const s = useStrings(dashPages)
  const threshold = largeShareThreshold(release.topics)
  if (threshold === null) return null
  const topics = release.topics.filter((tp) => tp.metrics.share_recent > 0 && quadrantOf(tp, threshold) !== null)
  if (!topics.length) return null
  const w = fmtWindow(windows(release.overview.last_complete_year).R)
  const counts = Object.fromEntries(QUADRANTS.map((q) => [q, topics.filter((tp) => quadrantOf(tp, threshold) === q).length])) as Record<Quadrant, number>
  const quad = (q: Quadrant) => t(`quad.${q}` as const)
  return (
    <Card span={8} title={s('tp.pf')} info={s('tp.pfInfo')}>
      <StatusLegend statuses={STATUSES.filter((st) => st !== 'LOW_DATA')} />
      <PortfolioMatrix
        topics={topics}
        threshold={threshold}
        ciLevel={release.ciLevel}
        counts={counts}
        labels={{ name: s('tp.pf'), x: t('ov.pf.x', { w }), y: t('ov.pf.y'), split: t('ov.pf.split', { v: fmtPct(threshold, 2) }), quadrants: { stars: quad('stars'), rising: quad('rising'), mature: quad('mature'), declining: quad('declining') } }}
      />
    </Card>
  )
}

/** Emerging author keywords, fastest growth first, each linking to the topic it belongs to. */
function KeywordsCard({ release, span }: { release: AtlasRelease; span: 4 | 6 }) {
  const { t, name } = useI18n()
  const s = useStrings(dashPages)
  const kw = sortBy((release.keywords ?? []).filter((k) => k.emerging), (k) => k.growth, 'desc')
  const page = usePaged(kw, 8)
  if (!kw.length) return null
  return (
    <Card span={span} title={s('tp.kw')} info={<>{s('tp.kwInfo')} ({t('em.kw.intro', { k: kw[0].term, b: fmtWindow(windows(release.overview.last_complete_year).B), o: DEFINITION.minOrgs, ky: DEFINITION.keywordMinActiveYears })})</>}>
      <RankRows
        label={s('tp.kw')}
        rows={page.shown.map((k) => {
          const tp = k.topic ? release.topicById.get(k.topic) : undefined
          return {
            key: k.term,
            to: tp ? `/topics/${tp.id}` : null,
            name: k.term,
            meta: tp ? <span className="rise-sub">{name(tp)}</span> : undefined,
            value: <b className="rise-g">{s('tp.perYear', { g: fmtSignedPct(k.growth, 0) })}</b>,
          }
        })}
      />
      <MoreRows {...page.more} />
    </Card>
  )
}

/** Growing topics only a few institutions work on (gaps.json), fewest institutions first. */
function GapsCard({ release }: { release: AtlasRelease }) {
  const { t, name } = useI18n()
  const s = useStrings(dashPages)
  const file = useReleaseFile<GapsFile>(MODULE_FILES.gaps)
  const few = file.status === 'ready' ? sortBy(file.data.few_institutions.filter((f) => release.topicById.has(f.topic)), (f) => f.institutions, 'asc') : []
  const page = usePaged(few, 6)
  if (file.status !== 'ready' || !few.length) return null
  const r = file.data.recent
  return (
    <Card span={6} title={s('tp.gaps')} info={s('tp.gapsInfo', { a: r.start, b: r.end })}>
      <RankRows
        label={s('tp.gaps')}
        rows={page.shown.map((f) => {
          const tp = release.topicById.get(f.topic) as Topic
          return { key: f.topic, to: `/topics/${tp.id}`, name: name(tp), meta: <StatusChip status={tp.status} label={statusName(t, tp.status)} small />, value: <b className="rise-a">{s('tp.gapsN', { n: fmtInt(f.institutions) })}</b> }
        })}
      />
      <MoreRows {...page.more} />
    </Card>
  )
}

/** Topics per main field, with how many of them are rising (emerging or hot). */
function GroupsCard({ release, span, lang }: { release: AtlasRelease; span: 4 | 6 | 12; lang: 'th' | 'en' }) {
  const s = useStrings(dashPages)
  const by = new Map<string, { n: number; up: number }>()
  for (const tp of release.topics) {
    const g = by.get(tp.group) ?? { n: 0, up: 0 }
    g.n += 1
    if (tp.status === 'EMERGING' || tp.status === 'HOT') g.up += 1
    by.set(tp.group, g)
  }
  const bars = rankBars([...by.entries()].map(([id, g]) => ({ key: groupName(release, id, lang), id, count: g.n })), 8)
  if (!bars.rows.length) return null
  return (
    <Card span={span} title={s('tp.groups')} info={s('tp.groupsInfo')}>
      <BarRank
        rows={bars.rows}
        label={s('tp.groups')}
        value={(r) => {
          const up = by.get(r.id ?? '')?.up ?? 0
          return up ? `${fmtInt(r.count)} · ${s('tp.groupsRising', { n: fmtInt(up) })}` : fmtInt(r.count)
        }}
      />
    </Card>
  )
}
