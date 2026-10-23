import { Link, useParams } from 'react-router'
import { ChecklistBars, type CheckRow } from '../charts/ChecklistBars'
import { checkState, periodMix } from '../charts/editorLayout'
import { PeriodMix } from '../charts/PeriodMix'
import SmallMultiples from '../charts/SmallMultiples'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { BarRank } from '../charts/BarRank'
import { rankBars } from '../charts/infographic'
import { DashGrid } from '../components/dashboard/Card'
import { KpiCard, KpiRow } from '../components/dashboard/KpiCard'
import { PageBar } from '../components/dashboard/PageBar'
import { RankRows } from '../components/dashboard/RankRows'
import { TopicLink } from '../components/TopicLink'
import { useReleaseFile } from '../data/atlasContext'
import { hasModule, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { CompletenessItem, JournalDetail, JournalSummary, JournalsFile, MethodsFile, Topic } from '../data/types'
import { DASH, fmtInt, fmtNum, fmtPct, fmtPts, fmtShare, yearSpan } from '../lib/format'
import { useI18n, useStrings } from '../lib/i18n'
import { inhouseGap, journalName, otherJournalName } from '../lib/journals'
import { editorViz } from '../strings/editorViz'
import { journals } from '../strings/journals'

export default function JournalPage() {
  const { id } = useParams()
  const sj = useStrings(journals)
  return (
    <RequireRelease title={sj('jr.title')}>
      {(release) => (
        <ModuleFile<JournalsFile> release={release} module="journals" path={MODULE_FILES.journals} title={sj('jr.title')}>
          {(file) => <JournalView release={release} file={file} id={id ?? ''} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

function JournalView({ release, file, id }: { release: AtlasRelease; file: JournalsFile; id: string }) {
  const sj = useStrings(journals)
  const journal = file.journals.find((j) => j.id === id)
  if (!journal) {
    return (
      <div className="container">
        <PageHeader title={sj('jr.notFound', { id: id || DASH })} lede={sj('jr.notFound.body')} />
        <p className="mt-6"><Link to="/journals">{sj('jr.back')}</Link></p>
      </div>
    )
  }
  return <JournalContent key={journal.id} release={release} file={file} journal={journal} />
}

function JournalContent({ release, file, journal }: { release: AtlasRelease; file: JournalsFile; journal: JournalSummary }) {
  const { t, lang, name } = useI18n()
  const sj = useStrings(journals)
  const s = useStrings(editorViz)
  const detailFile = useReleaseFile<JournalDetail>(`journals/${journal.id}.json`)
  const detail = detailFile.status === 'ready' ? detailFile.data : null
  const methodsFile = useReleaseFile<MethodsFile>(hasModule(release, 'methods') ? MODULE_FILES.methods : null)
  const methodInfo = new Map((methodsFile.status === 'ready' ? methodsFile.data.methods : []).map((m) => [m.key, m]))
  const w = file.window
  const shown = journalName(journal, lang)
  const other = otherJournalName(journal, lang)
  const topicOf = (tid: string): Topic | undefined => release.topicById.get(tid)
  const byId = new Map(file.journals.map((j) => [j.id, j]))
  const topics = (detail?.topics ?? []).filter((s) => topicOf(s.topic))
  const comp = detail?.completeness ?? []
  const methods = detail?.methods ?? []
  const peers = (detail?.peers ?? []).filter((p) => byId.has(p.id))
  const opps = (detail?.opportunities ?? []).filter((o) => topicOf(o.topic))
  const gained = (detail?.gained ?? []).filter((s) => topicOf(s.topic))
  const lost = (detail?.lost ?? []).filter((s) => topicOf(s.topic))
  const mix = periodMix([...gained, ...lost])
  const ty = detail?.topic_years ?? null
  const tyTopics = (ty?.topics ?? []).filter((x) => topicOf(x.topic))
  const hasTy = ty !== null && tyTopics.length > 0 && ty.years.length > 1
  const recentSpan = yearSpan(file.recent.start, file.recent.end)
  const baseSpan = yearSpan(file.baseline.start, file.baseline.end)
  const owner = journal.owner || ''
  /** an empty value: too few articles ("low data") or unknown — never shown as zero */
  const gap = journal.low_data ? sj('jr.lowData') : sj('jr.unknown')
  const inhouseSub = journal.inhouse_share == null && inhouseGap(journal) === 'owner_not_found'
    ? sj('jr.ownerNotFound')
    : owner ? sj(journal.owner_source === 'inferred' ? 'jr.inhouseSubInferred' : 'jr.inhouseSub', { o: owner }) : sj('jr.noOwner')
  const topTopic = topics.length ? topicOf(topics.reduce((a, b) => (b.count > a.count ? b : a)).topic) : undefined
  const mixName = (tid: string) => {
    const tp = topicOf(tid)
    return tp ? name(tp) : tid
  }
  const pts = (before: number, after: number) => s('pm.pts', { d: fmtPts(after - before) })
  const thinYears = ty ? ty.years.filter((_, k) => ty.articles[k] < ty.min_articles) : []
  /** the example: the largest topic, from its first to its last year with a share */
  const tyLead = (() => {
    const first = tyTopics[0]
    if (!ty || !first) return null
    const known = first.shares.flatMap((v, k) => (v == null ? [] : [k]))
    if (known.length < 2) return null
    const [a, b] = [known[0], known[known.length - 1]]
    return s('ty.lead', { t: mixName(first.topic), a: fmtShare(first.shares[a] ?? null, 0), y1: ty.years[a], b: fmtShare(first.shares[b] ?? null, 0), y2: ty.years[b] })
  })()
  const moved = mix.rows.length ? mix.rows.reduce((a, b) => (Math.abs(b.after - b.before) > Math.abs(a.after - a.before) ? b : a)) : null
  const checks: CheckRow[] = comp.map((c) => ({
    key: c.key, name: sj(`comp.${c.key}` as keyof typeof journals), rate: c.rate ?? null, state: checkState(c.rate), value: c.rate == null ? sj('jr.unknown') : fmtPct(c.rate, 0),
  }))
  const nFull = checks.filter((c) => c.state === 'full').length
  const weakest = comp.filter((c) => c.rate != null).reduce<CompletenessItem | null>((a, b) => (a === null || (b.rate as number) < (a.rate as number) ? b : a), null)
  const methodName = (key: string) => {
    const m = methodInfo.get(key)
    return m ? (lang === 'en' ? m.en : m.th) : key
  }
  return (
    <>
      <PageBar
        title={shown.text}
        titleLang={shown.lang ?? undefined}
        sub={[
          other ?? '',
          journal.tci_tier ? sj('jr.tier.n', { n: journal.tci_tier }) : '',
          journal.publisher ? sj('jr.publisher', { p: journal.publisher }) : '',
          journal.first_year && journal.last_year ? sj('jr.years', { a: journal.first_year, b: journal.last_year }) : '',
          journal.issn ? `ISSN ${journal.issn}` : '',
        ].filter(Boolean).join(' · ')}
        info={journal.low_data ? sj('jr.lowDataBody', { a: w.start, b: w.end, n: fmtInt(file.min_articles) }) : undefined}
        actions={journal.url ? <a className="see-all" href={journal.url} target="_blank" rel="noopener noreferrer">{sj('jr.site')}<span className="sr-only"> {t('newTab')}</span></a> : null}
      />
      <div className="dash">
        <KpiRow>
          <KpiCard icon="articles" label={sj('col.articlesW')} value={fmtInt(journal.articles_window)} sub={sj('jr.articlesSub', { a: w.start, b: w.end, all: fmtInt(journal.articles) })} />
          <KpiCard icon="layers" label={sj('col.completeness')} value={journal.completeness == null ? gap : fmtNum(journal.completeness, 0)} info={sj('jr.completenessSub')} />
          <KpiCard icon="building" label={sj('col.inhouse')} value={journal.inhouse_share == null ? gap : fmtPct(journal.inhouse_share, 0)} info={inhouseSub} />
          <KpiCard
            icon="goals"
            label={sj('col.foreign')}
            value={journal.foreign_share == null ? gap : fmtPct(journal.foreign_share, 0)}
            sub={sj('jr.orgsSubN', { n: fmtInt(journal.n_orgs ?? 0) })}
            info={<>{sj('jr.foreignSub')}. {journal.effective_orgs == null ? null : sj('jr.orgsSub', { n: fmtInt(journal.n_orgs ?? 0), e: fmtNum(journal.effective_orgs, 1) })}</>}
          />
        </KpiRow>
        {topics.length ? (
          <DashGrid>
            <Section id="topics" span={hasTy ? 5 : 12} title={sj('jr.topics.h')} intro={sj('jr.topics.intro', { a: w.start, b: w.end, topic: topTopic ? name(topTopic) : DASH })}>
              <BarRank
                rows={rankBars(topics.map((x) => ({ key: topicOf(x.topic) ? name(topicOf(x.topic) as Topic) : x.topic, id: x.topic, count: x.count })), 8).rows}
                href={(r) => (r.id && topicOf(r.id) ? `/topics/${r.id}` : null)}
                value={(r) => fmtInt(r.count)}
                label={sj('jr.topics.h')}
              />
            </Section>
            {hasTy && ty ? (
              <Section id="topic-years" span={7} title={s('ty.fig', { n: fmtInt(tyTopics.length), a: ty.years[0], b: ty.years[ty.years.length - 1] })} intro={[s('ty.how'), tyLead, thinYears.length ? s('ty.thin', { m: fmtInt(ty.min_articles), years: thinYears.join(', ') }) : ''].filter(Boolean).join(' ')}>
                <SmallMultiples
                  years={ty.years}
                  series={tyTopics.map((x) => ({ id: x.topic, label: mixName(x.topic), values: x.shares.map((v) => v ?? null) }))}
                  format={(v) => fmtShare(v, 0)}
                  axisFormat={(v) => fmtShare(v, 0)}
                  mono
                />
              </Section>
            ) : null}
          </DashGrid>
        ) : null}
        {mix.rows.length || comp.length ? (
          <DashGrid>
            {mix.rows.length ? (
              <Section
                id="drift"
                span={comp.length ? 6 : 12}
                title={sj('jr.drift.h')}
                intro={<>{moved ? s('pm.lead', { t: mixName(moved.topic), a: fmtShare(moved.before, 0), b: fmtShare(moved.after, 0) }) : null} {s('pm.how', { b: baseSpan, r: recentSpan })}</>}
              >
                <PeriodMix
                  rows={mix.rows}
                  other={mix.other}
                  periods={[baseSpan, recentSpan]}
                  name={(tid) => (topicOf(tid) ? <TopicLink topic={topicOf(tid) as Topic} /> : tid)}
                  fmt={(v) => fmtShare(v, 0)}
                  change={pts}
                  otherName={s('pm.other')}
                  label={s('pm.label', {
                    b: baseSpan,
                    r: recentSpan,
                    x: mix.rows.map((r) => `${mixName(r.topic)} ${fmtShare(r.before, 0)}`).join(', '),
                    y: mix.rows.map((r) => `${mixName(r.topic)} ${fmtShare(r.after, 0)}`).join(', '),
                  })}
                />
              </Section>
            ) : null}
            {comp.length ? (
              <Section
                id="completeness"
                span={mix.rows.length ? 6 : 12}
                title={sj('jr.comp.h')}
                intro={<>{weakest && nFull < checks.length ? s('ck.lead', { k: fmtInt(nFull), n: fmtInt(checks.length), item: sj(`comp.${weakest.key}` as keyof typeof journals), p: fmtPct(weakest.rate ?? null, 0) }) : s('ck.leadAll', { n: fmtInt(checks.length) })} {sj('jr.comp.intro')}</>}
              >
                <ChecklistBars rows={checks} words={{ full: s('ck.full'), partial: s('ck.partial'), none: s('ck.none'), unknown: s('ck.unknown') }} label={s('ck.label', { n: fmtInt(checks.length) })} />
              </Section>
            ) : null}
          </DashGrid>
        ) : null}
        {peers.length || methods.length || opps.length ? (
          <DashGrid>
            {peers.length ? (
              <Section id="peers" span={4} title={sj('jr.peers.h')} intro={sj('jr.peers.intro')}>
                <RankRows
                  numbered={false}
                  label={sj('jr.peers.h')}
                  rows={peers.map((p) => {
                    const j = byId.get(p.id) as JournalSummary
                    const n = journalName(j, lang)
                    return { key: p.id, to: `/journals/${p.id}`, name: n.text, nameLang: n.lang ?? undefined, value: <b className="rise-a">{fmtInt(j.articles_window)}</b> }
                  })}
                />
              </Section>
            ) : null}
            {methods.length ? (
              <Section id="methods" span={4} title={sj('jr.methods.h')} intro={sj('jr.methods.intro', { p: fmtPct(journal.methods_coverage ?? null, 0) })}>
                <BarRank rows={rankBars(methods.map((x) => ({ key: methodName(x.method), id: x.method, count: x.share })), 6).rows} value={(r) => fmtPct(r.count, 0)} label={sj('jr.methods.h')} />
              </Section>
            ) : null}
            {opps.length ? (
              <Section id="opportunities" span={4} title={sj('jr.opp.h')} intro={sj('jr.opp.intro')}>
                <RankRows
                  numbered={false}
                  label={sj('jr.opp.h')}
                  rows={opps.map((o) => {
                    const tp = topicOf(o.topic) as Topic
                    return { key: o.topic, to: `/topics/${tp.id}`, name: name(tp), meta: <span className="rise-sub">{sj(o.reason === 'in_scope' ? 'jr.opp.in_scope' : 'jr.opp.adjacent', { n: fmtInt(o.journal_articles), h: fmtInt(o.hosts) })}</span> }
                  })}
                />
              </Section>
            ) : null}
          </DashGrid>
        ) : null}
        {detailFile.status === 'loading' ? <p className="loading" role="status">{t('loading')}</p> : null}
      </div>
    </>
  )
}
