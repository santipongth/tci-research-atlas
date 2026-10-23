import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { DEFINITION } from './definition'

/** Scalar values of pipeline/config.example.yaml by dotted path ("emerging.breadth.min_journals"): two-space indentation, no lists. */
export function yamlScalars(text: string): Map<string, string> {
  const out = new Map<string, string>()
  const stack: { indent: number; key: string }[] = []
  for (const raw of text.split(/\r?\n/)) {
    const m = /^( *)([A-Za-z_]\w*):\s*(.*?)\s*(?:#.*)?$/.exec(raw)
    if (!m) continue
    const indent = m[1].length
    while (stack.length && stack[stack.length - 1].indent >= indent) stack.pop()
    const path = [...stack.map((x) => x.key), m[2]].join('.')
    if (m[3] === '') stack.push({ indent, key: m[2] })
    else out.set(path, m[3])
  }
  return out
}

describe('yamlScalars', () => {
  it('reads nested scalars, drops comments and keeps sections apart', () => {
    const y = yamlScalars(['a:', '  b: 3   # note', '  c:', '    d: 0.5', 'e:', '  d: 9'].join('\n'))
    expect(y.get('a.b')).toBe('3')
    expect(y.get('a.c.d')).toBe('0.5')
    expect(y.get('e.d')).toBe('9')
    expect(y.has('a.c')).toBe(false)
  })
})

describe('DEFINITION against pipeline/config.example.yaml', () => {
  // The web prints these numbers (rule texts, bars, windows) but the manifest does not carry them: when a default in the
  // pipeline's example config changes, this fails until web/src/lib/definition.ts follows (CLAUDE.md §6).
  const yaml = yamlScalars(readFileSync(fileURLToPath(new URL('../../../pipeline/config.example.yaml', import.meta.url)), 'utf8'))
  const pairs: [keyof typeof DEFINITION, string][] = [
    ['emergingMinGrowthLo', 'emerging.emerging.min_growth_lo'],
    ['emergingMinShareRatio', 'emerging.emerging.min_share_ratio'],
    ['decliningMaxShareRatio', 'emerging.declining.max_share_ratio'],
    ['largeQuantile', 'emerging.size.large_quantile'],
    ['minArticlesRecent', 'emerging.min_articles_recent'],
    ['minJournals', 'emerging.breadth.min_journals'],
    ['minOrgs', 'emerging.breadth.min_orgs'],
    ['maxNewJournalShare', 'emerging.breadth.max_new_journal_share'],
    ['recentYears', 'emerging.recent_window'],
    ['baselineYears', 'emerging.baseline_window'],
    ['trendYears', 'emerging.trend_window'],
    ['keywordMinActiveYears', 'keywords.min_active_years'],
  ]
  it.each(pairs)('%s matches %s', (name, path) => {
    expect(yaml.has(path), `${path} not found in the example config`).toBe(true)
    expect(DEFINITION[name]).toBe(Number(yaml.get(path)))
  })

  it('keeps the size rule the portfolio quadrants assume: a quantile of the classified topics', () => {
    expect(yaml.get('emerging.size.rule')).toBe('quantile')
  })

  it('keeps the definition version the web labels it with', () => {
    expect(Number(yaml.get('emerging.definition_version'))).toBe(3)
  })
})
