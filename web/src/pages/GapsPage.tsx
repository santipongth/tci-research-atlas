import { Link } from 'react-router'
import { BridgePairs } from '../charts/BridgePairs'
import { SplitBar } from '../charts/MixBar'
import { OpportunityQuadrant } from '../charts/OpportunityQuadrant'
import { DataTable, type Column } from '../components/DataTable'
import { Figure } from '../components/Figure'
import { ListMore } from '../components/ListMore'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { ShareBar } from '../components/ShareBar'
import { Term } from '../components/Term'
import { TopicLink } from '../components/TopicLink'
import { useReleaseFile } from '../data/atlasContext'
import { groupName, hasModule, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { Bridge, Concentration, FewInstitutions, GapsFile, GlobalFile, Topic, WorldGap } from '../data/types'
import { DASH, fmtInt, fmtNum, fmtPct, fmtRatio } from '../lib/format'
import { useI18n, useStrings } from '../lib/i18n'
import { figureCsv } from '../lib/tableCsv'
import { statusName } from '../lib/topicText'
import { useCapped } from '../lib/useCapped'
import { gapsCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import { execViz } from '../strings/execViz'

/** Rows of each picture before "show all": with hundreds of topics the tables carry the rest. */
const LIST_ROWS = 25

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
  const { t, lang, name } = useI18n()
  const x = useStrings(execViz)
  const [state, update] = useUrlState(gapsCodec)
  // the world thresholds and every subfield as context come from global.json when the release has it
  const globalFile = useReleaseFile<GlobalFile>(hasModule(release, 'global') ? MODULE_FILES.global : null)
  const glob = globalFile.status === 'ready' ? globalFile.data : null
  const topic = (id: string): Topic | undefined => release.topicById.get(id)
  const few = file.few_institutions.filter((f) => topic(f.topic))
  const bridges = file.bridges.filter((b) => topic(b.a) && topic(b.b))
  const risk = file.concentration.filter((c) => (c.scope === 'topic' ? topic(c.id) : true) && (state.all === 'yes' || c.concentrated))
  const r = file.recent
  const rw = `${r.start}–${r.end}`
  const tname = (id: string) => { const tp = topic(id); return tp ? name(tp) : id }
  // one real row per section is its example: the fastest world growth, the fewest institutions, the closest pair, the most concentrated unit
  const worldEx = file.world.reduce<WorldGap | null>((m, w) => ((w.world_ratio ?? 0) > (m?.world_ratio ?? -1) ? w : m), null)
  const fewEx = few.reduce<FewInstitutions | null>((m, f) => (m === null || f.institutions < m.institutions ? f : m), null)
  const bridgeEx = bridges.reduce<Bridge | null>((m, b) => (m === null || b.similarity > m.similarity ? b : m), null)
  const riskEx = file.concentration.filter((c) => c.concentrated && c.top_name && (c.scope === 'topic' ? topic(c.id) : release.groupById.has(c.id))).reduce<Concentration | null>((m, c) => (m === null || c.top_share > m.top_share ? c : m), null)
  const unitName = (c: Concentration) => (c.scope === 'topic' ? tname(c.id) : groupName(release, c.id, lang))
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
    { key: 'topic', csvHeader: 'topic_id', header: t('col.topic'), rowHeader: true, cell: (f) => <TopicLink topic={topic(f.topic) as Topic} showStatus />, sortValue: (f) => tname(f.topic), csv: (f) => f.topic },
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
    { key: 'jaccard', csvHeader: 'jaccard', header: t('gp.col.jaccard'), numeric: true, firstDir: 'asc', cell: (b) => fmtNum(b.jaccard, 2), sortValue: (b) => b.jaccard },
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
      sortValue: (c) => unitName(c), csv: (c) => c.id,
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
    { key: 'articles', csvHeader: 'articles', header: t('col.articlesR', { r: rw }), numeric: true, cell: (c) => fmtInt(c.articles), sortValue: (c) => c.articles },
  ]
  const source = t('source.line', { release: rel })
  const tbl = (n: number, title: string) => t('table.n', { n, title })
  const gapIds = new Set(file.world.map((w) => w.subfield))
  const quadPoints = (glob ? glob.subfields.map((g) => ({ id: g.id, label: g.en, x: g.activity_index, y: g.world_ratio, hot: gapIds.has(g.id) })) : file.world.map((w) => ({ id: w.subfield, label: w.en, x: w.activity_index, y: w.world_ratio, hot: true })))
    .filter((p): p is { id: string; label: string; x: number; y: number; hot: boolean } => typeof p.x === 'number' && typeof p.y === 'number')
  const fewSorted = [...few].sort((p, q) => p.institutions - q.institutions)
  const riskSorted = [...risk].sort((p, q) => q.top_share - p.top_share)
  const bridgesSorted = [...bridges].sort((p, q) => q.similarity - p.similarity)
  const fewCap = useCapped(fewSorted, LIST_ROWS)
  const bridgeCap = useCapped(bridgesSorted, LIST_ROWS)
  const riskCap = useCapped(riskSorted, LIST_ROWS)
  return (
    <div className="container">
      <PageHeader title={t('gp.title')} lede={t('gp.lede', { a: r.start, b: r.end })} />
      {file.world.length ? (
        <Section id="world" title={x('xv.gq.world')} intro={worldEx ? t('gl.example', { x: worldEx.en, wr: fmtNum(worldEx.world_ratio ?? null, 1), ai: fmtNum(worldEx.activity_index ?? null, 2) }) : undefined}>
          <Figure
            id="fig-world"
            number={1}
            title={t('gp.world.h')}
            tableTitle={tbl(1, t('gp.world.table'))}
            csv={figureCsv(`atlas-${rel}-gaps-world.csv`, file.world, worldColumns)}
            how={<p>{glob ? x('xv.q.how', { r: fmtNum(glob.min_world_ratio, 1), n: fmtInt(glob.min_world_works), ai: fmtNum(glob.max_activity_index, 1) }) : x('xv.q.howPlain')}</p>}
            source={glob ? t('gl.source', { v: glob.source }) : source}
            view={state.w}
            onView={(v) => update({ w: v })}
            chart={
              <OpportunityQuadrant
                points={quadPoints}
                xMax={glob?.max_activity_index ?? null}
                yMin={glob?.min_world_ratio ?? null}
                text={{ x: t('gl.col.ai'), y: t('gl.col.ratio'), zone: t('gl.opp'), same: x('xv.q.same'), flat: x('xv.q.flat'), opp: x('xv.q.key.opp'), other: x('xv.q.key.other') }}
                label={x('xv.q.label', { n: fmtInt(quadPoints.length), k: fmtInt(file.world.length) })}
                describe={(p) => x('xv.q.point', { x: p.label, wr: fmtNum(p.y, 2), ai: fmtNum(p.x, 2) })}
                labelLang="en"
              />
            }
            table={<DataTable caption={tbl(1, t('gp.world.table'))} rows={file.world} columns={worldColumns} rowKey={(w) => w.subfield} defaultSort={{ key: 'ratio', dir: 'desc' }} limit={25} />}
          />
        </Section>
      ) : null}
      {few.length ? (
        <Section
          id="few"
          title={x('xv.gq.few')}
          intro={t('gp.few.intro', { topic: fewEx ? tname(fewEx.topic) : '', k: fewEx ? fmtInt(fewEx.institutions) : '', r: rw, statuses: file.statuses.map((s) => statusName(t, s)).join(lang === 'en' ? ' or ' : 'หรือ'), n: fmtInt(file.max_institutions) })}
        >
          <Figure
            id="fig-few"
            number={2}
            title={x('xv.few.title', { n: fmtInt(file.max_institutions) })}
            tableTitle={tbl(2, t('gp.few.table'))}
            csv={figureCsv(`atlas-${rel}-gaps-few-institutions.csv`, few, fewColumns)}
            how={<p>{x('xv.few.how', { r: rw })}</p>}
            source={source}
            view={state.f}
            onView={(v) => update({ f: v })}
            chart={
              <>
              <ul className="few">
                {fewCap.shown.map((f) => (
                  <li key={f.topic} className="few-row">
                    <span className="few-name"><TopicLink topic={topic(f.topic) as Topic} showStatus /></span>
                    <span className="few-k"><b>{fmtInt(f.institutions)}</b> {x('xv.few.unit')}</span>
                  </li>
                ))}
              </ul>
              <ListMore {...fewCap.more} />
              </>
            }
            table={<DataTable caption={tbl(2, t('gp.few.table'))} rows={few} columns={fewColumns} rowKey={(f) => f.topic} stack={false} defaultSort={{ key: 'institutions', dir: 'asc' }} limit={25} />}
          />
        </Section>
      ) : null}
      {bridges.length ? (
        <Section id="bridges" title={x('xv.gq.bridge')} intro={bridgeEx ? t('gp.bridge.intro', { x: tname(bridgeEx.a), y: tname(bridgeEx.b), k: fmtInt(bridgeEx.shared) }) : undefined}>
          <Figure
            id="fig-bridges"
            number={3}
            title={x('xv.br.title')}
            tableTitle={tbl(3, t('gp.bridge.h'))}
            csv={figureCsv(`atlas-${rel}-gaps-bridges.csv`, bridges, bridgeColumns)}
            how={
              <>
                <p>{x('xv.br.how')}</p>
                <p>{t('gp.bridge.how', { s: fmtNum(file.bridge_min_similarity, 2), j: fmtNum(file.bridge_max_jaccard, 2) })}</p>
                <p className="how-terms">
                  <span>{t('glossary.terms')}:</span>
                  <Term term="jaccard" />
                </p>
              </>
            }
            source={source}
            view={state.b}
            onView={(v) => update({ b: v })}
            chart={
              <>
              <BridgePairs
                label={x('xv.br.title')}
                rows={bridgeCap.shown.map((b) => ({
                  key: `${b.a}~${b.b}`,
                  a: <TopicLink topic={topic(b.a) as Topic} showStatus />,
                  b: <TopicLink topic={topic(b.b) as Topic} showStatus />,
                  shared: b.shared,
                  sharedText: b.shared > 0 ? x('xv.br.shared', { k: fmtInt(b.shared) }) : x('xv.br.none'),
                  simText: x('xv.br.sim', { s: fmtNum(b.similarity, 2) }),
                }))}
              />
              <ListMore {...bridgeCap.more} />
              </>
            }
            table={<DataTable caption={tbl(3, t('gp.bridge.h'))} rows={bridges} columns={bridgeColumns} rowKey={(b) => `${b.a}~${b.b}`} defaultSort={{ key: 'similarity', dir: 'desc' }} limit={25} />}
          />
        </Section>
      ) : null}
      {file.concentration.length ? (
        <Section id="risk" title={x('xv.gq.risk')} intro={riskEx ? t('gp.risk.ex', { p: fmtPct(riskEx.top_share, 0), x: unitName(riskEx), top: riskEx.top_name ?? '' }) : undefined}>
          <label className="check">
            <input type="checkbox" checked={state.all === 'yes'} onChange={(e) => update({ all: e.target.checked ? 'yes' : 'no' })} />
            {t('gp.risk.all')}
          </label>
          <Figure
            id="fig-risk"
            number={4}
            title={x('xv.rk.title')}
            tableTitle={tbl(4, t('gp.risk.table'))}
            csv={figureCsv(`atlas-${rel}-concentration.csv`, risk, riskColumns)}
            how={
              <>
                <p>{x('xv.rk.how', { r: rw, p: fmtPct(file.max_top_share, 0) })}</p>
                <p>{t('gp.risk.how', { r: rw, m: fmtInt(file.min_articles), p: fmtPct(file.max_top_share, 0), h: fmtNum(file.max_hhi, 2) })}</p>
                <p className="how-terms">
                  <span>{t('glossary.terms')}:</span>
                  <Term term="hhi" />
                </p>
              </>
            }
            source={source}
            view={state.c}
            onView={(v) => update({ c: v })}
            legend={
              <ul className="sb-key">
                <li><span className="sb-sw is-top" aria-hidden="true" />{x('xv.rk.top')}</li>
                <li><span className="sb-sw" aria-hidden="true" />{x('xv.rk.rest')}</li>
                <li><span className="sb-sw is-mark" aria-hidden="true" />{x('xv.rk.bar', { p: fmtPct(file.max_top_share, 0) })}</li>
              </ul>
            }
            chart={
              riskSorted.length ? (
                <>
                <ul className="rk">
                  {riskCap.shown.map((c) => (
                    <li key={`${c.scope}:${c.id}:${c.kind}`} className="rk-row">
                      <span className="rk-unit">
                        {c.scope === 'topic' ? <TopicLink topic={topic(c.id) as Topic} showStatus /> : <b>{groupName(release, c.id, lang)}</b>}
                        <small>{t(c.kind === 'institution' ? 'gp.kind.institution' : 'gp.kind.journal')}: {topName(c)}</small>
                      </span>
                      <span className="rk-bar">
                        <SplitBar frac={c.top_share} marker={file.max_top_share} text={fmtPct(c.top_share, 0)} label={`${unitName(c)}: ${fmtPct(c.top_share, 0)}`} />
                        {c.concentrated ? <span className="flag-on">{t('gp.flag')}</span> : null}
                      </span>
                    </li>
                  ))}
                </ul>
                <ListMore {...riskCap.more} />
                </>
              ) : <p className="note">{t('gp.risk.all')}</p>
            }
            table={<DataTable caption={tbl(4, t('gp.risk.table'))} rows={risk} columns={riskColumns} rowKey={(c) => `${c.scope}:${c.id}:${c.kind}`} defaultSort={{ key: 'share', dir: 'desc' }} limit={25} />}
          />
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
