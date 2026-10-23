import { defineStrings } from './define'

export const about = defineStrings({
  'about.title': { th: 'อ่านตัวเลขอย่างไร', en: 'How to read the numbers' },
  'about.lede': { th: 'ตัวเลขในเว็บนี้มาจากไหน สถานะแต่ละแบบหมายถึงอะไร และนิยามเคยเปลี่ยนอย่างไร', en: 'Where the figures come from, what each status means and how the definition has changed.' },
  'about.generic.R': { th: '3 ปีล่าสุดที่ข้อมูลครบ', en: 'the last 3 complete years' },
  'about.generic.B': { th: '5 ปีก่อนหน้านั้น', en: 'the 5 years before' },
  'about.generic.W': { th: '5 ปีล่าสุด', en: 'the last 5 years' },
  'about.def.h': { th: 'สถานะแต่ละแบบหมายถึงอะไร', en: 'What each status means' },
  'about.def.intro': { th: 'ระบบดู “ข้อมูลน้อย” ก่อน หัวข้อที่ข้อมูลน้อยจะไม่ได้สถานะอื่น จากนั้นดูทีละกฎ: กำลังเกิดใหม่ จับตา กำลังมาแรง ลดลง และคงที่ หัวข้อได้สถานะแรกที่เข้ากฎ (นิยามฉบับที่ {v} ช่วงที่น่าจะเป็นใช้ระดับ {level}%)', en: 'The system checks “low data” first; a low-data topic gets no other status. Then it tries each rule in turn: emerging, watch, hot, declining and stable, and a topic takes the first one it meets. (Definition version {v}; every likely range is at the {level}% level.)' },
  'about.def.order': { th: 'ทุกเกณฑ์เป็นค่าตั้งของระบบและแสดงครบในหน้านี้ แต่ละรอบบันทึกเลขฉบับของนิยามและรหัสการตั้งค่าไว้ จึงตรวจย้อนหลังได้', en: 'Every threshold is a setting of the system and is listed on this page. Each release records the definition version and a code for its settings, so results can be checked later.' },
  'about.privacy.h': { th: 'ความเป็นส่วนตัวและลิขสิทธิ์', en: 'Privacy and copyright' },
  'about.privacy.body': { th: 'เว็บนี้แสดงเฉพาะหัวข้อ วารสาร และสถาบัน ไม่จัดอันดับหรือแสดงข้อมูลบุคคล (PDPA) ไม่เผยแพร่บทคัดย่อ เพราะเป็นลิขสิทธิ์ของวารสาร ชื่อเรื่องลิงก์กลับไปที่ ThaiJO และขณะเปิดดู เว็บไม่เรียกบริการภายนอกหรือ AI ใด ๆ', en: 'The site shows topics, journals and institutions only; it never ranks or shows individuals (PDPA). Abstracts are not republished because they belong to the journals; titles link back to ThaiJO, and the site calls no outside service or AI while you browse.' },
  'about.cite.h': { th: 'การอ้างอิง Atlas', en: 'Cite this atlas' },
  'about.cite.show': { th: 'แสดงข้อความอ้างอิง (APA และ BibTeX)', en: 'Show the citation (APA and BibTeX)' },
  'about.flow.h': { th: 'จากบทความถึงสถานะใน 4 ขั้น', en: 'From articles to a status in 4 steps' },
  'about.log.h': { th: 'นิยามเคยเปลี่ยนอย่างไร', en: 'How the definition has changed' },
  'about.log.intro': { th: 'นิยามเปลี่ยนทีไร เลขฉบับเพิ่มขึ้น ตัวเลขต่างฉบับจึงไม่ควรเทียบกันตรง ๆ', en: 'Each change to the definition raises its version number, so figures from different versions should not be compared directly.' },
  'about.log.version': { th: 'ฉบับที่ {v} · {date}', en: 'Version {v} · {date}' },
})
