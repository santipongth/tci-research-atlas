import { describe, expect, it } from 'vitest'
import { translate } from '../lib/i18n'
import { STR } from './index'

describe('strings that state a definition threshold', () => {
  it('take the large-topic share and the keyword persistence from DEFINITION, never a literal', () => {
    for (const key of ['rule.HOT', 'ov.pf.how'] as const) {
      expect(STR[key].th, key).toContain('{top}')
      expect(STR[key].en, key).toContain('{top}')
      expect(`${STR[key].th} ${STR[key].en}`, key).not.toMatch(/25\s?%/)
    }
    expect(STR['em.kw.intro'].th).toContain('{ky}')
    expect(STR['em.kw.intro'].en).toContain('{ky}')
    expect(STR['em.kw.intro'].th).not.toContain('3 ปี')
    expect(STR['em.kw.intro'].en).not.toContain('3 years')
  })

  it('names the non-growing small-topic quadrant without claiming every topic in it shrinks', () => {
    expect(translate('th', 'quad.declining')).toBe('ไม่โต/หด')
    expect(translate('th', 'quad.declining.hint')).toContain('ไม่โต')
    expect(translate('en', 'quad.declining')).toBe('Flat or shrinking')
  })

describe('about.def.intro', () => {
  it('states the real checking order: LOW_DATA first, then EMERGING, WATCH, HOT, DECLINING, STABLE', () => {
    for (const lang of ['th', 'en'] as const) {
      const text = STR['about.def.intro'][lang]
      const order = ['LOW_DATA', 'EMERGING', 'WATCH', 'HOT', 'DECLINING', 'STABLE'].map((k) => text.indexOf(k))
      expect(order.every((n) => n >= 0), lang).toBe(true)
      expect([...order].sort((a, b) => a - b), lang).toEqual(order)
    }
  })
})
})
