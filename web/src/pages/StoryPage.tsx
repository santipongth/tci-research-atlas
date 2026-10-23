import { useState } from 'react'
import { Link } from 'react-router'
import tciLogo from '../assets/brand/partners/tci.png'
import { HowNote } from '../components/HowNote'
import { KeepTogether } from '../components/KeepTogether'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { useReleaseFile } from '../data/atlasContext'
import { hasModule, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { RegionsFile } from '../data/types'
import { perVars, pickFindings } from '../lib/findings'
import { fmtInt, fmtNum, fmtPct, fmtSignedPct } from '../lib/format'
import { useI18n, useStrings } from '../lib/i18n'
import { sortBy } from '../lib/sort'
import { pickRisers } from '../lib/story'
import { drawStoryCard } from '../lib/storyCard'
import { story as ST } from '../strings/story'

interface Fact {
  id: string
  big: string
  line: string
  sub: string
  to: string
}

/** "เรื่องเล่าข้อมูลรายไตรมาส": five facts of the release, each with a square share image drawn in the browser. */
export default function StoryPage() {
  const s = useStrings(ST)
  return <RequireRelease title={s('st.title', { release: '' })}>{(release) => <Story release={release} />}</RequireRelease>
}

function Story({ release }: { release: AtlasRelease }) {
  const s = useStrings(ST)
  const { lang, name } = useI18n()
  const ov = release.overview
  const regionsFile = useReleaseFile<RegionsFile>(hasModule(release, 'regions') ? MODULE_FILES.regions : null)
  const facts: Fact[] = []
  const [leader] = pickRisers(release.topics, 1)
  if (leader) {
    const g = leader.metrics.share_growth ?? 0
    const m = g >= 1 ? fmtNum(1 + g, 1) : null
    facts.push({
      id: 'rise', big: m ? (lang === 'en' ? `×${m}` : `${m} เท่า`) : fmtSignedPct(g, 0), line: s('st.rise.line', { topic: name(leader) }),
      sub: m ? s('st.rise.subTimes', { m }) : s('st.rise.subPct', { g: fmtSignedPct(g, 0) }), to: `/topics/${leader.id}`,
    })
  }
  const emerging = sortBy(release.topics.filter((tp) => tp.status === 'EMERGING'), (tp) => tp.score, 'desc')
  if (emerging.length) {
    facts.push({
      id: 'emerging', big: s('st.em.big', { n: fmtInt(emerging.length) }), line: s('st.em.line'),
      sub: s('st.em.sub', { list: emerging.slice(0, 2).map((tp) => `“${name(tp)}”`).join(lang === 'en' ? ' and ' : ' และ ') }), to: '/emerging',
    })
  }
  const findings = pickFindings(release.topics)
  const large = findings.find((f) => f.kind === 'large')?.topic
  if (large) {
    const per = perVars(large.metrics.share_recent)
    facts.push({ id: 'large', big: s('st.big.big', per), line: s('st.big.line', { topic: name(large) }), sub: s('st.big.sub', { ...per, g: fmtSignedPct(large.metrics.share_growth, 0) }), to: `/topics/${large.id}` })
  }
  const down = findings.find((f) => f.kind === 'decline')?.topic
  if (down) {
    facts.push({ id: 'decline', big: fmtSignedPct(down.metrics.share_growth, 0), line: s('st.down.line', { topic: name(down) }), sub: s('st.down.sub', { g: fmtPct(Math.abs(down.metrics.share_growth ?? 0), 0) }), to: `/topics/${down.id}` })
  }
  const provinces = regionsFile.status === 'ready' ? sortBy([...regionsFile.data.provinces], (p) => p.articles, 'desc') : []
  if (provinces.length >= 2 && provinces[0].share != null) {
    const pn = (i: number) => (lang === 'en' ? provinces[i].name_en : provinces[i].name_th)
    facts.push({ id: 'province', big: fmtPct(provinces[0].share, 0), line: s('st.prov.line', { name: pn(0) }), sub: s('st.prov.sub', { p: fmtPct(provinces[0].share, 0), name: pn(0), next: pn(1) }), to: `/province/${provinces[0].code}` })
  } else if (regionsFile.status !== 'loading') {
    facts.push({ id: 'kpi', big: fmtInt(ov.kpis.articles), line: s('st.kpi.line'), sub: s('st.kpi.sub', { k: fmtInt(ov.kpis.topics), y: ov.last_complete_year }), to: '/overview' })
  }
  return (
    <div className="container">
      <PageHeader title={s('st.title', { release: ov.release })} titleNode={<KeepTogether text={s('st.title', { release: ov.release })} phrase={'งานวิจัยไทย'} />} lede={s('st.lede')} />
      <ol className="facts">
        {facts.map((f, i) => (
          <li className="fact" key={f.id}>
            <p className="fact-n" aria-hidden="true">{i + 1}</p>
            <div className="fact-body">
              <p className="fact-big">{f.big}</p>
              <h2 className="fact-line">{f.line}</h2>
              <p className="fact-sub">{f.sub}</p>
              <p className="fact-acts">
                <ShareButton fact={f} index={`${i + 1} / ${facts.length}`} release={release} />
                <Link to={f.to}>{s('st.more')}</Link>
              </p>
            </div>
          </li>
        ))}
      </ol>
      <HowNote>
        <p>{s('st.how')}</p>
      </HowNote>
    </div>
  )
}

function ShareButton({ fact, index, release }: { fact: Fact; index: string; release: AtlasRelease }) {
  const s = useStrings(ST)
  const { t } = useI18n()
  const [busy, setBusy] = useState(false)
  const save = async () => {
    setBusy(true)
    try {
      await Promise.all([document.fonts.load('700 60px Sarabun'), document.fonts.load('400 38px Sarabun')]).catch(() => undefined)
      const logo = new Image()
      logo.src = tciLogo
      await logo.decode().catch(() => undefined)
      const canvas = document.createElement('canvas')
      drawStoryCard(canvas, { index, big: fact.big, line: fact.line, sub: fact.sub, footer: s('st.footer', { release: release.overview.release }), sample: release.sample ? t('sample.tag') : null }, logo)
      const blob = await new Promise<Blob | null>((ok) => canvas.toBlob(ok, 'image/png'))
      if (!blob) return
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `atlas-${release.overview.release}-${fact.id}.png`
      a.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } finally {
      setBusy(false)
    }
  }
  return (
    <button type="button" className="btn" onClick={save} disabled={busy}>
      <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">
        <path d="M8 1.5v9 M4.5 7l3.5 3.5L11.5 7 M2.5 12.5v2h11v-2" fill="none" stroke="currentColor" strokeWidth="1.6" />
      </svg>
      {busy ? s('st.making') : s('st.download')}
    </button>
  )
}
