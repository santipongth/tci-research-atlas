import { defineStrings } from './define'

/** /match (R3 "match my abstract", R4 "where to publish"). */
export const match = defineStrings({
  'nav.match': { th: 'วางบทคัดย่อ', en: 'Match an abstract' },
  'mt.title': { th: 'วางบทคัดย่อของคุณ', en: 'Match your abstract' },
  'mt.lede': { th: 'วางชื่อเรื่อง บทคัดย่อ หรือคำสำคัญ (ไทยหรืออังกฤษ) เพื่อดูหัวข้อวิจัยที่ใกล้ที่สุด งานในหัวข้อนั้น และวารสารที่ตีพิมพ์หัวข้อเหล่านี้', en: 'Paste a title, abstract or keywords (Thai or English) to see the closest research topics, work on them, and the journals that publish them.' },
  'mt.privacy': { th: 'ข้อความที่วางประมวลผลในเบราว์เซอร์นี้เท่านั้น ไม่ถูกส่งไปที่ใด ไม่ถูกบันทึก และไม่อยู่ในลิงก์ของหน้า', en: 'Your text is processed in this browser only. It is not sent anywhere, not stored, and not put in the page link.' },
  'mt.label': { th: 'ข้อความของคุณ', en: 'Your text' },
  'mt.submit': { th: 'หาหัวข้อที่ใกล้ที่สุด', en: 'Find the closest topics' },
  'mt.clear': { th: 'ล้างข้อความ', en: 'Clear' },
  'mt.tooShort': { th: 'พิมพ์หรือวางข้อความอย่างน้อย {n} ตัวอักษร (ตอนนี้ {have})', en: 'Type or paste at least {n} characters (now {have})' },
  'mt.none': { th: 'ไม่พบหัวข้อที่ใกล้พอ ลองเพิ่มคำสำคัญหรือวางบทคัดย่อทั้งย่อหน้า', en: 'No topic is close enough. Add keywords or paste the whole abstract.' },
  'mt.topics.h': { th: 'หัวข้อที่ใกล้ที่สุด', en: 'Closest topics' },
  'mt.topics.intro': { th: 'เรียงตามความใกล้เคียงของถ้อยคำ (0–100%) เป็นการเทียบคำ ไม่ใช่การเข้าใจความหมาย', en: 'Ordered by word overlap (0–100%). This compares words; it does not understand meaning.' },
  'mt.score': { th: 'ความใกล้เคียง', en: 'Closeness' },
  'mt.works.h': { th: 'งานในหัวข้อที่ใกล้ที่สุด', en: 'Work on the closest topic' },
  'mt.works.intro': { th: 'บทความตัวแทนของ “{topic}” (ลิงก์ไปยัง ThaiJO)', en: 'Representative articles of “{topic}” (links to ThaiJO)' },
  'mt.journals.h': { th: 'ควรตีพิมพ์ที่ไหน', en: 'Where to publish' },
  'mt.journals.intro': { th: 'วารสารที่ตีพิมพ์หัวข้อใกล้เคียงเหล่านี้มากที่สุดเมื่อเทียบกับบทความทั้งหมดของวารสาร คิดจาก {n} หัวข้อแรกเท่านั้น ตรวจขอบเขต กลุ่ม TCI และค่าธรรมเนียมที่เว็บไซต์วารสารก่อนส่งบทความ', en: 'Journals for which these topics make up the largest part of their output, from the first {n} topics only. Check the scope, TCI tier and fees on the journal’s website before you submit.' },
  'mt.fit': { th: 'ความเหมาะสม', en: 'Fit' },
  'mt.fitTopics': { th: 'ตีพิมพ์ในหัวข้อเหล่านี้: {list}', en: 'Publishes on: {list}' },
  'mt.resultsN': { th: 'พบ {n} หัวข้อที่ใกล้เคียง', en: '{n} close topics found' },
})
