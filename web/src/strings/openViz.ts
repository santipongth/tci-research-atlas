import { defineStrings } from './define'

/**
 * /data and /about in plain words (web refresh, batch 6): easy downloads as file cards, the developers' part with the
 * quality report as a checklist, the four-step pipeline diagram and the status decision on /about. Read with useStrings
 * by the chunks those pages load on demand (both pages are in the entry chunk).
 */
export const openViz = defineStrings({
  'ez.h': { th: 'ดาวน์โหลดง่าย ๆ', en: 'Easy downloads' },
  'ez.intro': { th: 'ตารางสำหรับ Excel เปิดได้ทันที ภาษาไทยไม่เพี้ยน เช่น ไฟล์แรกมีทุกหัวข้อพร้อมสถานะและตัวเลขหลัก สัดส่วนในไฟล์เป็นทศนิยม (0.1 = 10%)', en: 'Tables for Excel that open straight away, with Thai shown correctly — the first one has every topic with its status and main figures. Shares in the files are decimals (0.1 = 10%).' },
  'ez.topics': { th: 'หัวข้อวิจัยทั้งหมด', en: 'Every research topic' },
  'ez.series': { th: 'บทความรายปีของแต่ละหัวข้อ', en: 'Articles a year for each topic' },
  'ez.keywords': { th: 'คำสำคัญที่กำลังเกิดใหม่', en: 'Emerging keywords' },
  'ez.meta': { th: '{n} แถว · ประมาณ {size}', en: '{n} rows · about {size}' },
  'ez.cards': { th: 'ไฟล์ตารางสำหรับดาวน์โหลด', en: 'Tables to download' },

  'dev.h': { th: 'สำหรับนักพัฒนา', en: 'For developers' },
  'dev.intro': { th: 'ไฟล์ JSON ที่เว็บนี้อ่าน รายงานคุณภาพข้อมูล และความหมายของแต่ละช่องข้อมูล ไฟล์ทุกไฟล์ตรวจได้ด้วยค่า sha256 ใน manifest.json', en: 'The JSON files this site reads, the data quality report and what each field means. Every file can be checked against its sha256 in manifest.json.' },

  'qc.ok': { th: 'เรียบร้อย', en: 'OK' },
  'qc.note': { th: 'ควรรู้', en: 'Worth knowing' },
  'qc.label': { th: 'รายงานคุณภาพข้อมูล', en: 'Data quality report' },
  'qc.through': { th: 'ถึงปี {y}', en: 'Through {y}' },
  'qc.none': { th: 'ไม่มี', en: 'None' },
  'qc.articles': { th: '{n} บทความ', en: '{n} articles' },
  'qc.topics': { th: '{n} หัวข้อ', en: '{n} topics' },
  'qc.files': { th: '{n} ไฟล์', en: '{n} files' },
  'qc.texts': { th: '{n} ข้อความ', en: '{n} texts' },
  'qc.buildV': { th: 'รุ่น {v} · รหัสการตั้งค่า {h}', en: 'version {v} · settings code {h}' },

  'ab.flow.label': { th: 'ขั้นตอนจากบทความถึงสถานะของหัวข้อ', en: 'From articles to a topic’s status' },
  'ab.1t': { th: 'รวบรวมบทความ', en: 'Collect the articles' },
  'ab.1b': { th: 'ชื่อเรื่อง คำสำคัญ และบทคัดย่อของบทความ {n} เรื่องจาก ThaiJO', en: 'The titles, keywords and abstracts of {n} articles from ThaiJO' },
  'ab.1bGeneric': { th: 'ชื่อเรื่อง คำสำคัญ และบทคัดย่อของบทความจาก ThaiJO', en: 'The titles, keywords and abstracts of articles from ThaiJO' },
  'ab.2t': { th: 'จัดกลุ่มเป็นหัวข้อ', en: 'Group them into topics' },
  'ab.2b': { th: 'บทความที่เนื้อหาใกล้กันอยู่หัวข้อเดียวกัน เช่น งานเรื่องการดูแลผู้สูงอายุในชุมชน', en: 'Articles about similar things share a topic — for example, work on community elderly care' },
  'ab.3t': { th: 'วัดการเติบโต', en: 'Measure the growth' },
  'ab.3b': { th: 'เทียบส่วนแบ่งของหัวข้อในบทความทั้งหมด ปี {R} กับปี {B}', en: 'Compare each topic’s share of all articles in {R} with {B}' },
  'ab.4t': { th: 'ให้สถานะ', en: 'Give a status' },
  'ab.4b': { th: 'ตรวจ 4 ข้อตามลำดับด้านล่าง แล้วให้หนึ่งในหกสถานะ', en: 'Four checks, in the order below, give one of six statuses' },
})
