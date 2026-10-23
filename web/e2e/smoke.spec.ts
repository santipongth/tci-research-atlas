import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { pathToFileURL } from 'node:url'
import type { GalaxyFile } from '../src/data/types'
import { dequantise, fitView } from '../src/lib/galaxyGl'
import { bundleOf } from '../test/fixtureData'

// ATLAS_E2E_PORT: another dev server may already own 4173 (the config reuses a running server), so a run can pick its own pair of ports
const PORT = Number(process.env.ATLAS_E2E_PORT ?? 4173)
const EXAMPLE = `http://127.0.0.1:${PORT}/`
const EMPTY = `http://127.0.0.1:${PORT + 1}/`

/** The five dashboards, their detail pages, the two maps, the reading guide and the two embeddable widgets. */
const ROUTES = [
  { name: 'overview', path: '/overview' },
  { name: 'topics', path: '/topics' },
  { name: 'places', path: '/places' },
  { name: 'journals', path: '/journals' },
  { name: 'goals', path: '/goals' },
  { name: 'topic', path: '/topics/T000201' },
  { name: 'journal', path: '/journals/so02.example0' },
  { name: 'institution', path: '/institutions/mu-a' },
  { name: 'province', path: '/province/TH-50' },
  { name: 'atlas', path: '/atlas' },
  { name: 'galaxy', path: '/galaxy' },
  { name: 'about', path: '/about' },
  { name: 'embedTopic', path: '/embed/topic/T000201' },
  { name: 'embedEmerging', path: '/embed/emerging' },
] as const

type RouteName = (typeof ROUTES)[number]['name']
type Check = (page: Page) => Promise<void>

