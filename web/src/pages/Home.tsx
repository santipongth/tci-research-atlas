import { useEffect, useState } from 'react'
import Header from '../sections/Header'
import AtlasMap from '../sections/AtlasMap'
import StatsBand from '../sections/StatsBand'
import GroupRanking from '../sections/GroupRanking'
import EmergingThemes from '../sections/EmergingThemes'
import Insights from '../sections/Insights'
import Methodology from '../sections/Methodology'
import { STR, type Lang } from '../lib/i18n'
import { loadAtlas, type AtlasData } from '../lib/loader'

export default function Home() {
  const [lang, setLang] = useState<Lang>('th')
  const [selected, setSelected] = useState<string | null>(null)
  const [data, setData] = useState<AtlasData | null>(null)

  useEffect(() => {
    let alive = true
    loadAtlas().then((d) => { if (alive) setData(d) })
    return () => { alive = false }
  }, [])

  if (!data) {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <div className="font-mono-data text-[13px] tracking-[0.18em] text-[#161611]/45">
          TCI RESEARCH ATLAS · LOADING…
        </div>
      </div>
    )
  }

  return (
    <div id="top" className="min-h-dvh">
      <Header lang={lang} setLang={setLang} />

      {/* hero */}
      <section className="mx-auto max-w-[1400px] px-5 pt-12 pb-8 lg:pt-16">
        <div className="eyebrow text-[#FF5F1F]">
          TCI · THAI RESEARCH LANDSCAPE · {data.totalArticles.toLocaleString('en-US')} ARTICLES
        </div>
        <h1 className="font-display mt-4 max-w-4xl text-[40px] font-semibold leading-[1.15] tracking-tight lg:text-[64px]">
          {(STR.heroTitle[lang] as string).split('\n').map((line, i) => (
            <span key={i} className="block">{line}</span>
          ))}
        </h1>
        <p className="mt-5 max-w-2xl text-[15.5px] leading-relaxed text-[#161611]/65">
          {lang === 'th'
            ? `สำรวจโครงสร้างของวารสารวิชาการไทยผ่านบทความ ${data.totalArticles.toLocaleString('en-US')} เรื่อง ที่ถูกจัดกลุ่มเชิงความหมายเป็น ${data.totalFields.toLocaleString('en-US')} ${data.dynamic ? 'หัวข้อวิจัย' : 'สาขา'} และรวมเป็น ${data.totalGroups} กลุ่มหลัก — ขนาดวงกลมแสดงจำนวนบทความ สีแสดงกลุ่ม คลิกที่วงกลมเพื่อเจาะลึกแต่ละหัวข้อ`
            : `Explore the structure of Thai academic journals through ${data.totalArticles.toLocaleString('en-US')} articles, semantically clustered into ${data.totalFields.toLocaleString('en-US')} ${data.dynamic ? 'topics' : 'fields'} and merged into ${data.totalGroups} groups. Circle size encodes article volume, color encodes the group — click any circle to drill down.`}
        </p>
        <div className="font-mono-data mt-4 text-[11.5px] tracking-wide text-[#161611]/45">
          {data.dynamic
            ? `● ${STR.dataLive[lang]}${data.lastCompleteYear ? ` · ${STR.dataThrough[lang]} ${data.lastCompleteYear}` : ''}${data.generatedAt ? ` · ${new Date(data.generatedAt).toLocaleDateString('th-TH')}` : ''}`
            : `○ ${STR.dataBundled[lang]}`}
        </div>
      </section>

      {/* stats */}
      <section className="mx-auto max-w-[1400px] px-5 pb-10">
        <StatsBand lang={lang} data={data} />
      </section>

      {/* atlas */}
      <section id="atlas" className="mx-auto max-w-[1400px] scroll-mt-20 px-5 pb-16">
        <AtlasMap lang={lang} selected={selected} onSelect={setSelected} data={data} />
      </section>

      {/* emerging themes (only when pipeline data provides statuses) */}
      <section id="emerging" className="mx-auto max-w-[1400px] scroll-mt-20 px-5 pb-20">
        <EmergingThemes lang={lang} selected={selected} onSelect={setSelected} data={data} />
      </section>

      {/* ranking */}
      <section id="ranking" className="mx-auto max-w-[1400px] scroll-mt-20 px-5 pb-20">
        <GroupRanking lang={lang} selected={selected} onSelect={setSelected} data={data} />
      </section>

      {/* insights */}
      <section id="insights" className="mx-auto max-w-[1400px] scroll-mt-20 px-5 pb-20">
        <Insights lang={lang} data={data} />
      </section>

      {/* method + footer */}
      <section id="method" className="mx-auto max-w-[1400px] scroll-mt-20 px-5 pb-10">
        <Methodology lang={lang} />
      </section>
    </div>
  )
}
