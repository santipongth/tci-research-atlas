import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { pathToFileURL } from 'node:url'
import { bundleOf } from '../test/fixtureData'

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
  { name: 'journals', path: '/journals' },
  { name: 'journal', path: '/journals/so02.example0' },
  { name: 'methods', path: '/methods' },
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
    // a topic new since the baseline is marked as such; the axis reaches its +129% upper bound instead of clipping it
    await expect(page.locator('.fr-row', { hasText: 'โมเดลภาษาขนาดใหญ่' }).first()).toContainText('ใหม่ — ไม่มีในช่วงฐาน')
    await expect(page.locator('.fr-axis').first()).toContainText('+120%')
    // portfolio labels sit beside the markers, never on one
    await page.evaluate(() => document.fonts.ready)
    await expect(page.locator('.pf-ltext').first()).toBeVisible()
    const onMarkers = await page.evaluate(() => {
      const marks = [...document.querySelectorAll('.pf-node .mk')].map((m) => m.getBoundingClientRect())
      return [...document.querySelectorAll('.pf-ltext')]
        .filter((l) => {
          const r = l.getBoundingClientRect()
          return marks.some((m) => r.left + 1 < m.right && m.left < r.right - 1 && r.top + 1 < m.bottom && m.top < r.bottom - 1)
        })
        .map((l) => l.textContent)
    })
    expect(onMarkers).toEqual([])
    await page.getByRole('tab', { name: 'ตาราง' }).first().click()
    await expect(page.getByRole('table').first()).toBeVisible()
    await expect(page.getByRole('table').first()).toContainText('ใหม่ — ไม่มีในช่วงฐาน')
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
    await expect(page.locator('.uncertain')).not.toContainText('บทความยังน้อย')
    await expect(page.locator('.tr-band')).toHaveCount(0)
    await expect(page.locator('.summary')).toContainText('ใหม่ — ไม่มีในช่วงฐาน')
    await page.goto(`${EXAMPLE}#/topics/T123456`)
    await expect(page.locator('h1')).toContainText('T123456')
  },
  atlas: async (page) => {
    await expect(page.locator('canvas.terrain')).toBeVisible()
    const marker = page.locator('.mnode').first()
    await marker.focus()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/sel=T\d{6}/)
    await expect(page.locator('#atlas-selection .g-ref')).toHaveText(/^[A-J][1-6]$/)
    await page.getByRole('button', { name: 'ขยาย', exact: true }).click()
    await page.getByLabel('เส้นชั้น', { exact: true }).uncheck()
    await expect(page).toHaveURL(/layers=/)
    await page.getByRole('searchbox', { name: 'ค้นหาในดัชนีหัวข้อ' }).fill('ข้าว')
    await page.getByRole('button', { name: /การปลูกข้าว/ }).click()
    await expect(page).toHaveURL(/sel=T000401/)
  },
  compare: async (page) => {
    await expect(page.locator('.cmp-chip')).toHaveCount(2)
    await expect(page.locator('svg.ml path.ml-line')).toHaveCount(2)
    const add = page.getByRole('combobox', { name: 'เพิ่มหัวข้อ' })
    await add.fill('ยานยนต์')
    await add.press('Enter')
    await expect(page).toHaveURL(/ids=T000201%2CT000701%2CT000502/)
    await page.getByLabel('จำนวนบทความ', { exact: true }).check()
    await expect(page).toHaveURL(/metric=count/)
    await page.getByRole('button', { name: 'เอาออก: AI เพื่อการศึกษา' }).click()
    await expect(page.locator('.cmp-chip')).toHaveCount(2)
    // focus follows the change: the next chip's remove button, then the "max 4" hint when the picker fills up
    await expect(page.locator('.cmp-remove').first()).toBeFocused()
    await add.fill('ข้าว')
    await add.press('Enter')
    await add.fill('ผู้สูงอายุ')
    await add.press('Enter')
    await expect(page.locator('.cmp-chip')).toHaveCount(4)
    await expect(add).toBeDisabled()
    await expect(page.locator('p.hint', { hasText: /4/ })).toBeFocused()
    await page.locator('.cmp-remove').last().click()
    await expect(page.locator('.cmp-remove').last()).toBeFocused()
    await expect(add).toBeEnabled()
  },
  data: async (page) => {
    await expect(page.locator('#downloads .dl-list li')).toHaveCount(7)
    await expect(page.locator('#downloads a[download]').first()).toHaveAttribute('href', /data\/2026Q4\/manifest\.json$/)
    await expect(page.locator('#quality')).toContainText('2025')
    await expect(page.locator('#dictionary table')).toBeVisible()
    await expect(page.locator('#modules .dl-list li')).toHaveCount(4)
    const download = page.waitForEvent('download')
    await page.locator('#csv').getByRole('button', { name: 'ดาวน์โหลด CSV' }).first().click()
    expect((await download).suggestedFilename()).toBe('atlas-2026Q4-topics.csv')
  },
  about: async (page) => {
    await expect(page.locator('.defs > div')).toHaveCount(6)
    await expect(page.locator('#changelog li')).toHaveCount(2)
    await expect(page.locator('#definition')).toContainText('+10%')
  },
  brief: async (page) => {
    await expect(page.locator('[data-brief-ready="true"]')).toBeVisible()
    await expect(page.locator('.brief .headline mark').first()).toBeVisible()
    await expect(page.locator('.brief-t').first().locator('tbody tr')).toHaveCount(5)
  },
  journals: async (page) => {
    const rows = page.locator('#journals tbody tr')
    await expect(rows).toHaveCount(6)
    await expect(page.locator('#journals')).toContainText('example2')          // no registry name → the OJS name
    await expect(page.locator('#journals .flag', { hasText: 'อนุมาน' }).first()).toBeVisible()
    await page.getByLabel('ค้นหาวารสาร (ชื่อ, ชื่อ OJS หรือ ISSN)').fill('example5')
    await expect(rows).toHaveCount(1)
    await expect(page).toHaveURL(/q=example5/)
    await page.getByLabel('ค้นหาวารสาร (ชื่อ, ชื่อ OJS หรือ ISSN)').fill('')
    await page.getByLabel('กลุ่มวารสาร TCI').selectOption('1')
    await expect(rows).toHaveCount(2)
    await expect(page.locator('#special-issues')).toContainText('ไมโครพลาสติก')
    await page.getByRole('link', { name: 'วารสารวิชาการตัวอย่าง ก' }).click()
    await expect(page).toHaveURL(/#\/journals\/so02\.example0$/)
  },
  journal: async (page) => {
    await expect(page.locator('h1')).toHaveText('วารสารวิชาการตัวอย่าง ก')
    await expect(page.locator('#topics table')).toBeVisible()
    await expect(page.locator('#peers')).toContainText('example2')
    await expect(page.locator('#completeness')).toContainText('DOI')
    await expect(page.locator('#opportunities')).toContainText('ยานยนต์ไฟฟ้า')
    await page.locator('#drift').getByRole('tab', { name: 'ตาราง' }).click()
    await expect(page).toHaveURL(/drift=table/)
    await page.goto(`${EXAMPLE}#/journals/so02.nowhere`)
    await expect(page.locator('h1')).toContainText('so02.nowhere')
  },
  methods: async (page) => {
    await expect(page.locator('svg.ml path.ml-line')).toHaveCount(4)
    await expect(page.locator('#lexicon li')).toHaveCount(16)
    await page.getByLabel('แสดงเฉพาะหัวข้อที่วิธีกระจุก').check()
    await expect(page).toHaveURL(/mono=only/)
    await expect(page.locator('#topics tbody tr')).toHaveCount(2)
  },
  // checks:end
}

