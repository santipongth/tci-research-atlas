import { defineStrings } from './define'

/** Glossary words as they appear in the text (in the entry: a `Term` shows the word at once). Definitions: glossaryDefs.ts. */
export const glossary = defineStrings({
  'g.ci.term': { th: 'ช่วงเชื่อมั่น', en: 'confidence interval' },
  'g.baseline.term': { th: 'ช่วงฐาน', en: 'baseline window' },
  'g.recent.term': { th: 'ช่วงล่าสุด', en: 'recent window' },
  'g.shareGrowth.term': { th: 'สัดส่วนเพิ่ม/ลดต่อปี', en: 'change in share' },
  'g.score.term': { th: 'คะแนนสัญญาณ', en: 'signal score' },
  'g.hhi.term': { th: 'HHI', en: 'HHI' },
  'g.jaccard.term': { th: 'Jaccard', en: 'Jaccard' },
  'g.jsd.term': { th: 'Jensen–Shannon', en: 'Jensen–Shannon' },
  'g.cosine.term': { th: 'ความคล้ายแบบ cosine', en: 'cosine similarity' },
  'g.activity.term': { th: 'ดัชนีความเข้มข้น', en: 'activity index' },
  'g.metadata.term': { th: 'metadata', en: 'metadata' },
  'g.embedding.term': { th: 'embedding', en: 'embedding' },
})
