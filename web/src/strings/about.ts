import { defineStrings } from './define'

export const about = defineStrings({
  'about.title': { th: 'วิธีการและนิยาม', en: 'Method and definitions' },
  'about.lede': { th: 'Atlas นี้สร้างอย่างไร สถานะแต่ละแบบหมายถึงอะไร และนิยามเปลี่ยนไปอย่างไรในแต่ละรอบ อธิบายด้วยภาษาง่าย', en: 'How this atlas is made, what each status means and how the definition has changed between releases, in plain language.' },
  'about.generic.R': { th: '3 ปีล่าสุดที่ข้อมูลครบ', en: 'the last 3 complete years' },
  'about.generic.B': { th: '5 ปีก่อนหน้านั้น', en: 'the 5 years before' },
  'about.generic.W': { th: '5 ปีล่าสุด', en: 'the last 5 years' },
  'about.def.h': { th: 'นิยามสถานะ', en: 'Status definitions' },
  'about.def.intro': { th: 'นิยามฉบับที่ {v} ช่วงเชื่อมั่นทุกช่วงใช้ระดับ {level}% ระบบตรวจสถานะตามลำดับด้านล่าง และหัวข้อได้สถานะแรกที่เข้าเกณฑ์', en: 'Definition version {v}; every interval is at the {level}% level. Statuses are checked in the order below, and a topic takes the first one it meets.' },
  'about.def.order': { th: 'เกณฑ์ตัวเลขทั้งหมดเป็นค่าตั้งของระบบและบันทึกไว้ในทุกรอบข้อมูล เพื่อให้ตรวจย้อนหลังได้', en: 'Every threshold is a setting of the system and is recorded with each release, so results can be checked later.' },
  'about.privacy.h': { th: 'ความเป็นส่วนตัวและลิขสิทธิ์', en: 'Privacy and copyright' },
  'about.privacy.body': { th: 'Atlas แสดงผลระดับหัวข้อ วารสาร และสถาบันเท่านั้น ไม่จัดอันดับหรือแสดงข้อมูลบุคคล (PDPA) ไม่เผยแพร่บทคัดย่อเพราะเป็นลิขสิทธิ์ของวารสาร ชื่อเรื่องบทความลิงก์กลับไปยัง ThaiJO และเว็บไซต์ไม่เรียกใช้บริการภายนอกหรือ AI ใด ๆ ขณะเปิดดู', en: 'The atlas shows topics, journals and institutions only; it never ranks or shows individuals (PDPA). Abstracts are not republished because they belong to the journals; article titles link back to ThaiJO, and the site calls no outside service or AI while you browse.' },
  'about.log.h': { th: 'ประวัติการเปลี่ยนนิยาม', en: 'Definition changelog' },
  'about.log.intro': { th: 'ทุกครั้งที่นิยามเปลี่ยน เลขฉบับจะเพิ่มขึ้น ตัวเลขต่างฉบับจึงไม่ควรนำมาเทียบกันโดยตรง', en: 'Each change to the definition raises its version number, so figures from different versions should not be compared directly.' },
  'about.log.version': { th: 'ฉบับที่ {v} · {date}', en: 'Version {v} · {date}' },
})
