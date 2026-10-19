import { describe, expect, it } from 'vitest'
import { bundleOf } from '../../test/fixtureData'
import type { JournalsFile } from '../data/types'
import { filterJournals, inhouseFlag, inhouseGap, journalName, otherJournalName } from './journals'

const file = bundleOf('example').files['journals.json'] as JournalsFile
const byId = new Map(file.journals.map((j) => [j.id, j]))

describe('journal helpers', () => {
  it('names a journal by its registry name, the other language, or its OJS path', () => {
    expect(journalName(byId.get('so02.example0')!, 'th')).toEqual({ text: 'วารสารวิชาการตัวอย่าง ก', lang: null, isPath: false })
    expect(journalName(byId.get('so02.example0')!, 'en')).toEqual({ text: 'วารสารวิชาการตัวอย่าง ก', lang: 'th', isPath: false })
    expect(journalName(byId.get('so02.example3')!, 'th').lang).toBe('en')
    expect(journalName(byId.get('so02.example2')!, 'th')).toEqual({ text: 'example2', lang: null, isPath: true })
    expect(otherJournalName({ name_th: 'ก', name_en: 'A', path: 'x' }, 'th')).toBe('A')
    expect(otherJournalName({ name_th: 'ก', name_en: '', path: 'x' }, 'th')).toBe('')
  })

  it('flags in-house shares above the published threshold only', () => {
    expect(inhouseFlag({ inhouse_share: 0.81 }, 0.6)).toBe(true)
    expect(inhouseFlag({ inhouse_share: 0.42 }, 0.6)).toBe(false)
    expect(inhouseFlag({ inhouse_share: 0.81 }, null)).toBe(false)
    expect(inhouseFlag({ inhouse_share: null }, 0.6)).toBe(false)
  })

  it('filters by folded text and tier', () => {
    expect(filterJournals(file.journals, 'วารสารวิชาการตัวอยาง', 'all').map((j) => j.id)).toEqual(['so02.example0', 'so02.example1'])
    expect(filterJournals(file.journals, 'EXAMPLE2', 'all').map((j) => j.id)).toEqual(['so02.example2'])
    expect(filterJournals(file.journals, '', '1').map((j) => j.id)).toEqual(['so02.example0', 'so02.example3'])
    expect(filterJournals(file.journals, '', 'none').every((j) => j.tci_tier == null)).toBe(true)
  })
})

describe('journal gaps', () => {
  it('marks only registry owners and names why a share is empty', () => {
    expect(inhouseFlag({ inhouse_share: 0.81, owner_source: 'inferred' }, 0.6)).toBe(false)
    expect(inhouseFlag({ inhouse_share: 0.81, owner_source: 'registry' }, 0.6)).toBe(true)
    expect(inhouseGap({ low_data: true, owner: '', owner_matched: false, inhouse_share: null })).toBe('low_data')
    expect(inhouseGap({ low_data: false, owner: 'X', owner_matched: false, inhouse_share: null })).toBe('owner_not_found')
    expect(inhouseGap({ low_data: false, owner: '', owner_matched: false, inhouse_share: null })).toBe('unknown')
  })
})
