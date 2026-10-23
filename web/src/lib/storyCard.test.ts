import { describe, expect, it } from 'vitest'
import { wrapLines } from './storyCard'

const measure = (s: string) => s.length * 10
const words = (s: string) => s.split(/(?<= )/)

describe('wrapLines', () => {
  it('fills each line up to the width and breaks between segments', () => {
    expect(wrapLines('aaa bbb ccc ddd', 75, measure, words)).toEqual(['aaa bbb', 'ccc ddd'])
  })
  it('gives a segment wider than the line a line of its own', () => {
    expect(wrapLines('aa bbbbbbbbbbbb cc', 50, measure, words)).toEqual(['aa', 'bbbbbbbbbbbb', 'cc'])
  })
  it('works on unspaced Thai when the segmenter splits words', () => {
    const seg = () => ['งาน', 'วิจัย', 'ไทย', 'กำลัง', 'โต']
    expect(wrapLines('งานวิจัยไทยกำลังโต', 80, measure, seg)).toEqual(['งานวิจัย', 'ไทยกำลัง', 'โต'])
    expect(wrapLines('', 80, measure, () => [])).toEqual([])
  })
})
