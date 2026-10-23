import { defineStrings } from './define'

/** Topic-page parts loaded on demand (SDG chips, RIS/BibTeX of the representative articles, the journal and institution
 *  rankings). Imported only by
 *  pages/topic/TopicExtras.tsx, a lazy chunk (entry budget). */
export const topicExtra = defineStrings({
  'sdg.label': { th: 'เกี่ยวข้องกับเป้าหมาย:', en: 'Related goals:' },
  'sdg.chip': { th: 'SDG {n}', en: 'SDG {n}' },
  'sdg.link': { th: 'SDG {n} {name} — ดูหัวข้ออื่นในเป้าหมายนี้', en: 'SDG {n} {name} — see other topics under this goal' },
  'x.h': { th: 'บันทึกบทความตัวแทน', en: 'Save the representative articles' },
  'x.ris': { th: 'RIS', en: 'RIS' },
  'x.bib': { th: 'BibTeX', en: 'BibTeX' },
  'x.label': { th: 'บันทึกบทความตัวแทน {n} เรื่องเป็น {format}', en: 'Save {n} representative articles as {format}' },
  'x.note': { th: 'สำหรับโปรแกรมจัดการบรรณานุกรม เช่น Zotero หรือ EndNote ไฟล์ไม่มีชื่อผู้แต่ง ใช้ DOI หรือลิงก์ ThaiJO เพื่อดูการอ้างอิงฉบับเต็ม', en: 'For reference managers such as Zotero or EndNote. Files carry no author names; use the DOI or ThaiJO link for the full citation.' },
  'rk.jr.title': { th: 'วารสารที่ลงหัวข้อนี้มากที่สุด {n} อันดับแรก (จำนวนบทความ)', en: 'The {n} journals publishing most on this topic (articles)' },
  'rk.org.title': { th: 'สถาบันที่มีผู้เขียนในหัวข้อนี้มากที่สุด {n} อันดับแรก (จำนวนบทความ)', en: 'The {n} institutions with most authors on this topic (articles)' },
  'rk.jr.label': { th: 'วารสาร เรียงตามจำนวนบทความ', en: 'Journals by number of articles' },
  'rk.org.label': { th: 'สถาบัน เรียงตามจำนวนบทความ', en: 'Institutions by number of articles' },
  'rk.how': { th: 'แท่งยาวตามจำนวนบทความ เทียบกับอันดับแรก ตัวเลขด้านขวาคือจำนวนบทความ ตารางมีรายการครบทุกแห่ง', en: 'Bars are as long as the article count, relative to the first; the number on the right is the count. The table lists every one.' },
  'rk.more': { th: 'และอีก {n} แห่งในตาราง', en: 'and {n} more in the table' },
})
