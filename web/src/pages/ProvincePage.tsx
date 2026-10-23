import { useParams } from 'react-router'
import { BarRank } from '../charts/BarRank'
import { rankBars } from '../charts/infographic'
import { Card, DashGrid, SeeAll } from '../components/dashboard/Card'
import { KpiCard, KpiRow } from '../components/dashboard/KpiCard'
import { PageBar } from '../components/dashboard/PageBar'
import { RankRows } from '../components/dashboard/RankRows'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { ProvinceLocator } from '../components/ProvinceLocator'
import { RequireRelease } from '../components/RequireRelease'
import { useReleaseFile } from '../data/atlasContext'
import { hasModule, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { InstitutionsFile, ProvinceStat, RegionsFile, Topic } from '../data/types'
import { windows } from '../lib/definition'
import { instName } from '../lib/executive'
import { fmtInt, fmtNum, fmtShare } from '../lib/format'
import { useI18n, useStrings, nameIn } from '../lib/i18n'
import { province as PV } from '../strings/province'

type TopicRow = { topic: Topic; count: number; share: number }

/** /province/:code: one province's page (the list of every province is on /places). */
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

function Province({ release, file }: { release: AtlasRelease; file: RegionsFile }) {
  const { code } = useParams()
  const s = useStrings(PV)
  const p = file.provinces.find((x) => x.code === code)
  if (!p) {
    return (
      <div className="container">
        <PageHeader title={s('pv.p.unknown')} lede={s('pv.p.unknownBody', { code: code ?? '' })} />
        <p className="dash-back"><SeeAll to="/places" label={s('pv.back')} /></p>
      </div>
    )
  }
  return <OneProvince release={release} file={file} p={p} />
}

/** One province: its figures, where it sits on the map, the topics it writes most about and its institutions. */
function OneProvince({ release, file, p }: { release: AtlasRelease; file: RegionsFile; p: ProvinceStat }) {
  const s = useStrings(PV)
  const { lang } = useI18n()
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
  const placed = file.provinces.filter((x) => x.articles > 0).sort((a, b) => b.articles - a.articles || a.code.localeCompare(b.code))
  const rank = placed.findIndex((x) => x.code === p.code) + 1
  const instRows = (insts?.institutions ?? []).filter((i) => i.province === p.code).sort((a, b) => b.articles - a.articles).slice(0, 8)
  const bars = rankBars(rows.map((r) => ({ key: nameIn(r.topic, lang), id: r.topic.id, count: r.count })), rows.length)
  return (
    <>
      <PageBar
        title={s('pv.p.title', { name })}
        sub={s('pv.p.sub', { a: w.start, b: w.end })}
        info={lead
          ? s('pv.p.lede', { a: w.start, b: w.end, name, n: fmtInt(p.articles), topic: nameIn(lead.topic, lang) })
          : s('pv.p.ledePlain', { a: w.start, b: w.end, name, n: fmtInt(p.articles) })}
      />
      <div className="dash">
        <KpiRow>
          <KpiCard icon="articles" label={s('pv.f.articles', { a: w.start, b: w.end })} value={fmtInt(p.articles)} />
          <KpiCard icon="topics" label={s('pv.f.recent', { a: R[0], b: R[1] })} value={fmtInt(p.articles_recent ?? null)} />
          <KpiCard icon="layers" label={s('pv.f.share')} value={fmtShare(p.share ?? null, 1)} sub={p.per_100k != null ? s('pv.f.per100kShort', { v: fmtNum(p.per_100k, 1) }) : undefined} />
          <KpiCard icon="places" label={s('pv.f.rank')} value={rank ? s('pv.f.rankShort', { r: fmtInt(rank) }) : '–'} sub={s('pv.f.rankOf', { n: fmtInt(placed.length) })} />
        </KpiRow>
        <DashGrid>
          <Card span={4} title={s('pv.map.one', { name })}>
            <div className="pv-locate">
              <ProvinceLocator articles={new Map(file.provinces.map((x) => [x.code, x.articles]))} current={p.code} label={s('pv.map.one', { name })} />
            </div>
          </Card>
          <Card span={insts ? 4 : 8} title={s('pv.t.h', { name })} info={lead ? s('pv.t.intro', { topic: nameIn(lead.topic, lang), p: fmtShare(lead.share, 0) }) : undefined}>
            {rows.length ? (
              <BarRank rows={bars.rows} href={(r) => `/topics/${r.id}`} value={(r) => s('pv.t.bar', { k: fmtInt(r.count), p: fmtShare(rows.find((x) => x.topic.id === r.id)?.share ?? null, 0) })} label={s('pv.t.fig', { name })} />
            ) : (
              <p className="card-empty">{s('pv.t.none')}</p>
            )}
          </Card>
          {insts ? (
            <Card span={4} title={s('pv.i.h', { name })} info={s('pv.i.intro', { k: fmtInt(insts.min_articles) })}>
              {instRows.length ? (
                <RankRows
                  label={s('pv.i.h', { name })}
                  rows={instRows.map((i) => {
                    const n = instName(i, lang)
                    return { key: i.id, to: `/institutions/${i.id}`, name: n.text, nameLang: n.lang ?? undefined, value: <b className="rise-a">{fmtInt(i.articles)}</b> }
                  })}
                />
              ) : (
                <p className="card-empty">{s('pv.i.none')}</p>
              )}
            </Card>
          ) : null}
        </DashGrid>
      </div>
    </>
  )
}
