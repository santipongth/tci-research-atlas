import { describe, expect, it } from 'vitest'
import { segmentHeadline, type Segment } from './highlight'

const linked = (segs: Segment[]) => segs.filter((s) => s.kind === 'topic').map((s) => (s.kind === 'topic' ? `${s.id}:${s.text}` : ''))

describe('segmentHeadline: Thai names link on word edges only', () => {
  const rice = { id: 'T1', th: 'การปลูกข้าว', en: 'Rice growing' }
  const water = { id: 'T2', th: 'การจัดการน้ำ', en: 'Water management' }

  it('does not link a topic inside a longer compound word', () => {
    expect(linked(segmentHeadline('งานเรื่องการปลูกข้าวโพดเพิ่มขึ้น 2 เท่า', [rice]))).toEqual([])
    expect(linked(segmentHeadline('การจัดการน้ำมันรั่วไหลในทะเลเพิ่มขึ้น', [water]))).toEqual([])
  })

  it('links the topic when the sentence uses it as whole words', () => {
    const segs = segmentHeadline('งานเรื่องการปลูกข้าวเพิ่มขึ้น 2 เท่า และการจัดการน้ำคงที่', [rice, water])
    expect(linked(segs)).toEqual(['T1:การปลูกข้าว', 'T2:การจัดการน้ำ'])
    expect(segs.map((s) => s.text).join('')).toBe('งานเรื่องการปลูกข้าวเพิ่มขึ้น 2 เท่า และการจัดการน้ำคงที่')
  })
})
