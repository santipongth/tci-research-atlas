import { describe, expect, it } from 'vitest'
import { bundleOf } from '../../test/fixtureData'
import { toCsv } from '../lib/csv'
import { translate } from '../lib/i18n'
import type { Lang } from '../lib/i18n'
import { tableCsvColumns } from '../lib/tableCsv'
import type { Topic } from '../data/types'
import { articlesColumn, ciColumn, ciHighColumn, growthColumn, idColumn, journalsColumn, orgsColumn, ratioColumn, scoreColumn, shareColumn, statusColumn, topicColumn, type ColumnContext } from './topicColumns'

const topics = (bundleOf('example').files['topics.json'] as { topics: Topic[] }).topics

const ctxFor = (lang: Lang): ColumnContext => ({
  t: ((k, v) => translate(lang, k, v)) as ColumnContext['t'],
  name: ((tp: Topic) => (lang === 'en' ? tp.en || tp.th : tp.th)) as ColumnContext['name'],
  groupName: (g) => g,
  base: '2016–2020',
  recent: '2021–2023',
})

/** The exact column set of the /emerging table for a signal status. */
const emergingColumns = (lang: Lang) => {
  const ctx = ctxFor(lang)
  return [idColumn(), topicColumn(ctx), shareColumn(ctx), growthColumn(ctx), ciColumn(ctx), ciHighColumn(), ratioColumn(ctx), journalsColumn(ctx), orgsColumn(ctx), scoreColumn(ctx)]
}

describe('emerging table CSV', () => {
  const rows = topics.filter((tp) => tp.status === 'EMERGING')
  const csv = (lang: Lang) => toCsv(rows, tableCsvColumns(emergingColumns(lang)))

  it('uses the contract field names as headers, whatever the UI language', () => {
    const header = csv('th').replace('﻿', '').split('\r\n')[0]
    expect(header).toBe('topic_id,name_th,name_en,share_recent,share_growth,share_growth_lo,share_growth_hi,share_ratio,no_baseline,n_journals_R,n_orgs_R,orgs_unverified,score')
  })

  it('never puts the lower bound under a "CI" header', () => {
    expect(csv('en')).not.toMatch(/CI|ช่วงเชื่อมั่น/)
    expect(csv('en')).toContain('share_growth_lo')
  })

  it('is byte-identical in Thai and English and keeps raw fractions', () => {
    expect(csv('en')).toBe(csv('th'))
    const first = csv('th').split('\r\n')[1].split(',')
    expect(Number(first[4])).toBe(rows[0].metrics.share_growth)
    expect(first[4]).not.toContain('%')
  })

  it('exports the other topic columns under contract names too', () => {
    const ctx = ctxFor('en')
    const cols = tableCsvColumns([idColumn(), topicColumn(ctx), statusColumn(ctx), articlesColumn(ctx)])
    expect(cols.map((c) => c.header)).toEqual(['topic_id', 'name_th', 'name_en', 'status', 'count_recent'])
  })
})
