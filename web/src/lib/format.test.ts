import { describe, expect, it } from 'vitest'
import { DASH, fmtCompact, fmtDate, fmtInt, fmtPct, fmtPp, fmtRatio, fmtSignedInt, fmtSignedPct, kpiDelta } from './format'
import { segmentHeadline, type Segment } from './highlight'

describe('number formatting', () => {
  it('groups integers the same way in both languages and uses the true minus', () => {
    expect(fmtInt(248310)).toBe('248,310')
    expect(fmtInt(-5)).toBe('−5')
    expect(fmtInt(null)).toBe(DASH)
    expect(fmtInt(Number.NaN)).toBe(DASH)
  })

  it('turns fractions into percentages', () => {
    expect(fmtPct(0.0123, 2)).toBe('1.23%')
    expect(fmtPct(0.742)).toBe('74.2%')
    expect(fmtPct(undefined)).toBe(DASH)
  })

  it('signs growth and never prints −0', () => {
    expect(fmtSignedPct(0.152)).toBe('+15.2%')
    expect(fmtSignedPct(-0.05)).toBe('−5.0%')
    expect(fmtSignedPct(0.00001)).toBe('±0.0%')
    expect(fmtSignedPct(1.4237, 0)).toBe('+142%')
    expect(fmtSignedInt(6140)).toBe('+6,140')
    expect(fmtSignedInt(0)).toBe('±0')
  })

  it('never renders a negative zero', () => {
    expect(fmtInt(-0.4)).toBe('0')
    expect(fmtPct(-0.00001)).toBe('0.0%')
    expect(fmtPct(-0.05)).toBe('−5.0%')
  })

  it('formats percentage points, ratios, compact ticks and dates', () => {
    expect(fmtPp(74.2 - 73.6, 'th')).toBe('+0.6 จุด')
    expect(fmtPp(-0.24, 'en')).toBe('−0.2 pp')
    expect(fmtRatio(1.84)).toBe('1.8×')
    expect(fmtCompact(12500)).toBe('13K')
    expect(fmtCompact(1500)).toBe('1.5K')
    expect(fmtCompact(950)).toBe('950')
    expect(fmtCompact(999999)).toBe('1M')
    expect(fmtCompact(999.9)).toBe('1K')
    expect(fmtCompact(9999.7)).toBe('10K')
    expect(fmtCompact(-0.2)).toBe('0')
    expect(fmtDate('2026-10-01T00:00:00+00:00', 'en')).toBe('1 October 2026')
    expect(fmtDate('2026-10-01T00:00:00+00:00', 'th')).toContain('2026')
    expect(fmtDate('not a date', 'th')).toBe('not a date')
  })

  it('describes KPI changes against the previous release', () => {
    expect(kpiDelta(248310, 242170, 'count', 'th')).toBe('+6,140 (+2.5%)')
    expect(kpiDelta(74.2, 73.6, 'pct', 'en')).toBe('+0.6 pp')
    expect(kpiDelta(10, null, 'count', 'th')).toBeNull()
  })
})

describe('segmentHeadline', () => {
  const topics = [{ id: 'T000201', th: 'AI เพื่อการศึกษา', en: 'AI in education' }]
  const kinds = (segs: Segment[], kind: Segment['kind']) => segs.filter((s) => s.kind === kind).map((s) => s.text)

  it('marks figures and links topic names, but not years or numbers inside words', () => {
    const text = 'รอบ 2026Q4 มีหัวข้อกำลังเกิดใหม่ 5 หัวข้อ และAI เพื่อการศึกษาโตเร็วที่สุด +38.0% ต่อปี'
    const segs = segmentHeadline(text, topics)
    expect(segs.map((s) => s.text).join('')).toBe(text)
    expect(kinds(segs, 'figure')).toEqual(['5', '+38.0%'])
    expect(segs.find((s) => s.kind === 'topic')).toMatchObject({ id: 'T000201', text: 'AI เพื่อการศึกษา' })
  })

  it('matches English names case-insensitively and skips COVID-19 style numbers', () => {
    const segs = segmentHeadline('ai in education grew 12% while COVID-19 papers fell −3.1% since 2020', topics)
    expect(kinds(segs, 'topic')).toEqual(['ai in education'])
    expect(kinds(segs, 'figure')).toEqual(['12%', '−3.1%'])
  })

  it('can link names without marking figures, and ignores very short names', () => {
    const segs = segmentHeadline('AI เพื่อการศึกษา 5 หัวข้อ', [...topics, { id: 'T000999', th: 'AI', en: 'AI' }], { figures: false })
    expect(kinds(segs, 'figure')).toEqual([])
    expect(kinds(segs, 'topic')).toEqual(['AI เพื่อการศึกษา'])
  })
})
