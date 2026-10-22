import { defineStrings } from './define'

/** Topic-page parts loaded on demand (SDG chips, RIS/BibTeX of the representative articles). Imported only by
 *  pages/topic/TopicExtras.tsx, a lazy chunk (entry budget). */
export const topicExtra = defineStrings({
  'sdg.label': { th: 'เกี่ยวข้องกับเป้าหมาย:', en: 'Related goals:' },
  'sdg.chip': { th: 'SDG {n}', en: 'SDG {n}' },
  'sdg.link': { th: 'SDG {n} {name} — ดูหัวข้ออื่นในเป้าหมายนี้', en: 'SDG {n} {name} — see other topics under this goal' },
  'x.h': { th: 'บันทึกบทความตัวแทน', en: 'Save the representative articles' },
  'x.ris': { th: 'RIS', en: 'RIS' },
  'x.bib': { th: 'BibTeX', en: 'BibTeX' },
  'x.label': { th: 'บันทึกบทความตัวแทน {n} เรื่องเป็น {format}', en: 'Save {n} representative articles as {format}' },
  'x.note': { th: 'สำหรับโปรแกรมจัดการบรรณานุกรม ไฟล์ไม่มีชื่อผู้แต่ง ใช้ DOI หรือลิงก์ ThaiJO เพื่อดูการอ้างอิงฉบับเต็ม', en: 'For reference managers. Files carry no author names; use the DOI or ThaiJO link for the full citation.' },
})
