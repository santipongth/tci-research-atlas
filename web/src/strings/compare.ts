import { defineStrings } from './define'

export const compare = defineStrings({
  'cmp.title': { th: 'เปรียบเทียบหัวข้อวิจัย', en: 'Compare research topics' },
  'cmp.lede': { th: 'เลือก 2–4 หัวข้อเพื่อดูแนวโน้มรายปีซ้อนกัน วัดเป็นสัดส่วนของบทความทั้งหมด (ไม่หลอกตาเพราะจำนวนบทความรวมเพิ่มขึ้นทุกปี) หรือเป็นจำนวนบทความ', en: 'Choose 2–4 topics to overlay their yearly trends, as a share of all articles (not inflated by the growing total) or as article counts.' },
  'cmp.add': { th: 'เพิ่มหัวข้อ', en: 'Add a topic' },
  'cmp.max': { th: 'เลือกได้สูงสุด 4 หัวข้อ เอาหัวข้อออกก่อนเพื่อเพิ่มหัวข้อใหม่', en: 'Up to 4 topics. Remove one to add another.' },
  'cmp.chosen': { th: 'หัวข้อที่เลือก', en: 'Chosen topics' },
  'cmp.remove': { th: 'เอาออก: {n}', en: 'Remove {n}' },
  'cmp.metric': { th: 'วัดเป็น', en: 'Measure' },
  'cmp.metric.share': { th: 'สัดส่วนของบทความทั้งหมด', en: 'Share of all articles' },
  'cmp.metric.count': { th: 'จำนวนบทความ', en: 'Number of articles' },
  'cmp.needTwo': { th: 'เลือกอย่างน้อย 2 หัวข้อเพื่อเปรียบเทียบ', en: 'Choose at least 2 topics to compare' },
  'cmp.try': { th: 'ลองเริ่มจากหัวข้อเหล่านี้', en: 'Try starting with these' },
  'cmp.chart.h': { th: 'แนวโน้มรายปี', en: 'Yearly trends' },
  'cmp.fig.share': { th: 'สัดส่วนบทความรายปี {a}–{b}', en: 'Share of articles a year, {a}–{b}' },
  'cmp.fig.count': { th: 'จำนวนบทความรายปี {a}–{b}', en: 'Articles a year, {a}–{b}' },
  'cmp.table': { th: 'ค่ารายปีของหัวข้อที่เลือก', en: 'Yearly values of the chosen topics' },
  'cmp.metrics.h': { th: 'ตัวเลขสำคัญ', en: 'Key figures' },
  'cmp.metrics.table': { th: 'ตัวเลขสำคัญของหัวข้อที่เลือก', en: 'Key figures of the chosen topics' },
  'cmp.how': { th: 'แต่ละเส้นมีลายเส้นต่างกันและมีชื่อกำกับที่ปลายเส้น จึงแยกได้โดยไม่ต้องอาศัยสี', en: 'Each line has its own dash pattern and a name at its end, so they can be told apart without colour.' },
})
