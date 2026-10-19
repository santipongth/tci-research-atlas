#!/usr/bin/env node
// Deterministic data-contract-v2 releases — synthetic, NOT real data — for `npm run dev`, unit tests and Playwright.
//   npm run fixtures  →  fixtures/example/data/{latest.json, 2026Q3/, 2026Q4/}  and  fixtures/empty/data/{latest.json, 2026Q4/}
// Every file must validate against src/data/contract.schema.json (src/data/fixtures.test.ts checks it).
// Covers: all six statuses, WATCH (journal-driven), no_baseline, both low_data_reason values, orgs_unverified,
// cross_field, hidden and shown forecasts, nowcast, lineage new/split/merge, a previous release for Δ, and an empty release.
import { createHash } from 'node:crypto'
import { mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', 'fixtures')
const GENERATED_AT = '2026-10-01T00:00:00+00:00'
const SCHEMA = '2.0.0'
const RELEASE = '2026Q4'
const PREVIOUS = '2026Q3'
const YEARS = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]
const R = [2022, 2023, 2024]
const B = [2017, 2018, 2019, 2020, 2021]
const W = [2020, 2021, 2022, 2023, 2024]

let seed = 20261019
const rand = () => {
  seed = (seed * 1664525 + 1013904223) % 4294967296
  return seed / 4294967296
}
const between = (a, b) => a + (b - a) * rand()
const r1 = (x) => Number(x.toFixed(1))
const r4 = (x) => Number(x.toFixed(4))
const r6 = (x) => Number(x.toFixed(6))
const sum = (xs) => xs.reduce((a, b) => a + b, 0)
const at = (years, values, wanted) => wanted.map((y) => values[years.indexOf(y)])
const signed = (g) => `${g >= 0 ? '+' : '−'}${Math.abs(g * 100).toFixed(1)}%`
const pct = (s) => `${(s * 100).toFixed(2)}%`

