#!/usr/bin/env node
// Deterministic data-contract-v2 releases — synthetic, NOT real data — for `npm run dev`, unit tests and Playwright.
//   npm run fixtures  →  fixtures/example/data/{latest.json, 2026Q3/, 2026Q4/}  and  fixtures/empty/data/{latest.json, 2026Q4/}
// Every file must validate against src/data/contract.schema.json (src/data/fixtures.test.ts checks it).
// Covers: all six statuses, WATCH (journal-driven), no_baseline, both low_data_reason values, orgs_unverified,
// cross_field, hidden and shown forecasts, nowcast, lineage new/split/merge, a previous release for Δ, and an empty release.
// P2 (contract 2.1): journals (registry-named and OJS-path-only, low data, a new journal), journal details, methods,
// the quarter diff and the match index — the empty release has none of them (pages explain the missing module).
import { createHash } from 'node:crypto'
import { mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', 'fixtures')
const GENERATED_AT = '2026-10-01T00:00:00+00:00'
const SCHEMA = '2.1.0'
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
      `หัวข้อจับตา ${by('WATCH').length} หัวข้อเติบโตแต่ไม่ผ่านเกณฑ์ความกว้าง เช่น ${watch.th} ควรตรวจสอบก่อนอ้างอิง`,
    ],
    bullets_en: [
      `${by('HOT').length} topics are hot, led by ${topHot.en} (${pct(topHot.metrics.share_recent)} of articles in 2022–2024)`,
      `${by('DECLINING').length} topics are declining, such as ${decl.en}, whose share is changing ${signed(decl.metrics.share_growth)} a year`,
      `${by('WATCH').length} watch topics are growing but did not pass the breadth test, such as ${watch.en}; check them before citing`,
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

// ---- P2 editors' modules (contract 2.1): journals, journals/<id>, methods, diff, match — synthetic, NOT real data
// Journal j of JOURNALS has the OJS path `example${j}` (the article URLs above use it). The registry names 0, 1, 3 and 4;
// 2 and 5 are shown by their OJS path. 4 has too few articles (low_data); 5 joined in 2023 (a new journal for the diff).
const J_IN_REGISTRY = [true, true, false, true, true, false]
const STATUS_ORDER = ['EMERGING', 'WATCH', 'HOT', 'DECLINING', 'STABLE', 'LOW_DATA']
const jId = (j) => `so02.example${j}`
const jName = (j) => (J_IN_REGISTRY[j] ? JOURNALS[j] : `example${j}`)
const METHOD_INFO = [
  ['survey', 'แบบสอบถาม/การสำรวจ', 'Questionnaire / survey'], ['interview', 'การสัมภาษณ์', 'Interviews'],
  ['focus_group', 'การสนทนากลุ่ม', 'Focus groups'], ['experiment', 'การทดลอง/กึ่งทดลอง', 'Experiment / quasi-experiment'],
  ['qualitative', 'การวิจัยเชิงคุณภาพ', 'Qualitative research'], ['mixed', 'การวิจัยแบบผสานวิธี', 'Mixed methods'],
  ['rnd', 'การวิจัยและพัฒนา', 'Research and development'], ['action', 'การวิจัยเชิงปฏิบัติการ', 'Action research'],
  ['case_study', 'กรณีศึกษา', 'Case study'], ['document', 'การวิเคราะห์เอกสาร/เนื้อหา', 'Document / content analysis'],
  ['review', 'การทบทวนอย่างเป็นระบบ/อภิมาน', 'Systematic review / meta-analysis'], ['descriptive_stats', 'สถิติเชิงพรรณนา', 'Descriptive statistics'],
  ['inferential', 'สถิติเชิงอนุมาน', 'Inferential statistics'], ['sem', 'สมการโครงสร้าง/องค์ประกอบ', 'SEM / factor analysis'],
  ['ml', 'การเรียนรู้ของเครื่อง', 'Machine learning'], ['lab', 'การทดลองในห้องปฏิบัติการ', 'Laboratory study'],
]

// the analyzer of web/src/lib/matcher.ts (= pipeline/atlas/matcher.py): fold, then char_wb trigrams
// (regexes built from code points: a literal invisible character in source code is easy to lose or corrupt)
const cp = (...xs) => String.fromCodePoint(...xs)
const DECOMPOSED_AM = new RegExp(cp(0x0e4d, 0x0e32), 'g')
const INVISIBLE = new RegExp(`[${cp(0x200b)}-${cp(0x200d)}${cp(0xfeff)}${cp(0xad)}]`, 'g')
const LATIN_ACCENTS = new RegExp(`[${cp(0x300)}-${cp(0x36f)}]`, 'g')
const THAI_ABOVE = new RegExp(`[${cp(0x0e47)}-${cp(0x0e4c)}]`, 'g')
const foldMatch = (s) =>
  s.normalize('NFC').replace(DECOMPOSED_AM, cp(0x0e33)).replace(INVISIBLE, '').normalize('NFD')
    .replace(LATIN_ACCENTS, '').replace(THAI_ABOVE, '').toLowerCase().replace(/\s+/g, ' ').trim()
const trigrams = (folded) => {
  const out = []
  for (const word of folded ? folded.split(' ') : []) {
    const w = [...` ${word} `]
    if (w.length <= 3) out.push(w.join(''))
    else for (let i = 0; i + 3 <= w.length; i++) out.push(w.slice(i, i + 3).join(''))
  }
  return out
}

function buildEditors(files, previousOverview) {
  const topics = files['topics.json'].topics
  const byId = new Map(topics.map((t) => [t.id, t]))
  const groupOf = (j) => GROUPS[j % GROUPS.length][0]
  const jTopics = (j) => topics.filter((t) => t.group === groupOf(j)).slice(0, 5).concat(j === 0 ? [byId.get('T000201')] : [])
  const summaries = JOURNALS.map((name, j) => {
    const low = j === 4
    const windowN = [240, 180, 150, 310, 12, 24][j]
    return {
      id: jId(j), key: `so02:example${j}`, path: `example${j}`,
      name_th: J_IN_REGISTRY[j] && j !== 3 ? name : '', name_en: j === 3 ? name : '',
      issn: '', eissn: '', tci_tier: [1, 2, null, 1, 2, null][j], tci_field: J_IN_REGISTRY[j] ? GROUPS[j % GROUPS.length][2] : '',
      publisher: j === 0 ? ORGS[0] : j === 3 ? ORGS[3] : '', url: J_IN_REGISTRY[j] ? `https://so02.tci-thaijo.org/index.php/example${j}` : '',
      in_registry: J_IN_REGISTRY[j], articles: [520, 410, 300, 640, 30, 24][j], articles_window: windowN, articles_recent: Math.round(windowN * 0.6),
      first_year: j === 5 ? 2023 : 2015, last_year: 2024, active: true, low_data: low, group: groupOf(j),
      completeness: low ? null : [86.4, 71.2, 58.9, 93.1, null, 64.0][j],
      owner: low ? '' : [ORGS[0], ORGS[1], ORGS[2], ORGS[3], '', ORGS[1]][j],
      owner_source: low ? null : j === 0 || j === 3 ? 'registry' : 'inferred', owner_matched: !low,
      inhouse_share: low ? null : [0.42, 0.81, 0.66, 0.12, null, 0.58][j],
      n_orgs: [64, 21, 33, 95, 3, 9][j], effective_orgs: low ? null : [22.5, 3.1, 8.4, 41.7, null, 4.2][j],
      foreign_share: low ? null : [0.03, 0, 0.01, 0.18, null, 0][j], affiliation_coverage: low ? null : [0.97, 0.92, 0.88, 0.99, null, 0.95][j],
      methods_coverage: low ? null : [0.81, 0.77, 0.69, 0.84, null, 0.72][j],
    }
  })
  const special = [
    { topic: 'T000406', hosts: 2, top_host_share: 0.58, articles_recent: byId.get('T000406').metrics.count_recent },
    { topic: 'T000502', hosts: 1, top_host_share: 0.71, articles_recent: byId.get('T000502').metrics.count_recent },
    { topic: 'T000305', hosts: 1, top_host_share: 0.83, articles_recent: byId.get('T000305').metrics.count_recent },
  ]
  files['journals.json'] = {
    schema_version: SCHEMA, window: { start: 2020, end: 2024 }, recent: { start: 2022, end: 2024 }, baseline: { start: 2017, end: 2021 },
    min_articles: 20, completeness_weights: { abstract_en: 0.2, title_en: 0.1, keywords_en: 0.15, doi: 0.2, references: 0.15, refs_romanized: 0.1, affiliations: 0.1 },
    inhouse_flag_share: 0.6, special_issue_statuses: ['EMERGING', 'WATCH'], special_issue_max_hosts: 5, special_issue_min_host_articles: 3, drift_reference_years: 3,
    journals: summaries, special_issue: special,
  }
  const PEERS = { 0: [[2, 0.82], [1, 0.35]], 1: [[5, 0.64], [0, 0.35]], 2: [[0, 0.82]], 3: [], 4: [], 5: [[1, 0.64]] }
  const OPPS = { 0: [['T000502', 'adjacent', 0, 1]], 1: [['T000305', 'in_scope', 2, 1]], 2: [], 3: [['T000406', 'in_scope', 5, 2], ['T000502', 'adjacent', 0, 1]], 4: [], 5: [] }
  const COMPLETE = ['abstract_en', 'title_en', 'keywords_en', 'doi', 'references', 'refs_romanized', 'affiliations']
  JOURNALS.forEach((_, j) => {
    const s = summaries[j]
    const tl = jTopics(j)
    const weights = tl.map((_, i) => 1 / (i + 1.5))
    const wsum = sum(weights) * 1.25
    files[`journals/${jId(j)}.json`] = {
      schema_version: SCHEMA, id: jId(j),
      years: YEARS.filter((y) => y >= s.first_year).map((y, i) => ({ year: y, articles: Math.round(s.articles / (j === 5 ? 2 : 10) * (0.8 + 0.04 * i)) })),
      topics: tl.map((t, i) => ({ topic: t.id, count: Math.round(s.articles_window * weights[i] / wsum), share: r4(weights[i] / wsum) })),
      drift: s.low_data ? [] : [2020, 2021, 2022, 2023, 2024].filter((y) => y >= s.first_year).map((y, i) => ({
        year: y, articles: Math.round(s.articles_window / 5), distance: j === 5 && i === 0 ? null : i === 0 && j !== 3 ? null : r4(j === 3 && y === 2023 ? 0.41 : 0.08 + 0.02 * i),
      })),
      gained: s.low_data ? [] : [{ topic: tl[0].id, share_before: 0.12, share_after: 0.21 }],
      lost: s.low_data ? [] : [{ topic: tl[tl.length - 1].id, share_before: 0.14, share_after: 0.06 }],
      peers: PEERS[j].map(([p, sim]) => ({ id: jId(p), similarity: sim })),
      completeness: s.low_data ? [] : COMPLETE.map((key, k) => ({ key, rate: key === 'refs_romanized' && j === 3 ? null : r4(0.55 + ((j + k) % 5) * 0.1), n: key === 'refs_romanized' && j === 3 ? 0 : s.articles_window })),
      methods: s.low_data ? [] : [['survey', 0.52], ['descriptive_stats', 0.47], ['interview', 0.21], ['inferential', 0.19]].map(([m, sh]) => ({ method: m, count: Math.round(s.articles_window * s.methods_coverage * sh), share: sh })),
      opportunities: OPPS[j].map(([topic, reason, n, hosts]) => ({ topic, reason, journal_articles: n, hosts })),
    }
  })
  // topic details link their journals by id
  for (const [path, d] of Object.entries(files)) {
    if (!path.startsWith('topics/')) continue
    d.journals = d.journals.map((c) => {
      const j = JOURNALS.indexOf(c.key)
      return j >= 0 ? { key: jName(j), count: c.count, id: jId(j) } : c
    })
  }

  // methods.json — E11 monoculture on two education/social topics
  const share = (k, i) => r4(Math.max(0.01, [0.52, 0.18, 0.06, 0.09, 0.14, 0.05, 0.07, 0.03, 0.08, 0.06, 0.02, 0.47, 0.24, 0.07, 0.04, 0.03][k] + 0.002 * i))
  const methodTopics = topics.filter((t) => t.status !== 'LOW_DATA').slice(0, 14).map((t, i) => {
    const mono = t.id === 'T000203' || t.id === 'T000204'
    const articles = Math.max(30, t.metrics.count_recent)
    const withM = Math.round(articles * 0.78)
    const ms = (mono ? [['survey', 0.82], ['descriptive_stats', 0.76], ['inferential', 0.12]] : [['survey', 0.44], ['interview', 0.31], ['descriptive_stats', 0.29], ['qualitative', 0.22]])
      .map(([m, sh]) => ({ method: m, count: Math.round(withM * sh), share: r4(sh + 0.001 * i) }))
    return {
      topic: t.id, articles, with_methods: withM, coverage: r4(withM / articles), methods: ms,
      sample_size_n: Math.round(withM * 0.6), sample_size_median: [400, 385, 220, 120, 30][i % 5], sample_size_q1: [200, 180, 120, 60, 15][i % 5], sample_size_q3: [420, 400, 380, 240, 45][i % 5],
      monoculture_share: r4(mono ? 0.71 + 0.01 * i : 0.18 + 0.01 * i), monoculture: mono,
      note: i < 2 ? { th: `บทความในหัวข้อ${t.th}ที่ระบุวิธีวิจัยได้ ${Math.round(ms[0].share * 100)}% ใช้แบบสอบถาม (ข้อมูลตัวอย่าง)`, en: `${Math.round(ms[0].share * 100)}% of the articles on ${t.en} that name a method use a questionnaire (sample data).`, source: 'template' } : null,
    }
  })
  files['methods.json'] = {
    schema_version: SCHEMA, lexicon_version: 'fixture1', window: { start: 2020, end: 2024 }, articles: 18234, with_methods: 14002,
    monoculture_methods: ['survey', 'descriptive_stats'], monoculture_min_share: 0.6, monoculture_share: 0.27, min_articles: 30,
    methods: METHOD_INFO.map(([key, th, en]) => ({ key, th, en })),
    corpus: METHOD_INFO.map(([key], k) => ({ method: key, count: Math.round(14002 * share(k, 0)), share: share(k, 0) })).sort((a, b) => b.count - a.count),
    by_year: {
      years: YEARS, articles: YEARS.map((_, i) => 900 + 60 * i),
      shares: Object.fromEntries(METHOD_INFO.map(([key], k) => [key, YEARS.map((_, i) => r4(key === 'survey' ? 0.58 - 0.012 * i : key === 'ml' ? 0.005 + 0.006 * i : share(k, i)))])),
    },
    topics: methodTopics,
  }

  // diff.json — what changed since 2026Q3
  const ov = files['overview.json']
  const KPI = ['articles', 'assigned_articles', 'topics', 'journals', 'institutions']
  const prevStatus = { T000201: 'WATCH', T000406: 'STABLE', T000104: 'HOT', T000305: 'STABLE', T000503: 'STABLE' }
  files['diff.json'] = {
    schema_version: SCHEMA, release: RELEASE, previous_release: PREVIOUS, previous_source: 'state',
    kpis: KPI.map((key) => ({ key, previous: previousOverview.kpis[key], current: ov.kpis[key] })),
    new_topics: [{ topic: 'T000701', event: 'new', parents: [] }, { topic: 'T000106', event: 'split', parents: ['T000105'] }, { topic: 'T000706', event: 'merge', parents: ['T000703', 'T000704'] }],
    retired: [
      { topic: 'T000999', th: 'หนังสือพิมพ์รายวัน', en: 'Daily newspapers', merged_into: null },
      { topic: 'T000998', th: 'การศึกษาทางไกลยุคแรก', en: 'Early distance learning', merged_into: 'T000201' },
    ],
    restructured: [
      { topic: 'T000201', event: 'merge', parents: ['T000998'] },
      { topic: 'T000105', event: 'split', parents: ['T000106'] },
    ],
    status_changes: Object.entries(prevStatus).map(([topic, previous]) => ({ topic, previous, current: byId.get(topic).status }))
      .sort((a, b) => STATUS_ORDER.indexOf(a.current) - STATUS_ORDER.indexOf(b.current) || a.topic.localeCompare(b.topic)),
    movers: [...topics].filter((t) => t.status !== 'LOW_DATA').sort((a, b) => b.metrics.share_recent - a.metrics.share_recent).slice(0, 6)
      .map((t, i) => ({ topic: t.id, share_previous: r6(t.metrics.share_recent * (i % 2 ? 1.12 : 0.86)), share_current: t.metrics.share_recent })),
    journals_compared: true, new_journals: [jId(5)],
  }

  // match.json — one "document" per topic (names, keywords, description), weighted like the pipeline
  const docs = topics.map((t) => trigrams(foldMatch([t.th, t.en, ...t.keywords, t.description].join(' '))))
  const df = new Map()
  for (const d of docs) for (const g of new Set(d)) df.set(g, (df.get(g) ?? 0) + 1)
  const vecs = docs.map((d) => {
    const tf = new Map()
    for (const g of d) tf.set(g, (tf.get(g) ?? 0) + 1)
    const w = [...tf].map(([g, n]) => [g, (1 + Math.log(n)) * (Math.log((1 + docs.length) / (1 + df.get(g))) + 1)])
    w.sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1))
    const top = w.slice(0, 60)
    const norm = Math.sqrt(sum(top.map(([, v]) => v * v)))
    return top.map(([g, v]) => [g, v / norm])
  })
  const grams = [...new Set(vecs.flatMap((v) => v.map(([g]) => g)))].sort()
  const pos = new Map(grams.map((g, i) => [g, i]))
  files['match.json'] = {
    schema_version: SCHEMA, analyzer: 'char_wb3', fold: 'atlas-fold-1', docs: docs.length, max_terms: 60, min_similarity: 0.05, fit_topics: 5, min_query_chars: 40,
    grams, idf: grams.map((g) => r4(Math.log((1 + docs.length) / (1 + df.get(g))) + 1)),
    topics: topics.map((t, i) => ({ id: t.id, terms: vecs[i].map(([g]) => pos.get(g)), weights: vecs[i].map(([, v]) => r4(v)) })),
    journals: JOURNALS.map((_, j) => j).filter((j) => !summaries[j].low_data)
      .map((j) => ({ id: jId(j), topics: files[`journals/${jId(j)}.json`].topics.map((x) => x.topic), shares: files[`journals/${jId(j)}.json`].topics.map((x) => x.share) })),
  }
  return ['journals', 'journal_detail', 'methods', 'diff', 'match']
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
const editorModules = buildEditors(ex.files, ex.previousOverview)
writeRelease(example, PREVIOUS, { 'overview.json': ex.previousOverview }, (entries) => manifest(PREVIOUS, '2026Q2', ['overview'], entries))
writeRelease(example, RELEASE, ex.files, (entries) =>
  manifest(RELEASE, PREVIOUS, ['overview', 'taxonomy', 'topics', 'topic_detail', 'series', 'edges', 'keywords', ...editorModules], entries, {
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
