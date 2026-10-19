#!/usr/bin/env node
// Print the executive brief (#/brief) to A4 PDFs in Thai and English with Playwright's Chromium.
//   npm run build && npm run brief:pdf -- [--site dist] [--data fixtures/example/data] [--out dist]
// Without --data the site's own data/ folder is used (after `uv run atlas publish --site dist`).
// The page uses the site's self-hosted Sarabun, so the Thai fonts are embedded in the PDF.
/* global document */
import { chromium } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { join } from 'node:path'
import { startServer } from './serve.mjs'

const args = {}
for (let i = 2; i < process.argv.length; i += 2) args[process.argv[i].replace(/^--/, '')] = process.argv[i + 1]
const site = args.site ?? 'dist'
const out = args.out ?? site
mkdirSync(out, { recursive: true })
const server = await startServer({ site, data: args.data ?? null, port: Number(args.port ?? 4180) })
const { port } = server.address()
const browser = await chromium.launch()
try {
  for (const lang of ['th', 'en']) {
    const page = await browser.newPage()
    await page.emulateMedia({ media: 'print', colorScheme: 'light', reducedMotion: 'reduce' })
    await page.goto(`http://127.0.0.1:${port}/#/brief?lang=${lang}`)
    await page.waitForSelector('[data-brief-ready="true"]', { timeout: 20_000 })
    await page.evaluate(async () => {
      await document.fonts.ready
      return true
    })
    const file = join(out, `brief-${lang}.pdf`)
    await page.pdf({ path: file, format: 'A4', printBackground: true, preferCSSPageSize: true })
    console.log(`[brief] ${file}`)
    await page.close()
  }
} finally {
  await browser.close()
  server.close()
}
