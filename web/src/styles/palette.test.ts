import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { contrastRatio, deltaE } from '../lib/color'

const css = readFileSync(new URL('./tokens.css', import.meta.url), 'utf8')

function block(selector: string): Record<string, string> {
  const start = css.indexOf(`${selector} {`)
  if (start < 0) throw new Error(`tokens.css has no "${selector} {" block`)
  const end = css.indexOf('}', start)
  const vars: Record<string, string> = {}
  for (const m of css.slice(start, end).matchAll(/--([\w-]+):\s*([^;]+);/g)) vars[m[1]] = m[2].trim()
  return vars
}

const light = block(':root')
const SIGNAL = ['EMERGING', 'WATCH', 'HOT', 'DECLINING'] as const
const ALL = [...SIGNAL, 'STABLE', 'LOW_DATA'] as const
const isHex = (v: string) => /^#[0-9a-f]{6}$/i.test(v)
const allPairs = <T,>(xs: readonly T[]) => xs.flatMap((a, i) => xs.slice(i + 1).map((b) => [a, b] as const))

describe('design tokens', () => {
  it('there is one light theme only (no dark blocks)', () => {
    expect(css).not.toMatch(/data-theme|prefers-color-scheme/)
  })

  for (const [name, t] of Object.entries({ light })) {
    describe(`${name} theme`, () => {
      it('status colours stay apart for every pair (CVD ≥ 8, normal vision ≥ 15)', () => {
        for (const [a, b] of allPairs(SIGNAL)) {
          const ca = t[`st-${a}`]
          const cb = t[`st-${b}`]
          const cvd = Math.min(deltaE(ca, cb, 'protan'), deltaE(ca, cb, 'deutan'))
          expect(cvd, `${a}/${b} CVD`).toBeGreaterThanOrEqual(8)
          expect(deltaE(ca, cb), `${a}/${b} normal`).toBeGreaterThanOrEqual(15)
        }
      })

      it('compare series colours stay apart as adjacent pairs (CVD ≥ 8, normal vision ≥ 15)', () => {
        for (let i = 1; i < 4; i++) {
          const ca = t[`series-${i}`]
          const cb = t[`series-${i + 1}`]
          expect(Math.min(deltaE(ca, cb, 'protan'), deltaE(ca, cb, 'deutan')), `series ${i}/${i + 1}`).toBeGreaterThanOrEqual(8)
          expect(deltaE(ca, cb), `series ${i}/${i + 1} normal`).toBeGreaterThanOrEqual(15)
        }
      })

      it('status marks reach 3:1 on the page and on the map sheet', () => {
        for (const st of [...SIGNAL, 'STABLE']) {
          expect(contrastRatio(t[`st-${st}`], t.bg), `${st} on bg`).toBeGreaterThanOrEqual(3)
          expect(contrastRatio(t[`st-${st}`], t['map-sheet']), `${st} on map`).toBeGreaterThanOrEqual(3)
        }
      })

      it('status tags and text reach 4.5:1', () => {
        for (const st of ALL) {
          expect(contrastRatio(t[`tag-${st}-ink`], t[`tag-${st}-bg`]), `tag ${st}`).toBeGreaterThanOrEqual(4.5)
        }
        const textPairs: [string, string][] = [
          ['ink', 'bg'], ['ink', 'surface'], ['ink-2', 'bg'], ['ink-2', 'surface'], ['link', 'bg'], ['link', 'surface'],
          ['brand-ink', 'brand'], ['brand-ink-2', 'brand'], ['btn-ink', 'btn'], ['up', 'bg'], ['ink-2', 'map-sheet'],
          ['brand', 'bg'], ['brand', 'brand-soft'], ['accent-ink', 'bg'], ['ink-3', 'bg'], ['tag-sample-ink', 'tag-sample-bg'],
        ]
        for (const [fg, bg] of textPairs) {
          expect(isHex(t[fg]) && isHex(t[bg]), `${fg}/${bg} are hex`).toBe(true)
          expect(contrastRatio(t[fg], t[bg]), `${fg} on ${bg}`).toBeGreaterThanOrEqual(4.5)
        }
      })

      it('form-field borders, the focus ring and the highlight mark reach 3:1', () => {
        expect(contrastRatio(t['field-border'], t.bg)).toBeGreaterThanOrEqual(3)
        expect(contrastRatio(t.focus, t.bg)).toBeGreaterThanOrEqual(3)
        expect(contrastRatio(t['accent-mark'], t.bg)).toBeGreaterThanOrEqual(3)
        expect(contrastRatio(t.context, t.bg)).toBeLessThan(3)          // context lines stay quiet: they never carry the answer
      })
    })
  }
})
