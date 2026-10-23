import { defineStrings } from './define'

/** Optional modules of a release (contract 2.1) — shared by the editors' pages and /data. */
export const modules = defineStrings({
  'mod.absent': { th: 'รอบข้อมูลนี้ไม่มีส่วนนี้', en: 'This release does not include this part' },
  'mod.absentBody': { th: 'ส่วนนี้เพิ่งเพิ่มเข้ามาใน Atlas รุ่นหลัง ข้อมูลรอบที่ทำไว้ก่อนหน้านั้น หรือรอบที่ปิดส่วนนี้ไว้ จึงไม่มีอะไรให้แสดง', en: 'This part was added in a later version of the Atlas. Releases built before it, or with it switched off, have nothing to show here.' },
  'mod.offline': { th: 'ฉบับออฟไลน์ไม่มีส่วนนี้', en: 'Not in the offline edition' },
  'mod.offlineBody': { th: 'ต้องใช้เว็บไซต์ออนไลน์ ฉบับออฟไลน์ไม่ได้ใส่ข้อมูลส่วนนี้ไว้ เพื่อให้ไฟล์มีขนาดเล็ก', en: 'This needs the online site: the offline file leaves this data out to stay small.' },
  'mod.missingFile': { th: 'ไม่พบไฟล์ข้อมูลของส่วนนี้บนเว็บไซต์', en: 'The data file for this part is not on the site' },
  'mod.error': { th: 'โหลดข้อมูลส่วนนี้ไม่สำเร็จ ลองโหลดหน้าใหม่', en: 'This part could not be loaded. Try reloading the page.' },
  'data.mod.h': { th: 'ไฟล์ของหน้าอื่น ๆ', en: 'Files behind the other pages' },
  'data.mod.intro': { th: 'เช่น ไฟล์ของหน้าวารสารและหน้าสถาบัน เว็บจะโหลดไฟล์เหล่านี้ก็ต่อเมื่อคุณเปิดหน้านั้น', en: 'For example, the files of the journal and institution pages; the site loads them only when you open that page.' },
  'data.file.journals': { th: 'วารสารทั้งหมดและตัวเลขของแต่ละฉบับ', en: 'Every journal and its figures' },
  'data.file.methods': { th: 'วิธีวิจัยรายหัวข้อและรายปี', en: 'Research methods by topic and year' },
  'data.file.diff': { th: 'สิ่งที่เปลี่ยนจากรอบก่อน', en: 'What changed since the previous release' },
  'data.file.references': { th: 'การอ้างอิงของแต่ละวารสาร และบทความที่อ้างถึงกันเอง', en: 'How each journal cites, and articles citing each other' },
  'data.file.search': { th: 'ดัชนีค้นหาบทความ: ชื่อเรื่องและคำสำคัญ ไม่มีบทคัดย่อหรือชื่อผู้แต่ง', en: 'Article search index: titles and keywords; no abstracts or author names' },
  'data.file.galaxy': { th: 'ตำแหน่งของบทความแต่ละเรื่องบนแผนที่บทความ', en: 'Where each article sits on the article map' },
  'data.file.kwtrends': { th: 'แนวโน้มคำสำคัญรายปี และคู่คำไทย–อังกฤษ', en: 'Keyword trends by year and Thai–English word pairs' },
  'nav.galaxy': { th: 'แผนที่บทความทุกเรื่อง', en: 'Map of every article' },
  'search.articles': { th: 'ค้นหาบทความทุกเรื่อง', en: 'Search every article' },
  'data.file.match': { th: 'ข้อมูลสำหรับหน้าวางบทคัดย่อ ไม่มีข้อความบทความ', en: 'Data for the abstract matcher; no article text' },
  'mod.skipped': { th: 'เหตุผล:', en: 'Reason:' },
})
