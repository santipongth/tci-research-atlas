import { goalTiles } from '../charts/execLayout'
import { GoalTiles } from '../charts/GoalTiles'
import { OpportunityQuadrant } from '../charts/OpportunityQuadrant'
import { Card, DashGrid } from '../components/dashboard/Card'
import { KpiCard, KpiRow } from '../components/dashboard/KpiCard'
import { MoreRows, RankRows } from '../components/dashboard/RankRows'
import { PageBar } from '../components/dashboard/PageBar'
import { Segmented } from '../components/dashboard/Segmented'
import { EmptyState } from '../components/EmptyState'
import { RequireRelease } from '../components/RequireRelease'
import { StatusChip } from '../components/StatusGlyph'
import { TopicLink } from '../components/TopicLink'
import { useReleaseFile } from '../data/atlasContext'
import { hasModule, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { GapsFile, GlobalFile, GoalStat, SdgFile, Topic } from '../data/types'
import { fmtInt, fmtNum, fmtPct, fmtShare, yearSpan } from '../lib/format'
import { useI18n, useStrings } from '../lib/i18n'
import { sortBy } from '../lib/sort'
import { statusName } from '../lib/topicText'
import { usePaged } from '../lib/usePaged'
import { goalsCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import { dashPages } from '../strings/dashPages'
import { execPages } from '../strings/execPages'
import { execViz } from '../strings/execViz'

/** Topics listed in an open goal tile. */
const TILE_TOPICS = 6

export default function GoalsPage() {
  const s = useStrings(dashPages)
  return <RequireRelease title={s('gl.title')}>{(release) => <GoalsLoad release={release} />}</RequireRelease>
}

/** sdg.json, global.json and gaps.json are each optional; every card shows when its file is there. */
function GoalsLoad({ release }: { release: AtlasRelease }) {
  const { t } = useI18n()
  const s = useStrings(dashPages)
  const on = { sdg: hasModule(release, 'sdg'), global: hasModule(release, 'global'), gaps: hasModule(release, 'gaps') }
  const sdg = useReleaseFile<SdgFile>(on.sdg ? MODULE_FILES.sdg : null)
  const glob = useReleaseFile<GlobalFile>(on.global ? MODULE_FILES.global : null)
  const gaps = useReleaseFile<GapsFile>(on.gaps ? MODULE_FILES.gaps : null)
  const bar = <PageBar title={s('gl.title')} sub={s('gl.sub')} info={s('gl.info')} />
  const skipped = release.manifest.skipped_modules?.global ?? null
  if (!on.sdg && !on.global && !on.gaps) {
    return (
      <>
        {bar}
        <div className="dash">
          <EmptyState title={t('mod.absent')}>
            <p>{t('mod.absentBody')}</p>
            {skipped ? <p>{t('mod.skipped')} <span lang="en">{skipped}</span></p> : null}
          </EmptyState>
        </div>
      </>
    )
  }
  if ((on.sdg && sdg.status === 'loading') || (on.global && glob.status === 'loading') || (on.gaps && gaps.status === 'loading')) {
    return (
      <>
        {bar}
        <div className="dash"><p className="loading" role="status">{t('loading')}</p></div>
      </>
    )
  }
  return (
    <>
      {bar}
      <Goals
        release={release}
        sdg={sdg.status === 'ready' ? sdg.data : null}
        glob={glob.status === 'ready' ? glob.data : null}
        gaps={gaps.status === 'ready' ? gaps.data : null}
        skipped={on.global ? null : skipped}
      />
    </>
  )
}

function Goals({ release, sdg, glob, gaps, skipped }: { release: AtlasRelease; sdg: SdgFile | null; glob: GlobalFile | null; gaps: GapsFile | null; skipped: string | null }) {
  const { t, lang } = useI18n()
  const s = useStrings(dashPages)
  const [state, update] = useUrlState(goalsCodec)
  const name = (o: { th: string; en: string }) => (lang === 'en' ? o.en : o.th)
  const known = (id: string) => release.topicById.has(id)
  const fw = sdg ? (sdg.frameworks.find((f) => f.key === state.fw) ?? sdg.frameworks[0]) : undefined
  const goals = sdg && fw ? sdg.goals.filter((g) => g.framework === fw.key) : []
  const covered = (key: string) => (sdg ? sdg.goals.filter((g) => g.framework === key && (g.topics ?? []).some(known)).length : 0)
  const icons = ['goals', 'layers', 'topics', 'places'] as const
  return (
    <div className="dash">
      {sdg ? (
        <KpiRow>
          {sdg.frameworks.slice(0, 4).map((f, i) => {
            const total = sdg.goals.filter((g) => g.framework === f.key).length
            return <KpiCard key={f.key} icon={icons[i]} label={name(f)} value={`${fmtInt(covered(f.key))}/${fmtInt(total)}`} sub={s('gl.k.covered')} />
          })}
        </KpiRow>
      ) : null}
      {sdg && fw ? (
        <DashGrid>
          <GoalsCard release={release} file={sdg} fw={fw.key} goals={goals} onFw={(key) => update({ fw: key })} />
          <GoalListCard release={release} goals={goals} label={(g) => (fw.key === 'sdg' ? `SDG ${g.number}` : String(g.number))} />
        </DashGrid>
      ) : null}
      {!glob && skipped ? (
        <DashGrid>
          <Card span={12} title={s('gl.world')}>
            <p className="card-empty">{t('mod.absentBody')} {t('mod.skipped')} <span lang="en">{skipped}</span></p>
          </Card>
        </DashGrid>
      ) : null}
      {glob ? (
        <DashGrid>
          <WorldCard file={glob} />
          <OppsCard release={release} file={glob} />
        </DashGrid>
      ) : null}
      {glob || gaps ? (
        <DashGrid>
          {glob ? <StrongCard release={release} file={glob} span={gaps ? 6 : 12} /> : null}
          {gaps ? <RiskCard release={release} file={gaps} span={glob ? 6 : 12} /> : null}
        </DashGrid>
      ) : null}
    </div>
  )
}

/** One tile per goal of the chosen framework (SDG, BCG …): topics per goal, hatched when none. */
function GoalsCard({ release, file, fw, goals, onFw }: { release: AtlasRelease; file: SdgFile; fw: string; goals: readonly GoalStat[]; onFw: (key: string) => void }) {
  const { lang } = useI18n()
  const s = useStrings(dashPages)
  const sx = useStrings(execPages)
  const x = useStrings(execViz)
  const name = (o: { th: string; en: string }) => (lang === 'en' ? o.en : o.th)
  const label = (g: GoalStat) => (fw === 'sdg' ? `SDG ${g.number}` : String(g.number))
  const byId = new Map(goals.map((g) => [g.id, g]))
  const tiles = goalTiles(goals, fw, (id) => release.topicById.has(id)).filter((tile) => tile.topics.length > 0).map((tile) => {
    const g = byId.get(tile.id) as GoalStat
    const tl = tile.topics.map((id) => release.topicById.get(id)).filter((tp): tp is Topic => tp !== undefined)
    return {
      ...tile,
      code: label(g),
      name: name(g),
      shareText: x('xv.goal.share', { p: fmtShare(tile.share, 1) }),
      list: (
        <>
          <p className="gt-list-h">{x('xv.goal.list')}</p>
          <ul className="gt-topics">
            {tl.slice(0, TILE_TOPICS).map((tp) => <li key={tp.id}><TopicLink topic={tp} showStatus /></li>)}
          </ul>
          {tl.length > TILE_TOPICS ? <p className="br-more">{x('xv.goal.more', { n: fmtInt(tl.length - TILE_TOPICS) })}</p> : null}
        </>
      ),
    }
  })
  return (
    <Card span={8} title={s('gl.goals')} info={s('gl.goalsInfo')}>
      {file.frameworks.length > 1 ? <Segmented label={s('gl.fw')} value={fw} onChange={onFw} options={file.frameworks.map((f) => ({ id: f.key, label: name(f) }))} /> : null}
      <GoalTiles tiles={tiles} label={x('xv.goal.label', { n: fmtInt(tiles.length) })} countWord={(n) => x(n === 1 ? 'xv.goal.topic1' : 'xv.goal.topics')} emptyText={sx('sdg.gap')} />
    </Card>
  )
}

/** Beside the tiles: the goals with no research yet (or, when every goal has some, the goals with the most). */
function GoalListCard({ release, goals, label }: { release: AtlasRelease; goals: readonly GoalStat[]; label: (g: GoalStat) => string }) {
  const { lang } = useI18n()
  const s = useStrings(dashPages)
  const count = (g: GoalStat) => (g.topics ?? []).filter((id) => release.topicById.has(id)).length
  const empty = goals.filter((g) => count(g) === 0).sort((a, b) => a.number - b.number)
  const most = sortBy(goals.filter((g) => count(g) > 0), count, 'desc')
  const list = empty.length ? empty : most
  const page = usePaged(list, 8)
  if (!goals.length) return null
  return (
    <Card span={4} title={empty.length ? s('gl.empty') : s('gl.most')}>
      {!empty.length ? <p className="card-empty">{s('gl.emptyNone')}</p> : null}
      <RankRows
        numbered={false}
        label={empty.length ? s('gl.empty') : s('gl.most')}
        rows={page.shown.map((g) => ({
          key: g.id,
          name: `${label(g)} ${lang === 'en' ? g.en : g.th}`,
          value: empty.length ? undefined : <b className="rise-a">{s('gl.topicsN', { n: fmtInt(count(g)) })}</b>,
        }))}
      />
      <MoreRows {...page.more} />
    </Card>
  )
}

/** Thailand's activity against world growth, one dot per subfield; the openings are top left. */
function WorldCard({ file }: { file: GlobalFile }) {
  const s = useStrings(dashPages)
  const sx = useStrings(execPages)
  const x = useStrings(execViz)
  const points = file.subfields
    .filter((f) => typeof f.activity_index === 'number' && typeof f.world_ratio === 'number')
    .map((f) => ({ id: f.id, label: f.en, x: f.activity_index as number, y: f.world_ratio as number, hot: Boolean(f.opportunity) }))
  if (!points.length) return null
  return (
    <Card span={8} title={s('gl.world')} info={s('gl.worldInfo', { b: yearSpan(file.baseline.start, file.baseline.end), r: yearSpan(file.recent.start, file.recent.end) })}>
      <OpportunityQuadrant
        points={points}
        xMax={file.max_activity_index}
        yMin={file.min_world_ratio}
        text={{ x: sx('gl.col.ai'), y: sx('gl.col.ratio'), zone: sx('gl.opp'), same: x('xv.q.same'), flat: x('xv.q.flat'), opp: x('xv.q.key.opp'), other: x('xv.q.key.other') }}
        label={x('xv.q.label', { n: fmtInt(points.length), k: fmtInt(points.filter((p) => p.hot).length) })}
        describe={(p) => x('xv.q.point', { x: p.label, wr: fmtNum(p.y, 2), ai: fmtNum(p.x, 2) })}
        labelLang="en"
      />
    </Card>
  )
}

/** Subfields growing fast worldwide where Thailand does little: fastest world growth first, with the Thai topics in them. */
function OppsCard({ release, file }: { release: AtlasRelease; file: GlobalFile }) {
  const { name } = useI18n()
  const s = useStrings(dashPages)
  const opps = sortBy(file.subfields.filter((f) => f.opportunity), (f) => f.world_ratio ?? 0, 'desc')
  const page = usePaged(opps, 8)
  if (!opps.length) return null
  return (
    <Card span={4} title={s('gl.opps')} info={s('gl.oppsInfo')}>
      <RankRows
        label={s('gl.opps')}
        rows={page.shown.map((f) => {
          const tp = (f.topics ?? []).map((id) => release.topicById.get(id)).find((x): x is Topic => x !== undefined)
          return {
            key: f.id,
            to: tp ? `/topics/${tp.id}` : null,
            name: f.en,
            nameLang: 'en',
            meta: tp ? <span className="rise-sub">{name(tp)}</span> : undefined,
            value: <b className="rise-g">{s('gl.times', { x: fmtNum(f.world_ratio ?? null, 1) })}</b>,
          }
        })}
      />
      <MoreRows {...page.more} />
    </Card>
  )
}

/** Subfields where Thailand's share is above the world's (activity index > 1), strongest first. */
function StrongCard({ release, file, span }: { release: AtlasRelease; file: GlobalFile; span: 6 | 12 }) {
  const { name } = useI18n()
  const s = useStrings(dashPages)
  const strong = sortBy(file.subfields.filter((f) => (f.activity_index ?? 0) > 1), (f) => f.activity_index ?? 0, 'desc')
  const page = usePaged(strong, 6)
  if (!strong.length) return null
  return (
    <Card span={span} title={s('gl.strong')} info={s('gl.strongInfo')}>
      <RankRows
        label={s('gl.strong')}
        rows={page.shown.map((f) => {
          const tp = (f.topics ?? []).map((id) => release.topicById.get(id)).find((x): x is Topic => x !== undefined)
          return { key: f.id, to: tp ? `/topics/${tp.id}` : null, name: f.en, nameLang: 'en', meta: tp ? <span className="rise-sub">{name(tp)}</span> : undefined, value: <b className="rise-a">×{fmtNum(f.activity_index ?? null, 1)}</b> }
        })}
      />
      <MoreRows {...page.more} />
    </Card>
  )
}

/** Topics whose recent articles come mostly from one institution or journal (gaps.json concentration). */
function RiskCard({ release, file, span }: { release: AtlasRelease; file: GapsFile; span: 6 | 12 }) {
  const { t, name } = useI18n()
  const s = useStrings(dashPages)
  const risky = sortBy(file.concentration.filter((c) => c.concentrated && c.scope === 'topic' && release.topicById.has(c.id)), (c) => c.top_share, 'desc')
  const page = usePaged(risky, 6)
  if (!risky.length) return null
  return (
    <Card span={span} title={s('gl.risk')} info={s('gl.riskInfo', { a: file.recent.start, b: file.recent.end })}>
      <RankRows
        label={s('gl.risk')}
        rows={page.shown.map((c) => {
          const tp = release.topicById.get(c.id) as Topic
          return {
            key: `${c.id}:${c.kind}`,
            to: `/topics/${tp.id}`,
            name: name(tp),
            meta: (
              <>
                <StatusChip status={tp.status} label={statusName(t, tp.status)} small />
                {c.top_name ? <span className="rise-sub">{s('gl.riskShare', { p: fmtPct(c.top_share, 0), x: c.top_name })}</span> : null}
              </>
            ),
            value: <b className="rise-a">{fmtPct(c.top_share, 0)}</b>,
          }
        })}
      />
      <MoreRows {...page.more} />
    </Card>
  )
}