// [id, th, en, subfield id, subfield name, topics: [th, en, keywords, status, flag]]
const GROUPS = [
  ['F27', 'การแพทย์', 'Medicine', '2739', 'Public Health, Environmental and Occupational Health', [
    ['การดูแลผู้สูงอายุในชุมชน', 'Community care for older adults', ['ผู้สูงอายุ', 'การดูแลระยะยาว', 'ageing', 'long-term care'], 'HOT', 'orgs'],
    ['เบาหวานและความดันโลหิตสูง', 'Diabetes and hypertension', ['เบาหวาน', 'ความดันโลหิตสูง', 'diabetes', 'hypertension'], 'STABLE'],
    ['สุขภาพจิตวัยรุ่น', 'Adolescent mental health', ['ภาวะซึมเศร้า', 'วัยรุ่น', 'depression', 'adolescents'], 'STABLE'],
    ['การแพทย์แผนไทยและสมุนไพร', 'Thai traditional medicine and herbs', ['สมุนไพร', 'การแพทย์แผนไทย', 'herbal medicine', 'Thai traditional medicine'], 'STABLE'],
    ['โควิด-19 กับระบบสาธารณสุข', 'COVID-19 and the health system', ['โควิด-19', 'ระบบสาธารณสุข', 'COVID-19', 'health system'], 'STABLE'],
    ['ปัญญาประดิษฐ์ทางการแพทย์', 'AI in medicine', ['ปัญญาประดิษฐ์', 'การวินิจฉัย', 'artificial intelligence', 'diagnosis'], 'EMERGING', 'split'],
  ]],
  ['F33', 'สังคมศาสตร์', 'Social Sciences', '3304', 'Education', [
    ['AI เพื่อการศึกษา', 'AI in education', ['ปัญญาประดิษฐ์', 'การเรียนการสอน', 'generative AI', 'teaching'], 'EMERGING', 'cross'],
    ['การจัดการเรียนรู้เชิงรุก', 'Active learning', ['การเรียนรู้เชิงรุก', 'ทักษะศตวรรษที่ 21', 'active learning', '21st-century skills'], 'HOT'],
    ['ภาวะผู้นำทางการศึกษา', 'Educational leadership', ['ผู้บริหารสถานศึกษา', 'ภาวะผู้นำ', 'school administrators', 'leadership'], 'STABLE'],
    ['การปกครองส่วนท้องถิ่น', 'Local government', ['องค์กรปกครองส่วนท้องถิ่น', 'การมีส่วนร่วม', 'local government', 'participation'], 'STABLE'],
    ['สื่อสิ่งพิมพ์', 'Print media', ['หนังสือพิมพ์', 'สื่อสิ่งพิมพ์', 'newspapers', 'print media'], 'DECLINING'],
    ['ความเหลื่อมล้ำทางการศึกษา', 'Educational inequality', ['ความเหลื่อมล้ำ', 'โอกาสทางการศึกษา', 'inequality', 'educational opportunity'], 'STABLE'],
  ]],
  ['F14', 'บริหารธุรกิจและการบัญชี', 'Business, Management and Accounting', '1406', 'Marketing', [
    ['การตลาดดิจิทัล', 'Digital marketing', ['การตลาดออนไลน์', 'สื่อสังคมออนไลน์', 'digital marketing', 'social media'], 'HOT'],
    ['การท่องเที่ยวเชิงชุมชน', 'Community-based tourism', ['การท่องเที่ยวโดยชุมชน', 'ชุมชน', 'community-based tourism', 'community'], 'STABLE'],
    ['วิสาหกิจชุมชน', 'Community enterprises', ['วิสาหกิจชุมชน', 'ผลิตภัณฑ์ชุมชน', 'community enterprise', 'local products'], 'STABLE'],
    ['การบัญชีภาครัฐ', 'Public sector accounting', ['การบัญชีภาครัฐ', 'งบประมาณ', 'public sector accounting', 'budgeting'], 'DECLINING'],
    ['ฟินเทคและการเงินดิจิทัล', 'Fintech and digital finance', ['ฟินเทค', 'การชำระเงินดิจิทัล', 'fintech', 'digital payments'], 'WATCH', 'journal'],
    ['ESG และความยั่งยืนขององค์กร', 'ESG and corporate sustainability', ['ความยั่งยืน', 'ธรรมาภิบาล', 'ESG', 'sustainability'], 'HOT'],
  ]],
  ['F11', 'เกษตรและชีววิทยา', 'Agricultural and Biological Sciences', '1102', 'Agronomy and Crop Science', [
    ['การปลูกข้าว', 'Rice farming', ['ข้าว', 'ผลผลิต', 'rice', 'yield'], 'STABLE'],
    ['เกษตรอัจฉริยะ', 'Smart farming', ['เกษตรอัจฉริยะ', 'เซนเซอร์', 'smart farming', 'sensors'], 'LOW_DATA', 'few'],
    ['ประมงและการเพาะเลี้ยงสัตว์น้ำ', 'Fisheries and aquaculture', ['การเพาะเลี้ยงสัตว์น้ำ', 'กุ้ง', 'aquaculture', 'shrimp'], 'STABLE'],
    ['ความหลากหลายทางชีวภาพ', 'Biodiversity', ['ความหลากหลายทางชีวภาพ', 'ป่าไม้', 'biodiversity', 'forests'], 'STABLE'],
    ['ปาล์มน้ำมัน', 'Oil palm', ['ปาล์มน้ำมัน', 'ต้นทุนการผลิต', 'oil palm', 'production cost'], 'DECLINING'],
    ['ไมโครพลาสติกในแหล่งน้ำ', 'Microplastics in water', ['ไมโครพลาสติก', 'แหล่งน้ำ', 'microplastics', 'water bodies'], 'EMERGING'],
  ]],
  ['F22', 'วิศวกรรมศาสตร์', 'Engineering', '2208', 'Electrical and Electronic Engineering', [
    ['พลังงานแสงอาทิตย์', 'Solar energy', ['เซลล์แสงอาทิตย์', 'พลังงานทดแทน', 'solar cells', 'renewable energy'], 'HOT'],
    ['ยานยนต์ไฟฟ้า', 'Electric vehicles', ['ยานยนต์ไฟฟ้า', 'แบตเตอรี่', 'electric vehicles', 'batteries'], 'EMERGING'],
    ['วัสดุก่อสร้าง', 'Construction materials', ['คอนกรีต', 'วัสดุก่อสร้าง', 'concrete', 'construction materials'], 'DECLINING'],
    ['การจัดการน้ำ', 'Water management', ['การจัดการน้ำ', 'อุทกภัย', 'water management', 'floods'], 'STABLE'],
    ['โลจิสติกส์และโซ่อุปทาน', 'Logistics and supply chains', ['โลจิสติกส์', 'โซ่อุปทาน', 'logistics', 'supply chain'], 'STABLE'],
    ['ระบบควบคุมอัตโนมัติ', 'Automatic control systems', ['ระบบควบคุม', 'หุ่นยนต์', 'control systems', 'robotics'], 'STABLE'],
  ]],
  ['F12', 'ศิลปศาสตร์และมนุษยศาสตร์', 'Arts and Humanities', '1212', 'Religious studies', [
    ['พุทธศาสนาออนไลน์', 'Buddhism online', ['พระพุทธศาสนา', 'สื่อออนไลน์', 'Buddhism', 'online media'], 'WATCH', 'journal'],
    ['วรรณกรรมไทย', 'Thai literature', ['วรรณกรรม', 'กวีนิพนธ์', 'literature', 'poetry'], 'STABLE'],
    ['ภาษาอังกฤษเพื่อการสื่อสาร', 'English for communication', ['ภาษาอังกฤษ', 'การสื่อสาร', 'English', 'communication'], 'STABLE'],
    ['ดนตรีพื้นบ้าน', 'Folk music', ['ดนตรีพื้นบ้าน', 'หมอลำ', 'folk music', 'mor lam'], 'DECLINING'],
    ['ประวัติศาสตร์ท้องถิ่น', 'Local history', ['ประวัติศาสตร์ท้องถิ่น', 'ชุมชน', 'local history', 'community'], 'STABLE'],
    ['การแปลด้วยเครื่อง', 'Machine translation', ['การแปล', 'ภาษาไทย', 'machine translation', 'Thai language'], 'LOW_DATA', 'few'],
  ]],
  ['F17', 'วิทยาการคอมพิวเตอร์', 'Computer Science', '1702', 'Artificial Intelligence', [
    ['โมเดลภาษาขนาดใหญ่', 'Large language models', ['แชตจีพีที', 'โมเดลภาษา', 'ChatGPT', 'large language models'], 'EMERGING', 'no_baseline'],
    ['ความมั่นคงปลอดภัยไซเบอร์', 'Cybersecurity', ['ความปลอดภัยไซเบอร์', 'การโจมตี', 'cybersecurity', 'attacks'], 'HOT'],
    ['อินเทอร์เน็ตของสรรพสิ่ง', 'Internet of Things', ['อินเทอร์เน็ตของสรรพสิ่ง', 'เซนเซอร์', 'Internet of Things', 'sensors'], 'STABLE'],
    ['การวิเคราะห์ข้อมูลขนาดใหญ่', 'Big data analytics', ['ข้อมูลขนาดใหญ่', 'การวิเคราะห์ข้อมูล', 'big data', 'data analytics'], 'STABLE'],
    ['ระบบสารสนเทศทางการศึกษา', 'Educational information systems', ['ระบบสารสนเทศ', 'สถานศึกษา', 'information systems', 'schools'], 'DECLINING'],
    ['บล็อกเชน', 'Blockchain', ['บล็อกเชน', 'สัญญาอัจฉริยะ', 'blockchain', 'smart contracts'], 'LOW_DATA', 'flat'],
  ]],
  ['F29', 'การพยาบาล', 'Nursing', '2902', 'Advanced and Specialized Nursing', [
    ['การพยาบาลผู้ป่วยระยะท้าย', 'Palliative nursing care', ['การดูแลแบบประคับประคอง', 'ผู้ป่วยระยะท้าย', 'palliative care', 'end of life'], 'STABLE'],
    ['การพยาบาลมารดาและทารก', 'Maternal and newborn nursing', ['มารดา', 'ทารกแรกเกิด', 'mothers', 'newborns'], 'STABLE'],
    ['การศึกษาพยาบาล', 'Nursing education', ['นักศึกษาพยาบาล', 'การฝึกปฏิบัติ', 'nursing students', 'clinical practice'], 'STABLE'],
    ['พฤติกรรมสุขภาพ', 'Health behaviour', ['พฤติกรรมสุขภาพ', 'การส่งเสริมสุขภาพ', 'health behaviour', 'health promotion'], 'STABLE'],
    ['ภาวะหมดไฟในพยาบาล', 'Nurse burnout', ['ภาวะหมดไฟ', 'พยาบาล', 'burnout', 'nurses'], 'LOW_DATA', 'few'],
    ['การพยาบาลทางไกล', 'Telenursing', ['การพยาบาลทางไกล', 'แอปพลิเคชัน', 'telenursing', 'mobile apps'], 'WATCH', 'journal'],
  ]],
]
const HUBS = [[170, 180], [400, 160], [630, 190], [860, 170], [170, 470], [400, 480], [630, 450], [860, 480]]
const JOURNALS = ['วารสารวิชาการตัวอย่าง ก', 'วารสารวิชาการตัวอย่าง ข', 'วารสารวิชาการตัวอย่าง ค', 'Example Journal of Science', 'วารสารสังคมศาสตร์ตัวอย่าง', 'Example Review of Education']
const ORGS = ['มหาวิทยาลัยตัวอย่าง ก', 'มหาวิทยาลัยตัวอย่าง ข', 'มหาวิทยาลัยราชภัฏตัวอย่าง', 'สถาบันวิจัยตัวอย่าง']
const STATUS_TH = { EMERGING: 'กำลังเกิดใหม่', WATCH: 'จับตา', HOT: 'กำลังมาแรง', DECLINING: 'ลดลง', STABLE: 'คงที่', LOW_DATA: 'ข้อมูลน้อย' }

