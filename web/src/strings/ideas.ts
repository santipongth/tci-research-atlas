import { defineStrings } from './define'

/** "หัวข้อน่าทำ" for students and advisors (/ideas). Lazy page only (read with useStrings). */
export const ideas = defineStrings({
  'id.title': { th: 'หัวข้อน่าทำสำหรับนักศึกษาและอาจารย์', en: 'Topics worth starting: for students and advisors' },
  'id.lede': {
    th: 'อยากหาหัวข้อวิทยานิพนธ์หรือโครงการวิจัย ลองเริ่มจากเรื่องที่กำลังโต หรือเรื่องที่ยังมีคนทำไม่มาก เลือกสาขาที่สนใจ แล้วกดชื่อหัวข้อเพื่อดูบทความตัวอย่างและวารสารที่ลงเรื่องนั้น',
    en: 'Looking for a thesis or project topic? Start from what is growing, or what few people work on yet. Pick a field, then open a topic for example articles and the journals that publish it.',
  },
  'id.field': { th: 'สาขา', en: 'Field' },
  'id.all': { th: 'ทุกสาขา', en: 'All fields' },
  'id.list.h': { th: 'หัวข้อที่น่าลงมือ', en: 'Topics worth starting on' },
  'id.list.intro': { th: 'เช่น “{topic}” {why}', en: 'For example, “{topic}”: {why}' },
  'id.list.count': { th: '{n} หัวข้อ', en: '{n} topics' },
  'id.none': { th: 'สาขานี้ยังไม่มีหัวข้อที่กำลังโตหรือมีคนทำน้อยในรอบนี้ ลองเลือกสาขาอื่น', en: 'No growing or under-studied topic in this field this release. Try another field.' },
  'id.why.emerging': { th: 'กำลังโต สัดส่วนบทความเพิ่มราว {g} ต่อปี และมีคนทำจากหลายสถาบันแล้ว', en: 'growing: its share of articles rises about {g} a year, already from many institutions' },
  'id.why.watch': { th: 'โตเร็ว ราว {g} ต่อปี แต่ยังมาจากไม่กี่วารสารหรือสถาบัน ยังมีที่ให้คนใหม่เข้าไปทำ', en: 'growing fast, about {g} a year, but from only a few journals or institutions — room for newcomers' },
  'id.why.few': { th: 'กำลังมาแรง แต่มีเพียง {k} สถาบันที่ทำในช่วงหลัง', en: 'on the rise, yet only {k} institutions work on it lately' },
  'id.facts': { th: '{n} บทความในปี {a}–{b} · {j} วารสาร · {o} สถาบัน', en: '{n} articles in {a}–{b} · {j} journals · {o} institutions' },
  'id.fewNote': { th: 'มีเพียง {k} สถาบันที่ทำเรื่องนี้ในช่วงหลัง', en: 'Only {k} institutions work on it lately' },
  'id.open': { th: 'ดูบทความตัวอย่างและวารสาร', en: 'Example articles and journals' },
  'id.how': {
    th: 'รายการนี้มาจากสถานะของหัวข้อ: “กำลังเกิดใหม่” คือเล็กแต่โตเร็วจากหลายแหล่ง “จับตา” คือโตเร็วแต่มาจากไม่กี่วารสารหรือสถาบัน และหัวข้อ “กำลังมาแรง” ที่มีสถาบันทำไม่เกิน {k} แห่ง ใช้เป็นจุดเริ่มคิดหัวข้อ ไม่ใช่คำแนะนำว่าต้องทำเรื่องไหน',
    en: 'Drawn from topic status: “emerging” is small but growing fast from many sources, “watch” grows fast from few journals or institutions, plus “hot” topics with at most {k} institutions. A starting point for ideas, not advice on what to study.',
  },
  'id.bridge.h': { th: 'ไอเดียเชื่อมสองเรื่อง', en: 'Ideas that join two topics' },
  'id.bridge.intro': { th: 'หัวข้อที่เนื้อหาใกล้กัน แต่แทบไม่มีใครทำทั้งสองเรื่องพร้อมกัน อาจเป็นจุดเริ่มของงานวิจัยข้ามเรื่อง', en: 'Topics close in content that almost nobody works on together — a possible start for cross-topic work.' },
  'id.bridge.k': { th: 'มี {k} สถาบันที่ทำทั้งสองเรื่อง', en: '{k} institutions work on both' },
  'id.bridge.none': { th: 'ยังไม่มีสถาบันที่ทำทั้งสองเรื่อง', en: 'No institution works on both yet' },
  'id.bridge.plus': { th: 'กับ', en: 'with' },
})
