import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { createReadStream, existsSync, statSync } from 'node:fs'
import { resolve, sep } from 'node:path'
import { defineConfig, type Plugin } from 'vite'
import { viteSingleFile } from 'vite-plugin-singlefile'

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

/**
 * Search and sharing metadata for the web build (never the offline file, which must not reference any other host):
 * canonical URL, Open Graph / Twitter cards with public/og-image.png, schema.org WebSite + Organization + Dataset
 * (Google Dataset Search), and robots.txt + sitemap.xml. ATLAS_SITE_URL is the public address of the site.
 * The synthetic demo stays out of search engines: `npm run stage:demo` adds a robots noindex meta.
 */
function atlasSeo(siteUrl: string): Plugin {
  const site = siteUrl.endsWith('/') ? siteUrl : `${siteUrl}/`
  const NL = String.fromCharCode(10)
  const title = 'TCI Research Atlas — แผนที่งานวิจัยไทย | หัวข้อวิจัยไหนกำลังมา'
  const description = 'ดูว่างานวิจัยไทยเรื่องไหนกำลังมา เรื่องไหนลดลง แต่ละจังหวัดทำวิจัยเรื่องอะไร สถาบันและวารสารไหนทำอะไร และไทยเทียบกับโลกอย่างไร จากบทความในวารสารไทยที่อยู่ในฐาน TCI อัปเดตทุก 3 เดือน ดาวน์โหลดข้อมูลได้ฟรี'
  const ld = [
    { '@context': 'https://schema.org', '@type': 'WebSite', name: 'TCI Research Atlas', alternateName: 'แผนที่ภูมิทัศน์งานวิจัยไทย', url: site, inLanguage: ['th', 'en'], publisher: { '@id': `${site}#tci` } },
    { '@context': 'https://schema.org', '@type': 'Organization', '@id': `${site}#tci`, name: 'ศูนย์ดัชนีการอ้างอิงวารสารไทย (Thai-Journal Citation Index Centre, TCI)', alternateName: 'TCI', url: 'https://tci-thailand.org/' },
    {
      '@context': 'https://schema.org', '@type': 'Dataset', name: 'TCI Research Atlas: หัวข้อวิจัยไทยและแนวโน้มการเติบโต',
      alternateName: 'TCI Research Atlas: Thai research topics and their growth',
      description: 'หัวข้อวิจัยจากบทความในวารสารไทยที่อยู่ในฐาน TCI พร้อมสถานะการเติบโต (กำลังเกิดใหม่ จับตา กำลังมาแรง ลดลง คงที่) จำนวนบทความรายปี วารสาร สถาบัน จังหวัด และเป้าหมาย SDG อัปเดตทุกไตรมาส',
      url: site, creator: { '@id': `${site}#tci` }, publisher: { '@id': `${site}#tci` },
      license: 'https://creativecommons.org/licenses/by/4.0/', isAccessibleForFree: true, inLanguage: ['th', 'en'],
      spatialCoverage: { '@type': 'Place', name: 'Thailand' },
      keywords: ['งานวิจัยไทย', 'หัวข้อวิจัย', 'TCI', 'ThaiJO', 'วารสารไทย', 'research trends', 'Thailand', 'bibliometrics'],
      distribution: [{ '@type': 'DataDownload', encodingFormat: 'application/json', contentUrl: `${site}data/latest.json` }],
    },
  ]
  const esc = (v: string) => v.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;')
  const meta = (attr: 'name' | 'property', key: string, value: string) => `<meta ${attr}="${key}" content="${esc(value)}" />`
  // JSON inside <script>: no "<" may appear, so "</script>" can never close it early
  const jsonLd = JSON.stringify(ld).split('<').join('\\u003c')
  return {
    name: 'atlas-seo',
    apply: 'build',
    transformIndexHtml(html) {
      const head = [
        `<link rel="canonical" href="${site}" />`,
        meta('name', 'robots', 'index, follow, max-image-preview:large'),
        meta('property', 'og:type', 'website'),
        meta('property', 'og:site_name', 'TCI Research Atlas'),
        meta('property', 'og:title', title),
        meta('property', 'og:description', description),
        meta('property', 'og:url', site),
        meta('property', 'og:image', `${site}og-image.png`),
        meta('property', 'og:image:width', '1200'),
        meta('property', 'og:image:height', '630'),
        meta('property', 'og:image:alt', 'TCI Research Atlas: งานวิจัยไทย เรื่องไหนกำลังมา'),
        meta('property', 'og:locale', 'th_TH'),
        meta('property', 'og:locale:alternate', 'en_US'),
        meta('name', 'twitter:card', 'summary_large_image'),
        meta('name', 'twitter:title', title),
        meta('name', 'twitter:description', description),
        meta('name', 'twitter:image', `${site}og-image.png`),
        `<script type="application/ld+json">${jsonLd}</script>`,
      ].join(`${NL}    `)
      return html
        .replace(/<title>[^<]*<\/title>/, `<title>${esc(title)}</title>`)
        .replace(/<meta name="description" content="[^"]*" \/>/, meta('name', 'description', description))
        .replace('</head>', `  ${head}${NL}  </head>`)
    },
    generateBundle() {
      const robots = ['User-agent: *', 'Allow: /', 'Disallow: /offline-template.html', '', `Sitemap: ${site}sitemap.xml`, '']
      this.emitFile({ type: 'asset', fileName: 'robots.txt', source: robots.join(NL) })
      const today = new Date().toISOString().slice(0, 10)
      const sitemap = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        `  <url><loc>${site}</loc><lastmod>${today}</lastmod><changefreq>monthly</changefreq><priority>1.0</priority></url>`,
        '</urlset>',
        '',
      ]
      this.emitFile({ type: 'asset', fileName: 'sitemap.xml', source: sitemap.join(NL) })
    },
  }
}

// base './' — the site works from any sub-path (GitHub Pages) and data is fetched relative to it.
// `vite build --mode offline` makes the single-file edition (dist-offline/index.html → dist/offline-template.html).
export default defineConfig(({ mode }) => {
  const offline = mode === 'offline'
  return {
    base: './',
    plugins: [react(), tailwindcss(), atlasDevData(process.env.ATLAS_DATA_DIR ?? 'fixtures/example/data'), ...(offline ? [viteSingleFile({ removeViteModuleLoader: true })] : [atlasSeo(process.env.ATLAS_SITE_URL ?? 'https://santipongth.github.io/tci-research-atlas/')])],
    build: { outDir: offline ? 'dist-offline' : 'dist', emptyOutDir: true },
    server: { port: 3000 },
  }
})
