import { Link, useNavigate, useParams } from 'react-router'
import { BarRank } from '../charts/BarRank'
import { rankBars } from '../charts/infographic'
import { DataTable, type Column } from '../components/DataTable'
import { Figure } from '../components/Figure'
import { ProvinceLocator } from '../components/ProvinceLocator'
import { EmptyState } from '../components/EmptyState'
import { InstitutionLink } from '../components/InstitutionLink'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { ShareBar } from '../components/ShareBar'
import { StatGrid, StatTile } from '../components/StatTile'
import { TopicLink } from '../components/TopicLink'
import { useReleaseFile } from '../data/atlasContext'
import { hasModule, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { InstitutionsFile, ProvinceStat, RegionsFile, Topic } from '../data/types'
import { windows } from '../lib/definition'
import { fmtInt, fmtNum, fmtShare } from '../lib/format'
import { useI18n, useStrings, nameIn } from '../lib/i18n'
import type { StrKey } from '../strings'
import { figureCsv } from '../lib/tableCsv'
import { provinceCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import { province as PV } from '../strings/province'

type TopicRow = { topic: Topic; count: number; share: number }

const REGION_ORDER = ['bangkok', 'central', 'north', 'northeast', 'south'] as const

/** "งานวิจัยในจังหวัดของฉัน": /province lists every province by region; /province/:code is one province's page. */
export default function ProvincePage() {
  const s = useStrings(PV)
  return (
    <RequireRelease title={s('pv.title')}>
      {(release) => (
        <ModuleFile<RegionsFile> release={release} module="regions" path={MODULE_FILES.regions} title={s('pv.title')}>
          {(file) => <Province release={release} file={file} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

function Picker({ file, current }: { file: RegionsFile; current?: string }) {
  const s = useStrings(PV)
  const { lang } = useI18n()
  const navigate = useNavigate()
  const sorted = [...file.provinces].sort((a, b) => (lang === 'en' ? a.name_en.localeCompare(b.name_en) : a.name_th.localeCompare(b.name_th, 'th')))
  return (
    <p className="pv-pick">
      <label htmlFor="pv-select">{current ? s('pv.p.other') : s('pv.pick')}</label>
      <select id="pv-select" value={current ?? ''} onChange={(e) => e.target.value && navigate(`/province/${e.target.value}`)}>
        {current ? null : <option value="">{s('pv.pickNone')}</option>}
        {sorted.map((p) => (
          <option key={p.code} value={p.code}>{lang === 'en' ? p.name_en : p.name_th}</option>
        ))}
      </select>
    </p>
  )
}

function Province({ release, file }: { release: AtlasRelease; file: RegionsFile }) {
  const { code } = useParams()
  const s = useStrings(PV)
  const { t, lang } = useI18n()
  const w = file.window
  const span = { a: w.start, b: w.end }
  if (!code) {
    const byRegion = REGION_ORDER.map((key) => ({ key, rows: file.provinces.filter((p) => p.region === key).sort((a, b) => b.articles - a.articles) })).filter((g) => g.rows.length)
    return (
      <div className="container">
        <PageHeader title={s('pv.title')} lede={s('pv.lede')}>
          <Picker file={file} />
        </PageHeader>
        <Section id="all" title={s('pv.byRegion')} intro={s('pv.byRegion.intro', span)}>
          <div className="pv-index">
            <figure className="pv-map">
              <ProvinceLocator articles={new Map(file.provinces.map((p) => [p.code, p.articles]))} label={s('pv.map.all')} size="lg" />
              <figcaption>{s('pv.map.allCap')}</figcaption>
            </figure>
            <div>
          {byRegion.map((g) => (
            <div className="pv-region" key={g.key}>
              <h3>{t(`rg.region.${g.key}` as StrKey)}</h3>
              <ul className="pv-list">
                {g.rows.map((p) => (
                  <li key={p.code}>
                    <Link to={`/province/${p.code}`}>{lang === 'en' ? p.name_en : p.name_th}</Link>
                    <span>{fmtInt(p.articles)}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
            </div>
          </div>
        </Section>
      </div>
    )
  }
  const p = file.provinces.find((x) => x.code === code)
  if (!p) {
    return (
      <div className="container">
        <PageHeader title={s('pv.p.unknown')} lede={s('pv.p.unknownBody', { code })}>
          <Picker file={file} />
        </PageHeader>
      </div>
    )
  }
  return <OneProvince release={release} file={file} p={p} />
}

function OneProvince({ release, file, p }: { release: AtlasRelease; file: RegionsFile; p: ProvinceStat }) {
  const s = useStrings(PV)
  const { t, lang } = useI18n()
  const instFile = useReleaseFile<InstitutionsFile>(hasModule(release, 'institutions') ? MODULE_FILES.institutions : null)
  const insts = instFile.status === 'ready' ? instFile.data : null
  const name = lang === 'en' ? p.name_en : p.name_th
  const w = file.window
  const R = windows(release.overview.last_complete_year).R
  const rows: TopicRow[] = (p.topics ?? []).flatMap((x) => {
    const tp = release.topicById.get(x.topic)
    return tp ? [{ topic: tp, count: x.count, share: x.share }] : []
  })
  const lead = rows[0]
  const placed = [...file.provinces].sort((a, b) => b.articles - a.articles || a.code.localeCompare(b.code))
  const rank = placed.findIndex((x) => x.code === p.code) + 1
  const instRows = (insts?.institutions ?? []).filter((i) => i.province === p.code).sort((a, b) => b.articles - a.articles).slice(0, 8)
  const maxShare = Math.max(0.0001, ...rows.map((r) => r.share))
  const [state, update] = useUrlState(provinceCodec)
  const bars = rankBars(rows.map((r) => ({ key: lang === 'en' ? r.topic.en : r.topic.th, id: r.topic.id, count: r.count })), rows.length)
  const columns: Column<TopicRow>[] = [
    { key: 'topic', csvHeader: 'topic_id', header: t('col.topic'), rowHeader: true, cell: (r) => <TopicLink topic={r.topic} showStatus />, sortValue: (r) => nameIn(r.topic, lang), csv: (r) => r.topic.id },
    { key: 'count', csvHeader: 'articles', header: t('col.articles'), numeric: true, cell: (r) => fmtInt(r.count), sortValue: (r) => r.count },
    { key: 'share', csvHeader: 'share', header: s('pv.t.share'), numeric: true, cell: (r) => <ShareBar value={r.share} max={maxShare} />, sortValue: (r) => r.share },
  ]
  return (
    <div className="container">
      <PageHeader
        title={s('pv.p.title', { name })}
        lede={lead
          ? s('pv.p.lede', { a: w.start, b: w.end, name, n: fmtInt(p.articles), topic: lang === 'en' ? lead.topic.en : lead.topic.th })
          : s('pv.p.ledePlain', { a: w.start, b: w.end, name, n: fmtInt(p.articles) })}
      >
        <Picker file={file} current={p.code} />
      </PageHeader>
      <Section id="numbers" title={s('pv.f.h', { name })}>
        <div className="pv-hero">
          <figure className="pv-map">
            <ProvinceLocator articles={new Map(file.provinces.map((x) => [x.code, x.articles]))} current={p.code} label={s('pv.map.one', { name })} />
            <figcaption>{s('pv.map.oneCap', { name })}</figcaption>
          </figure>
        <StatGrid cols={2}>
          <StatTile label={s('pv.f.articles', { a: w.start, b: w.end })} value={fmtInt(p.articles)} sub={s('pv.f.articlesSub')} />
          <StatTile label={s('pv.f.recent', { a: R[0], b: R[1] })} value={fmtInt(p.articles_recent ?? null)} sub={s('pv.f.recentSub')} />
          <StatTile label={s('pv.f.share')} value={fmtShare(p.share ?? null, 1)} sub={s('pv.f.shareSub')} />
          <StatTile label={s('pv.f.rank')} value={s('pv.f.rankV', { r: fmtInt(rank), n: fmtInt(placed.length) })} sub={s('pv.f.rankSub')} />
          {p.per_100k != null ? <StatTile label={s('pv.f.per100k')} value={fmtNum(p.per_100k, 1)} sub={s('pv.f.per100kSub', { y: file.population_year ?? '' })} /> : null}
        </StatGrid>
        </div>
      </Section>
      <Section id="topics" title={s('pv.t.h', { name })} intro={lead ? s('pv.t.intro', { topic: lang === 'en' ? lead.topic.en : lead.topic.th, p: fmtShare(lead.share, 0) }) : undefined}>
        {rows.length ? (
          <Figure
            id="fig-pv-topics"
            number={1}
            title={s('pv.t.fig', { name })}
            tableTitle={t('table.n', { n: 1, title: s('pv.t.table', { name }) })}
            csv={figureCsv(`atlas-${release.overview.release}-${p.code}-topics.csv`, rows, columns)}
            how={<p>{s('pv.t.how')}</p>}
            source={t('source.line', { release: release.overview.release })}
            view={state.v}
            onView={(v) => update({ v })}
            chart={<BarRank rows={bars.rows} href={(r) => `/topics/${r.id}`} value={(r) => s('pv.t.bar', { k: fmtInt(r.count), p: fmtShare(rows.find((x) => x.topic.id === r.id)?.share ?? null, 0) })} label={s('pv.t.fig', { name })} />}
            table={<DataTable caption={t('table.n', { n: 1, title: s('pv.t.table', { name }) })} rows={rows} columns={columns} rowKey={(r) => r.topic.id} defaultSort={{ key: 'count', dir: 'desc' }} csvFilename={`atlas-${release.overview.release}-${p.code}-topics.csv`} limit={25} />}
          />
        ) : (
          <EmptyState title={s('pv.t.none')} />
        )}
      </Section>
      {insts ? (
        <Section id="institutions" title={s('pv.i.h', { name })} intro={s('pv.i.intro', { k: fmtInt(insts.min_articles) })}>
          {instRows.length ? (
            <ul className="pv-insts">
              {instRows.map((i) => (
                <li key={i.id}>
                  <InstitutionLink inst={i} />
                  <span>{s('pv.i.articles', { k: fmtInt(i.articles) })}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="hint">{s('pv.i.none')}</p>
          )}
        </Section>
      ) : null}
      <p className="page-back"><Link to="/regions">{s('pv.back')}</Link> · <Link to="/province">{s('pv.byRegion')}</Link></p>
      <p className="source">{t('source.line', { release: release.overview.release })}</p>
    </div>
  )
}
