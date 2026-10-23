import { defineStrings } from './define'

/** Embeddable widgets (/embed/*), the embed-code disclosure, feed links and "cite this atlas". Imported only by lazy
 *  chunks (src/embed/*, pages/about/CiteAtlas.tsx) so none of it adds to the entry chunk. */
export const embed = defineStrings({
  'attr.link': { th: 'TCI Research Atlas', en: 'TCI Research Atlas' },
  'attr.release': { th: 'รอบข้อมูล {release}', en: 'Release {release}' },
  'nf.title': { th: 'ไม่พบหัวข้อ {id}', en: 'Topic {id} not found' },
  'nf.body': { th: 'หัวข้อนี้อาจรวมกับหัวข้ออื่น หรือเปลี่ยนรหัสไปในรอบข้อมูลใหม่', en: 'It may have been merged or renumbered in a newer release.' },
  'nf.page': { th: 'ไม่พบวิดเจ็ตนี้', en: 'Widget not found' },
  'em.title': { th: 'หัวข้อที่กำลังเกิดใหม่และควรจับตา', en: 'Emerging and watch-list topics' },
  'em.sub': { th: '{n} หัวข้อแรก เรียงตามคะแนน', en: 'Top {n}, ordered by score' },
  'em.none': { th: 'รอบนี้ไม่มีหัวข้อที่กำลังเกิดใหม่หรือควรจับตา', en: 'No emerging or watch-list topics in this release.' },
  'em.more': { th: 'ดูหัวข้อทั้งหมดในเว็บ', en: 'See every topic on the site' },

  'snip.topic': { th: 'ฝังกราฟ', en: 'Embed this chart' },
  'snip.emerging': { th: 'ฝังรายการ', en: 'Embed this list' },
  'snip.intro': { th: 'วางโค้ดนี้ในหน้าเว็บของคุณ กราฟจะแสดงรอบข้อมูลล่าสุดเสมอ', en: 'Paste this code into your web page. It always shows the latest release.' },
  'snip.label': { th: 'โค้ด HTML', en: 'HTML code' },
  'snip.lang': { th: 'วิดเจ็ตจะใช้ภาษาเดียวกับที่คุณเลือกอยู่ตอนนี้', en: 'The widget uses the language you are reading in now.' },
  'copy': { th: 'คัดลอก', en: 'Copy' },
  'copy.done': { th: 'คัดลอกแล้ว', en: 'Copied' },
  'copy.fail': { th: 'คัดลอกอัตโนมัติไม่ได้ เลือกข้อความแล้วกด Ctrl+C', en: 'Could not copy automatically. Select the text and press Ctrl+C.' },

  'feed.releases': { th: 'ติดตามรอบใหม่ (Atom/RSS)', en: 'Follow new releases (Atom/RSS)' },
  'feed.topic': { th: 'ติดตามหัวข้อนี้ (Atom/RSS)', en: 'Follow this topic (Atom/RSS)' },
  'feed.hint': { th: 'ใส่ลิงก์นี้ในโปรแกรมอ่านฟีด', en: 'Add this link to a feed reader.' },

  'cite.intro': { th: 'ถ้าใช้ตัวเลขจาก Atlas ในงานเขียน โปรดระบุรอบข้อมูลที่ใช้ ตัวเลขของแต่ละรอบไม่เปลี่ยนย้อนหลัง', en: 'If you use figures from the atlas, name the release you used. A release never changes after it is published.' },
  'cite.apa': { th: 'แบบ APA', en: 'APA style' },
  'cite.bib': { th: 'BibTeX', en: 'BibTeX' },
  'cite.org': { th: 'ศูนย์ดัชนีการอ้างอิงวารสารไทย (TCI)', en: 'Thai-Journal Citation Index Centre (TCI)' },
  'cite.title': { th: 'TCI Research Atlas: แผนที่ภูมิทัศน์งานวิจัยไทย', en: 'TCI Research Atlas: Thai research landscape' },
  'cite.version': { th: 'รอบข้อมูล {release}', en: 'Release {release}' },
  'cite.kind': { th: 'ชุดข้อมูล', en: 'Data set' },
  'cite.noRelease': { th: 'ข้อความอ้างอิงที่ระบุรอบข้อมูลจะแสดงเมื่อหน้านี้โหลดข้อมูลได้แล้ว', en: 'Open this page with a loaded release to get a citation that names it.' },
})
