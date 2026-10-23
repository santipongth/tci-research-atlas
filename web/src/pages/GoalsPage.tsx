import type { ReactNode } from 'react'
import { goalTiles } from '../charts/execLayout'
import { Card, DashGrid } from '../components/dashboard/Card'
import { Icon } from '../components/dashboard/Icon'
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
import type { Concentration, GapsFile, GlobalFile, GoalStat, SdgFile, SubfieldBench, Topic } from '../data/types'
import { fmtInt, fmtNum, fmtPct, fmtShare, yearSpan } from '../lib/format'
import { useI18n, useStrings } from '../lib/i18n'
import { sortBy } from '../lib/sort'
import { statusName } from '../lib/topicText'
import { usePaged } from '../lib/usePaged'
import { goalsCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import { dashPages } from '../strings/dashPages'

/** Topics listed under an opened goal. */
const GOAL_TOPICS = 8

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

/**
 * Three bands: how many goals of each framework have research (KPIs), every goal of the chosen framework as one bar
 * list (goals with no research yet are dashed rows in the same list), then Thailand against the world and the topics
 * that lean on one institution or journal, as three short ranked lists.
 */
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
  const opps = glob ? sortBy(glob.subfields.filter((f) => f.opportunity), (f) => f.world_ratio ?? 0, 'desc') : []
  const strong = glob ? sortBy(glob.subfields.filter((f) => (f.activity_index ?? 0) > 1), (f) => f.activity_index ?? 0, 'desc') : []
  const risky = gaps ? sortBy(gaps.concentration.filter((c) => c.concentrated && c.scope === 'topic' && known(c.id)), (c) => c.top_share, 'desc') : []
  const lower = [opps.length > 0, strong.length > 0, risky.length > 0].filter(Boolean).length
  const span = lower === 3 ? 4 : lower === 2 ? 6 : 12
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
      {sdg && fw && goals.length ? (
        <DashGrid>
          <Card
            span={12}
            title={s('gl.goals')}
            info={s('gl.goalsInfo')}
            action={sdg.frameworks.length > 1 ? <Segmented label={s('gl.fw')} value={fw.key} onChange={(key) => update({ fw: key })} options={sdg.frameworks.map((f) => ({ id: f.key, label: name(f) }))} /> : null}
          >
            <GoalBars release={release} goals={goals} fw={fw.key} />
          </Card>
        </DashGrid>
      ) : null}
      {!glob && skipped ? (
        <DashGrid>
          <Card span={12} title={s('gl.world')}>
            <p className="card-empty">{t('mod.absentBody')} {t('mod.skipped')} <span lang="en">{skipped}</span></p>
          </Card>
        </DashGrid>
      ) : null}
      {lower ? (
        <DashGrid>
          {glob && opps.length ? (
            <Card span={span} title={s('gl.opps')} info={s('gl.oppsInfo', { b: yearSpan(glob.baseline.start, glob.baseline.end), r: yearSpan(glob.recent.start, glob.recent.end) })}>
              <SubfieldRows release={release} rows={opps} value={(f) => <b className="rise-g">{s('gl.times', { x: fmtNum(f.world_ratio ?? null, 1) })}</b>} label={s('gl.opps')} />
            </Card>
          ) : null}
          {glob && strong.length ? (
            <Card span={span} title={s('gl.strong')} info={s('gl.strongInfo')}>
              <SubfieldRows release={release} rows={strong} value={(f) => <b className="rise-a">{s('gl.more', { x: fmtNum(f.activity_index ?? null, 1) })}</b>} label={s('gl.strong')} />
            </Card>
          ) : null}
          {gaps && risky.length ? (
            <Card span={span} title={s('gl.risk')} info={s('gl.riskInfo', { a: gaps.recent.start, b: gaps.recent.end })}>
              <RiskRows release={release} rows={risky} />
            </Card>
          ) : null}
        </DashGrid>
      ) : null}
    </div>
  )
}

