import { describe, expect, it } from 'vitest'
import { PARTS, STR } from '../strings'
import { galaxy } from '../strings/galaxy'
import { keywords } from '../strings/keywords'
import { references } from '../strings/references'
import { search } from '../strings/search'
import { topicExtra } from '../strings/topicExtra'
import { translate } from './i18n'

const placeholders = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()
/** Strings files of lazy pages: not in STR (entry budget), read with useStrings. */
const LAZY = { search, galaxy, keywords, references, topicExtra } as const
const ALL = { ...STR, ...Object.fromEntries(Object.entries(LAZY).flatMap(([file, d]) => Object.entries(d).map(([k, e]) => [`${file}:${k}`, e]))) }

describe('i18n strings', () => {
  it('every key has Thai and English text with the same placeholders', () => {
    for (const [key, e] of Object.entries(ALL)) {
      expect(e.th.trim(), `${key} th`).not.toBe('')
      expect(e.en.trim(), `${key} en`).not.toBe('')
      expect(placeholders(e.th), key).toEqual(placeholders(e.en))
    }
  })

  it('no key is defined in two string files', () => {
    const total = Object.values(PARTS).reduce((n, part) => n + Object.keys(part).length, 0)
    expect(total).toBe(Object.keys(STR).length)
  })

  it('no italics markup in Thai and no Thai script in English', () => {
    for (const [key, e] of Object.entries(STR)) {
      expect(/<\/?(i|em)\b/.test(e.th), key).toBe(false)
      expect(/[฀-๿]/.test(e.en), `${key} en contains Thai`).toBe(false)
    }
  })

  it('fills placeholders and leaves unknown ones visible', () => {
    expect(translate('en', 'topicsN', { n: 3 })).toBe('3 topics')
    expect(translate('th', 'topicsN', { n: 1200 })).toBe('1200 หัวข้อ')
    expect(translate('th', 'topicsN', {})).toBe('{n} หัวข้อ')
  })
})
