/**
 * Changes to the status definition (docs/EMERGING_SPEC.md). /about shows entries up to the release's
 * definition_version: `th`/`en` in plain words; `tech` names the methods for readers who want them (behind a disclosure).
 */
export interface ChangelogEntry {
  version: number
  date: string
  th: string
  en: string
  tech: { th: string; en: string }
}

export const CHANGELOG: readonly ChangelogEntry[] = [
  {
    version: 2,
    date: '2026-10-18',
    th: 'เริ่มบอกการเติบโตเป็นช่วงที่น่าจะเป็น ไม่ใช่ตัวเลขเดียว “หัวข้อใหญ่” คือหัวข้อที่อยู่ใน 25% ที่มีบทความมากที่สุด หัวข้อที่จะเป็น “กำลังเกิดใหม่” ต้องมาจากอย่างน้อย 3 วารสารและ 3 สถาบัน และเพิ่มสถานะ “จับตา” กับ “ข้อมูลน้อย”',
    en: 'Growth is now given as a likely range, not a single number. A “large” topic is one in the top 25% by articles. An emerging topic must come from at least 3 journals and 3 institutions, and the “watch” and “low data” statuses were added.',
    tech: { th: 'Poisson GLM ของสัดส่วน พร้อมช่วงเชื่อมั่น 90%', en: 'A Poisson GLM of the share with a 90% confidence interval.' },
  },
  {
    version: 3,
    date: '2026-10-18',
    th: 'ช่วงที่น่าจะเป็นกว้างขึ้นเมื่อจำนวนบทความแต่ละปีแกว่งมาก และรับมือปีที่ไม่มีบทความได้ เตือนเมื่อรู้สังกัดผู้เขียนน้อยเกินกว่าจะนับสถาบัน หัวข้อที่ประมาณการเติบโตไม่ได้ถือเป็น “ข้อมูลน้อย” และไม่นับปีที่ข้อมูลยังเข้าระบบไม่ครบ',
    en: 'The likely range widens when yearly counts swing a lot, and copes with years without articles. A warning shows when too few affiliations are known to count institutions. Topics whose growth cannot be estimated count as “low data”, and years still arriving are not counted.',
    tech: { th: 'ใช้ควอนไทล์ t เมื่อข้อมูลกระจายเกินแบบปัวซอง (นอกนั้นใช้แบบปกติ)', en: 'A t-quantile interval when the counts are overdispersed (normal otherwise).' },
  },
]