/**
 * Every goal of one framework as a bar list, most research first: the goal's code and name, its topic count, and a bar
 * for its share of recent articles (one scale for the framework). A goal with research opens to list its topics; a goal
 * with none is a plain dashed row (nothing to open, so nothing looks clickable).
 */
function GoalBars({ release, goals, fw }: { release: AtlasRelease; goals: readonly GoalStat[]; fw: string }) {
  const { lang } = useI18n()
  const s = useStrings(dashPages)
  const byId = new Map(goals.map((g) => [g.id, g]))
  const rows = goalTiles(goals, fw, (id) => release.topicById.has(id))
  const ranked = [...sortBy(rows.filter((r) => r.count > 0), (r) => r.share, 'desc'), ...rows.filter((r) => r.count === 0)]
  const code = (n: number) => (fw === 'sdg' ? `SDG ${n}` : String(n))
  return (
    <ul className="gb" aria-label={s('gl.goals')}>
      {ranked.map((r) => {
        const g = byId.get(r.id) as GoalStat
        const title = (
          <span className="gb-main">
            <span className="gb-name" title={lang === 'en' ? g.en : g.th}><b className="gb-code">{code(r.number)}</b> {lang === 'en' ? g.en : g.th}</span>
            <span className="gb-n">{r.count ? s('gl.topicsN', { n: fmtInt(r.count) }) : s('gl.none')}</span>
          </span>
        )
        if (!r.count) {
          return (
            <li key={r.id} className="gb-row is-empty">
              <div className="gb-sum">
                {title}
                <span className="gb-bar" aria-hidden="true" />
                <span className="gb-v" />
                <span className="gb-chev" />
              </div>
            </li>
          )
        }
        const topics = r.topics.map((id) => release.topicById.get(id)).filter((tp): tp is Topic => tp !== undefined)
        return (
          <li key={r.id} className="gb-row">
            <details>
              <summary className="gb-sum">
                {title}
                <span className="gb-bar" aria-hidden="true"><i style={{ width: `${Math.max(2, r.frac * 100)}%` }} /></span>
                <span className="gb-v">{s('gl.share', { p: fmtShare(r.share, 1) })}</span>
                <span className="gb-chev"><Icon name="chevron" size={16} /></span>
              </summary>
              <ul className="gb-topics">
                {topics.slice(0, GOAL_TOPICS).map((tp) => <li key={tp.id}><TopicLink topic={tp} showStatus /></li>)}
                {topics.length > GOAL_TOPICS ? <li className="gb-more">{s('gl.moreTopics', { n: fmtInt(topics.length - GOAL_TOPICS) })}</li> : null}
              </ul>
            </details>
          </li>
        )
      })}
    </ul>
  )
}

/** A world subfield (English name from OpenAlex) with the Thai topic in it as the link, 6 at a time. */
function SubfieldRows({ release, rows, value, label }: { release: AtlasRelease; rows: readonly SubfieldBench[]; value: (f: SubfieldBench) => ReactNode; label: string }) {
  const { name } = useI18n()
  const page = usePaged(rows, 6)
  return (
    <>
      <RankRows
        label={label}
        rows={page.shown.map((f) => {
          const tp = (f.topics ?? []).map((id) => release.topicById.get(id)).find((x): x is Topic => x !== undefined)
          return { key: f.id, to: tp ? `/topics/${tp.id}` : null, name: f.en, nameLang: 'en', meta: tp ? <span className="rise-sub">{name(tp)}</span> : undefined, value: value(f) }
        })}
      />
      <MoreRows {...page.more} />
    </>
  )
}

/** Topics whose recent articles come mostly from one institution or journal (gaps.json concentration). */
function RiskRows({ release, rows }: { release: AtlasRelease; rows: readonly Concentration[] }) {
  const { t, name } = useI18n()
  const s = useStrings(dashPages)
  const page = usePaged(rows, 6)
  return (
    <>
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
    </>
  )
}
