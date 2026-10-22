import { defineStrings } from './define'

/** Optional modules of a release (contract 2.1) — shared by the editors' pages and /data. */
export const modules = defineStrings({
  'mod.absent': { th: 'รอบข้อมูลนี้ไม่มีส่วนนี้', en: 'This release does not include this part' },
  'mod.absentBody': { th: 'ส่วนนี้เพิ่มในรุ่นหลังของ Atlas รอบข้อมูลที่สร้างก่อนหน้านั้น หรือที่ปิดโมดูลนี้ จะไม่มีข้อมูลให้แสดง', en: 'This part was added in a later version of the Atlas. Releases built before it, or with the module switched off, have nothing to show here.' },
  'mod.offline': { th: 'ฉบับออฟไลน์ไม่มีส่วนนี้', en: 'Not in the offline edition' },
  'mod.offlineBody': { th: 'ต้องใช้เว็บไซต์ออนไลน์ ไฟล์ HTML เดี่ยวไม่ได้ใส่ข้อมูลส่วนนี้เพื่อให้ไฟล์เล็ก', en: 'This needs the online site: the single HTML file leaves this data out to stay small.' },
  'mod.missingFile': { th: 'ไม่พบไฟล์ข้อมูลของส่วนนี้บนเว็บไซต์', en: 'The data file for this part is not on the site' },
  'mod.error': { th: 'โหลดข้อมูลส่วนนี้ไม่สำเร็จ ลองโหลดหน้าใหม่', en: 'This part could not be loaded. Try reloading the page.' },
  'data.mod.h': { th: 'ไฟล์ส่วนเสริม (JSON)', en: 'Module files (JSON)' },
  'data.mod.intro': { th: 'ไฟล์ของส่วนสำหรับบรรณาธิการ โหลดเมื่อเปิดหน้าที่ใช้เท่านั้น', en: 'Files of the editors’ modules, loaded only when a page needs them.' },
  'data.file.journals': { th: 'วารสารทั้งหมด: ความครบถ้วนของ metadata สัดส่วนผู้แต่งในสถาบันเจ้าของ ความหลากหลายสถาบัน', en: 'Every journal: metadata completeness, in-house share, institutional diversity' },
  'data.file.methods': { th: 'วิธีวิจัยรายหัวข้อและรายปี', en: 'Research methods by topic and year' },
  'data.file.diff': { th: 'สิ่งที่เปลี่ยนจากรอบก่อน', en: 'What changed since the previous release' },
  'data.file.references': { th: 'การอ้างอิงรายวารสาร และการอ้างอิงกันเองระหว่างบทความในคลัง', en: 'Reference practice per journal and citations between articles of the collection' },
  'data.file.search': { th: 'ดัชนีค้นหาบทความ (ชื่อเรื่องและคำสำคัญ ไม่มีบทคัดย่อ ไม่มีชื่อผู้แต่ง) — ไฟล์นี้อธิบายชิ้นดัชนีในโฟลเดอร์ search/', en: 'Article search index (titles and keywords; no abstracts, no author names) — this file describes the shards in search/' },
  'data.file.galaxy': { th: 'ตำแหน่งบทความบนแผนที่ (หนึ่งจุดต่อบทความ)', en: 'Article positions on the map (one point per article)' },
  'data.file.kwtrends': { th: 'แนวโน้มคำสำคัญรายปี และอภิธานศัพท์ไทย–อังกฤษ', en: 'Keyword trends by year and the Thai–English glossary' },
  'nav.search': { th: 'ค้นหาบทความ', en: 'Search articles' },
  'nav.galaxy': { th: 'กาแล็กซีบทความ', en: 'Article galaxy' },
  'search.articles': { th: 'ค้นหาบทความทั้งคลัง', en: 'Search all articles' },
  'data.file.match': { th: 'ดัชนีสำหรับเทียบบทคัดย่อ (น้ำหนักชิ้นอักษร ไม่มีข้อความบทความ)', en: 'Index for matching an abstract (character-trigram weights, no article text)' },
})
