import { readdirSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const DIR = fileURLToPath(new URL('.', import.meta.url))

/** Thai stacks vowels and tone marks above and below the line: under 1.5 they collide when a heading wraps. */
const DISPLAY_HEADINGS = ['.page-h h1', '.story h1', '.story-big']
const MIN = 1.5
const MIN_DISPLAY = 1.45
/** Latin has no stacked marks: rules scoped to English (`:lang(en)`) may close headings up to 1.3. */
const MIN_EN = 1.25
const isEnglishOnly = (selector: string) => selector.split(',').every((s) => s.includes(':lang(en)'))

interface Hit {
  file: string
  selector: string
  value: number
}

function scan(): Hit[] {
  const hits: Hit[] = []
  for (const file of readdirSync(DIR).filter((f) => f.endsWith('.css'))) {
    const css = readFileSync(DIR + file, 'utf8')
    for (const m of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
      const lh = /line-height:\s*([0-9.]+)\s*[;}]?/.exec(m[2])
      if (lh) hits.push({ file, selector: m[1].trim().replace(/\s+/g, ' '), value: Number(lh[1]) })
    }
  }
  return hits
}

describe('line-height in the stylesheets', () => {
  const hits = scan()

  it('finds the declarations it is meant to guard', () => {
    expect(hits.length).toBeGreaterThan(5)
  })

  it('never goes below 1.45, and below 1.5 only for display headings (English-only rules: 1.25)', () => {
    const bad = hits.filter((h) =>
      isEnglishOnly(h.selector) ? h.value < MIN_EN : h.value < MIN_DISPLAY || (h.value < MIN && !DISPLAY_HEADINGS.some((d) => h.selector.endsWith(d))),
    )
    expect(bad.map((h) => `${h.file}: ${h.selector} { line-height: ${h.value} }`)).toEqual([])
  })
})
