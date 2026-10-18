import { STR, fmt, pct, type Lang } from '../lib/i18n'
import type { AtlasData } from '../lib/loader'

interface Insight {
  stat: string
  th: { title: string; body: string }
  en: { title: string; body: string }
}

export default function Insights({ lang, data }: { lang: Lang; data: AtlasData }) {
  const { groups: GROUPS, nodes: NODES, totalArticles: TOTAL_ARTICLES } = data
  const byId = new Map(GROUPS.map((g) => [g.id, g]))
  const pick = (...ids: string[]) => ids.reduce((s, id) => s + (byId.get(id)?.articles ?? 0), 0)

  const fields = NODES.filter((n) => n.kind === 'field')
  const top2 = GROUPS[0].articles + GROUPS[1].articles
  const longTail = fields.filter((f) => f.articles < 100)
  const longTailSum = longTail.reduce((s, f) => s + f.articles, 0)
  const hybrid = fields.filter((f) => f.th.includes('และ') && f.th.indexOf('และ') > 3)
  const smallest = GROUPS[GROUPS.length - 1]

  const insights: Insight[] = []

  // 1. สายสุขภาพรวม — เฉพาะชุดข้อมูล bundled ที่มี group ids มาตรฐาน
  const healthAll = pick('health-sci', 'medicine', 'nursing', 'dentistry', 'psychology', 'rehab-sport')
  if (healthAll > 0) {
    insights.push({
      stat: pct(healthAll, TOTAL_ARTICLES),
      th: {
        title: 'สายสุขภาพครองแผนที่งานวิจัยไทย',
        body: `เมื่อรวมวิทยาศาสตร์สุขภาพ การแพทย์-เภสัช-สาธารณสุข พยาบาล ทันตแพทย์ จิตวิทยา และการกีฬาเข้าด้วยกัน งานวิจัยสายสุขภาพคิดเป็น ${fmt(healthAll)} บทความ หรือเกือบ 1 ใน 3 ของวารสารไทยทั้งหมด — โครงสร้างที่สะท้อนทั้งจำนวนวารสารและกำลังคนในสาขานี้`,
      },
      en: {
        title: 'Health dominates the Thai research map',
        body: `Health sciences, medicine-pharmacy-public health, nursing, dentistry, psychology and sport science together account for ${fmt(healthAll)} articles — nearly one in three of all Thai journal articles.`,
      },
    })
  }

  // 2. concentration — generic
  insights.push({
    stat: pct(top2, TOTAL_ARTICLES),
    th: {
      title: 'สองขั้วใหญ่กินพื้นที่เกือบครึ่งประเทศ',
      body: `${GROUPS[0].th} (${pct(GROUPS[0].articles, TOTAL_ARTICLES)}) และ${GROUPS[1].th} (${pct(GROUPS[1].articles, TOTAL_ARTICLES)}) รวมกันแทบครึ่งหนึ่งของบทความทั้งหมด ขณะที่${GROUPS[2].th}ซึ่งใหญ่เป็นอันดับ 3 มีเพียง ${pct(GROUPS[2].articles, TOTAL_ARTICLES)}`,
    },
    en: {
      title: 'Two poles hold nearly half the country',
      body: `${GROUPS[0].en} (${pct(GROUPS[0].articles, TOTAL_ARTICLES)}) and ${GROUPS[1].en} (${pct(GROUPS[1].articles, TOTAL_ARTICLES)}) together make up almost half of all articles, while third-ranked ${GROUPS[2].en} holds only ${pct(GROUPS[2].articles, TOTAL_ARTICLES)}.`,
    },
  })

  // 3. long tail — generic
  insights.push({
    stat: `${longTail.length} ${lang === 'th' ? (data.dynamic ? 'หัวข้อ' : 'สาขา') : (data.dynamic ? 'topics' : 'fields')}`,
    th: {
      title: 'หางยาวของหัวข้อเล็กจิ๋ว',
      body: `มี ${longTail.length} จาก ${fields.length} ที่มีบทความต่ำกว่า 100 เรื่อง รวมกันได้เพียง ${fmt(longTailSum)} บทความ (${pct(longTailSum, TOTAL_ARTICLES, 2)}) — หัวข้อเหล่านี้อาจเป็นช่องว่างของระบบวารสารไทย หรือพื้นที่ที่งานวิจัยไหลไปตีพิมพ์ต่างประเทศ`,
    },
    en: {
      title: 'A long tail of tiny topics',
      body: `${longTail.length} of ${fields.length} have fewer than 100 articles, totaling just ${fmt(longTailSum)} articles (${pct(longTailSum, TOTAL_ARTICLES, 2)}) — these may be structural gaps in Thai journals, or areas where research flows to international venues.`,
    },
  })

  // 4. hybrid/interdisciplinary — generic
  if (hybrid.length > 0) {
    insights.push({
      stat: `${hybrid.length} ${lang === 'th' ? (data.dynamic ? 'หัวข้อ' : 'สาขา') : (data.dynamic ? 'topics' : 'fields')}`,
      th: {
        title: 'งานวิจัยสหวิทยาการที่ชื่อบอกไว้',
        body: `หัวข้อที่ชื่อเชื่อมสองวิชาเข้าด้วยกัน เช่น ${hybrid.slice(0, 3).map((f) => f.th).join(' ')} มีถึง ${hybrid.length} รายการ — หลักฐานว่าขอบเขตวินัยในวารสารไทยซ้อนทับกันมากกว่าที่หมวดหมู่ดั้งเดิมจะรองรับ`,
      },
      en: {
        title: 'Interdisciplinarity written into topic names',
        body: `${hybrid.length} topics join two disciplines in their very name — evidence that Thai journal boundaries overlap more than legacy categories suggest.`,
      },
    })
  }

  // 5. AI/ML — เฉพาะเมื่อมี field ที่เกี่ยวข้อง
  const ai = fields.find((f) => f.th.includes('ปัญญาประดิษฐ์') || /AI|machine learning/i.test(f.en))
  if (ai) {
    insights.push({
      stat: pct(ai.articles, TOTAL_ARTICLES, 2),
      th: {
        title: 'AI/ML ยังเป็นจุดเล็กบนแผนที่',
        body: `"${ai.th}" มีเพียง ${fmt(ai.articles)} บทความ แม้เป็นหัวข้อร้อนระดับโลก — สัญญาณให้บรรณาธิการและผู้บริหารมองหาโอกาสเปิดวารสาร/ฉบับพิเศษสายนี้ หรือคาดว่างานส่วนใหญ่ถูกดูดไปยังวารสารนานาชาติ`,
      },
      en: {
        title: 'AI/ML is still a dot on the map',
        body: `"${ai.en}" holds only ${fmt(ai.articles)} articles despite being a global hotspot — an opportunity for editors to launch venues, or a sign that this work is published abroad.`,
      },
    })
  }

  // 6. size gap — generic
  insights.push({
    stat: `${Math.round(GROUPS[0].articles / smallest.articles)}×`,
    th: {
      title: 'ช่องว่างขนาดระหว่างกลุ่มใหญ่สุดและเล็กสุด',
      body: `กลุ่มใหญ่สุด (${GROUPS[0].th}) มีบทความมากกว่ากลุ่มเล็กสุด (${smallest.th}, ${fmt(smallest.articles)} เรื่อง) ถึง ${Math.round(GROUPS[0].articles / smallest.articles)} เท่า — ภูมิทัศน์ที่ไม่สมดุลนี้คือคำถามเชิงนโยบายว่าจะ "เติมหาง" หรือ "ยกเครื่อง" โครงสร้างวารสารอย่างไร`,
    },
    en: {
      title: 'The size gap between largest and smallest groups',
      body: `The largest group (${GROUPS[0].en}) has ${Math.round(GROUPS[0].articles / smallest.articles)}× the articles of the smallest (${smallest.en}, ${fmt(smallest.articles)}) — a policy question of whether to grow the tail or rebalance the journal ecosystem.`,
    },
  })

  return (
    <div>
      <div className="mb-10 max-w-2xl">
        <div className="eyebrow text-[#161611]/45">DISCOVERY · WHAT THE DATA SAYS</div>
        <h2 className="font-display mt-3 text-[28px] font-semibold leading-snug lg:text-[36px]">
          {STR.insightsTitle[lang]}
        </h2>
        <p className="mt-2 text-[14px] text-[#161611]/60">{STR.insightsLead[lang]}</p>
      </div>
      <div className="grid gap-x-12 border-t border-[#161611]/12 lg:grid-cols-2">
        {insights.map((ins, i) => (
          <article key={i} className="grid grid-cols-[3.5rem_minmax(0,1fr)] gap-x-4 border-b border-[#161611]/12 py-7">
            <div className="font-mono-data pt-1 text-[12px] text-[#161611]/35">{String(i + 1).padStart(2, '0')}</div>
            <div>
              <div className="font-mono-data text-[34px] font-semibold leading-none tracking-tight text-[#FF5F1F]">
                {ins.stat}
              </div>
              <h3 className="font-display mt-3 text-[19px] font-semibold leading-snug">{ins[lang].title}</h3>
              <p className="mt-2 max-w-[62ch] text-[14px] leading-relaxed text-[#161611]/65">{ins[lang].body}</p>
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