function counts(status, flag) {
  if (flag === 'no_baseline') return YEARS.map((y) => (y < 2022 ? 0 : [18, 46, 95][y - 2022]))
  if (flag === 'flat') return YEARS.map((y) => (y < 2022 ? 0 : [11, 12, 10][y - 2022]))
  const base = { EMERGING: between(2, 4), WATCH: between(3, 6), HOT: between(150, 230), DECLINING: between(70, 130), STABLE: between(40, 120), LOW_DATA: between(1, 2.6) }[status]
  const g = { EMERGING: between(0.36, 0.46), WATCH: between(0.06, 0.1), HOT: between(0.1, 0.15), DECLINING: between(-0.1, -0.05), STABLE: between(0.02, 0.06), LOW_DATA: 0 }[status]
  return YEARS.map((y, i) => {
    let v = base * (1 + g) ** i
    if (status === 'WATCH' && y >= 2021) v *= 4.2 // a journal is indexed and uploads its back issues
    return Math.max(status === 'LOW_DATA' ? 1 : 0, Math.round(v * (0.94 + 0.12 * rand())))
  })
}

/** exp(OLS slope of ln share over the trend window) − 1, on years with articles. */
function shareGrowth(cs, totals) {
  const pts = W.map((y) => [y, cs[YEARS.indexOf(y)] / totals[YEARS.indexOf(y)]]).filter(([, s]) => s > 0)
  if (pts.length < 3) return null
  const mx = sum(pts.map(([x]) => x)) / pts.length
  const my = sum(pts.map(([, s]) => Math.log(s))) / pts.length
  const b = sum(pts.map(([x, s]) => (x - mx) * (Math.log(s) - my))) / sum(pts.map(([x]) => (x - mx) ** 2))
  return Math.exp(b) - 1
}

