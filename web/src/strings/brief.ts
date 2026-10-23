import { defineStrings } from './define'

export const brief = defineStrings({
  'brief.title': { th: 'สรุปผู้บริหาร: งานวิจัยไทย รอบข้อมูล {release}', en: 'Executive brief: Thai research, release {release}' },
  'brief.sub': { th: 'ข้อมูลถึงปี {year} · จัดทำเมื่อ {date}', en: 'Data through {year} · produced {date}' },
  'brief.kpi': { th: 'ตัวเลขหลัก', en: 'Headline figures' },
  'brief.points': { th: 'ประเด็นสำคัญ', en: 'Key points' },
  'brief.status': { th: 'สถานะของหัวข้อวิจัย', en: 'Status of research topics' },
  'brief.top': { th: '{status}: {n} หัวข้อที่เปลี่ยนเร็วที่สุด', en: '{status}: the {n} fastest-changing topics' },
  'brief.watch': { th: 'หัวข้อสถานะจับตา {n} หัวข้อโตเร็ว แต่บทความมาจากวารสารหรือสถาบันไม่กี่แห่ง ควรตรวจดูก่อนนำไปอ้างอิง', en: '{n} watch topics are growing fast, but from only a few journals or institutions; check them before citing.' },
  'brief.def': { th: 'สถานะในเอกสารนี้ใช้นิยามฉบับที่ {v} การเติบโต หมายถึงสัดส่วนบทความที่เพิ่มขึ้นหรือลดลงในแต่ละปี ช่วงที่น่าจะเป็นคิดที่ความมั่นใจ {level}% หัวข้อที่กำลังเกิดใหม่ต้องโตอย่างน้อย {bar} ต่อปี แม้จะคิดแบบระวังที่สุด', en: 'Statuses follow definition version {v}. Growth is the yearly change in share of articles; likely ranges are at the {level}% level. An emerging topic grows at least {bar} a year even on the most cautious reading.' },
  'brief.more': { th: 'ดูรายละเอียดของทุกหัวข้อได้ที่เว็บไซต์ TCI Research Atlas', en: 'Every topic is detailed on the TCI Research Atlas website' },
  'brief.movers.title': { th: 'หัวข้อที่สัดส่วนบทความเปลี่ยนเร็วที่สุด: โตเร็วสุด {up} และลดเร็วสุด {down} หัวข้อ', en: 'Topics whose share of articles changes fastest: the {up} fastest-rising and {down} fastest-falling' },
  'brief.movers.table': { th: 'หัวข้อที่เปลี่ยนเร็วที่สุด พร้อมช่วงที่น่าจะเป็น', en: 'The fastest-changing topics with their likely ranges' },
  'brief.movers.how': { th: 'แต่ละจุดคือค่าประมาณว่าสัดส่วนบทความเปลี่ยนไปปีละเท่าไร จุดที่อยู่ขวาเส้นทึบคือโต ซ้ายคือลด เส้นประคือเกณฑ์ {bar} ต่อปีของหัวข้อที่กำลังเกิดใหม่ ตัวเลขด้านขวาบอกช่วงที่ค่าจริงน่าจะอยู่ (ความมั่นใจ {level}%)', en: 'Each dot is the estimated yearly change in share of articles: right of the solid line is growth, left is decline. The dashed line is the emerging bar of {bar} a year. The numbers on the right give the range the true value likely sits in ({level}%).' },
  'brief.print': { th: 'พิมพ์หรือบันทึกเป็น PDF', en: 'Print or save as PDF' },
})
