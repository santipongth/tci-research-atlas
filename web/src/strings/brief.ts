import { defineStrings } from './define'

export const brief = defineStrings({
  'brief.title': { th: 'สรุปผู้บริหาร: งานวิจัยไทย รอบข้อมูล {release}', en: 'Executive brief: Thai research, release {release}' },
  'brief.sub': { th: 'ข้อมูลถึงปี {year} · จัดทำเมื่อ {date}', en: 'Data through {year} · produced {date}' },
  'brief.kpi': { th: 'ตัวเลขหลัก', en: 'Headline figures' },
  'brief.points': { th: 'ประเด็นสำคัญ', en: 'Key points' },
  'brief.status': { th: 'สถานะของหัวข้อวิจัย', en: 'Status of research topics' },
  'brief.top': { th: '{status}: {n} หัวข้อที่เปลี่ยนเร็วที่สุด', en: '{status}: the {n} fastest-changing topics' },
  'brief.watch': { th: 'หัวข้อจับตา {n} หัวข้อโตเร็ว แต่มาจากวารสารหรือสถาบันไม่กี่แห่ง ควรตรวจก่อนอ้างอิง', en: '{n} watch topics are growing fast, but from only a few journals or institutions; check them before citing.' },
  'brief.def': { th: 'สถานะตามนิยามฉบับที่ {v} การเติบโตคือสัดส่วนบทความที่เพิ่มหรือลดต่อปี ช่วงที่น่าจะเป็นใช้ระดับ {level}% หัวข้อกำลังเกิดใหม่ต้องโตอย่างน้อย {bar} ต่อปีแม้คิดแบบระวังที่สุด', en: 'Statuses follow definition version {v}. Growth is the yearly change in share of articles; likely ranges are at the {level}% level. An emerging topic grows at least {bar} a year even on the most cautious reading.' },
  'brief.more': { th: 'รายละเอียดทุกหัวข้ออยู่ในเว็บไซต์ TCI Research Atlas', en: 'Every topic is detailed on the TCI Research Atlas website' },
  'brief.movers.title': { th: 'หัวข้อที่สัดส่วนบทความเปลี่ยนเร็วที่สุด: โตเร็วสุด {up} และลดเร็วสุด {down} หัวข้อ', en: 'Topics whose share of articles changes fastest: the {up} fastest-rising and {down} fastest-falling' },
  'brief.movers.table': { th: 'หัวข้อที่เปลี่ยนเร็วที่สุด พร้อมช่วงที่น่าจะเป็น', en: 'The fastest-changing topics with their likely ranges' },
  'brief.movers.how': { th: 'จุดคือค่าประมาณการเปลี่ยนแปลงของสัดส่วนบทความต่อปี ขวาของเส้นทึบคือโต ซ้ายคือลด เส้นประคือเกณฑ์ {bar} ต่อปีของหัวข้อกำลังเกิดใหม่ ตัวเลขด้านขวาบอกช่วงที่ค่าจริงน่าจะอยู่ ({level}%)', en: 'Each dot is the estimated yearly change in share of articles: right of the solid line is growth, left is decline. The dashed line is the emerging bar of {bar} a year. The numbers on the right give the range the true value likely sits in ({level}%).' },
  'brief.print': { th: 'พิมพ์หรือบันทึกเป็น PDF', en: 'Print or save as PDF' },
})