function interval(status, g) {
  if (g === null) return [null, null]
  if (status === 'EMERGING' || status === 'WATCH') return [Math.max(0.12, g - 0.12), g + 0.16]
  if (status === 'HOT') return [Math.max(0.01, g - 0.035), g + 0.045]
  if (status === 'DECLINING') return [g - 0.06, Math.min(-0.01, g + 0.04)]
  if (status === 'STABLE') return [g - 0.07, g + 0.07]
  return [g - 0.45, g + 0.45]
}

function forecast(status, cs, flag) {
  if (status === 'LOW_DATA') return null
  const show = status === 'HOT' || (status === 'EMERGING' && flag !== 'no_baseline') || (status === 'DECLINING' && rand() < 0.6) || (status === 'STABLE' && rand() < 0.4)
  if (!show) return { model: 'naive', mase: r4(between(1.02, 1.4)), skill_vs_naive: r4(between(-0.3, -0.01)), show: false, years: [], mean: [], lo80: [], hi80: [], lo95: [], hi95: [] }
  const last = cs[cs.length - 1]
  const g = cs[cs.length - 4] > 0 ? (last / cs[cs.length - 4]) ** (1 / 3) - 1 : 0
  const mean = [r1(last * (1 + g)), r1(last * (1 + g) ** 2)]
  const band = (f) => mean.map((m, i) => r1(m * f[i]))
  return {
    model: status === 'STABLE' ? 'ets_damped' : 'nb_glm', mase: r4(between(0.55, 0.95)), skill_vs_naive: r4(between(0.08, 0.4)), show: true,
    years: [2025, 2026], mean, lo80: band([0.85, 0.78]), hi80: band([1.16, 1.25]), lo95: band([0.76, 0.66]), hi95: band([1.27, 1.4]),
  }
}

function lineage(flag, id) {
  if (flag === 'no_baseline') return { born: '2026Q3', event: 'new', parents: [] }
  if (flag === 'split') return { born: '2026Q2', event: 'split', parents: ['T000105'] }
  if (id === 'T000706') return { born: '2026Q4', event: 'merge', parents: ['T000703', 'T000704'] }
  return { born: '2026Q1', event: 'continue', parents: [] }
}

