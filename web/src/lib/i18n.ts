export type Lang = 'th' | 'en'

export const STR = {
  brand: { th: 'TCI RESEARCH ATLAS', en: 'TCI RESEARCH ATLAS' },
  brandSub: { th: 'แผนที่ภูมิทัศน์งานวิจัยไทย', en: 'Thai Research Landscape Atlas' },
  navMap: { th: 'แผนที่', en: 'Atlas' },
  navEmerging: { th: 'หัวข้อเกิดใหม่', en: 'Emerging' },
  navRanking: { th: 'อันดับกลุ่มสาขา', en: 'Ranking' },
  navInsights: { th: 'อินไซต์', en: 'Insights' },
  navMethod: { th: 'วิธีการ', en: 'Method' },
  dataLive: { th: 'ข้อมูลสดจาก pipeline', en: 'Live pipeline data' },
  dataBundled: { th: 'ข้อมูลตัวอย่าง (71 สาขา)', en: 'Bundled sample (71 fields)' },
  dataThrough: { th: 'ข้อมูลถึงปี', en: 'data through' },
  heroEyebrow: { th: 'TCI · THAI RESEARCH LANDSCAPE · 200,003 ARTICLES', en: 'TCI · THAI RESEARCH LANDSCAPE · 200,003 ARTICLES' },
  heroTitle: { th: 'แผนที่ภูมิทัศน์\nงานวิจัยไทย', en: 'The landscape of\nThai research' },
  heroLead: {
    th: 'สำรวจโครงสร้างของวารสารวิชาการไทยผ่านบทความ 200,003 เรื่อง ที่ถูกจัดกลุ่มเชิงความหมายเป็น 71 สาขา และรวมเป็น 20 กลุ่มสาขาหลัก — ขนาดวงกลมแสดงจำนวนบทความ สีแสดงกลุ่มสาขา คลิกที่วงกลมเพื่อเจาะลึกแต่ละสาขา',
    en: 'Explore the structure of Thai academic journals through 200,003 articles, semantically clustered into 71 fields and merged into 20 field groups. Circle size encodes article volume, color encodes the field group — click any circle to drill down.',
  },
  hint: { th: 'ลากเพื่อเลื่อน · scroll เพื่อซูม · คลิกวงกลมเพื่อดูรายละเอียด', en: 'Drag to pan · scroll to zoom · click a circle for details' },
  articles: { th: 'บทความ', en: 'articles' },
  fieldsUnit: { th: 'สาขา', en: 'fields' },
  groupsUnit: { th: 'กลุ่มสาขา', en: 'groups' },
  share: { th: 'สัดส่วน', en: 'share' },
  ofTotal: { th: 'ของบทความทั้งหมด', en: 'of all articles' },
  rank: { th: 'อันดับ', en: 'Rank' },
  overview: { th: 'ภาพรวมทั้งหมด', en: 'Full overview' },
  overviewSub: { th: 'เลือกวงกลมบนแผนที่เพื่อดูรายละเอียดกลุ่มสาขาและสาขาย่อย', en: 'Select a circle on the map to inspect a group or field' },
  groupLabel: { th: 'กลุ่มสาขา', en: 'FIELD GROUP' },
  fieldLabel: { th: 'สาขา', en: 'FIELD' },
  memberFields: { th: 'สาขาย่อยในกลุ่ม', en: 'Fields in this group' },
  belongsTo: { th: 'อยู่ในกลุ่ม', en: 'Belongs to' },
  clearSelection: { th: 'กลับไปภาพรวม', en: 'Back to overview' },
  statsTitle: { th: 'ตัวเลขภาพรวม', en: 'At a glance' },
  topGroupShare: { th: 'สัดส่วนกลุ่มใหญ่สุด', en: 'Largest group share' },
  rankingTitle: { th: '20 กลุ่มสาขาเรียงตามจำนวนบทความ', en: '20 field groups ranked by article volume' },
  rankingLead: {
    th: 'คลิกแถวเพื่อไฮไลต์กลุ่มนั้นบนแผนที่',
    en: 'Click a row to highlight the group on the atlas',
  },
  insightsTitle: { th: 'Discovery Insights', en: 'Discovery Insights' },
  insightsLead: {
    th: 'สิ่งที่ตัวเลขเผยให้เห็นเกี่ยวกับภูมิทัศน์งานวิจัยไทย — สำหรับนักวิจัย บรรณาธิการ และผู้บริหาร',
    en: 'What the numbers reveal about the Thai research landscape — for researchers, editors, and executives',
  },
  methodTitle: { th: 'วิธีการและที่มาของข้อมูล', en: 'Method & data source' },
  methodBody: {
    th: 'ข้อมูลจากการจัดกลุ่มเชิงความหมาย (semantic merging) ของสาขาวิชาในฐานข้อมูลวารสาร TCI/ThaiJO จำนวน 71 สาขา รวม 200,003 บทความ แต่ละสาขาถูกรวมเข้าเป็น 20 กลุ่มสาขาหลักโดยอัตโนมัติจากชื่อสาขาภาษาไทยและอังกฤษ ตำแหน่งบนแผนที่จัดวางด้วยอัลกอริทึมแบบกระจายรอบจุดศูนย์กลางกลุ่ม ขนาดวงกลมแปรตามรากที่สองของจำนวนบทความ — แผนที่นี้ใช้เพื่อการสำรวจภาพรวม (discovery) ไม่ใช่การวัดคุณภาพงานวิจัย',
    en: 'Built from a semantic merge of 71 journal fields in the TCI/ThaiJO database covering 200,003 articles. Fields are automatically merged into 20 major groups based on their Thai and English names. Map positions are laid out by a radial relaxation algorithm; circle area scales with article count. This atlas is a discovery tool, not a measure of research quality.',
  },
  footer: {
    th: 'TCI Research Atlas · สร้างจากข้อมูล fields_merged_semantic.json · เพื่อการสำรวจเชิงค้นพบ',
    en: 'TCI Research Atlas · built from fields_merged_semantic.json · for discovery exploration',
  },
} as const

export type StrKey = keyof typeof STR

export function fmt(n: number): string {
  return n.toLocaleString('en-US')
}

export function pct(part: number, whole: number, digits = 1): string {
  return ((part / whole) * 100).toFixed(digits) + '%'
}
