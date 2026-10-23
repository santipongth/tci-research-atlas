import { expect, test } from '@playwright/test'

// ATLAS_E2E_PORT: another dev server may already own 4173 (the config reuses a running server), so a run can pick its own pair of ports
const PORT = Number(process.env.ATLAS_E2E_PORT ?? 4173)
const EXAMPLE = `http://127.0.0.1:${PORT}/`

type Rect = { left: number; right: number; top: number; bottom: number }
const overlap = (a: Rect, b: Rect) => a.left + 1 < b.right && b.left + 1 < a.right && a.top + 1 < b.bottom && b.top + 1 < a.bottom

test.describe('360 px', () => {
  test.use({ viewport: { width: 360, height: 800 } })

  for (const lang of ['th', 'en'] as const) {
    test(`topics portfolio matrix: no overlapping text or text over markers (${lang})`, async ({ page }) => {
      await page.addInitScript((l) => localStorage.setItem('atlas-lang', l), lang)
      await page.goto(`${EXAMPLE}#/topics`)
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
        return { texts, marks, svg }
      })
      const clashes: string[] = []
      found.texts.forEach((a, i) => {
        found.texts.slice(i + 1).forEach((b) => overlap(a.r, b.r) && clashes.push(`${a.s} x ${b.s}`))
        found.marks.forEach((m) => overlap(a.r, m) && clashes.push(`${a.s} x marker`))
        if (a.r.left < found.svg.left - 1 || a.r.right > found.svg.right + 1) clashes.push(`${a.s} outside the sheet`)
      })
      expect(clashes).toEqual([])
      const scroll = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
      expect(scroll).toBeLessThanOrEqual(0)
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
  })
})

test.describe('390 px atlas', () => {
  test.use({ viewport: { width: 390, height: 844 } })

  test('the sheet takes the map\'s own shape and names more than one topic', async ({ page }) => {
    await page.goto(`${EXAMPLE}#/atlas`)
    await page.evaluate(() => document.fonts.ready)
    const sheet = (await page.locator('.sheet-in').boundingBox())!
    // 1000 × 640 map plus the fit margin: no tall band of empty paper under it
    expect(sheet.height / sheet.width).toBeLessThan(0.75)
    await expect.poll(() => page.locator('.mlabel').count()).toBeGreaterThan(1)
    await expect(page.locator('.gaz .g-val').first()).toContainText('ต่อปี')
  })
})

test.describe('390 × 844 phone chrome', () => {
  test.use({ viewport: { width: 390, height: 844 } })

  test('the h1 starts high, and the menu button opens the page list in a drawer that Escape closes', async ({ page }) => {
    await page.goto(`${EXAMPLE}#/overview`)
    await page.evaluate(() => document.fonts.ready)
    const h1 = page.locator('h1').first()
    await expect(h1).toBeVisible()
    expect((await h1.boundingBox())!.y).toBeLessThan(160)
    await expect(page.locator('.pbar .phase-tag.is-sample')).toBeVisible()
    // phones skip the line chart: the ranked list beside it carries the same topics
    await expect(page.locator('.sl-series')).toHaveCount(0)

    const menu = page.getByRole('button', { name: 'เมนู', exact: true })
    const drawer = page.getByRole('dialog', { name: 'เมนูหลัก' })
    await expect(drawer).toBeHidden()
    await expect(menu).toHaveAttribute('aria-expanded', 'false')
    await menu.click()
    await expect(drawer).toBeVisible()
    await expect(drawer.getByRole('link', { name: 'วารสาร', exact: true })).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(drawer).toBeHidden()
    await expect(menu).toBeFocused()

    await menu.click()
    await drawer.getByRole('link', { name: 'วารสาร', exact: true }).click()
    await expect(page).toHaveURL(/#\/journals$/)
    await expect(drawer).toBeHidden()
    await expect(menu).toHaveAttribute('aria-expanded', 'false')
  })
})
