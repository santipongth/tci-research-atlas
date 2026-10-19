import { describe, expect, it } from 'vitest'
import type { Topic } from '../data/types'
import { translate } from './i18n'
import { breadthReasons, breadthText } from './breadth'

const topic = (m: Record<string, unknown>) => ({ id: 'T1', status: 'WATCH', metrics: { n_journals_R: 5, n_orgs_R: 5, new_journal_share: 0.1, orgs_unverified: false, ...m } }) as unknown as Topic
const tr = (lang: 'th' | 'en') => (k: never, v?: never) => translate(lang, k, v)

describe('breadthReasons', () => {
  it('lists only the failed tests, against DEFINITION', () => {
    expect(breadthReasons(topic({ n_journals_R: 2 }))).toEqual([{ kind: 'journals', n: 2, min: 3 }])
    expect(breadthReasons(topic({ n_orgs_R: 1, new_journal_share: 0.6 }))).toEqual([
      { kind: 'orgs', n: 1, min: 3 },
      { kind: 'newShare', share: 0.6, max: 0.5 },
    ])
  })
  it('a new-journal share of exactly 50% fails (the test is < 50%)', () => {
    expect(breadthReasons(topic({ new_journal_share: 0.5 }))).toHaveLength(1)
  })
  it('skips the institution test when institutions are unverified', () => {
    expect(breadthReasons(topic({ n_orgs_R: 0, orgs_unverified: true }))).toEqual([])
  })
  it('says it in both languages with the numbers', () => {
    const t = topic({ n_journals_R: 2, new_journal_share: 0.62 })
    expect(breadthText(tr('th') as never, t)).toBe('มาจาก 2 วารสาร (เกณฑ์ ≥ 3) · 62% ของบทความล่าสุดมาจากวารสารที่เพิ่งเข้าระบบ (เกณฑ์ < 50%)')
    expect(breadthText(tr('en') as never, t)).toContain('From 2 journals (needs ≥ 3)')
  })
  it('falls back to a generic sentence when no test shows as failed', () => {
    expect(breadthText(tr('en') as never, topic({}))).toContain('Did not pass the breadth test')
  })
})
