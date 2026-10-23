import { describe, expect, it } from 'vitest'
import { fitText } from './measure'

/** 10 px per grapheme cluster: a Thai consonant with its marks counts once */
const seg = new Intl.Segmenter('th', { granularity: 'grapheme' })
const measure = (s: string) => [...seg.segment(s)].length * 10

describe('fitText', () => {
  it('keeps a label that fits', () => {
    expect(fitText('การปลูกข้าว', 200, 16, 600, measure)).toBe('การปลูกข้าว')
  })

  it('cuts a long Thai name after a whole word and adds an ellipsis within the width', () => {
    const name = 'การพัฒนาหลักสูตรการเรียนการสอนภาษาอังกฤษสำหรับนักเรียนมัธยมศึกษาตอนปลายในภาคตะวันออกเฉียงเหนือ'
    const out = fitText(name, 160, 16, 600, measure)
    expect(out.endsWith('…')).toBe(true)
    expect(measure(out)).toBeLessThanOrEqual(160)
    const kept = out.slice(0, -1)
    expect(name.startsWith(kept)).toBe(true)
    // the cut is on a word edge of the full name
    const edges = new Set([...new Intl.Segmenter('th', { granularity: 'word' }).segment(name)].map((s) => s.index))
    expect(edges.has(kept.length)).toBe(true)
  })

  it('falls back to whole graphemes when the first word is wider than the room', () => {
    const out = fitText('ประชาธิปไตย', 45, 16, 600, measure)
    expect(out.endsWith('…')).toBe(true)
    expect(measure(out)).toBeLessThanOrEqual(45)
    const kept = [...seg.segment(out.slice(0, -1))].map((g) => g.segment)
    const whole = [...seg.segment('ประชาธิปไตย')].map((g) => g.segment)
    expect(kept).toEqual(whole.slice(0, kept.length))
  })
})
