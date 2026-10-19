import { DataTable, type Column } from '../components/DataTable'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { ShareBar } from '../components/ShareBar'
import { Tabs } from '../components/Tabs'
import { TopicLink } from '../components/TopicLink'
import { MODULE_FILES, type AtlasRelease } from '../data/release'
import type { GoalStat, SdgFile, Topic } from '../data/types'
import { fmtInt, fmtRatio } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { sdgCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'

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
  const [state, update] = useUrlState(sdgCodec)
  const name = (o: { th: string; en: string }) => (lang === 'en' ? o.en : o.th)
  const fw = file.frameworks.find((f) => f.key === state.fw) ?? file.frameworks[0]
  const goals = fw ? file.goals.filter((g) => g.framework === fw.key) : []
  const count = (g: GoalStat) => (g.topics ?? []).length
  const covered = goals.filter((g) => count(g) > 0).length
  const maxShare = Math.max(0.0001, ...goals.map((g) => g.share_recent ?? 0))
  const label = (g: GoalStat) => (fw?.key === 'sdg' ? `SDG ${g.number}` : String(g.number))
  const columns: Column<GoalStat>[] = [
    {
      key: 'goal', csvHeader: 'goal_id', header: t('sdg.col.goal'), rowHeader: true, firstDir: 'asc',
      cell: (g) => <span className="goal-name"><strong>{label(g)}</strong> {name(g)}</span>, sortValue: (g) => g.number, csv: (g) => g.id,
    },
    { key: 'topics', csvHeader: 'topics', header: t('sdg.col.topics'), numeric: true, cell: (g) => (count(g) ? fmtInt(count(g)) : <span className="flag">{t('sdg.gap')}</span>), sortValue: count },
    { key: 'articles', csvHeader: 'articles_recent', header: t('col.articlesR'), numeric: true, cell: (g) => fmtInt(g.articles_recent ?? 0), sortValue: (g) => g.articles_recent ?? 0 },
    { key: 'share', csvHeader: 'share_recent', header: t('col.share'), numeric: true, cell: (g) => <ShareBar value={g.share_recent ?? 0} digits={1} max={maxShare} />, sortValue: (g) => g.share_recent ?? 0 },
    { key: 'ratio', csvHeader: 'share_ratio', header: t('sdg.col.ratio'), numeric: true, cell: (g) => fmtRatio(g.share_ratio ?? null), sortValue: (g) => g.share_ratio ?? null },
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
  return (
    <div className="container">
      <PageHeader title={t('sdg.title')} lede={t('sdg.lede', { method: t(file.method === 'embedding' ? 'sdg.method.embedding' : 'sdg.method.lexical') })} />
      {fw ? (
        <Section id="goals" title={t('sdg.frameworks')}>
          <Tabs id="sdg-fw" label={t('sdg.frameworks')} items={file.frameworks.map((f) => ({ id: f.key, label: name(f) }))} value={fw.key} onChange={(id) => update({ fw: id })}>
            <p className="note">{t('sdg.coverage', { n: fmtInt(covered), total: fmtInt(goals.length) })}</p>
            <DataTable
              caption={t('table.n', { n: 1, title: t('sdg.table', { f: name(fw) }) })}
              rows={goals}
              columns={columns}
              rowKey={(g) => g.id}
              defaultSort={{ key: 'goal', dir: 'asc' }}
              csvFilename={`atlas-${rel}-${fw.key}.csv`}
              footnote={t('sdg.foot')}
            />
          </Tabs>
        </Section>
      ) : null}
    </div>
  )
}
