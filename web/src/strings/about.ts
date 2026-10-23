import { defineStrings } from './define'

export const about = defineStrings({
  'about.title': { th: 'อ่านตัวเลขอย่างไร', en: 'How to read the numbers' },
  'about.lede': { th: 'ตัวเลขในเว็บนี้มาจากไหน คำนวณอย่างไร และสถานะแต่ละแบบแปลว่าอะไร', en: 'Where the figures come from, how they are worked out and what each status means.' },
  'about.generic.R': { th: '3 ปีล่าสุดที่ข้อมูลครบ', en: 'the last 3 complete years' },
  'about.generic.B': { th: '5 ปีก่อนหน้านั้น', en: 'the 5 years before' },
  'about.generic.W': { th: '5 ปีล่าสุด', en: 'the last 5 years' },
  'about.def.h': { th: 'สถานะแต่ละแบบหมายถึงอะไร', en: 'What each status means' },
  'about.def.intro': { th: 'ระบบดูก่อนว่าหัวข้อ “ข้อมูลน้อย” หรือไม่ ถ้าใช่ หัวข้อนั้นจะไม่ได้สถานะอื่น จากนั้นจึงไล่ดูทีละกฎ ได้แก่ กำลังเกิดใหม่ จับตา กำลังมาแรง ลดลง และคงที่ หัวข้อจะได้สถานะแรกที่เข้าเกณฑ์ (นิยามฉบับที่ {v} ช่วงที่น่าจะเป็นคิดที่ความมั่นใจ {level}%)', en: 'The system checks “low data” first; a low-data topic gets no other status. Then it tries each rule in turn: emerging, watch, hot, declining and stable, and a topic takes the first one it meets. (Definition version {v}; every likely range is at the {level}% level.)' },
  'about.def.order': { th: 'เกณฑ์ทุกข้อเป็นค่าที่ตั้งไว้ในระบบ และมีครบในหน้านี้ ข้อมูลแต่ละรอบจดเลขฉบับของนิยามและรหัสการตั้งค่าไว้ จึงตรวจย้อนหลังได้เสมอ', en: 'Every threshold is a setting of the system and is listed on this page. Each release records the definition version and a code for its settings, so results can be checked later.' },
  'about.privacy.h': { th: 'ความเป็นส่วนตัวและลิขสิทธิ์', en: 'Privacy and copyright' },
  'about.privacy.body': { th: 'เว็บนี้แสดงแค่หัวข้อ วารสาร และสถาบัน ไม่จัดอันดับและไม่แสดงข้อมูลของบุคคล (ตาม PDPA) ไม่นำบทคัดย่อมาแสดง เพราะเป็นลิขสิทธิ์ของวารสาร ชื่อเรื่องจึงลิงก์กลับไปที่ ThaiJO และระหว่างที่คุณเปิดดู เว็บไม่ได้เชื่อมต่อบริการภายนอกหรือ AI ใด ๆ', en: 'The site shows topics, journals and institutions only; it never ranks or shows individuals (PDPA). Abstracts are not republished because they belong to the journals; titles link back to ThaiJO, and the site calls no outside service or AI while you browse.' },
  'about.cite.h': { th: 'การอ้างอิง Atlas', en: 'Cite this atlas' },
  'about.cite.show': { th: 'แสดงข้อความอ้างอิง (APA และ BibTeX)', en: 'Show the citation (APA and BibTeX)' },
  'about.flow.h': { th: 'Atlas ทำงานอย่างไร: จากบทความถึงเว็บนี้ใน 5 ขั้น', en: 'How the Atlas works: from articles to this site in 5 steps' },
})
