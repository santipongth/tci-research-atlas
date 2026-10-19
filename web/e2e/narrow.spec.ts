import { expect, test } from '@playwright/test'

const EXAMPLE = 'http://127.0.0.1:4173/'

type Rect = { left: number; right: number; top: number; bottom: number }
const overlap = (a: Rect, b: Rect) => a.left + 1 < b.right && b.left + 1 < a.right && a.top + 1 < b.bottom && b.top + 1 < a.bottom

test.describe('360 px', () => {
  test.use({ viewport: { width: 360, height: 800 } })

  for (const lang of ['th', 'en'] as const) {
    test(`overview portfolio matrix: no overlapping text or text over markers (${lang})`, async ({ page }) => {
      await page.addInitScript((l) => localStorage.setItem('atlas-lang', l), lang)
      await page.goto(`${EXAMPLE}#/overview`)
      await page.evaluate(() => document.fonts.ready)
      const pf = page.locator('svg.pf')
      await pf.scrollIntoViewIfNeeded()
      await expect(pf).toBeVisible()
      const found = await page.evaluate(() => {
        const box = (e: Element) => {
          const r = e.getBoundingClientRect()
          return { left: r.left, right: r.right, top: r.top, bottom: r.bottom }
        }
        const texts = [...document.querySelectorAll('svg.pf text')].map((e) => ({ s: e.textContent ?? '', r: box(e) }))
        const marks = [...document.querySelectorAll('svg.pf .pf-node .mk')].map((e) => box(e))
        const svg = box(document.querySelector('svg.pf') as Element)
        return { texts, marks, svg, legend: document.querySelectorAll('.pf-quads li').length }
      })
      expect(found.legend).toBe(4)
      const clashes: string[] = []
      found.texts.forEach((a, i) => {
        found.texts.slice(i + 1).forEach((b) => overlap(a.r, b.r) && clashes.push(`${a.s} x ${b.s}`))
        found.marks.forEach((m) => overlap(a.r, m) && clashes.push(`${a.s} x marker`))
        if (a.r.left < found.svg.left - 1 || a.r.right > found.svg.right + 1) clashes.push(`${a.s} outside the sheet`)
      })
      expect(clashes).toEqual([])
      const scroll = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
      expect(scroll).toBeLessThanOrEqual(0)
      await pf.screenshot({ path: `test-results/pf-360-${lang}.png` })
    })
  }
})
