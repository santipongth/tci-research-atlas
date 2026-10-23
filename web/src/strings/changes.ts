import { defineStrings } from './define'

/**
 * /changes (E5). Its link on /overview lives in overview.ts.
 * Lazy pages only (read with useStrings) — kept out of the entry chunk.
 */
export const changes = defineStrings({
  'ch.title': { th: 'อะไรเปลี่ยนไปจากรอบที่แล้ว', en: 'What changed since the last release' },
  'ch.lede': { th: 'เทียบข้อมูลรอบ {release} กับรอบ {prev} ว่ามีหัวข้อไหนใหม่ หัวข้อไหนหายไป หัวข้อไหนเปลี่ยนสถานะ และหัวข้อไหนสัดส่วนเปลี่ยนมากที่สุด', en: 'Release {release} compared with {prev}: new and vanished topics, status changes and the biggest movers.' },
  'ch.fromOutput': { th: 'หน้านี้เทียบกับไฟล์ที่เผยแพร่ของรอบ {prev} เพราะรอบนั้นยังไม่ได้เก็บข้อมูลไว้สำหรับเทียบ', en: 'Compared with the published files of {prev}, which predates the comparison snapshot.' },
  'ch.kpi.h': { th: 'ตัวเลขรวม', en: 'Totals' },
  'col.kpi': { th: 'ตัวเลข', en: 'Figure' },
  'col.previous': { th: 'รอบก่อน', en: 'Previous' },
  'col.current': { th: 'รอบนี้', en: 'This release' },
  'col.change': { th: 'เปลี่ยนแปลง', en: 'Change' },
  'ch.status.h': { th: 'หัวข้อที่เปลี่ยนสถานะ', en: 'Status changes' },
  'ch.status.intro': { th: 'เช่น “{topic}” เปลี่ยนจาก “{from}” เป็น “{to}”', en: 'For example, “{topic}” went from {from} to {to}.' },
  'ch.status.table': { th: 'หัวข้อที่เปลี่ยนสถานะ', en: 'Topics whose status changed' },
  'ch.status.none': { th: 'ไม่มีหัวข้อที่เปลี่ยนสถานะ', en: 'No topic changed status' },
  'ch.new.h': { th: 'หัวข้อใหม่', en: 'New topics' },
  'ch.new.new': { th: 'หัวข้อใหม่', en: 'New' },
  'ch.new.split': { th: 'แยกออกมาจาก', en: 'Split from' },
  'ch.new.merge': { th: 'รวมมาจาก', en: 'Merged from' },
  'ch.retired.h': { th: 'หัวข้อที่ไม่มีแล้วในรอบนี้', en: 'Topics gone in this release' },
  'ch.retired.intro': { th: 'บทความของหัวข้อเหล่านี้ย้ายไปอยู่ในหัวข้ออื่นแล้ว', en: 'Their articles now belong to other topics.' },
  'ch.retired.into': { th: 'รวมเข้ากับ', en: 'Merged into' },
  'ch.retired.ended': { th: 'ไม่มีหัวข้อที่รับช่วงต่อ', en: 'No successor topic' },
  'ch.restructured.h': { th: 'หัวข้อที่รวมหรือแยก', en: 'Topics merged or split' },
  'ch.restructured.intro': { th: 'หัวข้อเหล่านี้ยังใช้รหัสเดิม แต่รวมหรือแยกกับหัวข้ออื่นแล้ว ถ้าจะเทียบตัวเลขข้ามรอบ ควรดูอย่างระมัดระวัง', en: 'These kept their id through a merge or a split; compare their figures across releases with care.' },
  'ch.restructured.merge': { th: 'รวมกับ', en: 'Merged with' },
  'ch.restructured.split': { th: 'แยกจาก', en: 'Split with' },
  'ch.movers.h': { th: 'หัวข้อที่สัดส่วนเปลี่ยนมากที่สุด', en: 'Biggest movers' },
  'ch.movers.intro': { th: 'เช่น “{topic}” เปลี่ยนจาก {a} เป็น {b} ของบทความ เพราะมีข้อมูลปีใหม่เข้ามา หรือมีบทความเก่าเพิ่มเข้ามาย้อนหลัง', en: 'For example, “{topic}” went from {a} to {b} of articles, after a new year of data or back-filled articles.' },
  'ch.movers.table': { th: 'หัวข้อที่สัดส่วนเปลี่ยนมากที่สุด', en: 'Topics whose share changed most' },
  'ch.journals.h': { th: 'วารสารที่เข้ามาใหม่', en: 'Newly covered journals' },
  'ch.noPrevious': { th: 'ยังไม่มีรอบก่อนให้เทียบ', en: 'No previous release to compare with' },
  'ch.noPreviousBody': { th: 'หน้านี้จะเริ่มแสดงการเปลี่ยนแปลงเมื่อมีข้อมูลรอบที่สอง', en: 'This page shows changes from the second release on.' },
})