function buildExample() {
  const specs = []
  GROUPS.forEach(([, , , , , topics], gi) => topics.forEach((tp, ti) => specs.push({ gi, ti, id: `T000${gi + 1}0${ti + 1}`, th: tp[0], en: tp[1], keywords: tp[2], status: tp[3], flag: tp[4] ?? null })))
  for (const s of specs) s.counts = counts(s.status, s.flag)
  const other = YEARS.map((_, i) => 1000 + 60 * i)
  const totals = YEARS.map((_, i) => sum(specs.map((s) => s.counts[i])) + other[i])
  const totalR = sum(at(YEARS, totals, R))
  const totalB = sum(at(YEARS, totals, B))

  for (const s of specs) {
    s.countR = sum(at(YEARS, s.counts, R))
    s.shareR = s.countR / totalR
    s.shareB = sum(at(YEARS, s.counts, B)) / totalB
    s.g = s.flag === 'flat' ? null : shareGrowth(s.counts, totals)
    ;[s.lo, s.hi] = interval(s.status, s.g)
  }
  const maxShare = Math.max(...specs.map((s) => s.shareR))

  const topics = specs.map((s) => {
    const [hx, hy] = HUBS[s.gi]
    const angle = ((s.ti * 60 + between(-15, 15)) * Math.PI) / 180
    const dist = between(45, 85)
    const fc = forecast(s.status, s.counts, s.flag)
    const signal = ['EMERGING', 'WATCH', 'HOT', 'DECLINING'].includes(s.status)
    const group = GROUPS[s.gi]
    return {
      id: s.id, group: group[0], th: s.th, en: s.en,
      description: `ตัวอย่าง: งานวิจัยเกี่ยวกับ${s.th}`,
      keywords: s.keywords, label_source: 'keywords', size: sum(s.counts),
      x: r1(hx + Math.cos(angle) * dist), y: r1(hy + Math.sin(angle) * dist), r: r1(6 + 20 * Math.sqrt(s.shareR / maxShare)),
      status: s.status,
      score: r1({ EMERGING: between(70, 95), WATCH: between(55, 75), HOT: between(45, 65), DECLINING: between(5, 20), STABLE: between(15, 45), LOW_DATA: between(0, 10) }[s.status]),
      metrics: {
        count_recent: s.countR, share_recent: r6(s.shareR), share_baseline: r6(s.shareB),
        share_ratio: s.shareB === 0 ? null : r4(s.shareR / s.shareB), no_baseline: s.shareB === 0,
        share_growth: s.g === null ? null : r4(s.g), share_growth_lo: s.lo === null ? null : r4(s.lo), share_growth_hi: s.hi === null ? null : r4(s.hi),
        acceleration: r4(between(-0.05, 0.1)),
        burst_frac: { EMERGING: 0.6667, WATCH: 0.6667, HOT: 0.3333 }[s.status] ?? 0,
        burst_years: { EMERGING: [2023, 2024], WATCH: [2021, 2022], HOT: [2024] }[s.status] ?? [],
        novelty: r4(s.status === 'EMERGING' ? between(0.8, 0.95) : between(0.05, 0.4)),
        coherence: r4(between(0.55, 0.8)),
        n_journals_R: s.status === 'WATCH' ? 2 : Math.round(s.status === 'LOW_DATA' ? between(1, 3) : s.status === 'HOT' ? between(40, 90) : between(8, 40)),
        n_orgs_R: s.status === 'WATCH' ? 3 : Math.round(s.status === 'LOW_DATA' ? between(1, 4) : s.status === 'HOT' ? between(30, 80) : between(6, 45)),
        new_journal_share: r4(s.status === 'WATCH' ? between(0.6, 0.8) : between(0, 0.15)),
        journal_hhi: r4(s.status === 'WATCH' ? between(0.55, 0.7) : between(0.03, 0.2)),
        journal_driven: s.flag === 'journal', orgs_unverified: s.flag === 'orgs',
        low_data_reason: s.status !== 'LOW_DATA' ? null : s.flag === 'flat' ? 'not_estimable' : 'few_articles',
      },
      forecast: fc,
      lineage: lineage(s.flag, s.id),
      sdg: [],
      subfield: group[3], subfield_en: group[4],
      cross_field: s.flag === 'cross', taxonomy_vote: r4(s.flag === 'cross' ? 0.42 : between(0.6, 0.95)),
      nowcast: fc && fc.show ? { year: 2025, as_of_month: 9, ytd: Math.round(fc.mean[0] * 0.68), mean: fc.mean[0] } : null,
      _signal: signal,
    }
  })

  const groupSizes = GROUPS.map(([gid]) => sum(topics.filter((t) => t.group === gid).map((t) => t.size)))
  const rank = [...groupSizes.keys()].sort((a, b) => groupSizes[b] - groupSizes[a])
  const groups = rank.map((gi, r) => ({
    id: GROUPS[gi][0], th: GROUPS[gi][1], en: GROUPS[gi][2], color: `cat-${String(r + 1).padStart(2, '0')}`,
    size: groupSizes[gi], n_topics: 6, x: HUBS[gi][0], y: HUBS[gi][1], r: 120,
  }))
  const subfields = GROUPS.map(([gid, , , sid, sname], gi) => ({ id: sid, en: sname, group: gid, n_topics: 6, size: groupSizes[gi] }))

  const edges = []
  for (let gi = 0; gi < 8; gi++) for (let ti = 1; ti < 6; ti++) edges.push({ s: `T000${gi + 1}0${ti}`, t: `T000${gi + 1}0${ti + 1}`, w: r4(between(0.55, 0.9)) })
  edges.push({ s: 'T000201', t: 'T000701', w: 0.82 }, { s: 'T000106', t: 'T000701', w: 0.77 }, { s: 'T000305', t: 'T000701', w: 0.58 })

  const details = topics.map((t, n) => {
    const neighbors = edges.filter((e) => e.s === t.id || e.t === t.id).sort((a, b) => b.w - a.w).map((e) => (e.s === t.id ? e.t : e.s)).slice(0, 5)
    const articles = [1, 2, 3, 4].map((k) => {
      const j = (n + k) % JOURNALS.length
      const year = 2020 + ((n + k) % 5)
      const num = 10000 + n * 10 + k
      return {
        article_id: `so02:example${j}:${num}`, title: `${t.th}: กรณีศึกษาที่ ${k}`, title_en: `${t.en}: case study ${k}`, year,
        journal: JOURNALS[j], url: `https://so02.tci-thaijo.org/index.php/example${j}/article/view/${num}`, doi: `10.14456/example.${year}.${num}`, gx: null, gy: null,
      }
    })
    const share = pct(t.metrics.share_recent)
    const narrative = t._signal
      ? {
          th: `${t.th}อยู่ในสถานะ${STATUS_TH[t.status]} สัดส่วนบทความช่วง 2022–2024 อยู่ที่ ${share}${t.metrics.share_growth === null ? '' : ` และเปลี่ยนแปลง ${signed(t.metrics.share_growth)} ต่อปี`} (ข้อมูลตัวอย่าง)`,
          en: `${t.en} is ${t.status.toLowerCase()}: ${share} of articles in 2022–2024${t.metrics.share_growth === null ? '' : `, changing ${signed(t.metrics.share_growth)} a year`} (sample data).`,
          source: 'template',
        }
      : null
    return {
      schema_version: SCHEMA, id: t.id, articles,
      journals: [0, 1, 2].map((k) => ({ key: JOURNALS[(n + k) % JOURNALS.length], count: 40 - 11 * k })),
      institutions: [0, 1, 2].map((k) => ({ key: ORGS[(n + k) % ORGS.length], count: 25 - 7 * k })),
      keywords: t.keywords, neighbors, narrative,
    }
  })
  for (const t of topics) delete t._signal

  const by = (st) => topics.filter((t) => t.status === st)
  const fastest = [...by('EMERGING')].sort((a, b) => b.metrics.share_growth - a.metrics.share_growth)[0]
  const topHot = [...by('HOT')].sort((a, b) => b.metrics.share_recent - a.metrics.share_recent)[0]
  const decl = [...by('DECLINING')].sort((a, b) => a.metrics.share_growth - b.metrics.share_growth)[0]
  const watch = by('WATCH')[0]
  const brief = {
    headline_th: `รอบ ${RELEASE} มีหัวข้อกำลังเกิดใหม่ ${by('EMERGING').length} หัวข้อ และ${fastest.th}โตเร็วที่สุด ${signed(fastest.metrics.share_growth)} ต่อปี`,
    headline_en: `In ${RELEASE}, ${by('EMERGING').length} topics are emerging and ${fastest.en} is growing fastest, ${signed(fastest.metrics.share_growth)} a year`,
    bullets_th: [
      `หัวข้อกำลังมาแรง ${by('HOT').length} หัวข้อ นำโดย${topHot.th} (${pct(topHot.metrics.share_recent)} ของบทความช่วง 2022–2024)`,
      `หัวข้อที่ลดลง ${by('DECLINING').length} หัวข้อ เช่น ${decl.th} ซึ่งสัดส่วนเปลี่ยนแปลง ${signed(decl.metrics.share_growth)} ต่อปี`,
      `หัวข้อจับตา ${by('WATCH').length} หัวข้อโตจากวารสารเดียว เช่น ${watch.th} ควรตรวจสอบก่อนอ้างอิง`,
    ],
    bullets_en: [
      `${by('HOT').length} topics are hot, led by ${topHot.en} (${pct(topHot.metrics.share_recent)} of articles in 2022–2024)`,
      `${by('DECLINING').length} topics are declining, such as ${decl.en}, whose share is changing ${signed(decl.metrics.share_growth)} a year`,
      `${by('WATCH').length} watch topics grew from a single journal, such as ${watch.en}; check them before citing`,
    ],
    source: 'template',
  }

  const yearMissing = 37
  const assigned = sum(topics.map((t) => t.size))
  const articles = sum(totals) + yearMissing
  const statusCounts = Object.fromEntries(['EMERGING', 'WATCH', 'HOT', 'DECLINING', 'STABLE', 'LOW_DATA'].map((st) => [st, by(st).length]))
  const last = totals[totals.length - 1]
  const overview = {
    schema_version: SCHEMA, release: RELEASE, previous_release: PREVIOUS, generated_at: GENERATED_AT, definition_version: 3, last_complete_year: 2024,
    kpis: { articles, assigned_articles: assigned, topics: topics.length, groups: groups.length, journals: 412, institutions: 187, pct_abstract_en: 74.2, pct_doi: 61.5, pct_keywords: 96.1 },
    status_counts: statusCounts,
    corpus_by_year: YEARS.map((year, i) => ({ year, articles: totals[i] })),
    corpus_forecast: [{ year: 2025, articles: r1(last * 1.06) }, { year: 2026, articles: r1(last * 1.12) }],
    nowcast: { year: 2025, as_of_month: 9, ytd: Math.round(last * 0.71), mean: r1(last * 1.06) },
    lineage_events: { continue: 45, new: 1, split: 1, merge: 1 },
    retired_topics: ['T000999'],
    data_quality: { year_missing: yearMissing, unassigned_articles: sum(other), completeness_method: 'median', text_quality: { thai_pua_repaired: 214, tone_marks_missing: 19, decode_replaced: 3 } },
    brief,
  }
  const previousOverview = {
    ...overview, release: PREVIOUS, previous_release: '2026Q2', brief: null,
    kpis: { articles: articles - 1850, assigned_articles: assigned - 1700, topics: 46, groups: 8, journals: 405, institutions: 183, pct_abstract_en: 73.6, pct_doi: 60.9, pct_keywords: 95.8 },
    status_counts: { EMERGING: 4, WATCH: 2, HOT: 6, DECLINING: 5, STABLE: 25, LOW_DATA: 4 },
  }
  const keywords = [
    { term: 'chatgpt', count_recent: 212, share_ratio: null, no_baseline: true, growth: 1.42, growth_lo: 0.88, n_active_years: 3, n_orgs_R: 41, n_journals_R: 37, journal_driven: false, emerging: true, topic: 'T000701' },
    { term: 'generative ai', count_recent: 158, share_ratio: 9.4, no_baseline: false, growth: 0.95, growth_lo: 0.61, n_active_years: 4, n_orgs_R: 33, n_journals_R: 29, journal_driven: false, emerging: true, topic: 'T000201' },
    { term: 'ไมโครพลาสติก', count_recent: 64, share_ratio: 5.1, no_baseline: false, growth: 0.48, growth_lo: 0.22, n_active_years: 5, n_orgs_R: 14, n_journals_R: 12, journal_driven: false, emerging: true, topic: 'T000406' },
    { term: 'ยานยนต์ไฟฟ้า', count_recent: 77, share_ratio: 4.2, no_baseline: false, growth: 0.41, growth_lo: 0.19, n_active_years: 6, n_orgs_R: 18, n_journals_R: 15, journal_driven: false, emerging: true, topic: 'T000502' },
    { term: 'soft power', count_recent: 39, share_ratio: 3.3, no_baseline: false, growth: 0.37, growth_lo: 0.12, n_active_years: 3, n_orgs_R: 9, n_journals_R: 8, journal_driven: false, emerging: true, topic: null },
    { term: 'ธรรมะออนไลน์', count_recent: 58, share_ratio: 7.8, no_baseline: false, growth: 0.66, growth_lo: 0.3, n_active_years: 3, n_orgs_R: 3, n_journals_R: 1, journal_driven: true, emerging: false, topic: 'T000601' },
  ]
  const files = {
    'overview.json': overview,
    'taxonomy.json': { schema_version: SCHEMA, source: 'openalex', version: 'fixture-1', holdout_accuracy_subfield: 0.81, holdout_accuracy_field: 0.93, groups, subfields },
    'topics.json': { schema_version: SCHEMA, topics },
    'series.json': { schema_version: SCHEMA, years: YEARS, corpus_total: totals, topics: Object.fromEntries(topics.map((t) => [t.id, specs.find((s) => s.id === t.id).counts])) },
    'edges.json': { schema_version: SCHEMA, edges },
    'keywords.json': { schema_version: SCHEMA, keywords },
    ...Object.fromEntries(details.map((d) => [`topics/${d.id}.json`, d])),
  }
  return { files, previousOverview, nOrgsUnverified: topics.filter((t) => t.metrics.orgs_unverified).length, nTopics: topics.length }
}