/** Page-specific checks against the example release. */
const CHECKS: Partial<Record<RouteName, Check>> = {
  overview: async (page) => {
    await expect(page.locator('h1')).toHaveText('ภาพรวม')
    await expect(page).toHaveTitle(/ภาพรวม/)
    // four KPI cards, each with its change since the last release
    await expect(page.locator('.kpi')).toHaveCount(4)
    await expect(page.locator('.kpi-d').first()).toContainText('+')
    await expect(page.locator('.pbar-sub')).toContainText('2026Q3')
    // the rising topics: the line chart and the ranked list beside it; the list switches to falling topics (in the URL)
    await expect(page.locator('.sl-series')).toHaveCount(4)                 // the small risers; the large hot one is left out of the chart
    await expect(page.locator('.rise').first().locator('li')).toHaveCount(5)
    await expect(page.locator('.rise-name').first()).toHaveAttribute('href', /#\/topics\/T\d{6}$/)
    await page.getByRole('button', { name: 'ลดลง', exact: true }).click()
    await expect(page).toHaveURL(/mv=down/)
    await expect(page.locator('.rise').first().locator('.chip-DECLINING').first()).toBeVisible()
    // every topic by status: the ring and a row per status with glyph, name, count and share
    await expect(page.locator('.dn-list li')).toHaveCount(6)
    await expect(page.locator('.dn-total')).toHaveText('48')
    // where: the province map and the institutions (lazy cards)
    await expect(page.locator('.pv-mini .pmap')).toBeVisible()
    await expect(page.locator('a[href$="/institutions/mu-a"]').first()).toBeVisible()
    // this release in brief: findings, and the notes for policy makers behind the switch
    await expect(page.locator('.pol li').first()).toBeVisible()
    await page.getByRole('button', { name: 'สำหรับผู้วางนโยบาย' }).click()
    await expect(page).toHaveURL(/pt=policy/)
    await expect(page.getByRole('button', { name: 'พิมพ์ / บันทึก PDF' })).toBeVisible()
    // no chart ⇄ table tabs, "how to read" or CSV buttons on a dashboard (owner 2026-10-24)
    await expect(page.getByRole('tab')).toHaveCount(0)
    await expect(page.getByRole('button', { name: /CSV/ })).toHaveCount(0)
    // an explanation opens from the (i) beside a card title, by click
    const info = page.getByRole('button', { name: /เกี่ยวกับ5 จังหวัด|เกี่ยวกับหัวข้อที่ขยับมากที่สุด/ }).first()
    await info.click()
    await expect(info).toHaveAttribute('aria-expanded', 'true')
  },
  topics: async (page) => {
    await expect(page.locator('h1')).toHaveText('หัวข้อวิจัย')
    // six status buttons: glyph, name, count; the emerging ones open first
    await expect(page.locator('.st-pick-b')).toHaveCount(6)
    await expect(page.locator('.st-pick-b.is-EMERGING')).toHaveAttribute('aria-pressed', 'true')
    await expect(page.locator('.dgrid .rise').first().locator('li')).toHaveCount(5)
    await page.locator('.st-pick-b.is-WATCH').click()
    await expect(page).toHaveURL(/status=WATCH/)
    await expect(page.locator('.card-title').first()).toContainText('จับตา')
    // a long status shows ten rows at a time
    await page.locator('.st-pick-b.is-STABLE').click()
    await expect(page.locator('.dgrid .rise').first().locator('li')).toHaveCount(10)
    await page.getByRole('button', { name: /แสดงเพิ่มอีก 10/ }).click()
    await expect(page.locator('.dgrid .rise').first().locator('li')).toHaveCount(20)
    await page.getByRole('button', { name: 'บทความมากที่สุด' }).click()
    await expect(page).toHaveURL(/by=size/)
    // what changed since 2026Q3, the portfolio, rising keywords, few-institution topics and the fields
    await expect(page.locator('.mini-stats > div')).toHaveCount(3)
    await expect(page.locator('svg.pf .pf-node').first()).toBeVisible()
    await expect(page.locator('.rise-name', { hasText: 'chatgpt' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'หัวข้อในแต่ละสาขาหลัก' })).toBeVisible()
  },
  places: async (page) => {
    await expect(page.locator('h1')).toHaveText('สถาบันและจังหวัด')
    await expect(page.locator('.kpi')).toHaveCount(4)
    await expect(page.locator('.pv-big .pmap')).toBeVisible()
    await expect(page.locator('.prov-cols a').first()).toBeVisible()
    await expect(page.getByRole('heading', { name: 'ใครเขียนร่วมกับใคร' })).toBeVisible()
    await page.locator('.prov-cols').getByRole('link', { name: 'เชียงใหม่' }).click()
    await expect(page).toHaveURL(/#\/province\/TH-50$/)
  },
  journals: async (page) => {
    await expect(page.locator('h1')).toHaveText('วารสาร')
    await expect(page.locator('.kpi').first()).toBeVisible()
    await expect(page.getByRole('heading', { name: /วารสารแต่ละฉบับ/ })).toBeVisible()
    const list = page.locator('.card', { has: page.getByRole('heading', { name: 'วารสารทั้งหมด' }) })
    await expect(list.locator('.rise li')).toHaveCount(6)
    await page.getByRole('button', { name: 'ข้อมูลครบที่สุด' }).click()
    await expect(page).toHaveURL(/by=complete/)
    await expect(list.locator('.rise-name').first()).toHaveAttribute('href', /#\/journals\//)
    await expect(page.getByRole('heading', { name: 'วิธีวิจัยที่ใช้บ่อยที่สุด' })).toBeVisible()
  },
  goals: async (page) => {
    await expect(page.locator('h1')).toHaveText('เป้าหมายชาติและโลก')
    // every SDG is one row: 10 with research open to their topics; the 7 without are dashed rows with nothing to open
    await expect(page.locator('.gb-row')).toHaveCount(17)
    await expect(page.locator('.gb-row.is-empty')).toHaveCount(7)
    await expect(page.locator('.gb-row.is-empty summary, .gb-row.is-empty a, .gb-row.is-empty button')).toHaveCount(0)
    await page.locator('.gb-row:not(.is-empty) summary').first().click()
    await expect(page.locator('.gb-topics a').first()).toBeVisible()
    await page.locator('.seg').getByRole('button').nth(1).click()
    await expect(page).toHaveURL(/fw=/)
    await expect(page.getByRole('heading', { name: 'โลกโตเร็ว แต่ไทยยังทำน้อย' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'เรื่องที่พึ่งสถาบันหรือวารสารเดียว' })).toBeVisible()
  },
  topic: async (page) => {
    await expect(page.locator('h1')).toHaveText('AI เพื่อการศึกษา')
    await expect(page.locator('.pbar .chip')).toContainText('กำลังเกิดใหม่')
    await expect(page.locator('.kpi')).toHaveCount(4)
    await expect(page.locator('.kpi').first()).toContainText('ต่อปี')
    await expect(page.locator('svg.tr')).toBeVisible()
    await expect(page.getByRole('link', { name: /AI เพื่อการศึกษา: กรณีศึกษาที่ 1/ }).first()).toHaveAttribute('href', /tci-thaijo\.org/)
    await expect(page.locator('.br-row').first()).toBeVisible()
    await expect(page.locator('.gloss')).toContainText('generative AI')
    await expect(page.locator('.tp-sdg-chip')).toContainText('SDG 4')
    await expect(page.locator('.tp-sdg-chip').first()).toHaveAttribute('href', '#/goals')
    // no compare button, RIS/BibTeX or embed code any more; fixtures have no feeds → no feed link
    await expect(page.getByRole('link', { name: /เปรียบเทียบ/ })).toHaveCount(0)
    await expect(page.getByRole('button', { name: /RIS|BibTeX/ })).toHaveCount(0)
    await expect(page.locator('a[type="application/atom+xml"]')).toHaveCount(0)
    await page.goto(`${EXAMPLE}#/topics/T000701`)
    await expect(page.locator('.tr-band')).toHaveCount(0)
    await page.goto(`${EXAMPLE}#/topics/T123456`)
    await expect(page.locator('h1')).toContainText('T123456')
    await expect(page.getByRole('link', { name: 'ไปหน้าหัวข้อวิจัยทั้งหมด' })).toHaveAttribute('href', '#/topics')
  },
  journal: async (page) => {
    await expect(page.locator('h1')).toHaveText('วารสารวิชาการตัวอย่าง ก')
    await expect(page.locator('.kpi')).toHaveCount(4)
    await expect(page.locator('#topics .br-row').first()).toBeVisible()
    await expect(page.locator('#topic-years .smx-panel')).toHaveCount(4)
    await expect(page.locator('#drift .pm-row')).toHaveCount(2)
    await expect(page.locator('#completeness .ck-row')).toHaveCount(7)
    await expect(page.locator('#peers')).toContainText('example2')
    await expect(page.locator('#opportunities')).toContainText('ยานยนต์ไฟฟ้า')
    await page.goto(`${EXAMPLE}#/journals/so02.nowhere`)
    await expect(page.locator('h1')).toContainText('so02.nowhere')
  },
  institution: async (page) => {
    await expect(page.locator('h1')).toHaveText('มหาวิทยาลัยตัวอย่าง ก')
    await expect(page.locator('.kpi')).toHaveCount(4)
    await expect(page.locator('#years .cc-col')).toHaveCount(10)
    await expect(page.locator('#topics .mx-seg')).toHaveCount(5)                  // 4 topics + "อื่น ๆ"
    await expect(page.locator('#partners .br-row')).toHaveCount(3)
    await expect(page.locator('#suggested')).toContainText('มหาวิทยาลัยเทคโนโลยีราชมงคลตัวอย่าง')
    await page.goto(`${EXAMPLE}#/institutions/nowhere`)
    await expect(page.locator('h1')).toContainText('nowhere')
  },
  province: async (page) => {
    await expect(page.locator('h1')).toHaveText('งานวิจัยในเชียงใหม่')
    await expect(page.locator('.kpi')).toHaveCount(4)
    await expect(page.locator('svg.plc path.is-on')).toHaveCount(1)
    await expect(page.locator('.dgrid .br-row')).toHaveCount(5)
    await expect(page.getByRole('combobox')).toHaveCount(0)
  },
  atlas: async (page) => {
    await expect(page.locator('canvas.terrain')).toBeVisible()
    const marker = page.locator('.mnode').first()
    await marker.focus()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/sel=T\d{6}/)
    await expect(page.locator('#atlas-selection .g-ref')).toHaveText(/^[A-J][1-6]$/)
    await page.getByRole('button', { name: 'ขยาย', exact: true }).click()
    await page.getByRole('button', { name: 'เส้นชั้น', exact: true }).click()
    await expect(page).toHaveURL(/layers=/)
    // one card: status chips filter the map and the list beside it; a row selects its topic on the map
    await expect(page.locator('.ab-chip')).toHaveCount(9)                      // 6 statuses + 3 layers
    await page.getByRole('button', { name: /^คงที่/ }).click()
    await expect(page).toHaveURL(/hide=STABLE/)
    await expect(page.locator('.ab-row', { hasText: 'การปลูกข้าว' })).toHaveCount(0)   // a stable topic leaves the list too
    await page.locator('.ab-row').first().click()
    await expect(page.locator('.ab-row').first()).toHaveAttribute('aria-pressed', 'true')
    await expect(page.locator('.ab-sel .see-all')).toHaveAttribute('href', /#\/topics\/T\d{6}$/)
    await page.getByRole('button', { name: 'ใหญ่ที่สุด' }).click()
    await expect(page).toHaveURL(/by=size/)
  },
  galaxy: async (page) => {
    // headless Chromium normally has WebGL2 (SwiftShader); without it the page explains itself — either is fine
    const canvas = page.locator('canvas.gx-canvas')
    await expect(canvas.or(page.getByText('เบราว์เซอร์นี้วาดแผนที่บทความไม่ได้'))).toBeVisible()
    if (!(await canvas.isVisible())) return
    await expect(page.locator('.ab-keys li').first()).toBeVisible()
    // click one article's dot (screen position from galaxy.json and the fitted view) → its card
    const gx = bundleOf('example').files['galaxy.json'] as GalaxyFile
    const stage = page.locator('.gx-stage')
    await stage.scrollIntoViewIfNeeded()
    const box = await stage.boundingBox()
    if (!box) throw new Error('no stage box')
    const W = box.width - 2
    const H = box.height - 2
    const v = fitView(gx.bounds, W, H)
    const docs = Object.entries(bundleOf('example').files).filter(([p]) => p.startsWith('search/docs-')).flatMap(([, f]) => (f as { docs: unknown[][] }).docs)
    const all = gx.x.map((x, i) => ({ i, x, y: gx.y[i] })).filter((p) => p.x >= 0)
      .map((p) => ({ i: p.i, sx: dequantise(p.x, gx.bounds.x0, gx.bounds.x1, gx.scale) * v.k + v.tx, sy: dequantise(p.y, gx.bounds.y0, gx.bounds.y1, gx.scale) * v.k + v.ty }))
    // a dot with a ThaiJO link, clear of the zoom buttons, with no other dot close enough to be picked instead
    const spot = all.find((p) => docs[p.i]?.[7] && p.sx > 30 && p.sx < W - 90 && p.sy > 30 && p.sy < H - 30 && box.y + p.sy > 10 && box.y + p.sy < 700 && all.every((q) => q.i === p.i || Math.hypot(q.sx - p.sx, q.sy - p.sy) > 14))
    if (!spot) throw new Error('no isolated galaxy dot in the fixture')
    await page.mouse.click(box.x + 1 + spot.sx, box.y + 1 + spot.sy)
    await expect(page.locator('.gx-title')).toBeVisible()
    await expect(page.locator('.gx-card a.btn')).toHaveAttribute('href', /tci-thaijo\.org/)
    await page.getByRole('button', { name: 'ล้างการเลือก' }).click()
    await expect(page.locator('.gx-try-btn')).toHaveCount(3)
    // years are presets and the field legend is the field filter — no drop-downs
    await expect(page.getByRole('combobox')).toHaveCount(0)
    await page.getByRole('button', { name: '5 ปีล่าสุด' }).click()
    await expect(page).toHaveURL(/from=\d{4}/)
    await expect(page.locator('.gx-count')).toContainText('จาก')
    await page.locator('.gx-field-row').nth(1).click()
    await expect(page).toHaveURL(/g=/)
    await expect(page.locator('.gx-field-row').nth(1)).toHaveAttribute('aria-pressed', 'true')
    await expect(page.getByRole('tab')).toHaveCount(0)
  },
  about: async (page) => {
    await expect(page.locator('#flow .afl-st')).toHaveCount(5)
    await expect(page.locator('#definition .ab-tree .sfc-row')).toHaveCount(4)
    await expect(page.locator('.defs > div')).toHaveCount(6)
    await expect(page.locator('#changelog')).toHaveCount(0)
    await page.locator('#cite summary').click()
    await expect(page.locator('#cite-apa')).toHaveValue(/ศูนย์ดัชนีการอ้างอิงวารสารไทย \(TCI\)\. \(\d{4}\)\. .*รอบข้อมูล 2026Q4/)
  },
  embedTopic: async (page) => {
    await expect(page.locator('h1')).toHaveText('AI เพื่อการศึกษา')
    await expect(page.locator('.embed-status .chip')).toBeVisible()
    await expect(page.locator('svg.tr')).toBeVisible()
    await expect(page.locator('aside, footer')).toHaveCount(0)
    await expect(page.locator('.embed-sample .phase-tag.is-sample')).toBeVisible()
    await expect(page.getByRole('link', { name: /TCI Research Atlas/ })).toHaveAttribute('href', /#\/topics\/T000201\?lang=th$/)
  },
  embedEmerging: async (page) => {
    await expect(page.locator('h1')).toHaveText('หัวข้อที่กำลังเกิดใหม่และควรจับตา')
    await expect(page.locator('aside, footer')).toHaveCount(0)
    const items = page.locator('.embed-list li')
    expect(await items.count()).toBeGreaterThan(0)
    expect(await items.count()).toBeLessThanOrEqual(10)
    await expect(page.getByRole('link', { name: /TCI Research Atlas/ })).toHaveAttribute('href', /#\/topics\?lang=th$/)
  },
}

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

function offlineFile(info: { outputPath: (n: string) => string }, name: string, bundle: ReturnType<typeof bundleOf>): string {
  const template = readFileSync('dist/offline-template.html', 'utf8')
  const slot = '<script type="application/json" id="atlas-data">null</script>'
  expect(template.split(slot)).toHaveLength(2)
  const file = info.outputPath(name)
  mkdirSync(dirname(file), { recursive: true })
  writeFileSync(file, template.replace(slot, () => `<script type="application/json" id="atlas-data">${JSON.stringify(bundle).replaceAll('</', '<\\/')}</script>`))
  return pathToFileURL(file).href
}

for (const route of ROUTES) {
  test(`${route.name}: example release renders without serious a11y issues`, async ({ page }) => {
    const errors = collectErrors(page)
    await page.goto(`${EXAMPLE}#${route.path}`)
    await expect(page.locator('h1').first()).toBeVisible()
    await CHECKS[route.name]?.(page)
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

test('there is no search box on any page', async ({ page }) => {
  for (const route of ROUTES) {
    await page.goto(`${EXAMPLE}#${route.path}`)
    await expect(page.locator('h1').first()).toBeVisible()
    await expect(page.locator('input[type="search"], [role="combobox"][aria-autocomplete], [role="searchbox"]'), route.path).toHaveCount(0)
  }
})

test('old links land on the dashboard that carries their content', async ({ page }) => {
  const moves: [string, RegExp][] = [
    ['/emerging?status=HOT', /#\/topics\?status=HOT$/],
    ['/changes', /#\/topics$/],
    ['/gaps', /#\/topics$/],
    ['/keywords', /#\/topics$/],
    ['/regions', /#\/places$/],
    ['/institutions', /#\/places$/],
    ['/province', /#\/places$/],
    ['/methods', /#\/journals$/],
    ['/references', /#\/journals$/],
    ['/sdg', /#\/goals$/],
    ['/global', /#\/goals$/],
    ['/brief', /#\/overview$/],
    ['/story', /#\/overview$/],
    ['/search?q=x', /#\/overview$/],
    ['/compare?ids=T000201', /#\/overview$/],
    ['/match', /#\/overview$/],
    ['/data', /#\/overview$/],
  ]
  for (const [from, to] of moves) {
    await page.goto(`${EXAMPLE}#${from}`)
    await expect(page, from).toHaveURL(to)
    await expect(page.locator('h1').first()).toBeVisible()
  }
  await page.goto(`${EXAMPLE}#/emerging?status=HOT`)
  await expect(page.locator('.st-pick-b.is-HOT')).toHaveAttribute('aria-pressed', 'true')
})

test('a missing data release shows a banner, not a white page', async ({ page }) => {
  await page.route('**/data/latest.json', (r) => r.fulfill({ status: 404, body: 'not found' }))
  await page.goto(`${EXAMPLE}#/overview`)
  await expect(page.getByRole('alert')).toContainText('latest.json')
  await expect(page.locator('h1').first()).toBeVisible()
})

test('a sample release is labelled as sample data on every page bar', async ({ page }) => {
  for (const path of ['/overview', '/topics', '/topics/T000201']) {
    await page.goto(`${EXAMPLE}#${path}`)
    await expect(page.locator('.pbar .phase-tag.is-sample')).toBeVisible()
  }
})

test('pages do not scroll sideways on a 360 px phone', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 780 })
  for (const route of ROUTES) {
    await page.goto(`${EXAMPLE}#${route.path}`)
    await expect(page.locator('h1').first()).toBeVisible()
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow, route.path).toBeLessThanOrEqual(0)
  }
})

test('the sidebar names every page and marks the current one', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto(`${EXAMPLE}#/topics/T000201`)
  const nav = page.getByRole('navigation', { name: 'เมนูหลัก' })
  await expect(nav.getByRole('link')).toHaveCount(8)
  await expect(nav.getByRole('link', { name: 'หัวข้อวิจัย' })).toHaveAttribute('aria-current', 'page')
  await nav.getByRole('link', { name: 'วารสาร' }).click()
  await expect(page).toHaveURL(/#\/journals$/)
  await expect(page.locator('h1')).toHaveText('วารสาร')
  await expect(page.locator('main')).toBeFocused()
})

test('a chart tooltip is linked to its marker and Escape dismisses it', async ({ page }) => {
  await page.goto(`${EXAMPLE}#/topics`)
  const node = page.locator('.pf-node[tabindex="0"]').first()
  await node.focus()
  await expect(page.getByRole('tooltip')).toBeVisible()
  await expect(node).toHaveAttribute('aria-describedby', /atlas-tooltip/)
  await page.keyboard.press('Escape')
  await expect(page.getByRole('tooltip')).toHaveCount(0)
})

test('the offline file works from file:// without a single network request', async ({ page }, info) => {
  const url = offlineFile(info, 'atlas-offline.html', bundleOf('example'))
  const remote: string[] = []
  page.on('request', (r) => {
    if (!/^(file|data|blob):/.test(r.url())) remote.push(r.url())
  })
  const errors = collectErrors(page)
  await page.goto(`${url}#/overview`)
  await expect(page.locator('.kpi').first()).toBeVisible()
  await page.goto(`${url}#/topics/T000201`)
  await expect(page.locator('h1')).toHaveText('AI เพื่อการศึกษา')
  await page.goto(`${url}#/atlas`)
  await expect(page.locator('canvas.terrain')).toBeVisible()
  await page.goto(`${url}#/journals/so02.example0`)
  await expect(page.locator('h1')).toHaveText('วารสารวิชาการตัวอย่าง ก')
  expect(remote).toEqual([])
  expect(errors).toEqual([])
})

test('the footer is the partner logos and the licence line', async ({ page }) => {
  await page.goto(`${EXAMPLE}#/overview`)
  const footer = page.locator('footer')
  await expect(footer.locator('.ftr-logos img')).toHaveCount(3)
  await expect(footer.getByRole('link')).toHaveCount(1) // "อ้างอิง Atlas นี้", in the licence line
  await expect(footer.locator('.licence').getByRole('link', { name: 'อ้างอิง Atlas นี้' })).toHaveAttribute('href', '#/about')
  await expect(footer.locator('.licence')).toContainText('CC BY 4.0')
})

test('a module the pipeline skipped says why', async ({ page }) => {
  await page.goto(`${EMPTY}#/goals`)
  await expect(page.locator('h1')).toHaveText('เป้าหมายชาติและโลก')
  await expect(page.locator('.empty-state')).toContainText('ATLAS_OFFLINE')
})

test('the article galaxy explains itself on a release without it and in the offline file', async ({ page }, info) => {
  await page.goto(`${EMPTY}#/galaxy`)
  await expect(page.locator('h1')).toHaveText('แผนที่บทความทุกเรื่อง')
  await expect(page.locator('.empty-state')).toContainText('รอบข้อมูลนี้ไม่มีส่วนนี้')
  const bundle = bundleOf('example')
  delete bundle.files['galaxy.json']   // export.offline_exclude
  await page.goto(`${offlineFile(info, 'atlas-offline-nogalaxy.html', bundle)}#/galaxy`)
  await expect(page.locator('h1')).toHaveText('แผนที่บทความทุกเรื่อง')
  await expect(page.locator('.empty-state')).toContainText('ฉบับออฟไลน์ไม่มีส่วนนี้')
})

test('feed links appear on /topics and the topic page when the site has Atom feeds', async ({ page }) => {
  await page.route('**/data/latest.json', async (route) => {
    const res = await route.fetch()
    await route.fulfill({ response: res, json: { ...(await res.json()), feeds: true } })
  })
  await page.goto(`${EXAMPLE}#/topics`)
  await expect(page.getByRole('link', { name: 'ติดตามรอบใหม่ (Atom/RSS)' })).toHaveAttribute('href', './data/feeds/releases.xml')
  await page.goto(`${EXAMPLE}#/topics/T000201`)
  await expect(page.getByRole('link', { name: 'ติดตามหัวข้อนี้ (Atom/RSS)' })).toHaveAttribute('href', './data/feeds/topics/T000201.xml')
})

test('the offline template is kept out of search engines', () => {
  expect(readFileSync('dist/offline-template.html', 'utf8')).toContain('<meta name="robots" content="noindex">')
})
