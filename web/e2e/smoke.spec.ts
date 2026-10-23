import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { pathToFileURL } from 'node:url'
import type { GalaxyFile } from '../src/data/types'
import { dequantise, fitView } from '../src/lib/galaxyGl'
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
  { name: 'changes', path: '/changes' },
  { name: 'match', path: '/match' },
  { name: 'institutions', path: '/institutions' },
  { name: 'institution', path: '/institutions/mu-a' },
  { name: 'regions', path: '/regions' },
  { name: 'sdg', path: '/sdg' },
  { name: 'global', path: '/global' },
  { name: 'gaps', path: '/gaps' },
  { name: 'search', path: '/search' },
  { name: 'galaxy', path: '/galaxy' },
  { name: 'keywords', path: '/keywords' },
  { name: 'references', path: '/references' },
  { name: 'embedTopic', path: '/embed/topic/T000201' },
  { name: 'embedEmerging', path: '/embed/emerging' },
] as const

type RouteName = (typeof ROUTES)[number]['name']
type Check = (page: Page) => Promise<void>

/** Page-specific checks against the example release; each page task adds one line between the markers. */
const CHECKS: Partial<Record<RouteName, Check>> = {
  // checks:start
  overview: async (page) => {
    await expect(page.locator('.headline mark').first()).toBeVisible()
    await expect(page.getByRole('link', { name: /โมเดลภาษาขนาดใหญ่/ }).first()).toBeVisible()
    await expect(page.locator('#kpi .stat')).toHaveCount(8)
    await expect(page.locator('#policy li')).toHaveCount(3)
    await expect(page.locator('#kpi .stat-d').first()).toContainText('2026Q3')
    await expect(page.locator('.fr-row').first()).toBeVisible()
    // a topic new since the baseline is marked as such; the axis reaches its +129% upper bound instead of clipping it
    await expect(page.locator('.fr-row', { hasText: 'โมเดลภาษาขนาดใหญ่' }).first()).toContainText('ใหม่ — ปี')
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
    await expect(page.getByRole('table').first()).toContainText('ใหม่ — ปี')
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
    await expect(page.locator('#numbers .stats')).toContainText('%')
    await expect(page.locator('svg.tr')).toBeVisible()
    await expect(page.getByRole('link', { name: /AI เพื่อการศึกษา: กรณีศึกษาที่ 1/ })).toHaveAttribute('href', /tci-thaijo\.org/)
    await expect(page.locator('#related')).toBeVisible()
    // P4: glossary, cited-in-TCI figure (0 is a value, not a missing one), SDG goal chips, RIS export of the articles
    await expect(page.locator('#glossary tbody tr')).toHaveCount(2)
    await expect(page.locator('#glossary')).toContainText('generative AI')
    await expect(page.locator('#numbers .stats')).toContainText('บทความอื่นอ้างถึง')
    await expect(page.locator('.tp-sdg-chip')).toContainText('SDG 4')
    const ris = page.waitForEvent('download')
    await page.getByRole('button', { name: /บทความตัวแทน 4 เรื่องเป็น RIS/ }).click()
    expect((await ris).suggestedFilename()).toBe('atlas-2026Q4-T000201-articles.ris')
    // P4: fixtures have latest.feeds false → no feed link; the embed code points at this site's widget
    await expect(page.locator('.feed-link')).toHaveCount(0)
    await page.locator('.embed-snip summary').click()
    await expect(page.locator('#embed-code-topic')).toHaveValue(/^<iframe src="http:\/\/127\.0\.0\.1:4173\/#\/embed\/topic\/T000201\?lang=th" title="AI เพื่อการศึกษา — TCI Research Atlas"/)
    await page.goto(`${EXAMPLE}#/topics/T000701`)
    await expect(page.locator('.uncertain')).toContainText('แนวโน้มไม่แน่นอน')
    await expect(page.locator('.uncertain')).not.toContainText('บทความยังน้อย')
    await expect(page.locator('.tr-band')).toHaveCount(0)
    await expect(page.locator('#numbers .stats')).toContainText('ใหม่ — ปี')
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
    await expect(page.locator('#modules .dl-list li')).toHaveCount(13)
    const download = page.waitForEvent('download')
    await page.locator('#csv').getByRole('button', { name: 'ดาวน์โหลด CSV' }).first().click()
    expect((await download).suggestedFilename()).toBe('atlas-2026Q4-topics.csv')
  },
  about: async (page) => {
    await expect(page.locator('.defs > div')).toHaveCount(6)
    await expect(page.locator('#changelog li')).toHaveCount(2)
    await expect(page.locator('#definition')).toContainText('+10%')
    // cite this atlas: APA-like text and BibTeX for the current release, organisation as author
    await expect(page.locator('#cite-apa')).toHaveValue(/ศูนย์ดัชนีการอ้างอิงวารสารไทย \(TCI\)\. \(\d{4}\)\. .*รอบข้อมูล 2026Q4/)
    await expect(page.locator('#cite-bib')).toHaveValue(/^@misc\{tci-atlas-2026q4,[\s\S]*author = \{\{Thai-Journal Citation Index Centre \(TCI\)\}\}/)
    await expect(page.locator('#cite').getByRole('button', { name: 'คัดลอก แบบ APA' })).toBeVisible()
  },
  brief: async (page) => {
    await expect(page.locator('[data-brief-ready="true"]')).toBeVisible()
    await expect(page.locator('h2#brief-exec')).toBeVisible()
    await expect(page.locator('.brief .headline mark').first()).toBeVisible()
    await expect(page.locator('.brief-t').first().locator('tbody tr')).toHaveCount(7)
  },
  journals: async (page) => {
    const rows = page.locator('#journals tbody tr')
    await expect(rows).toHaveCount(6)
    await expect(page.locator('#journals')).toContainText('example2')          // no registry name → the OJS name
    await expect(page.locator('#journals .flag', { hasText: 'อนุมาน' }).first()).toBeVisible()
    await page.getByLabel('ค้นหาวารสาร (ชื่อหรือ ISSN)').fill('example5')
    await expect(rows).toHaveCount(1)
    await expect(page).toHaveURL(/q=example5/)
    await page.getByLabel('ค้นหาวารสาร (ชื่อหรือ ISSN)').fill('')
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
    await page.getByLabel('แสดงเฉพาะหัวข้อที่ใช้วิธีเดียวเป็นหลัก').check()
    await expect(page).toHaveURL(/mono=only/)
    await expect(page.locator('#topics tbody tr')).toHaveCount(2)
  },
  changes: async (page) => {
    await expect(page.locator('#status tbody tr')).toHaveCount(5)
    await expect(page.locator('#new li')).toHaveCount(3)
    await expect(page.locator('#retired')).toContainText('หนังสือพิมพ์รายวัน')
    await expect(page.locator('#retired')).toContainText('รวมเข้ากับ')                 // merged_into is never a plain disappearance
    await expect(page.locator('#restructured li')).toHaveCount(2)
    await expect(page.locator('#movers table')).toBeVisible()
    await expect(page.locator('#journals')).toContainText('example5')
    await expect(page.locator('.feed-link')).toHaveCount(0)
  },
  match: async (page) => {
    await expect(page.locator('.privacy')).toBeVisible()
    const box = page.getByLabel('ข้อความของคุณ')
    await box.fill('AI')
    await page.getByRole('button', { name: 'หาหัวข้อที่ใกล้ที่สุด' }).click()
    await expect(page.getByRole('alert')).toContainText('อย่างน้อย')
    const text = 'AI เพื่อการศึกษา ปัญญาประดิษฐ์ การเรียนการสอน generative AI teaching'
    await box.fill(text)
    await page.getByRole('button', { name: 'หาหัวข้อที่ใกล้ที่สุด' }).click()
    await expect(page.locator('#match-results')).toBeFocused()
    await expect(page.locator('.hits .topic-link').first()).toContainText('AI เพื่อการศึกษา')
    await expect(page.locator('#match-journals')).toBeVisible()
    expect(page.url()).not.toContain('generative')                       // the pasted text never enters the URL
    expect(page.url()).not.toContain(encodeURIComponent('ปัญญา'))
  },
  institutions: async (page) => {
    const rows = page.locator('#institutions tbody tr')
    await expect(rows).toHaveCount(8)
    await page.getByLabel('ประเภทสถาบัน').selectOption('rajabhat')
    await expect(rows).toHaveCount(1)
    await expect(page).toHaveURL(/type=rajabhat/)
    await page.getByLabel('ประเภทสถาบัน').selectOption('all')
    await expect(page.locator('#partnerships tbody tr')).toHaveCount(6)
    await expect(page.locator('#countries')).toContainText('ญี่ปุ่น')
    await page.locator('#institutions').getByRole('link', { name: 'มหาวิทยาลัยตัวอย่าง ก' }).click()
    await expect(page).toHaveURL(/#\/institutions\/mu-a$/)
  },
  institution: async (page) => {
    await expect(page.locator('h1')).toHaveText('มหาวิทยาลัยตัวอย่าง ก')
    await expect(page.locator('#topics tbody tr')).toHaveCount(5)
    await expect(page.locator('#suggested')).toContainText('มหาวิทยาลัยเทคโนโลยีราชมงคลตัวอย่าง')
    await page.goto(`${EXAMPLE}#/topics/T000101`)
    await expect(page.locator('#orgs a[href$="/institutions/mu-a"]').first()).toBeVisible()
    await page.goto(`${EXAMPLE}#/institutions/nowhere`)
    await expect(page.locator('h1')).toContainText('nowhere')
  },
  regions: async (page) => {
    await expect(page.locator('svg.pmap path')).toHaveCount(77)
    await expect(page.locator('svg.pmap path.pv-none')).toHaveCount(65)          // 12 provinces have data
    await expect(page.locator('.pkey li')).toHaveCount(6)                         // 5 classes + no data
    await page.getByLabel('บทความต่อประชากรแสนคน').check()
    await expect(page).toHaveURL(/m=per100k/)
    await expect(page.locator('svg.pmap path.pv-none')).toHaveCount(67)          // two have no population
    await page.locator('#map').getByRole('tab', { name: 'ตาราง' }).click()
    await expect(page.locator('#map tbody tr')).toHaveCount(12)
    await expect(page.locator('#by-region tbody tr')).toHaveCount(5)
  },
  sdg: async (page) => {
    await expect(page.getByRole('tab', { name: /SDGs/ })).toHaveAttribute('aria-selected', 'true')
    await expect(page.locator('#goals tbody tr')).toHaveCount(17)
    await expect(page.locator('#goals')).toContainText('ยังไม่พบหัวข้อ')
    await page.getByRole('tab', { name: 'โมเดลเศรษฐกิจ BCG' }).click()
    await expect(page).toHaveURL(/fw=bcg/)
    await expect(page.locator('#goals tbody tr')).toHaveCount(3)
  },
  global: async (page) => {
    await expect(page.locator('#opportunities tbody tr')).toHaveCount(3)
    await expect(page.locator('#opportunities')).toContainText('Artificial Intelligence')
    await expect(page.locator('#all tbody tr')).toHaveCount(11)
  },
  gaps: async (page) => {
    await expect(page.locator('#world tbody tr')).toHaveCount(3)
    await expect(page.locator('#few tbody tr')).toHaveCount(2)
    await expect(page.locator('#bridges tbody tr')).toHaveCount(2)
    const risk = page.locator('#risk tbody tr')
    await expect(risk).toHaveCount(2)
    await page.getByLabel('แสดงทุกรายการ รวมที่ไม่ได้พึ่งแหล่งเดียว').check()
    await expect(risk).toHaveCount(4)
    await expect(page).toHaveURL(/all=yes/)
    await expect(page.locator('#risk')).toContainText('มหาวิทยาลัยราชภัฏตัวอย่าง')
  },
  search: async (page) => {
    await expect(page.locator('#srch-tips-h')).toBeVisible()                      // an empty query shows how to search
    const box = page.getByLabel('คำค้น', { exact: true })
    await box.fill('ผู้สูงอายุควอนตัม')
    await box.press('Enter')
    await expect(page).toHaveURL(/q=/)
    await expect(page.locator('.srch-count')).toContainText('พบ')
    await expect(page.locator('.srch-hit').first()).toBeVisible()
    await expect(page.locator('.srch-unknown')).toContainText('ไม่พบคำว่า “ควอนตัม”')   // an unknown word is named
    await expect(page.locator('.srch-hit .topic-link').first()).toContainText('การดูแลผู้สูงอายุในชุมชน')
    await page.getByLabel('ตั้งแต่ปี').selectOption('2020')
    await expect(page).toHaveURL(/from=2020/)
    const download = page.waitForEvent('download')
    await page.getByRole('button', { name: /เป็น RIS$/ }).click()
    expect((await download).suggestedFilename()).toBe('atlas-2026Q4-search.ris')
  },
  galaxy: async (page) => {
    // headless Chromium normally has WebGL2 (SwiftShader); without it the page explains itself — either is fine
    const canvas = page.locator('canvas.gx-canvas')
    await expect(canvas.or(page.getByText('เบราว์เซอร์นี้วาดแผนที่บทความไม่ได้'))).toBeVisible()
    if (!(await canvas.isVisible())) return
    await expect(page.locator('.lede')).toContainText('600')
    await expect(page.locator('.gx-keys li').first()).toBeVisible()
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
    await expect(page.locator('.gx-card .topic-link')).toBeVisible()
    await page.getByRole('button', { name: 'ล้างการเลือก' }).click()
    await expect(page.locator('.gx-card-empty')).toBeVisible()
    // keyboard: the sheet takes focus, zooms and picks the dot in the middle (or says there is none)
    await stage.focus()
    await page.keyboard.press('+')
    await page.keyboard.press('Enter')
    await expect(page.locator('.gx-title').or(page.locator('.gx-card-empty'))).toBeVisible()
    await page.keyboard.press('0')
    await page.getByLabel('ตั้งแต่ปี').selectOption('2020')
    await expect(page).toHaveURL(/from=2020/)
    await page.getByRole('combobox', { name: /สาขาวิชา/ }).selectOption({ index: 1 })
    await expect(page).toHaveURL(/g=F\d+/)
    await expect(page.locator('.gx-count')).toContainText('เน้น')
    await page.getByRole('tab', { name: 'ตาราง' }).click()
    await expect(page.getByRole('table')).toBeVisible()
    await expect(page.getByRole('table').locator('.topic-link').first()).toBeVisible()
    await expect(page).toHaveURL(/view=table/)
    await page.getByRole('tab', { name: 'แผนภูมิ' }).click()
    await expect(canvas).toBeVisible()
  },
  keywords: async (page) => {
    // opens on the most used keywords, led by a plain sentence about the first one
    await expect(page.locator('.cmp-chip')).toHaveCount(3)
    await expect(page.locator('.kw-insight')).toContainText('digital marketing')
    await expect(page.locator('svg.ml')).toBeVisible()
    const box = page.getByRole('combobox', { name: 'เพิ่มคำสำคัญ (ไทยหรืออังกฤษ)' })
    await box.fill('ผู้สูงอายุ')
    await expect(page.getByRole('option').first()).toBeVisible()
    await box.press('ArrowDown')
    await box.press('Enter')
    await expect(page).toHaveURL(/k=/)
    await expect(page.locator('.cmp-chip')).toHaveCount(4)
    await expect(page.getByText('เลือกได้ครั้งละ 4 คำ')).toBeFocused()
    await expect(box).toBeDisabled()
    await page.getByRole('button', { name: /^เอา “digital marketing” ออก$/ }).click()
    await expect(page.locator('.cmp-chip')).toHaveCount(3)
    await page.locator('#fig-kw-tab-table').click()
    await expect(page).toHaveURL(/view=table/)
    await expect(page.locator('#fig-kw-panel table')).toContainText('2024')
    // glossary: filter, sort, CSV
    await page.getByLabel('กรองคำ').fill('solar')
    await expect(page).toHaveURL(/gq=solar/)
    await expect(page.locator('#kw-glossary tbody')).toContainText('เซลล์แสงอาทิตย์')
    await page.locator('#kw-glossary').getByRole('button', { name: 'คำอังกฤษ' }).click()
    await expect(page.locator('#kw-glossary th[aria-sort="ascending"]')).toContainText('คำอังกฤษ')
    const csv = page.waitForEvent('download')
    await page.locator('#kw-glossary').getByRole('button', { name: 'ดาวน์โหลด CSV' }).click()
    expect((await csv).suggestedFilename()).toBe('atlas-2026Q4-glossary.csv')
  },
  references: async (page) => {
    await expect(page.locator('.lede')).toContainText('72%')
    await expect(page.locator('.ref-kpis .kpi')).toHaveCount(3)
    await expect(page.locator('#ref-journals tbody tr')).toHaveCount(5)
    await expect(page.locator('#ref-journals').getByRole('link').first()).toHaveAttribute('href', /#\/journals\/so02\./)
    await page.locator('#ref-journals').getByRole('button', { name: 'มี DOI' }).click()
    await expect(page.locator('#ref-journals th[aria-sort="descending"]')).toContainText('มี DOI')
    await expect(page.locator('#ref-top .srch-hit')).toHaveCount(10)
    await expect(page.locator('#ref-top .srch-hit').first()).toContainText('ถูกอ้าง 9 ครั้ง')
    const ris = page.waitForEvent('download')
    await page.getByRole('button', { name: /เป็น RIS$/ }).click()
    expect((await ris).suggestedFilename()).toBe('atlas-2026Q4-most-cited.ris')
    await expect(page.locator('#ref-flows tbody tr')).toHaveCount(5)
    await expect(page.locator('#ref-topics tbody tr').first().locator('.topic-link')).toBeVisible()
  },
  embedTopic: async (page) => {
    await expect(page.locator('h1')).toHaveText('AI เพื่อการศึกษา')
    await expect(page.locator('.embed-status .chip')).toBeVisible()
    await expect(page.locator('svg.tr')).toBeVisible()
    await expect(page.locator('header, nav, footer')).toHaveCount(0)
    await expect(page.locator('.embed-sample .phase-tag.is-sample')).toBeVisible()
    const attr = page.getByRole('link', { name: /TCI Research Atlas/ })
    await expect(attr).toHaveAttribute('target', '_blank')
    await expect(attr).toHaveAttribute('href', /#\/topics\/T000201\?lang=th$/)
    await page.goto(`${EXAMPLE}#/embed/topic/T999999`)
    await expect(page.locator('h1')).toHaveText('ไม่พบหัวข้อ T999999')
    await expect(page.getByRole('link', { name: /TCI Research Atlas/ })).toHaveAttribute('href', /#\/overview\?lang=th$/)
  },
  embedEmerging: async (page) => {
    await expect(page.locator('h1')).toHaveText('หัวข้อที่กำลังเกิดใหม่และควรจับตา')
    await expect(page.locator('header, nav, footer')).toHaveCount(0)
    const items = page.locator('.embed-list li')
    expect(await items.count()).toBeGreaterThan(0)
    expect(await items.count()).toBeLessThanOrEqual(10)
    await expect(items.first().locator('.chip')).toContainText('กำลังเกิดใหม่')
    await expect(items.first().getByRole('link')).toHaveAttribute('target', '_blank')
    await expect(page.getByRole('link', { name: /TCI Research Atlas/ })).toHaveAttribute('href', /#\/emerging\?lang=th$/)
  },
  // checks:end
}

/** Routes that must not scroll sideways at 360 px. */
const PHONE = ['/overview', '/emerging', '/topics/T000201', '/atlas', '/compare?ids=T000201,T000701', '/data', '/about', '/journals', '/journals/so02.example0', '/methods', '/changes', '/match', '/institutions', '/institutions/mu-a', '/regions', '/sdg', '/global', '/gaps', `/search?q=${encodeURIComponent('ผู้สูงอายุ')}`, '/galaxy', '/keywords', '/references', '/embed/topic/T000201', '/embed/emerging']

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

test('the offline file without the match index explains that /match needs the web edition', async ({ page }, info) => {
  const template = readFileSync('dist/offline-template.html', 'utf8')
  const slot = '<script type="application/json" id="atlas-data">null</script>'
  const bundle = bundleOf('example')
  delete bundle.files['match.json']                                         // export.offline_exclude (default)
  const file = info.outputPath('atlas-offline-nomatch.html')
  mkdirSync(dirname(file), { recursive: true })
  writeFileSync(file, template.replace(slot, () => `<script type="application/json" id="atlas-data">${JSON.stringify(bundle).replaceAll('</', '<\\/')}</script>`))
  await page.goto(`${pathToFileURL(file).href}#/match`)
  await expect(page.locator('h1')).toHaveText('วางบทคัดย่อของคุณ')
  await expect(page.locator('.empty-state')).toContainText('ฉบับออฟไลน์ไม่มีส่วนนี้')
  await expect(page.locator('.empty-state')).toContainText('ต้องใช้เว็บไซต์ออนไลน์')
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

test('the grouped navigation opens with the keyboard, closes with Escape and marks the current group', async ({ page }) => {
  await page.goto(`${EXAMPLE}#/overview`)
  const exec = page.getByRole('button', { name: 'สำหรับผู้บริหาร' })
  await expect(exec).toHaveAttribute('aria-expanded', 'false')
  await exec.focus()
  await page.keyboard.press('Enter')
  await expect(exec).toHaveAttribute('aria-expanded', 'true')
  await expect(page.locator('#nav-exec-menu a')).toHaveCount(6)
  await page.keyboard.press('Escape')
  await expect(exec).toHaveAttribute('aria-expanded', 'false')
  await expect(exec).toBeFocused()
  const editors = page.getByRole('button', { name: 'สำหรับบรรณาธิการ' })
  await editors.click()
  await page.locator('#nav-editors-menu').getByRole('link', { name: 'วารสาร' }).click()
  await expect(page).toHaveURL(/#\/journals$/)
  await expect(page.getByRole('button', { name: 'สำหรับบรรณาธิการ' })).toHaveClass(/is-active/)
  await expect(page.locator('#nav-editors-menu')).toBeHidden()
})

test('the footer leads to what next: cite opens the About page at its cite section', async ({ page }) => {
  await page.goto(`${EXAMPLE}#/overview`)
  const footer = page.locator('footer')
  await expect(footer.getByRole('link', { name: 'ดาวน์โหลดข้อมูล' })).toHaveAttribute('href', '#/data')
  await expect(footer.getByRole('link', { name: 'รอบก่อนหน้า' })).toHaveAttribute('href', '#/changes')
  await footer.getByRole('link', { name: 'อ้างอิง Atlas' }).click()
  await expect(page).toHaveURL(/#\/about$/)
  await expect(page.locator('#cite-h')).toBeFocused()
  await expect(page.locator('#cite-h')).toBeInViewport()
})

test('article search explains itself on a release without it and in the offline file', async ({ page }, info) => {
  await page.goto(`${EMPTY}#/search`)
  await expect(page.locator('h1')).toHaveText('ค้นหาบทความ')
  await expect(page.locator('.empty-state')).toContainText('รอบข้อมูลนี้ไม่มีส่วนนี้')
  const template = readFileSync('dist/offline-template.html', 'utf8')
  const slot = '<script type="application/json" id="atlas-data">null</script>'
  const bundle = bundleOf('example')
  for (const path of Object.keys(bundle.files)) if (path.startsWith('search/')) delete bundle.files[path]   // export.offline_exclude
  const file = info.outputPath('atlas-offline-nosearch.html')
  mkdirSync(dirname(file), { recursive: true })
  writeFileSync(file, template.replace(slot, () => `<script type="application/json" id="atlas-data">${JSON.stringify(bundle).replaceAll('</', '<\\/')}</script>`))
  await page.goto(`${pathToFileURL(file).href}#/search`)
  await expect(page.locator('h1')).toHaveText('ค้นหาบทความ')
  await expect(page.locator('.empty-state')).toContainText('ฉบับออฟไลน์ไม่มีส่วนนี้')
})

test('a module the pipeline skipped says why', async ({ page }) => {
  await page.goto(`${EMPTY}#/global`)
  await expect(page.locator('h1')).toHaveText('ไทยเทียบโลก')
  await expect(page.locator('.empty-state')).toContainText('ATLAS_OFFLINE')
})

test('the article galaxy explains itself on a release without it and in the offline file', async ({ page }, info) => {
  await page.goto(`${EMPTY}#/galaxy`)
  await expect(page.locator('h1')).toHaveText('แผนที่บทความทุกเรื่อง')
  await expect(page.locator('.empty-state')).toContainText('รอบข้อมูลนี้ไม่มีส่วนนี้')
  const template = readFileSync('dist/offline-template.html', 'utf8')
  const slot = '<script type="application/json" id="atlas-data">null</script>'
  const bundle = bundleOf('example')
  delete bundle.files['galaxy.json']   // export.offline_exclude
  const file = info.outputPath('atlas-offline-nogalaxy.html')
  mkdirSync(dirname(file), { recursive: true })
  writeFileSync(file, template.replace(slot, () => `<script type="application/json" id="atlas-data">${JSON.stringify(bundle).replaceAll('</', '<\\/')}</script>`))
  await page.goto(`${pathToFileURL(file).href}#/galaxy`)
  await expect(page.locator('h1')).toHaveText('แผนที่บทความทุกเรื่อง')
  await expect(page.locator('.empty-state')).toContainText('ฉบับออฟไลน์ไม่มีส่วนนี้')
})

test('keyword trends and references explain themselves on a release without them', async ({ page }) => {
  for (const [path, h1] of [['/keywords', 'แนวโน้มคำสำคัญ'], ['/references', 'การอ้างอิง']]) {
    await page.goto(`${EMPTY}#${path}`)
    await expect(page.locator('h1')).toHaveText(h1)
    await expect(page.locator('.empty-state')).toContainText('รอบข้อมูลนี้ไม่มีส่วนนี้')
  }
})

test('references: a skipped module gives its coverage reason; too few internal matches are explained in words', async ({ page }, info) => {
  const template = readFileSync('dist/offline-template.html', 'utf8')
  const slot = '<script type="application/json" id="atlas-data">null</script>'
  const write = (name: string, bundle: ReturnType<typeof bundleOf>) => {
    const file = info.outputPath(name)
    mkdirSync(dirname(file), { recursive: true })
    writeFileSync(file, template.replace(slot, () => `<script type="application/json" id="atlas-data">${JSON.stringify(bundle).replaceAll('</', '<\\/')}</script>`))
    return pathToFileURL(file).href
  }
  // low coverage: the pipeline leaves the module out and says why (Review Focus 3)
  const skipped = bundleOf('example')
  const manifest = skipped.files['manifest.json'] as { modules: string[]; skipped_modules?: Record<string, string> }
  manifest.modules = manifest.modules.filter((m) => m !== 'references')
  manifest.skipped_modules = { ...(manifest.skipped_modules ?? {}), references: 'reference coverage 31% of 18,234 articles 2020–2024 (< references.min_coverage 50%)' }
  delete skipped.files['references.json']
  await page.goto(`${write('atlas-offline-refs-skipped.html', skipped)}#/references`)
  await expect(page.locator('h1')).toHaveText('การอ้างอิง')
  await expect(page.locator('.empty-state')).toContainText('reference coverage 31%')
  // coverage fine, but too few citations inside the collection: those sections give way to a plain explanation
  const few = bundleOf('example')
  Object.assign(few.files['references.json'] as object, { internal: null, internal_reason: '12 references matched a corpus article (< references.min_internal_matches 20)' })
  await page.goto(`${write('atlas-offline-refs-few.html', few)}#/references`)
  await expect(page.locator('#ref-journals tbody tr')).toHaveCount(5)
  await expect(page.locator('#ref-internal .empty-state')).toContainText('จับคู่รายการอ้างอิงกับบทความในคลังได้น้อยเกินไป')
  await expect(page.locator('#ref-internal .empty-state')).toContainText('12 references matched')
  await expect(page.locator('#ref-flows')).toHaveCount(0)
})

test('feed links appear on /changes and the topic page when the site has Atom feeds', async ({ page }) => {
  await page.route('**/data/latest.json', async (route) => {
    const res = await route.fetch()
    await route.fulfill({ response: res, json: { ...(await res.json()), feeds: true } })
  })
  await page.goto(`${EXAMPLE}#/changes`)
  await expect(page.getByRole('link', { name: 'ติดตามรอบใหม่ (Atom/RSS)' })).toHaveAttribute('href', './data/feeds/releases.xml')
  await page.goto(`${EXAMPLE}#/topics/T000201`)
  await expect(page.getByRole('link', { name: 'ติดตามหัวข้อนี้ (Atom/RSS)' })).toHaveAttribute('href', './data/feeds/topics/T000201.xml')
})

test('the offline template is kept out of search engines', () => {
  expect(readFileSync('dist/offline-template.html', 'utf8')).toContain('<meta name="robots" content="noindex">')
})
