import { Link } from 'react-router'
import { DataTable, type Column } from '../components/DataTable'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { ShareBar } from '../components/ShareBar'
import { TopicLink } from '../components/TopicLink'
import { groupName, hasModule, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { Bridge, Concentration, FewInstitutions, GapsFile, Topic, WorldGap } from '../data/types'
import { DASH, fmtInt, fmtNum, fmtPct, fmtRatio } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { statusName } from '../lib/topicText'
import { gapsCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'

export default function GapsPage() {
  const { t } = useI18n()
  return (
    <RequireRelease title={t('gp.title')}>
      {(release) => (
        <ModuleFile<GapsFile> release={release} module="gaps" path={MODULE_FILES.gaps} title={t('gp.title')}>
          {(file) => <Gaps release={release} file={file} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

function Gaps({ release, file }: { release: AtlasRelease; file: GapsFile }) {
  const { t, lang } = useI18n()
  const [state, update] = useUrlState(gapsCodec)
  const topic = (id: string): Topic | undefined => release.topicById.get(id)
  const few = file.few_institutions.filter((f) => topic(f.topic))
  const bridges = file.bridges.filter((b) => topic(b.a) && topic(b.b))
  const risk = file.concentration.filter((c) => (c.scope === 'topic' ? topic(c.id) : true) && (state.all === 'yes' || c.concentrated))
  const r = file.recent
  const rel = release.overview.release
  const topicList = (ids: readonly string[]) => {
    const tl = ids.map(topic).filter((tp): tp is Topic => tp !== undefined).slice(0, 3)
    return tl.length ? <span className="sdg-ex">{tl.map((tp) => <TopicLink key={tp.id} topic={tp} showStatus />)}</span> : DASH
  }
  const worldColumns: Column<WorldGap>[] = [
    { key: 'subfield', header: t('gl.col.subfield'), rowHeader: true, cell: (w) => <span lang="en">{w.en}</span>, sortValue: (w) => w.en, csvCols: [{ header: 'subfield_id', value: (w) => w.subfield }, { header: 'subfield_en', value: (w) => w.en }] },
    { key: 'ratio', csvHeader: 'world_ratio', header: t('gl.col.ratio'), numeric: true, cell: (w) => fmtRatio(w.world_ratio ?? null), sortValue: (w) => w.world_ratio ?? null },
    { key: 'ai', csvHeader: 'activity_index', header: t('gl.col.ai'), numeric: true, cell: (w) => fmtNum(w.activity_index ?? null, 2), sortValue: (w) => w.activity_index ?? null },
    { key: 'topics', csvHeader: 'topic_ids', header: t('gl.col.topics'), cell: (w) => topicList(w.topics ?? []), csv: (w) => (w.topics ?? []).join(';') },
  ]
  const fewColumns: Column<FewInstitutions>[] = [
    { key: 'topic', csvHeader: 'topic_id', header: t('col.topic'), rowHeader: true, cell: (f) => <TopicLink topic={topic(f.topic) as Topic} showStatus />, sortValue: (f) => f.topic, csv: (f) => f.topic },
    { key: 'institutions', csvHeader: 'institutions', header: t('gp.col.institutions'), numeric: true, firstDir: 'asc', cell: (f) => fmtInt(f.institutions), sortValue: (f) => f.institutions },
  ]
  const bridgeColumns: Column<Bridge>[] = [
    {
      key: 'pair', header: t('gp.col.pair'), rowHeader: true,
      cell: (b) => (
        <span className="pair">
          <TopicLink topic={topic(b.a) as Topic} showStatus />
          <TopicLink topic={topic(b.b) as Topic} showStatus />
        </span>
      ),
      csvCols: [{ header: 'topic_a', value: (b) => b.a }, { header: 'topic_b', value: (b) => b.b }],
    },
    { key: 'similarity', csvHeader: 'similarity', header: t('in.col.similarity'), numeric: true, cell: (b) => fmtNum(b.similarity, 2), sortValue: (b) => b.similarity },
    { key: 'shared', csvHeader: 'shared', header: t('gp.col.shared'), numeric: true, firstDir: 'asc', cell: (b) => fmtInt(b.shared), sortValue: (b) => b.shared },
    { key: 'jaccard', csvHeader: 'jaccard', header: 'Jaccard', numeric: true, firstDir: 'asc', cell: (b) => fmtNum(b.jaccard, 2), sortValue: (b) => b.jaccard },
  ]
  const topName = (c: Concentration) => {
    if (!c.top && !c.top_name) return <span className="topic-sub">{t('gp.withheld')}</span>
    const module = c.kind === 'institution' ? 'institutions' : 'journals'
    return c.top && hasModule(release, module) ? <Link to={`/${module}/${c.top}`}>{c.top_name || c.top}</Link> : c.top_name || c.top
  }
  const riskColumns: Column<Concentration>[] = [
    {
      key: 'unit', csvHeader: 'unit', header: t('gp.col.unit'), rowHeader: true,
      cell: (c) => (c.scope === 'topic' ? <TopicLink topic={topic(c.id) as Topic} showStatus /> : groupName(release, c.id, lang)),
      sortValue: (c) => c.id, csv: (c) => c.id,
    },
    { key: 'kind', csvHeader: 'kind', header: t('gp.col.kind'), cell: (c) => t(c.kind === 'institution' ? 'gp.kind.institution' : 'gp.kind.journal'), csv: (c) => c.kind },
    { key: 'top', csvHeader: 'top', header: t('gp.col.top'), cell: topName, csv: (c) => c.top ?? '' },
    {
      key: 'share', csvHeader: 'top_share', header: t('gp.col.topShare'), numeric: true, sortValue: (c) => c.top_share,
      cell: (c) => (
        <>
          <ShareBar value={c.top_share} />
          {c.concentrated ? <span className="flag-on">{t('gp.flag')}</span> : null}
        </>
      ),
    },
    { key: 'hhi', csvHeader: 'hhi', header: t('gp.col.hhi'), numeric: true, cell: (c) => fmtNum(c.hhi, 2), sortValue: (c) => c.hhi },
    { key: 'articles', csvHeader: 'articles', header: t('col.articlesR'), numeric: true, cell: (c) => fmtInt(c.articles), sortValue: (c) => c.articles },
  ]
  return (
    <div className="container">
      <PageHeader title={t('gp.title')} lede={t('gp.lede', { a: r.start, b: r.end })} />
      {file.world.length ? (
        <Section id="world" title={t('gp.world.h')} intro={t('gp.world.intro')}>
          <DataTable caption={t('table.n', { n: 1, title: t('gp.world.table') })} rows={file.world} columns={worldColumns} rowKey={(w) => w.subfield} defaultSort={{ key: 'ratio', dir: 'desc' }} csvFilename={`atlas-${rel}-gaps-world.csv`} />
        </Section>
      ) : null}
      {few.length ? (
        <Section
          id="few"
          title={t('gp.few.h')}
          intro={t('gp.few.intro', { statuses: file.statuses.map((s) => statusName(t, s)).join(lang === 'en' ? ' or ' : 'หรือ'), n: fmtInt(file.max_institutions) })}
        >
          <DataTable caption={t('table.n', { n: 2, title: t('gp.few.table') })} rows={few} columns={fewColumns} rowKey={(f) => f.topic} stack={false} defaultSort={{ key: 'institutions', dir: 'asc' }} csvFilename={`atlas-${rel}-gaps-few-institutions.csv`} />
        </Section>
      ) : null}
      {bridges.length ? (
        <Section id="bridges" title={t('gp.bridge.h')} intro={t('gp.bridge.intro', { s: fmtNum(file.bridge_min_similarity, 2), j: fmtNum(file.bridge_max_jaccard, 2) })}>
          <DataTable caption={t('table.n', { n: 3, title: t('gp.bridge.table') })} rows={bridges} columns={bridgeColumns} rowKey={(b) => `${b.a}~${b.b}`} defaultSort={{ key: 'similarity', dir: 'desc' }} csvFilename={`atlas-${rel}-gaps-bridges.csv`} />
        </Section>
      ) : null}
      {file.concentration.length ? (
        <Section id="risk" title={t('gp.risk.h')} intro={t('gp.risk.intro', { m: fmtInt(file.min_articles), p: fmtPct(file.max_top_share, 0), h: fmtNum(file.max_hhi, 2) })}>
          <label className="check">
            <input type="checkbox" checked={state.all === 'yes'} onChange={(e) => update({ all: e.target.checked ? 'yes' : 'no' })} />
            {t('gp.risk.all')}
          </label>
          <DataTable caption={t('table.n', { n: 4, title: t('gp.risk.table') })} rows={risk} columns={riskColumns} rowKey={(c) => `${c.scope}:${c.id}:${c.kind}`} defaultSort={{ key: 'share', dir: 'desc' }} csvFilename={`atlas-${rel}-concentration.csv`} />
        </Section>
      ) : null}
      {hasModule(release, 'institutions') ? (
        <p className="note mt-6">
          {t('gp.collab')} <Link to="/institutions">{t('gp.collabLink')}</Link>
        </p>
      ) : null}
    </div>
  )
}
