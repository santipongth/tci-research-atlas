#!/usr/bin/env node
// Bundle budget for the Pages build (run after `npm run build`):
//   * the entry chunk named in dist/index.html stays under the budget, gzip (default 180 KB, or --budget <kb>)
//   * every page App.tsx loads with lazy(() => import('./pages/X')) is its own chunk (not in the first download)
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { gzipSync } from 'node:zlib'

const LAZY = [...readFileSync(join('src', 'App.tsx'), 'utf8').matchAll(/lazy\(\(\) => import\('\.\/pages\/(\w+)'\)\)/g)].map((m) => m[1])
const arg = process.argv.indexOf('--budget')
const budget = Number(arg > 0 ? process.argv[arg + 1] : 180)
const html = readFileSync(join('dist', 'index.html'), 'utf8')
const entry = /src="\.\/assets\/([^"]+\.js)"/.exec(html)?.[1]
if (!entry) throw new Error('no entry script in dist/index.html — run npm run build first')
const assets = readdirSync(join('dist', 'assets'))
const kb = (f) => gzipSync(readFileSync(join('dist', 'assets', f))).length / 1024
const size = kb(entry)
const missing = LAZY.filter((name) => !assets.some((f) => f.startsWith(`${name}-`) && f.endsWith('.js')))
console.log(`[bundle] entry ${entry}: ${size.toFixed(1)} KB gzip (budget ${budget} KB)`)
for (const f of assets.filter((a) => LAZY.some((n) => a.startsWith(`${n}-`)))) console.log(`[bundle] lazy ${f}: ${kb(f).toFixed(1)} KB gzip`)
if (missing.length) {
  console.error(`[bundle] not split into lazy chunks: ${missing.join(', ')}`)
  process.exit(1)
}
if (size > budget) {
  console.error(`[bundle] entry chunk is over budget by ${(size - budget).toFixed(1)} KB`)
  process.exit(1)
}
