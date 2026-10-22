import { defineStrings } from './define'

/** /references (D7 reference practice + R12 citations inside the collection). Imported only by the lazy ReferencesPage. */
export const references = defineStrings({
  title: { th: 'การอ้างอิง', en: 'References' },
  lede: {
    th: 'บทความ {p} ในช่วง {a}–{b} มีรายการอ้างอิงที่ระบบอ่านได้ รวม {refs} รายการ หน้านี้ดูว่าแต่ละวารสารอ้างอิงอย่างไร และบทความในคลังอ้างถึงกันเองแค่ไหน',
    en: '{p} of articles from {a}–{b} have a reference list the system could read: {refs} references in all. See how each journal cites, and how often articles in the collection cite each other.',
  },

  'cov.h': { th: 'อ่านรายการอ้างอิงได้มากแค่ไหน', en: 'How much of the reference lists could be read' },
  'cov.with': { th: 'บทความที่อ่านรายการอ้างอิงได้', en: 'Articles with a readable reference list' },
  'cov.withSub': { th: '{n} จาก {all} บทความ ปี {a}–{b}', en: '{n} of {all} articles, {a}–{b}' },
  'cov.refs': { th: 'รายการอ้างอิงที่นับ', en: 'References counted' },
  'cov.refsSub': { th: 'เฉลี่ยราว {n} รายการต่อบทความ', en: 'about {n} per article' },
  'cov.internal': { th: 'อ้างถึงบทความอื่นในคลัง', en: 'Citations to other articles here' },
  'cov.internalSub': { th: 'จาก {n} บทความที่อ้าง', en: 'from {n} citing articles' },
  'cov.note': {
    th: 'ไม่นับการอ้างงานตนเองที่ระบบระบุได้ และรายการที่ซ้ำเพราะเป็นฉบับแปลของรายการเดียวกัน ส่วนนี้แสดงเมื่ออ่านรายการอ้างอิงได้อย่างน้อย {p} ของบทความ',
    en: 'Self-citations the system can spot and translated duplicates of the same reference are not counted. This part is shown only when at least {p} of articles have a readable reference list.',
  },

  'jr.h': { th: 'แต่ละวารสารอ้างอิงอย่างไร', en: 'How each journal cites' },
  'jr.intro': {
    th: 'เฉพาะวารสารที่มีบทความซึ่งอ่านรายการอ้างอิงได้อย่างน้อย {n} เรื่อง “ใหม่” คือเอกสารที่อายุไม่เกิน {y} ปีเมื่อนับจากปีที่บทความตีพิมพ์',
    en: 'Journals with at least {n} articles whose reference list could be read. “Recent” means at most {y} years older than the citing article.',
  },
  'jr.insight': { th: 'วารสารที่อ้างงานใหม่มากที่สุดคือ {j} ({p} ของรายการอ้างอิงอายุไม่เกิน {y} ปี)', en: 'The journal citing the most recent work is {j}: {p} of its references are at most {y} years old.' },
  'jr.table': { th: 'แนวปฏิบัติการอ้างอิงรายวารสาร', en: 'Reference practice by journal' },
  'jr.none': { th: 'ยังไม่มีวารสารที่มีบทความพอสำหรับตารางนี้', en: 'No journal has enough articles for this table yet.' },
  'col.journal': { th: 'วารสาร', en: 'Journal' },
  'col.withRefs': { th: 'บทความที่อ่านได้', en: 'Articles read' },
  'col.median': { th: 'อ้างอิงต่อบทความ (มัธยฐาน)', en: 'References per article (median)' },
  'col.age': { th: 'อายุเอกสารที่อ้าง (ปี, มัธยฐาน)', en: 'Age of cited work (years, median)' },
  'col.recent': { th: 'อ้างงานใหม่', en: 'Recent work' },
  'col.thai': { th: 'เอกสารภาษาไทย', en: 'Thai-language' },
  'col.doi': { th: 'มี DOI', en: 'With a DOI' },
  'col.ofAll': { th: 'จาก {n}', en: 'of {n}' },

  'in.h': { th: 'บทความในคลังอ้างถึงกันเอง', en: 'Articles citing each other' },
  'in.intro': {
    th: 'พบการอ้างอิงไปยังบทความอื่นในคลัง {n} ครั้ง จาก {citing} บทความ ไปยัง {cited} บทความ จับคู่ด้วย DOI {doi} และด้วยชื่อเรื่องที่ตรงกันทุกตัวอักษร {title}',
    en: '{n} references point to another article in the collection, from {citing} articles to {cited}. Matched by DOI for {doi}, and by an exactly matching title for {title}.',
  },
  'in.off.h': { th: 'ยังไม่แสดงการอ้างอิงกันเองระหว่างบทความ', en: 'Citations between articles are not shown yet' },
  'in.off.body': {
    th: 'รอบข้อมูลนี้จับคู่รายการอ้างอิงกับบทความในคลังได้น้อยเกินไปที่จะสรุปผลได้อย่างน่าเชื่อถือ',
    en: 'This release matched too few references to articles in the collection to draw a reliable picture.',
  },
  'in.off.detail': { th: 'รายละเอียดจากระบบ:', en: 'Details from the system:' },

  'top.h': { th: 'บทความที่ถูกอ้างถึงมากที่สุดในคลัง', en: 'Most-cited articles in the collection' },
  'top.intro': { th: 'นับจำนวนบทความอื่นในคลังที่อ้างถึง (บทความหนึ่งนับครั้งเดียวต่อบทความที่อ้าง)', en: 'Counted as the number of other articles here that cite it (once per citing article).' },
  'top.cited': { th: 'ถูกอ้าง {n} ครั้ง', en: 'Cited {n} times' },
  'top.noTopic': { th: 'ไม่อยู่ในหัวข้อใด', en: 'No topic' },
  'x.h': { th: 'บันทึกรายการนี้', en: 'Save this list' },
  'x.ris': { th: 'RIS', en: 'RIS' },
  'x.bib': { th: 'BibTeX', en: 'BibTeX' },
  'x.csv': { th: 'CSV', en: 'CSV' },
  'x.label': { th: 'บันทึกบทความ {n} เรื่องเป็น {format}', en: 'Save {n} articles as {format}' },
  'x.note': { th: 'ไฟล์ไม่มีชื่อผู้แต่ง ใช้ DOI หรือลิงก์ ThaiJO เพื่อดูการอ้างอิงฉบับเต็ม', en: 'Files carry no author names; use the DOI or ThaiJO link for the full citation.' },

  'flow.h': { th: 'หัวข้อไหนอ้างถึงหัวข้อไหน', en: 'Which topics cite which' },
  'flow.intro': { th: 'คู่หัวข้อที่บทความในหัวข้อหนึ่งอ้างถึงบทความในอีกหัวข้อหนึ่งอย่างน้อย {n} ครั้ง', en: 'Topic pairs where articles of one topic cite articles of another at least {n} times.' },
  'flow.table': { th: 'การอ้างอิงจากหัวข้อหนึ่งไปอีกหัวข้อหนึ่ง', en: 'Citations from one topic to another' },
  'flow.none': { th: 'ยังไม่มีคู่หัวข้อที่อ้างถึงกันถึงเกณฑ์', en: 'No topic pair reaches the threshold yet.' },
  'col.source': { th: 'หัวข้อที่อ้าง', en: 'Citing topic' },
  'col.target': { th: 'หัวข้อที่ถูกอ้าง', en: 'Cited topic' },
  'col.n': { th: 'ครั้ง', en: 'Citations' },
  'flow.same': { th: 'อ้างในหัวข้อเดียวกัน', en: 'within the same topic' },

  'tp.h': { th: 'การอ้างอิงรายหัวข้อ', en: 'Citations by topic' },
  'tp.intro': { th: '“ถูกอ้าง” นับการอ้างที่บทความของหัวข้อได้รับจากบทความอื่นในคลัง “อ้างถึง” นับการอ้างที่บทความของหัวข้อให้แก่บทความอื่นในคลัง', en: '“Received” counts citations a topic’s articles got from other articles here; “given” counts the citations they made to other articles here.' },
  'tp.table': { th: 'การอ้างอิงที่แต่ละหัวข้อได้รับและให้', en: 'Citations received and given by each topic' },
  'col.topic': { th: 'หัวข้อ', en: 'Topic' },
  'col.received': { th: 'ถูกอ้าง', en: 'Received' },
  'col.given': { th: 'อ้างถึง', en: 'Given' },
})
