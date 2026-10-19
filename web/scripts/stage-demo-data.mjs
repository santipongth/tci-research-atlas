#!/usr/bin/env node
// Put the SYNTHETIC example release into a built site for the public demo (GitHub Pages):
//   npm run build && npm run stage:demo -- dist
// → <site>/data/{latest.json, 2026Q3/, 2026Q4/} and <site>/atlas-offline.html (the offline edition with the same data).
// Refuses a release that is not labelled as sample data (manifest.embedding_provider fixture | lite), so the
// "ข้อมูลตัวอย่าง / Sample data" banner always shows on the demo. Real releases go through `uv run atlas publish --site`.
import { cpSync, existsSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import { dirname, join, relative, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const web = join(dirname(fileURLToPath(import.meta.url)), '..')
const site = resolve(process.argv[2] ?? join(web, 'dist'))
const src = join(web, 'fixtures', 'example', 'data')
const fail = (msg) => {
  console.error(`[demo] ${msg}`)
  process.exit(1)
}
if (!existsSync(join(site, 'index.html'))) fail(`${site} is not a built site — run npm run build first`)
const latest = JSON.parse(readFileSync(join(src, 'latest.json'), 'utf8'))
const manifest = JSON.parse(readFileSync(join(src, latest.path), 'utf8'))
if (!['fixture', 'lite'].includes(manifest.embedding_provider)) fail('the demo release must be sample data (embedding_provider fixture | lite)')

cpSync(src, join(site, 'data'), { recursive: true })

const walk = (dir) => readdirSync(dir).flatMap((n) => (statSync(join(dir, n)).isDirectory() ? walk(join(dir, n)) : [join(dir, n)]))
const root = join(src, latest.release)
const files = Object.fromEntries(walk(root).map((p) => [relative(root, p).split(sep).join('/'), JSON.parse(readFileSync(p, 'utf8'))]))
const template = join(site, 'offline-template.html')
if (existsSync(template)) {
  const slot = '<script type="application/json" id="atlas-data">null</script>'
  const html = readFileSync(template, 'utf8')
  if (html.split(slot).length !== 2) fail('offline-template.html must contain exactly one empty atlas-data slot')
  const payload = JSON.stringify({ latest, files }).replaceAll('</', '<\\/')
  writeFileSync(join(site, 'atlas-offline.html'), html.replace(slot, () => `<script type="application/json" id="atlas-data">${payload}</script>`))
}
console.log(`[demo] sample release ${latest.release} → ${join(site, 'data')}${existsSync(template) ? ' + atlas-offline.html' : ''}`)
