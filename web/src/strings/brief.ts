import { defineStrings } from './define'

export const brief = defineStrings({
  'brief.title': { th: 'สรุปผู้บริหาร: งานวิจัยไทย รอบข้อมูล {release}', en: 'Executive brief: Thai research, release {release}' },
  'brief.sub': { th: 'ข้อมูลถึงปี {year} · จัดทำเมื่อ {date}', en: 'Data through {year} · produced {date}' },
  'brief.kpi': { th: 'ตัวเลขหลัก', en: 'Headline figures' },
  'brief.points': { th: 'ประเด็นสำคัญ', en: 'Key points' },
  'brief.status': { th: 'สถานะของหัวข้อวิจัย', en: 'Status of research topics' },
  'brief.top': { th: '{status}: {n} หัวข้อที่เปลี่ยนเร็วที่สุด', en: '{status}: the {n} fastest-changing topics' },
  'brief.watch': { th: 'หัวข้อจับตา {n} หัวข้อมีการเติบโตเข้าเกณฑ์ แต่ไม่ผ่านเกณฑ์ความกว้าง (วารสาร สถาบัน หรือวารสารใหม่) ควรตรวจสอบก่อนอ้างอิง', en: '{n} watch topics meet the growth bar but did not pass the breadth test (journals, institutions or new journals); check them before citing.' },
  'brief.def': { th: 'สถานะตามนิยามฉบับที่ {v} อัตราโตคืออัตราโตของสัดส่วนบทความต่อปี ช่วงเชื่อมั่น {level}% และหัวข้อกำลังเกิดใหม่ต้องมีขอบล่างอย่างน้อย {bar} ต่อปี', en: 'Statuses follow definition version {v}. Growth is the yearly growth in share of articles with {level}% confidence intervals; an emerging topic’s lower bound is at least {bar} a year.' },
  'brief.more': { th: 'รายละเอียดทุกหัวข้ออยู่ในเว็บไซต์ TCI Research Atlas', en: 'Every topic is detailed on the TCI Research Atlas website' },
  'brief.print': { th: 'พิมพ์หรือบันทึกเป็น PDF', en: 'Print or save as PDF' },
})
