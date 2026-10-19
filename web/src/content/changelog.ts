/** Changes to the status definition (docs/EMERGING_SPEC.md). /about shows entries up to the release's definition_version. */
export interface ChangelogEntry {
  version: number
  date: string
  th: string
  en: string
}

export const CHANGELOG: readonly ChangelogEntry[] = [
  {
    version: 2,
    date: '2026-10-18',
    th: 'อัตราโตของสัดส่วนประมาณด้วย Poisson GLM พร้อมช่วงเชื่อมั่น 90% เกณฑ์หัวข้อใหญ่แบบสัมพัทธ์ (25% บนสุด) เกณฑ์ความกว้าง 3 วารสารและ 3 สถาบัน และสถานะใหม่ “จับตา” กับ “ข้อมูลน้อย”',
    en: 'Share growth from a Poisson GLM with a 90% confidence interval, a relative “large” threshold (top 25%), a breadth test of 3 journals and 3 institutions, and the new “watch” and “low data” statuses.',
  },
  {
    version: 3,
    date: '2026-10-18',
    th: 'ช่วงเชื่อมั่นแบบ t ที่ทนต่อปีที่ไม่มีบทความ ธงเมื่อข้อมูลสังกัดไม่พอตรวจความกว้างของสถาบัน หัวข้อที่ประมาณอัตราโตไม่ได้ถือเป็น “ข้อมูลน้อย” และไม่นับปีที่ข้อมูลยังเข้าไม่ครบ',
    en: 'A t-based interval that copes with years without articles, a flag when affiliations are too sparse to check institution breadth, topics whose growth cannot be estimated count as “low data”, and incomplete years are not counted.',
  },
]
