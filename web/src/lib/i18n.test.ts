import { describe, expect, it, vi } from 'vitest'
import type { Region, Source1, Type } from '../data/contract'
import { PARTS, STR } from '../strings'
import { atlas } from '../strings/atlas'
import { brief } from '../strings/brief'
import { changes } from '../strings/changes'
import { embed } from '../strings/embed'
import { editorViz } from '../strings/editorViz'
import { execPages } from '../strings/execPages'
import { execViz } from '../strings/execViz'
import { galaxy } from '../strings/galaxy'
import { glossaryDefs } from '../strings/glossaryDefs'
import { journals } from '../strings/journals'
import { keywords } from '../strings/keywords'
import { match } from '../strings/match'
import { methods } from '../strings/methods'
import { openViz } from '../strings/openViz'
import { province } from '../strings/province'
import { ideas } from '../strings/ideas'
import { story } from '../strings/story'
import { references } from '../strings/references'
import { search } from '../strings/search'
import { topicExtra } from '../strings/topicExtra'
import { yearSpan } from './format'
import { fillVars, missingKey, translate } from './i18n'
import { INST_TYPE_FILTERS } from './urlState'

const placeholders = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()
/** Strings files of lazy pages: not in STR (entry budget), read with useStrings. */
const LAZY = {
  search, galaxy, keywords, references, topicExtra, embed, glossaryDefs, execViz, editorViz, openViz, province, ideas, story,
  execPages, journals, atlas, brief, changes, match, methods,
} as const
const ALL = { ...STR, ...Object.fromEntries(Object.entries(LAZY).flatMap(([file, d]) => Object.entries(d).map(([k, e]) => [`${file}:${k}`, e]))) }

/** Every value of a contract enum, checked against the union at compile time (a new pipeline value fails tsc here). */
function every<T extends string>() {
  return <const A extends readonly T[]>(values: A & ([T] extends [A[number]] ? unknown : never)) => values
}
const INST_TYPES = every<Type>()(['university', 'rajabhat', 'rajamangala', 'hospital', 'government', 'research', 'company', 'other'])
const INST_SOURCES = every<Source1>()(['alias', 'ror', 'name'])
const REGIONS = every<Region>()(['bangkok', 'central', 'northeast', 'north', 'south'])
/** pipeline atlas/config.py COMPLETENESS_COMPONENTS (CompletenessItem.key is a plain string in the contract) */
const COMPLETENESS = ['abstract_en', 'title_en', 'keywords_en', 'doi', 'references', 'refs_romanized', 'affiliations']
/** pipeline atlas/diff.py KPI_KEYS (KpiChange.key on /changes) */
const DIFF_KPIS = ['articles', 'assigned_articles', 'topics', 'journals', 'institutions']

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
    for (const [key, e] of Object.entries(ALL)) {
      expect(/<\/?(i|em)\b/.test(e.th), key).toBe(false)
      expect(/[฀-๿]/.test(e.en), `${key} en contains Thai`).toBe(false)
    }
  })

  it('every enum value the UI turns into a key has a string in both languages', () => {
    const want: [Record<string, unknown>, string][] = [
      ...[...INST_TYPES, ...INST_TYPE_FILTERS].map((v): [Record<string, unknown>, string] => [execPages, `in.type.${v}`]),
      ...INST_SOURCES.map((v): [Record<string, unknown>, string] => [execPages, `in.source.${v}`]),
      ...REGIONS.map((v): [Record<string, unknown>, string] => [execPages, `rg.region.${v}`]),
      ...COMPLETENESS.map((v): [Record<string, unknown>, string] => [journals, `comp.${v}`]),
      ...DIFF_KPIS.map((v): [Record<string, unknown>, string] => [STR, `kpi.${v}`]),
    ]
    for (const [dict, key] of want) expect(dict[key], key).toBeDefined()
  })

  it('a key the dictionary does not know shows its last segment (or a dash), never the raw key', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    expect(translate('th', 'in.type.foundation' as never)).toBe('foundation')
    expect(missingKey('in.source.undefined')).toBe('–')
    expect(missingKey('in.source.')).toBe('–')
    expect(warn).toHaveBeenCalled()
    warn.mockRestore()
  })

  it('keeps a year range from the dictionary or from code on one line (en dash + word joiner)', () => {
    expect(fillVars('ปี {a}–{b}', { a: 2022, b: 2024 })).toBe('ปี 2022–⁠2024')
    expect(yearSpan(2017, 2021)).toBe('2017–⁠2021')
    expect(yearSpan(2017, 2021).replace('⁠', '')).toBe('2017–2021')
  })

  it('fills placeholders and leaves unknown ones visible', () => {
    expect(translate('en', 'topicsN', { n: 3 })).toBe('3 topics')
    expect(translate('th', 'topicsN', { n: 1200 })).toBe('1200 หัวข้อ')
    expect(translate('th', 'topicsN', {})).toBe('{n} หัวข้อ')
  })
})
