#!/usr/bin/env node
// Print the executive brief — the overview dashboard's print layout (#/overview) — to A4 PDFs in Thai and English
// with Playwright's Chromium.
//   npm run build && npm run brief:pdf -- [--site dist] [--data <release data folder>] [--out dist]
// Without --data the site's own data/ folder is used (after `uv run atlas publish --site dist`);
// for a local try-out with the synthetic release: npm run brief:pdf -- --data fixtures/example/data
// The page uses the site's self-hosted Sarabun, so the Thai fonts are embedded in the PDF.
/* global document */
import { chromium } from '@playwright/test'
import { existsSync, mkdirSync } from 'node:fs'
import { join } from 'node:path'
import { startServer } from './serve.mjs'

const USAGE = 'usage: npm run brief:pdf -- [--site dist] [--data <release data folder>] [--out <folder>]'
const KNOWN = new Set(['site', 'data', 'out'])
const args = {}
const argv = process.argv.slice(2)
if (argv.includes('--help') || argv.includes('-h')) {
  console.log(USAGE)
  process.exit(0)
}
for (let i = 0; i < argv.length; i++) {
  const key = argv[i].startsWith('--') ? argv[i].slice(2) : ''
  if (!KNOWN.has(key) || argv[i + 1] === undefined || argv[i + 1].startsWith('--')) {
    console.error(`[brief] unexpected argument "${argv[i]}"\n${USAGE}`)
    process.exit(2)
  }
  args[key] = argv[++i]
}
const site = args.site ?? 'dist'
const out = args.out ?? site
if (!existsSync(join(site, 'index.html'))) {
  console.error(`[brief] ${join(site, 'index.html')} not found — run npm run build first`)
  process.exit(1)
}
const server = await startServer({ site, data: args.data ?? null, port: 0 }) // port 0: never collides with a running server
const { port } = server.address()
const base = `http://127.0.0.1:${port}`
// Pre-flight: no release to print means no point launching Chromium and waiting for a selector.
const probe = await fetch(`${base}/data/latest.json`).catch(() => null)
if (!probe?.ok) {
  server.close()
  console.error('[brief] No data found: pass --data <release data folder> or run `uv run atlas publish --site <dir>` (sample: --data fixtures/example/data)')
  process.exit(1)
}
mkdirSync(out, { recursive: true })
const browser = await chromium.launch()
try {
  for (const lang of ['th', 'en']) {
    const page = await browser.newPage()
    await page.emulateMedia({ media: 'print', colorScheme: 'light', reducedMotion: 'reduce' })
    await page.goto(`${base}/#/overview?lang=${lang}`)
    await page.waitForSelector('.kpi', { timeout: 20_000 })
    // the province map and institution cards load on demand: wait until no card still says "loading"
    await page.waitForFunction(() => !document.querySelector('main [role="status"].loading'), null, { timeout: 20_000 })
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
