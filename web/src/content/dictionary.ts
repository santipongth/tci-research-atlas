/** /data: what the published files and main fields mean (full specification: docs/DATA_SPEC.md). */
export interface DictEntry {
  file: string
  field: string
  th: string
  en: string
}

export const DICTIONARY: readonly DictEntry[] = [
  { file: 'latest.json', field: 'release, path', th: 'รอบข้อมูลล่าสุดและตำแหน่งไฟล์ manifest ของรอบนั้น', en: 'The newest release and the path of its manifest' },
  { file: 'manifest.json', field: 'files[].bytes, sha256', th: 'ขนาดและค่า sha256 ของทุกไฟล์ในรอบ ใช้ตรวจว่าไฟล์ไม่ถูกแก้ไข', en: 'Size and sha256 of every file in the release, to check the files are unaltered' },
  { file: 'manifest.json', field: 'definition_version, ci_level', th: 'ฉบับของนิยามสถานะ และระดับของช่วงเชื่อมั่นทุกช่วงในรอบนี้', en: 'Status-definition version and the level of every interval in the release' },
  { file: 'overview.json', field: 'kpis', th: 'ตัวเลขหลัก: บทความ หัวข้อ สาขา วารสาร สถาบัน และสัดส่วนที่มีบทคัดย่ออังกฤษ DOI และคำสำคัญ', en: 'Headline figures: articles, topics, fields, journals, institutions, and the shares with an English abstract, a DOI and keywords' },
  { file: 'overview.json', field: 'brief', th: 'ประโยคสรุปและประเด็นสำหรับผู้บริหาร จากแม่แบบหรือ AI ที่ตรวจตัวเลขแล้ว', en: 'Headline sentence and executive points, from templates or number-checked AI' },
  { file: 'overview.json', field: 'data_quality', th: 'ปีที่หายไป บทความที่ยังไม่จัดหมวด วิธีตรวจความครบถ้วน และธงคุณภาพข้อความ', en: 'Missing years, unassigned articles, the completeness method and text-quality flags' },
  { file: 'taxonomy.json', field: 'groups[]', th: 'สาขาหลัก (OpenAlex fields หรือกลุ่มสำรอง) สีเป็นชื่อ token เช่น cat-01', en: 'Main fields (OpenAlex fields or fallback groups); colours are token names such as cat-01' },
  { file: 'topics.json', field: 'id', th: 'รหัสหัวข้อที่คงที่ข้ามรอบ เช่น T000123', en: 'Topic id, stable across releases, e.g. T000123' },
  { file: 'topics.json', field: 'status', th: 'EMERGING กำลังเกิดใหม่ · WATCH จับตา · HOT กำลังมาแรง · DECLINING ลดลง · STABLE คงที่ · LOW_DATA ข้อมูลน้อย', en: 'EMERGING · WATCH · HOT · DECLINING · STABLE · LOW_DATA' },
  { file: 'topics.json', field: 'metrics.share_recent, share_baseline', th: 'สัดส่วนบทความของหัวข้อในช่วงล่าสุดและช่วงฐาน เป็นทศนิยม 0–1', en: 'The topic’s share of articles in the recent and baseline windows, as fractions 0–1' },
  { file: 'topics.json', field: 'metrics.share_growth, share_growth_lo, share_growth_hi', th: 'อัตราโตของสัดส่วนต่อปี (0.10 = +10%) และขอบล่าง/บนของช่วงเชื่อมั่นที่ระดับ ci_level', en: 'Yearly share growth (0.10 = +10%) and the lower/upper bounds of its interval at ci_level' },
  { file: 'topics.json', field: 'metrics.share_ratio, no_baseline', th: 'สัดส่วนช่วงล่าสุดหารด้วยช่วงฐาน เป็น null และ no_baseline = true เมื่อช่วงฐานไม่มีบทความ', en: 'Recent share divided by baseline share; null with no_baseline = true when the baseline had no articles' },
  { file: 'topics.json', field: 'metrics.n_journals_R, n_orgs_R', th: 'จำนวนวารสารและสถาบันในช่วงล่าสุด (เกณฑ์ความกว้าง)', en: 'Journals and institutions in the recent window (the breadth test)' },
  { file: 'topics.json', field: 'metrics.journal_driven, orgs_unverified', th: 'โตแต่ไม่ผ่านเกณฑ์ความกว้าง / ตรวจความกว้างของสถาบันไม่ได้', en: 'Growth without passing the breadth test / institution breadth not verified' },
  { file: 'topics.json', field: 'metrics.low_data_reason', th: 'few_articles = บทความน้อย, not_estimable = ประมาณอัตราโตไม่ได้', en: 'few_articles = too few articles, not_estimable = growth could not be estimated' },
  { file: 'topics.json', field: 'forecast', th: 'คาดการณ์ 2 ปี (mean, lo80/hi80, lo95/hi95) แสดงเมื่อ show = true คือโมเดลแม่นกว่าการใช้ค่าปีล่าสุด', en: 'Two-year forecast (mean, lo80/hi80, lo95/hi95), shown when show = true, i.e. the model beats repeating last year' },
  { file: 'topics.json', field: 'nowcast', th: 'ประมาณการปีปัจจุบันจากข้อมูลถึงเดือนล่าสุด', en: 'Current-year estimate from data up to the latest month' },
  { file: 'topics.json', field: 'x, y, r', th: 'ตำแหน่งบนแผนที่ (คงที่ข้ามรอบ) และขนาด', en: 'Map position (kept stable across releases) and size' },
  { file: 'series.json', field: 'years, corpus_total, topics', th: 'จำนวนบทความรายปีของทั้งคลังและของแต่ละหัวข้อ (ค่าดิบ)', en: 'Articles a year for the whole corpus and for each topic (raw counts)' },
  { file: 'edges.json', field: 's, t, w', th: 'คู่หัวข้อที่ใกล้กันและน้ำหนักความใกล้', en: 'Pairs of related topics and their similarity weight' },
  { file: 'keywords.json', field: 'term, emerging, journal_driven', th: 'คำสำคัญเกิดใหม่ วัดจากคำสำคัญของผู้แต่ง', en: 'Emerging keywords, measured on author keywords' },
  { file: 'topics/<id>.json', field: 'articles[]', th: 'บทความตัวแทน: ชื่อเรื่อง วารสาร ปี ลิงก์ ThaiJO และ DOI (ไม่มีบทคัดย่อ)', en: 'Representative articles: title, journal, year, ThaiJO link and DOI (no abstracts)' },
  { file: 'topics/<id>.json', field: 'journals[], institutions[]', th: 'วารสารและสถาบันที่มีบทความในหัวข้อนี้มากที่สุด (ระดับองค์กร ไม่ใช่บุคคล)', en: 'Journals and institutions with the most articles on the topic (organisations, never people)' },
]
