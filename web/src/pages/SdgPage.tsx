import { goalTiles } from '../charts/execLayout'
import { GoalTiles } from '../charts/GoalTiles'
import { DataTable, type Column } from '../components/DataTable'
import { Figure } from '../components/Figure'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { ShareBar } from '../components/ShareBar'
import { Tabs } from '../components/Tabs'
import { TopicLink } from '../components/TopicLink'
import { MODULE_FILES, type AtlasRelease } from '../data/release'
import type { GoalStat, SdgFile, Topic } from '../data/types'
import { fmtWindow, windows } from '../lib/definition'
import { fmtInt, fmtPct, fmtRatio } from '../lib/format'
import { useI18n, useStrings } from '../lib/i18n'
import { figureCsv } from '../lib/tableCsv'
import { sdgCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import { execViz } from '../strings/execViz'

/** Topics listed in an open goal tile (the rest are in the table view). */
const TILE_TOPICS = 6

export default function SdgPage() {
  const { t } = useI18n()
  return (
    <RequireRelease title={t('sdg.title')}>
      {(release) => (
        <ModuleFile<SdgFile> release={release} module="sdg" path={MODULE_FILES.sdg} title={t('sdg.title')}>
          {(file) => <Sdg release={release} file={file} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

function Sdg({ release, file }: { release: AtlasRelease; file: SdgFile }) {
  const { t, lang } = useI18n()
  const x = useStrings(execViz)
  const [state, update] = useUrlState(sdgCodec)
  const name = (o: { th: string; en: string }) => (lang === 'en' ? o.en : o.th)
  const fw = file.frameworks.find((f) => f.key === state.fw) ?? file.frameworks[0]
  const goals = fw ? file.goals.filter((g) => g.framework === fw.key) : []
  const count = (g: GoalStat) => (g.topics ?? []).length
  const covered = goals.filter((g) => count(g) > 0).length
  const maxShare = Math.max(0.0001, ...goals.map((g) => g.share_recent ?? 0))
  const win = windows(release.overview.last_complete_year)
  const b = fmtWindow(win.B)
  const r = fmtWindow(win.R)
  const label = (g: GoalStat) => (fw?.key === 'sdg' ? `SDG ${g.number}` : String(g.number))
  const columns: Column<GoalStat>[] = [
    {
      key: 'goal', csvHeader: 'goal_id', header: t('sdg.col.goal'), rowHeader: true, firstDir: 'asc',
      cell: (g) => <span className="goal-name"><strong>{label(g)}</strong> {name(g)}</span>, sortValue: (g) => g.number, csv: (g) => g.id,
    },
    { key: 'topics', csvHeader: 'topics', header: t('sdg.col.topics'), numeric: true, cell: (g) => (count(g) ? fmtInt(count(g)) : <span className="flag">{t('sdg.gap')}</span>), sortValue: count },
    { key: 'articles', csvHeader: 'articles_recent', header: t('col.articlesR', { r }), numeric: true, cell: (g) => fmtInt(g.articles_recent ?? 0), sortValue: (g) => g.articles_recent ?? 0 },
    { key: 'share', csvHeader: 'share_recent', header: t('col.share'), numeric: true, cell: (g) => <ShareBar value={g.share_recent ?? 0} digits={1} max={maxShare} />, sortValue: (g) => g.share_recent ?? 0 },
    { key: 'ratio', csvHeader: 'share_ratio', header: t('sdg.col.ratio', { b }), numeric: true, cell: (g) => fmtRatio(g.share_ratio ?? null), sortValue: (g) => g.share_ratio ?? null },
    {
      key: 'examples', csvHeader: 'topic_ids', header: t('sdg.col.examples'),
      cell: (g) => (
        <span className="sdg-ex">
          {(g.topics ?? []).slice(0, 3).map((id) => release.topicById.get(id)).filter((tp): tp is Topic => tp !== undefined).map((tp) => (
            <TopicLink key={tp.id} topic={tp} showStatus />
          ))}
        </span>
      ),
      csv: (g) => (g.topics ?? []).join(';'),
    },
  ]
  const rel = release.overview.release
  // the example: the first goal (in goal order) that has a topic, and its largest topic
  const exGoal = goals.filter((g) => count(g) > 0).sort((x, y) => x.number - y.number)[0]
  const exTopic = exGoal ? (exGoal.topics ?? []).map((id) => release.topicById.get(id)).find((tp): tp is Topic => tp !== undefined) : undefined
  const goalById = new Map(goals.map((g) => [g.id, g]))
  const tiles = fw
    ? goalTiles(goals, fw.key, (id) => release.topicById.has(id)).map((tile) => {
        const g = goalById.get(tile.id) as GoalStat
        const tl = tile.topics.map((id) => release.topicById.get(id)).filter((tp): tp is Topic => tp !== undefined)
        return {
          ...tile,
          code: label(g),
          name: name(g),
          shareText: x('xv.goal.share', { p: fmtPct(tile.share, 1) }),
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
    : []
  const tableTitle = fw ? t('table.n', { n: 1, title: t('sdg.table', { f: name(fw) }) }) : ''
  return (
    <div className="container">
      <PageHeader title={t('sdg.title')} lede={t('sdg.lede')} />
      {fw ? (
        <Section id="goals" title={t('sdg.frameworks')}>
          <Tabs id="sdg-fw" label={t('sdg.frameworks')} items={file.frameworks.map((f) => ({ id: f.key, label: name(f) }))} value={fw.key} onChange={(id) => update({ fw: id })}>
            {exGoal && exTopic ? <p>{t('sdg.example', { topic: lang === 'en' ? exTopic.en || exTopic.th : exTopic.th, goal: `${label(exGoal)} ${name(exGoal)}` })}</p> : null}
            <p className="note">{t('sdg.coverage', { n: fmtInt(covered), total: fmtInt(goals.length) })}</p>
            <Figure
              id="fig-goals"
              number={1}
              title={x('xv.goal.title', { f: name(fw) })}
              tableTitle={tableTitle}
              toggle="buttons"
              csv={figureCsv(`atlas-${rel}-${fw.key}.csv`, goals, columns)}
              how={
                <>
                  <p>{x('xv.goal.how', { r })}</p>
                  <p>{t('sdg.how', { method: t(file.method === 'embedding' ? 'sdg.method.embedding' : 'sdg.method.lexical'), b, r })}</p>
                </>
              }
              source={t('source.line', { release: rel })}
              view={state.view}
              onView={(v) => update({ view: v })}
              chart={<GoalTiles tiles={tiles} label={x('xv.goal.label', { n: fmtInt(tiles.length) })} countWord={(n) => x(n === 1 ? 'xv.goal.topic1' : 'xv.goal.topics')} emptyText={t('sdg.gap')} />}
              table={<DataTable caption={tableTitle} rows={goals} columns={columns} rowKey={(g) => g.id} defaultSort={{ key: 'goal', dir: 'asc' }} />}
            />
          </Tabs>
        </Section>
      ) : null}
    </div>
  )
}
