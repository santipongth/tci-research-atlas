import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { createReadStream, existsSync, statSync } from 'node:fs'
import { resolve, sep } from 'node:path'
import { defineConfig, type Plugin } from 'vite'

/** `npm run dev` serves /data/* from fixtures (or ATLAS_DATA_DIR) — the built site never contains data. */
function atlasDevData(dir: string): Plugin {
  const root = resolve(dir)
  return {
    name: 'atlas-dev-data',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use('/data', (req, res) => {
        const rel = decodeURIComponent((req.url ?? '/').split('?')[0])
        const file = resolve(root, `.${rel}`)
        if (!file.startsWith(root + sep) || !existsSync(file) || !statSync(file).isFile()) {
          res.statusCode = 404
          res.end('not found')
          return
        }
        res.setHeader('Content-Type', 'application/json; charset=utf-8')
        createReadStream(file).pipe(res)
      })
    },
  }
}

// base './' — the site works from any sub-path (GitHub Pages) and data is fetched relative to it.
export default defineConfig({
  base: './',
  plugins: [react(), tailwindcss(), atlasDevData(process.env.ATLAS_DATA_DIR ?? 'fixtures/example/data')],
  server: { port: 3000 },
})