function manifest(release, previous, modules, entries, extra = {}) {
  return {
    schema_version: SCHEMA, release, generated_at: GENERATED_AT, pipeline_version: 'fixture', config_hash: '0000000000000000',
    definition_version: 3, ci_level: 0.9, as_of_year: 2025, trimmed_years: [2025], embedding_provider: 'fixture', embedding_model: 'fixture|none|0',
    taxonomy_version: 'fixture-1', modules, files: entries, previous_release: previous, n_orgs_unverified: 0, ingest_errors: 0,
    labels: { provider: 'off', llm: 0, keywords: 0, overrides: 0 }, llm: [], ...extra,
  }
}

function writeRelease(dataDir, release, files, makeManifest) {
  const entries = []
  for (const [path, obj] of Object.entries(files).sort(([a], [b]) => a.localeCompare(b))) {
    const bytes = Buffer.from(JSON.stringify(obj), 'utf8')
    const file = join(dataDir, release, path)
    mkdirSync(dirname(file), { recursive: true })
    writeFileSync(file, bytes)
    entries.push({ path, bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') })
  }
  writeFileSync(join(dataDir, release, 'manifest.json'), JSON.stringify(makeManifest(entries)))
}

function writeLatest(dataDir, release) {
  writeFileSync(join(dataDir, 'latest.json'), JSON.stringify({ release, path: `${release}/manifest.json`, schema_version: SCHEMA, generated_at: GENERATED_AT }))
}

const example = join(ROOT, 'example', 'data')
const empty = join(ROOT, 'empty', 'data')
rmSync(join(ROOT, 'example'), { recursive: true, force: true })
rmSync(join(ROOT, 'empty'), { recursive: true, force: true })

const ex = buildExample()
writeRelease(example, PREVIOUS, { 'overview.json': ex.previousOverview }, (entries) => manifest(PREVIOUS, '2026Q2', ['overview'], entries))
writeRelease(example, RELEASE, ex.files, (entries) =>
  manifest(RELEASE, PREVIOUS, ['overview', 'taxonomy', 'topics', 'topic_detail', 'series', 'edges', 'keywords'], entries, {
    n_orgs_unverified: ex.nOrgsUnverified, ingest_errors: 2, labels: { provider: 'off', llm: 0, keywords: ex.nTopics, overrides: 0 },
  }))
writeLatest(example, RELEASE)

writeRelease(empty, RELEASE, {
  'overview.json': {
    schema_version: SCHEMA, release: RELEASE, previous_release: null, generated_at: GENERATED_AT, definition_version: 3, last_complete_year: 2024,
    kpis: { articles: 0, assigned_articles: 0, topics: 0, groups: 0, journals: 0, institutions: 0, pct_abstract_en: 0, pct_doi: 0, pct_keywords: 0 },
    status_counts: {}, corpus_by_year: [], corpus_forecast: [], nowcast: null, lineage_events: {}, retired_topics: [],
    data_quality: { year_missing: 0, unassigned_articles: 0, completeness_method: 'median', text_quality: {} }, brief: null,
  },
  'taxonomy.json': { schema_version: SCHEMA, source: 'agglomerative', version: null, holdout_accuracy_subfield: null, holdout_accuracy_field: null, groups: [], subfields: [] },
  'topics.json': { schema_version: SCHEMA, topics: [] },
  'series.json': { schema_version: SCHEMA, years: [], corpus_total: [], topics: {} },
  'edges.json': { schema_version: SCHEMA, edges: [] },
}, (entries) => manifest(RELEASE, null, ['overview', 'taxonomy', 'topics', 'topic_detail', 'series', 'edges'], entries, { trimmed_years: [] }))
writeLatest(empty, RELEASE)

console.log(`[fixtures] example ${RELEASE} (${ex.nTopics} topics, previous ${PREVIOUS}) and empty ${RELEASE} → ${ROOT}`)
