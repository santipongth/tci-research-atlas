import { describe, expect, it } from 'vitest'
import { bundleOf } from '../../test/fixtureData'
import type { InstitutionsFile } from '../data/types'
import { bucketOf, filterInstitutions, instName, otherInstName, quantileBreaks } from './executive'

const file = bundleOf('example').files['institutions.json'] as InstitutionsFile
const byId = new Map(file.institutions.map((i) => [i.id, i]))

describe('executive helpers', () => {
  it('names an institution in the UI language, else in the other language with its lang', () => {
    expect(instName(byId.get('o1a2b3c4d5e')!, 'en')).toEqual({ text: 'โรงพยาบาลตัวอย่าง', lang: 'th', fallback: false })
    expect(instName(byId.get('mu-a')!, 'en')).toEqual({ text: 'Example University A', lang: null, fallback: false })
    expect(otherInstName(byId.get('mu-a')!, 'th')).toBe('Example University A')
  })

  it('filters by folded name and by type', () => {
    expect(filterInstitutions(file.institutions, 'ราชภัฏ', 'all').map((i) => i.id)).toEqual(['rbu-x'])
    expect(filterInstitutions(file.institutions, '', 'rajamangala').map((i) => i.id)).toEqual(['rmu-y'])
    expect(filterInstitutions(file.institutions, 'EXAMPLE UNIVERSITY', 'university').map((i) => i.id)).toEqual(['mu-a', 'mu-b'])
  })

  it('splits values into quantile classes and keeps no data apart', () => {
    const breaks = quantileBreaks([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    expect(breaks).toEqual([2, 4, 6, 8, 10])
    expect([1, 3, 10, 11].map((v) => bucketOf(v, breaks))).toEqual([0, 1, 4, 4])
    expect(bucketOf(null, breaks)).toBe(-1)
    expect(quantileBreaks([5, 5, 5])).toEqual([5])
  })
})
