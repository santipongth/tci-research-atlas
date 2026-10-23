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

  test('atlas: zoom buttons sit below the sheet and the key lists every field with a swatch', async ({ page }) => {
    await page.goto(`${EXAMPLE}#/atlas`)
    await page.evaluate(() => document.fonts.ready)
    const zoom = page.locator('.zoom')
    await expect(zoom).toBeVisible()
    const [z, sheet] = await Promise.all([zoom.boundingBox(), page.locator('.sheet-in').boundingBox()])
    expect(z && sheet && z.y >= sheet.y + sheet.height - 1).toBe(true)
    expect(await page.locator('.fieldkey li .swatch').count()).toBeGreaterThanOrEqual(2)
    await page.locator('.sheet').screenshot({ path: 'test-results/atlas-360.png' })
  })
})

test.describe('390 × 844 phone chrome', () => {
  test.use({ viewport: { width: 390, height: 844 } })

  test('the overview h1 starts high, and one menu button opens and closes the whole navigation', async ({ page }) => {
    await page.goto(`${EXAMPLE}#/overview`)
    await page.evaluate(() => document.fonts.ready)
    const h1 = page.locator('h1').first()
    await expect(h1).toBeVisible()
    expect((await h1.boundingBox())!.y).toBeLessThan(300)
    await expect(page.locator('.phase-tag.is-sample')).toBeVisible()
    await expect(page.locator('.toc-d')).not.toHaveAttribute('open')

    const nav = page.locator('#site-nav')
    const menu = page.getByRole('button', { name: 'เมนู', exact: true })
    await expect(nav).toBeHidden()
    await expect(menu).toHaveAttribute('aria-expanded', 'false')
    await expect(menu).toHaveAttribute('aria-controls', 'site-nav')
    await menu.click()
    await expect(menu).toHaveAttribute('aria-expanded', 'true')
    await expect(nav.getByRole('combobox', { name: 'ค้นหาหัวข้อวิจัย' })).toBeVisible()
    await expect(nav.getByRole('link', { name: 'วารสาร', exact: true })).toBeVisible()
    await expect(nav.getByRole('button', { name: 'English' })).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(menu).toHaveAttribute('aria-expanded', 'false')
    await expect(menu).toBeFocused()
    await expect(nav).toBeHidden()

    await menu.click()
    await nav.getByRole('link', { name: 'วารสาร', exact: true }).click()
    await expect(page).toHaveURL(/#\/journals$/)
    await expect(nav).toBeHidden()
    await expect(menu).toHaveAttribute('aria-expanded', 'false')
  })
})
