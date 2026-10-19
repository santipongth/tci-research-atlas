#!/usr/bin/env node
// After `vite build --mode offline`: check the single-file build against the `atlas publish` contract
// (exactly one empty atlas-data slot, everything inlined, nothing fetched from the network),
// then move it to dist/offline-template.html.
import { readFileSync, rmSync, statSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const web = join(dirname(fileURLToPath(import.meta.url)), '..')
const src = join(web, 'dist-offline', 'index.html')
const out = join(web, 'dist', 'offline-template.html')
const html = readFileSync(src, 'utf8')
const OPEN = '<script type="application/json" id="atlas-data">'
const fail = (msg) => {
  console.error(`[offline] ${msg}`)
  process.exit(1)
}
if (html.split(OPEN).length !== 2) fail(`expected exactly one ${OPEN}`)
if (!html.includes(`${OPEN}null</script>`)) fail('the atlas-data slot must contain null')
const remote = html.match(/\b(?:src|href)\s*=\s*["'](?:https?:)?\/\/[^"']+/gi)
if (remote) fail(`external references: ${remote.join(', ')}`)
if (/<script[^>]+\bsrc\s*=/i.test(html) || /<link[^>]+rel=["']?stylesheet/i.test(html)) fail('scripts and styles must be inlined')
writeFileSync(out, html)
rmSync(join(web, 'dist-offline'), { recursive: true, force: true })
console.log(`[offline] ${out} (${Math.round(statSync(out).size / 1024)} KB)`)
