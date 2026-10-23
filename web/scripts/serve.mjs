#!/usr/bin/env node
// Tiny static server for the built site (Playwright smoke tests, the PDF brief).
//   node scripts/serve.mjs --site dist [--data fixtures/example/data] [--port 4173]
// With --data, /data/* comes from that folder instead of <site>/data, so tests never copy data into dist/.
import { readFile, stat } from 'node:fs/promises'
import { createServer } from 'node:http'
import { extname, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const TYPES = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.png': 'image/png', '.xml': 'application/xml; charset=utf-8',
  '.pdf': 'application/pdf', '.txt': 'text/plain; charset=utf-8',
}

function inside(root, rel) {
  const base = resolve(root)
  const file = resolve(base, `.${rel}`)
  return file === base || file.startsWith(base + sep) ? file : null
}

export function startServer({ site, data = null, port = 4173 }) {
  const server = createServer(async (req, res) => {
    try {
      let rel = decodeURIComponent(new URL(req.url ?? '/', 'http://localhost').pathname)
      let root = site
      if (data && rel.startsWith('/data/')) {
        root = data
        rel = rel.slice('/data'.length)
      }
      if (rel.endsWith('/')) rel += 'index.html'
      const file = inside(root, rel)
      const ok = file ? await stat(file).then((s) => s.isFile(), () => false) : false
      if (!ok) {
        res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' })
        res.end('not found')
        return
      }
      res.writeHead(200, { 'content-type': TYPES[extname(file)] ?? 'application/octet-stream', 'cache-control': 'no-cache' })
      res.end(await readFile(file))
    } catch (e) {
      res.writeHead(500, { 'content-type': 'text/plain; charset=utf-8' })
      res.end(String(e))
    }
  })
  return new Promise((done) => server.listen(port, '127.0.0.1', () => done(server)))
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = {}
  for (let i = 2; i < process.argv.length; i += 2) args[process.argv[i].replace(/^--/, '')] = process.argv[i + 1]
  const server = await startServer({ site: args.site ?? 'dist', data: args.data ?? null, port: Number(args.port ?? 4173) })
  console.log(`[serve] http://127.0.0.1:${server.address().port}/  site=${args.site ?? 'dist'}${args.data ? ` data=${args.data}` : ''}`)
}
