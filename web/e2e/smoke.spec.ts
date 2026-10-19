import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

const EXAMPLE = 'http://127.0.0.1:4173/'
const EMPTY = 'http://127.0.0.1:4174/'

const ROUTES = [
  { name: 'overview', path: '/overview' },
  { name: 'atlas', path: '/atlas' },
  { name: 'topic', path: '/topics/T000201' },
  { name: 'emerging', path: '/emerging' },
  { name: 'compare', path: '/compare?ids=T000201,T000701' },
  { name: 'data', path: '/data' },
  { name: 'about', path: '/about' },
  { name: 'brief', path: '/brief' },
] as const

type RouteName = (typeof ROUTES)[number]['name']
type Check = (page: Page) => Promise<void>

/** Page-specific checks against the example release; each page task adds one line between the markers. */
const CHECKS: Partial<Record<RouteName, Check>> = {
  // checks:start
  overview: async (page) => {
    await expect(page.locator('.headline mark').first()).toBeVisible()
    await expect(page.getByRole('link', { name: /โมเดลภาษาขนาดใหญ่/ }).first()).toBeVisible()
    await expect(page.locator('.kpi')).toHaveCount(6)
    await expect(page.locator('.kpi .d').first()).toContainText('2026Q3')
    await expect(page.locator('.fr-row').first()).toBeVisible()
    await page.getByRole('tab', { name: 'ตาราง' }).first().click()
    await expect(page.getByRole('table').first()).toBeVisible()
    await expect(page).toHaveURL(/st=table/)
  },
  emerging: async (page) => {
    await expect(page.getByRole('tab', { name: /กำลังเกิดใหม่/ })).toHaveAttribute('aria-selected', 'true')
    await page.getByRole('tab', { name: /จับตา/ }).click()
    await expect(page).toHaveURL(/status=WATCH/)
    await expect(page.locator('#em-status-panel .inset')).toBeVisible()
    await page.locator('#em-status-panel').getByRole('button', { name: 'วารสาร' }).first().click()
    await expect(page.locator('#em-status-panel th[aria-sort="descending"]')).toContainText('วารสาร')
    await expect(page).toHaveURL(/sort=journals/)
    await expect(page.locator('#em-status-panel').getByRole('button', { name: 'ดาวน์โหลด CSV' })).toBeVisible()
    await expect(page.locator('#keywords')).toContainText('chatgpt')
  },
  topic: async (page) => {
    await expect(page.locator('h1')).toHaveText('AI เพื่อการศึกษา')
    await expect(page.locator('.summary')).toContainText('%')
    await expect(page.locator('svg.tr')).toBeVisible()
    await expect(page.getByRole('link', { name: /AI เพื่อการศึกษา: กรณีศึกษาที่ 1/ })).toHaveAttribute('href', /tci-thaijo\.org/)
    await expect(page.locator('#related')).toBeVisible()
    await page.goto(`${EXAMPLE}#/topics/T000701`)
    await expect(page.locator('.uncertain')).toContainText('แนวโน้มไม่แน่นอน')
    await expect(page.locator('.summary')).toContainText('ใหม่ — ไม่มีในช่วงฐาน')
    await page.goto(`${EXAMPLE}#/topics/T123456`)
    await expect(page.locator('h1')).toContainText('T123456')
  },
  // checks:end
}

/** Routes that must not scroll sideways at 360 px. */
const PHONE = ['/overview', '/emerging', '/topics/T000201', '/atlas', '/compare?ids=T000201,T000701', '/data', '/about']

function collectErrors(page: Page): string[] {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`))
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(`console: ${m.text()}`)
  })
  return errors
}

async function seriousA11yViolations(page: Page): Promise<string[]> {
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze()
  return result.violations
    .filter((v) => v.impact === 'serious' || v.impact === 'critical')
    .map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(' | ')}`)
}

for (const route of ROUTES) {
  test(`${route.name}: example release renders in light and dark without serious a11y issues`, async ({ page }) => {
    const errors = collectErrors(page)
    await page.goto(`${EXAMPLE}#${route.path}`)
    await expect(page.locator('h1').first()).toBeVisible()
    await CHECKS[route.name]?.(page)
    expect(await seriousA11yViolations(page)).toEqual([])
    await page.emulateMedia({ colorScheme: 'dark' })
    expect(await seriousA11yViolations(page)).toEqual([])
    expect(errors).toEqual([])
  })

  test(`${route.name}: an empty release renders without errors`, async ({ page }) => {
    const errors = collectErrors(page)
    await page.goto(`${EMPTY}#${route.path}`)
    await expect(page.locator('h1').first()).toBeVisible()
    await expect(page.getByRole('alert')).toHaveCount(0)
    expect(errors).toEqual([])
  })
}

test('a missing data release shows a banner, not a white page', async ({ page }) => {
  await page.route('**/data/latest.json', (r) => r.fulfill({ status: 404, body: 'not found' }))
  await page.goto(`${EXAMPLE}#/overview`)
  await expect(page.getByRole('alert')).toContainText('latest.json')
  await expect(page.locator('h1').first()).toBeVisible()
})

test('a sample release is labelled as sample data', async ({ page }) => {
  await page.goto(`${EXAMPLE}#/overview`)
  await expect(page.locator('.phase-tag.is-sample')).toBeVisible()
})

test('pages do not scroll sideways on a 360 px phone', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 780 })
  for (const path of PHONE) {
    await page.goto(`${EXAMPLE}#${path}`)
    await expect(page.locator('h1').first()).toBeVisible()
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow, path).toBeLessThanOrEqual(0)
  }
})

test('the header search finds a Thai topic typed without tone marks and opens it with the keyboard', async ({ page }) => {
  await page.goto(`${EXAMPLE}#/overview`)
  const box = page.getByRole('combobox', { name: 'ค้นหาหัวข้อวิจัย' })
  await box.fill('ผูสูงอายุ')
  await expect(page.getByRole('option').first()).toContainText('การดูแลผู้สูงอายุในชุมชน')
  await box.press('Enter')
  await expect(page).toHaveURL(/#\/topics\/T000101$/)
})

test('the printable brief shows the data banner when the release cannot load', async ({ page }) => {
  await page.route('**/data/latest.json', (r) => r.fulfill({ status: 404, body: 'not found' }))
  await page.goto(`${EXAMPLE}#/brief`)
  await expect(page.getByRole('alert')).toContainText('latest.json')
  await expect(page.locator('h1').first()).toBeVisible()
})
