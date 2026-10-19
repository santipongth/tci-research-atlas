#!/usr/bin/env node
// Copy the Sarabun files the Atlas ships (Thai + Latin subsets, weights 400/600/700, woff2 only)
// and the SIL OFL 1.1 licence from @fontsource/sarabun into src/assets/fonts/.
// Run after changing the font set:  npm run vendor:fonts
import { copyFileSync, mkdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const web = join(dirname(fileURLToPath(import.meta.url)), '..')
const pkg = join(web, 'node_modules', '@fontsource', 'sarabun')
const out = join(web, 'src', 'assets', 'fonts')
mkdirSync(out, { recursive: true })
for (const subset of ['thai', 'latin']) {
  for (const weight of [400, 600, 700]) {
    const name = `sarabun-${subset}-${weight}-normal.woff2`
    copyFileSync(join(pkg, 'files', name), join(out, name))
  }
}
copyFileSync(join(pkg, 'LICENSE'), join(out, 'OFL.txt'))
console.log(`[fonts] Sarabun (thai+latin × 400/600/700) → ${out}`)
