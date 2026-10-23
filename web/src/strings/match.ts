import { defineStrings } from './define'

/** /match (R3 "match my abstract", R4 "where to publish"). */
export const match = defineStrings({
  'nav.match': { th: 'วางบทคัดย่อ', en: 'Match an abstract' },
  'mt.title': { th: 'วางบทคัดย่อของคุณ', en: 'Match your abstract' },
  'mt.lede': { th: 'เช่น วางบทคัดย่อเรื่องการดูแลผู้สูงอายุ แล้วดูว่าใกล้หัวข้อไหน มีงานอะไรแล้ว และวารสารไหนตีพิมพ์ ใช้ได้ทั้งไทยและอังกฤษ', en: 'For example, paste an abstract on elderly care to see the closest topics, existing work and the journals that publish it. Thai or English.' },
  'mt.privacy': { th: 'ข้อความที่วางอยู่ในเบราว์เซอร์นี้เท่านั้น ไม่ถูกส่งไปที่ใด ไม่ถูกบันทึก และไม่อยู่ในลิงก์ของหน้า', en: 'Your text stays in this browser. It is not sent anywhere, not stored, and not put in the page link.' },
  'mt.label': { th: 'ข้อความของคุณ', en: 'Your text' },
  'mt.submit': { th: 'หาหัวข้อที่ใกล้ที่สุด', en: 'Find the closest topics' },
  'mt.clear': { th: 'ล้างข้อความ', en: 'Clear' },
  'mt.tooShort': { th: 'พิมพ์หรือวางข้อความอย่างน้อย {n} ตัวอักษร (ตอนนี้ {have})', en: 'Type or paste at least {n} characters (now {have})' },
  'mt.none': { th: 'ไม่พบหัวข้อที่ใกล้พอ ลองเพิ่มคำสำคัญหรือวางบทคัดย่อทั้งย่อหน้า', en: 'No topic is close enough. Add keywords or paste the whole abstract.' },
  'mt.topics.h': { th: 'หัวข้อที่ใกล้ที่สุด', en: 'Closest topics' },
  'mt.topics.intro': { th: 'เรียงตามคำที่ตรงกัน (0–100%) ระบบเทียบคำ ไม่ได้เข้าใจความหมาย', en: 'Ordered by matching words (0–100%). The system compares words; it does not understand meaning.' },
  'mt.works.h': { th: 'งานในหัวข้อที่ใกล้ที่สุด', en: 'Work on the closest topic' },
  'mt.works.intro': { th: 'บทความตัวแทนของ “{topic}” (ลิงก์ไปยัง ThaiJO)', en: 'Representative articles of “{topic}” (links to ThaiJO)' },
  'mt.journals.h': { th: 'ควรตีพิมพ์ที่ไหน', en: 'Where to publish' },
  'mt.journals.intro': { th: 'วารสารที่เรื่องเหล่านี้เป็นส่วนใหญ่ของงานที่ตีพิมพ์ คิดจาก {n} หัวข้อแรก ก่อนส่งบทความ ตรวจขอบเขต กลุ่ม TCI และค่าธรรมเนียมที่เว็บไซต์วารสาร', en: 'Journals for which these topics are a large part of their output, from the first {n} topics. Before you submit, check the scope, TCI tier and fees on the journal’s website.' },
  'mt.fitTopics': { th: 'ตีพิมพ์เรื่องเหล่านี้: {list}', en: 'Publishes on: {list}' },
  'mt.resultsN': { th: 'พบ {n} หัวข้อที่ใกล้เคียง', en: '{n} close topics found' },
})
