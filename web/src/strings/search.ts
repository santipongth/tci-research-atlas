import { defineStrings } from './define'

/** /search (R2 whole-corpus article search, R9 RIS/BibTeX). Imported only by the lazy SearchPage (entry budget). */
export const search = defineStrings({
  title: { th: 'ค้นหาบทความ', en: 'Search articles' },
  lede: { th: 'ค้นจากชื่อเรื่องและคำสำคัญของบทความ {n} เรื่อง ทั้งภาษาไทยและภาษาอังกฤษ', en: 'Search the titles and keywords of {n} articles, in Thai or English.' },
  label: { th: 'คำค้น', en: 'Search words' },
  placeholder: { th: 'เช่น ผู้สูงอายุ หรือ digital marketing', en: 'e.g. ageing or digital marketing' },
  submit: { th: 'ค้นหา', en: 'Search' },
  clear: { th: 'ล้างคำค้น', en: 'Clear' },
  scope: { th: 'บทความที่มีทุกคำจะแสดง · ไม่รวมบทคัดย่อ', en: 'Shows articles that contain every word · abstracts are not searched' },

  'tips.h': { th: 'วิธีค้น', en: 'How to search' },
  'tips.1': { th: 'พิมพ์คำไทยติดกันได้เลย ระบบแยกคำให้เอง เช่น “การตลาดดิจิทัล”', en: 'Type Thai words without spaces if you like; they are split for you.' },
  'tips.2': { th: 'ใส่หลายคำเพื่อให้ผลแคบลง บทความต้องมีครบทุกคำ', en: 'Add more words to narrow the results: an article must contain all of them.' },
  'tips.3': { th: 'ค้นได้เฉพาะชื่อเรื่องและคำสำคัญที่ผู้เขียนระบุ ไม่ค้นในบทคัดย่อหรือชื่อผู้แต่ง', en: 'Only titles and the authors’ keywords are searched — not abstracts or author names.' },
  'tips.try': { th: 'ลองค้น', en: 'Try' },

  'res.h': { th: 'ผลการค้น', en: 'Results' },
  'res.loading': { th: 'กำลังค้น…', en: 'Searching…' },
  'res.error': { th: 'ค้นไม่สำเร็จ ไฟล์ดัชนีบางส่วนโหลดไม่ได้ ลองค้นอีกครั้งหรือโหลดหน้าใหม่', en: 'The search failed: part of the index could not be loaded. Try again or reload the page.' },
  'res.count': { th: 'พบ {n} บทความ', en: '{n} articles found' },
  'res.countFiltered': { th: 'พบ {n} บทความตามตัวกรอง จาก {all} บทความที่ตรงคำค้น', en: '{n} articles match the filters, of {all} that match the words' },
  'res.none': { th: 'ไม่พบบทความที่มีครบทุกคำ ลองใช้คำน้อยลงหรือคำที่กว้างขึ้น', en: 'No article contains all of these words. Try fewer or broader words.' },
  'res.noneFiltered': { th: 'ไม่มีบทความที่ตรงตัวกรองนี้ ลองขยายช่วงปีหรือล้างตัวกรอง', en: 'No article matches these filters. Widen the years or clear the filters.' },
  'res.words': { th: 'ค้นด้วยคำ', en: 'Searched for' },
  'res.unknown': { th: 'ไม่พบคำว่า {words} ในคลัง จึงไม่ได้ใช้ค้น', en: '{words} is not in the collection, so it was not used' },
  'res.unknownOnly': { th: 'ไม่พบคำว่า {words} ในคลัง ลองสะกดใหม่หรือใช้คำอื่น', en: '{words} is not in the collection. Check the spelling or try another word.' },
  'res.partial': { th: 'มีบทความตรงคำค้น {total} เรื่อง รายการนี้คัดจาก {examined} เรื่องที่ตรวจได้ในครั้งเดียว เพิ่มคำค้นให้เจาะจงขึ้นเพื่อดูผลครบ', en: '{total} articles match. This list is drawn from the {examined} checked in one go; add a word to see complete results.' },
  'res.capped': { th: 'แสดง {n} รายการแรก', en: 'Showing the first {n}' },
  'res.more': { th: 'แสดงเพิ่มอีก {n} รายการ', en: 'Show {n} more' },
  'res.shown': { th: 'แสดง {shown} จาก {n} รายการ', en: 'Showing {shown} of {n}' },
  'res.order': { th: 'เรียงตามจำนวนคำค้นที่อยู่ในชื่อเรื่อง แล้วตามปีล่าสุด', en: 'Ordered by how many search words appear in the title, then newest first' },

  'f.h': { th: 'กรองผล', en: 'Filter' },
  'f.from': { th: 'ตั้งแต่ปี', en: 'From' },
  'f.to': { th: 'ถึงปี', en: 'To' },
  'f.topic': { th: 'หัวข้อวิจัย', en: 'Research topic' },
  'f.journal': { th: 'วารสาร', en: 'Journal' },
  'f.any': { th: 'ทั้งหมด', en: 'All' },
  'f.reset': { th: 'ล้างตัวกรอง', en: 'Clear filters' },

  'x.h': { th: 'ดาวน์โหลดผล', en: 'Download results' },
  'x.csv': { th: 'ตาราง CSV', en: 'CSV table' },
  'x.ris': { th: 'RIS', en: 'RIS' },
  'x.bib': { th: 'BibTeX', en: 'BibTeX' },
  'x.label': { th: 'ดาวน์โหลด {n} รายการเป็น {format}', en: 'Download {n} results as {format}' },
  'x.note': { th: 'RIS และ BibTeX ใช้นำเข้าโปรแกรมจัดการอ้างอิง เช่น Zotero หรือ EndNote ไฟล์ไม่มีชื่อผู้แต่ง ใช้ DOI หรือลิงก์ ThaiJO เพื่อดึงข้อมูลฉบับเต็ม', en: 'RIS and BibTeX import into reference managers such as Zotero or EndNote. They carry no author names; use the DOI or ThaiJO link for the full record.' },

  'r.cited': { th: 'ถูกอ้างใน TCI {n} ครั้ง', en: 'Cited {n} times in TCI' },
  'r.noTopic': { th: 'ยังไม่จัดหัวข้อ', en: 'No topic' },
  'r.doi': { th: 'DOI', en: 'DOI' },
})