/** Routes that must not scroll sideways at 360 px. */
const PHONE = ['/overview', '/emerging', '/topics/T000201', '/atlas', '/compare?ids=T000201,T000701', '/data', '/about', '/journals', '/journals/so02.example0', '/methods']

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

test('a chart tooltip is linked to its marker and Escape dismisses it', async ({ page }) => {
  await page.goto(`${EXAMPLE}#/overview`)
  const node = page.locator('.pf-node[tabindex="0"]').first()
  await node.focus()
  await expect(page.getByRole('tooltip')).toBeVisible()
  await expect(node).toHaveAttribute('aria-describedby', /atlas-tooltip/)
  await page.keyboard.press('Escape')
  await expect(page.getByRole('tooltip')).toHaveCount(0)
})

test('the offline file works from file:// without a single network request', async ({ page }, info) => {
  const template = readFileSync('dist/offline-template.html', 'utf8')
  const slot = '<script type="application/json" id="atlas-data">null</script>'
  expect(template.split(slot)).toHaveLength(2)
  const payload = JSON.stringify(bundleOf('example')).replaceAll('</', '<\\/')
  const file = info.outputPath('atlas-offline.html')
  mkdirSync(dirname(file), { recursive: true })
  writeFileSync(file, template.replace(slot, () => `<script type="application/json" id="atlas-data">${payload}</script>`))
  const remote: string[] = []
  page.on('request', (r) => {
    if (!/^(file|data|blob):/.test(r.url())) remote.push(r.url())
  })
  const errors = collectErrors(page)
  const url = pathToFileURL(file).href
  await page.goto(`${url}#/overview`)
  await expect(page.locator('.headline mark').first()).toBeVisible()
  await page.goto(`${url}#/topics/T000201`)
  await expect(page.locator('h1')).toHaveText('AI เพื่อการศึกษา')
  await page.goto(`${url}#/atlas`)
  await expect(page.locator('canvas.terrain')).toBeVisible()
  await page.goto(`${url}#/journals/so02.example0`)
  await expect(page.locator('h1')).toHaveText('วารสารวิชาการตัวอย่าง ก')
  expect(remote).toEqual([])
  expect(errors).toEqual([])
})
