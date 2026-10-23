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
  'brief.print': { th: 'พิมพ์หรือบันทึกเป็น PDF', en: 'Print or save as PDF' },
})
