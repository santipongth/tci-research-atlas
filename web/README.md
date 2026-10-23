# TCI Research Atlas — เว็บ v2

เว็บ static (React 19 + Vite 7 + TypeScript + Tailwind 4, HashRouter) ที่อ่านข้อมูลรอบล่าสุด **ตอนเปิดหน้า** — ไม่มี server ไม่มี API key และไม่โหลดอะไรจากบริการภายนอกตอนใช้งาน (ฟอนต์ self-hosted, ไม่มี CDN/analytics, ไม่เรียก AI)
ดีไซน์: `../DESIGN.md` (ชนะ catalog ทั่วไปเสมอ) — โลก **"ข่าวข้อมูล" (data explainer)**: หน้าขึ้นด้วยคำถามเป็น h1 · คำตอบ 1 ประโยค · ตัวเลข 1 ตัว · กราฟที่เน้นจุดเดียว; ธีมสว่างธีมเดียว (ไม่มีโหมดมืด), ฟอนต์ Sarabun อย่างเดียว, น้ำเงิน TCI `#283894` + ส้ม TCI เฉพาะจุดเน้น; สัญญาทิศทาง `../.impeccable/surfaces/web-src.md`, ข้อมูลผลิตภัณฑ์ `../PRODUCT.md`
แบรนด์: `src/brand/brand.ts` จุดเดียว — โลโก้ TCI ที่แถบบน และ TCI · NECTEC · สวทช. ที่ส่วนท้าย (ไฟล์ใน `src/assets/brand/partners/`)

Node ≥ 22.12 (CI ใช้ 24)

## คำสั่ง

| คำสั่ง | ทำอะไร |
|---|---|
| `npm ci` | ติดตั้ง (ทุกเวอร์ชันล็อกไว้ใน `package-lock.json`) |
| `npm run dev` | dev server http://localhost:3000 อ่านข้อมูลสังเคราะห์จาก `fixtures/example/data` (เปลี่ยนด้วย env `ATLAS_DATA_DIR`) |
| `npm run build` | `tsc -b` + `dist/` (วางบน static host ใดก็ได้) + `dist/offline-template.html` (ต้นแบบไฟล์เดียวให้ `atlas publish`) · env `ATLAS_SITE_URL` = ที่อยู่สาธารณะสำหรับ SEO (ดูด้านล่าง) |
| `npm test` | unit tests (vitest) |
| `npm run lint` · `npx tsc -b` | ตรวจโค้ด |
| `npm run check:bundle` | หลัง build: entry chunk ≤ 180 KB gzip (`--budget <kb>`) และทุกหน้า/กราฟฝังที่ `App.tsx` โหลดด้วย `lazy()` ต้องเป็น chunk แยก |
| `npm run e2e` | Playwright หลัง build (ครั้งแรก `npx playwright install chromium`) — `e2e/smoke.spec.ts`: ทุกหน้า × รอบตัวอย่าง/รอบว่าง + axe, ไม่มีหน้าขาวเมื่อไม่มีข้อมูล, ป้ายข้อมูลตัวอย่าง, จอ 360 px ไม่เลื่อนข้าง, ไฟล์ออฟไลน์ไม่มี network request, โมดูลที่ข้ามอธิบายตัวเอง, เมนูด้วยแป้นพิมพ์ · `e2e/narrow.spec.ts`: จอ 360/390 px (เมนูมือถือ, h1 อยู่สูง, แผนที่) |
| `npm run fixtures` | สร้างรอบข้อมูลสังเคราะห์ใน `fixtures/` ใหม่ — CI ตรวจว่าไม่ drift |
| `npm run gen:types` | สร้าง `src/data/contract.ts` จาก `src/data/contract.schema.json` (หลัง `uv run atlas schema` ใน `pipeline/`) — CI ตรวจ drift |
| `npm run stage:demo -- dist` | วางรอบสังเคราะห์ลง `dist/` สำหรับเว็บสาธิต (ใส่ `robots noindex`; ไม่ยอมวางรอบที่ไม่ได้ติดป้ายตัวอย่าง) |
| `npm run brief:pdf -- [--data <โฟลเดอร์ data>] [--out <โฟลเดอร์>]` | พิมพ์หน้า `#/brief` เป็น `brief-th.pdf` และ `brief-en.pdf` (ฟอนต์ไทยฝังในไฟล์) · ไม่มีข้อมูลจะหยุดพร้อมข้อความ · ลองในเครื่อง: `--data fixtures/example/data` |
| `node scripts/serve.mjs --site dist [--data <dir>] [--port 4173]` | static server เล็ก ๆ สำหรับดูเว็บที่ build แล้ว (เช่น `--site ../deploy/<รอบ>/site`) |
| `node scripts/make-province-map.mjs <ne_admin1.geojson>` | สร้าง `src/geo/thProvinces.ts` (เส้นขอบ 77 จังหวัดจาก Natural Earth 1:10m admin-1 v5.1.2, สาธารณสมบัติ) — รันครั้งเดียว ไฟล์ที่ได้ commit แล้ว; geojson ~40 MB อยู่นอก repo (ดูหัวสคริปต์) |
| `npm run vendor:fonts` | คัดลอก Sarabun (woff2, OFL) เข้า `src/assets/fonts/` |

## ข้อมูลเข้าเว็บอย่างไร

```
web:      npm run build ──► dist/  (+ offline-template.html, robots.txt, sitemap.xml)
pipeline: uv run atlas publish -c config.yaml --site ../web/dist
          ──► dist/data/<release>/*.json · dist/data/latest.json · dist/atlas-offline.html (· dist/data/feeds/)
```

- รอบปกติใช้ `uv run atlas quarterly` (ใน `pipeline/`): build เว็บให้เมื่อยังไม่มี `dist/` (หรือ `--build-web`, ส่ง `publish.site_url` เป็น `ATLAS_SITE_URL`) → publish → คัดลอกทั้งเว็บไป `../deploy/<รอบ>/site/` + zip — ดู `../docs/OPERATIONS.md` §1
- เว็บอ่าน `./data/latest.json` → `./data/<release>/manifest.json` → ไฟล์หลัก (path สัมพัทธ์จาก `BASE_URL` = `./` จึงวางใต้ sub-path ได้ เช่น GitHub Pages) · `overview.json` ของรอบก่อนใช้แสดง Δ · `topics/<id>.json` โหลดเมื่อเปิดหัวข้อ
- ตรวจ schema major = 2 ด้วย zod (contract ปัจจุบัน 2.5 — ชนิดข้อมูลมาจาก `src/data/contract.ts` ที่ generate เท่านั้น ผ่าน `src/data/types.ts`)
- **อัปเดตรายไตรมาส = วางโฟลเดอร์ `data/` ใหม่ขึ้น host** (`deploy/atlas-data-<รอบ>.zip`) — ไม่ต้อง build เว็บใหม่ ไม่ต้องมี Node บนเครื่องผู้รัน
- `atlas-offline.html` = เว็บทั้งหมดในไฟล์เดียว เปิดจาก `file://` ได้โดยไม่ต่อเน็ต (ข้อมูลฝังใน `<script type="application/json" id="atlas-data">`); ไม่มี `match.json`, `search/`, `galaxy.json` — หน้า `/match` `/search` `/galaxy` ในไฟล์นี้บอกให้ใช้เว็บออนไลน์
- `dev` เสิร์ฟ `/data/*` จาก fixtures — `dist/` ที่ build แล้วไม่มีข้อมูลเลย (`public/data/` มีแค่ `.gitkeep`)

## หน้าไม่มีวันขาว

- โหลดข้อมูลไม่ได้ / schema ไม่ใช่ 2.x / ไฟล์เสีย → แถบแจ้งเหตุผล (`DataBanner`) — ไม่มีข้อมูล bundle สำรอง
- render พัง (chunk เก่าหลัง redeploy, ข้อมูลผิดรูป) → `ErrorBoundary` ใน `Layout` แทนเฉพาะพื้นที่หน้า (ส่วนหัว/เมนูยังอยู่) และ reload ครั้งเดียวเมื่อ chunk หาย; `main.tsx` ครอบทั้งแอป; กราฟฝังมี `EmbedBoundary` ของตัวเอง
- ไฟล์ module ที่ไม่มี หรือโมดูลที่ pipeline ข้าม (`manifest.skipped_modules`) → หน้าแสดง h1 พร้อมเหตุผลผ่าน `ModuleFile`
- รอบที่ `embedding_provider` เป็น `fixture` หรือ `lite` → ป้าย "ข้อมูลตัวอย่าง" ทุกหน้า (`PhaseBanner`)

## หน้า

เมนู (`src/components/Header.tsx`) จัดตาม **คำถามของผู้อ่าน** ไม่ใช่ตามกลุ่มผู้ใช้ — ทุกหน้าห่างไม่เกิน 2 คลิก; เมนูเดสก์ท็อปมีบรรทัดคำถามใต้ชื่อหน้า, มือถือรวมเป็นปุ่มเดียว

| กลุ่ม | หน้า |
|---|---|
| (ต้น) | `#/overview` ภาพรวม (เรื่องเล่าข้อมูล `StoryHero`, KPI, ประโยคเชิงนโยบาย, waffle สถานะ + forest plot, ผัง size × growth) · `#/brief` สรุปผู้บริหาร 1 หน้า (พิมพ์แล้วซ่อนส่วนหัว/เมนู) |
| อะไรกำลังมา | `#/story` 5 เรื่องน่ารู้รอบนี้ · `#/emerging` สถานะหัวข้อ · `#/keywords` แนวโน้มคำสำคัญ + อภิธานศัพท์ไทย↔อังกฤษ · `#/changes` อะไรเปลี่ยน (รวม/แยก/ยุติหัวข้อ) · `#/gaps` โอกาสที่ยังไม่มีใครทำ · `#/ideas` หัวข้อน่าทำ |
| ใครทำเรื่องอะไร | `#/institutions` + `#/institutions/:id` สถาบัน (ระดับสถาบันเท่านั้น) · `#/journals` + `#/journals/:id` วารสาร · `#/methods` วิธีวิจัย · `#/references` การอ้างอิง (+ "ถูกอ้างใน TCI") |
| ไทยอยู่ตรงไหน | `#/province` + `#/province/:code` งานวิจัยในจังหวัดของฉัน · `#/regions` แผนที่จังหวัด (มีมุมมองตารางทุกจังหวัด) · `#/global` ไทยเทียบโลก · `#/sdg` SDG และแผนชาติ |
| หางานวิจัย | `#/search` ค้นหาบทความ (CSV · RIS · BibTeX) · `#/atlas` แผนที่หัวข้อ · `#/galaxy` แผนที่บทความทุกเรื่อง (WebGL2) · `#/compare` เปรียบเทียบ 2–4 หัวข้อ · `#/match` วางบทคัดย่อ (คำนวณในเบราว์เซอร์ ข้อความไม่ออกจากเครื่อง) |
| (ท้าย) | `#/data` ข้อมูลเปิด · `#/about` อ่านตัวเลขอย่างไร (ขั้นตอน + ทางตัดสินสถานะ + นิยาม + changelog + อ้างอิง Atlas) |

นอกเมนู: `#/topics/:id` หน้าหัวข้อ · กราฟฝัง `#/embed/topic/:id` และ `#/embed/emerging` (นอก app shell มีลิงก์ที่มา) · หน้า 404
หน้าแรกที่โหลดพร้อม entry: overview, topics/:id, emerging, compare, data, about — หน้าอื่นทั้งหมด (รวม atlas และ brief) เป็น `React.lazy` และไฟล์ข้อมูลของหน้า lazy เป็น optional
สถานะตัวกรอง/การเลือกอยู่ใน URL เสมอ (`useUrlState`, เช่น `#/emerging?status=WATCH&sort=journals`) แชร์ลิงก์ได้

## ข้อมูลขนาดจริง

ออกแบบสำหรับหัวข้อ ~1,500 · วารสาร ~2,000 · สถาบัน ~10,000: ตารางยาวส่ง `limit` ให้ `DataTable`, รายการ/กราฟยาวใช้ `useCapped` + `ListMore` (แสดง 20–25 รายการ + "แสดงทั้งหมด (n)" — มุมมองตารางมีครบทุกแถว), ช่องของ `StatusWaffle` รวมหลายหัวข้อเมื่อเกิน 300 (`waffleUnit`), ป้ายชื่อบนแผนที่วางด้วยกล่องที่วัดจริง (`lib/labels.ts`); `/search` โหลด doc shard ≤ 6 ไฟล์ต่อคำค้น (`MAX_DOC_SHARDS`) และบอกผู้อ่านเมื่อผลมาจากบางส่วน

## SEO และการแชร์ลิงก์

`npm run build` (เฉพาะเว็บ ไม่ใช่ไฟล์ออฟไลน์) เติม canonical, Open Graph / Twitter card (`public/og-image.png` 1200×630), schema.org `WebSite` + `Organization` + `Dataset` และเขียน `robots.txt` + `sitemap.xml` จาก `ATLAS_SITE_URL` (ดีฟอลต์คือที่อยู่ GitHub Pages ของ repo — ตั้งให้ตรงเว็บจริงก่อน build) · `offline-template.html` ถูก disallow ใน robots · เว็บสาธิต (`stage:demo`) เป็น noindex · ขั้นตอนส่ง Google: `../docs/OPERATIONS.md` §22

## โครงสร้างโค้ด

```
src/App.tsx         routes (lazy แยก chunk) · src/main.tsx (ErrorBoundary ทั้งแอป)
src/brand/          brand.ts (โลโก้ TCI + พาร์ทเนอร์) · Wordmark.tsx
src/assets/         brand/partners/ (tci · nectec · nstda) · fonts/ (Sarabun woff2 + OFL)
src/styles/         tokens.css (ธีมสว่างธีมเดียว) · fonts.css · CSS ของแต่ละส่วน · palette.test.ts (CVD + contrast + ไม่มีบล็อกธีมมืด) · lineHeight.test.ts
src/strings/        ข้อความ UI ไทย + อังกฤษ (i18n.test.ts ตรวจครบคู่) · ไฟล์ของหน้า lazy อ่านด้วย useStrings(dict) ไม่เข้า dictionary กลาง
src/data/           contract.ts + contract.schema.json (generated) · types.ts · source.ts (Http | Embedded) · release.ts (loader) · atlasContext.ts
src/lib/            urlState/useUrlState · format · csv · i18n · definition (ค่าคงที่ของนิยามที่เว็บแสดง) · search (ตัดวรรณยุกต์ + Intl.Segmenter)
                    searchTokens (คู่ของ atlas.search_index — ตรึงด้วย pipeline/tests/fixtures/search_parity.json) · searchClient · citation (RIS/BibTeX ไม่มีผู้แต่ง)
                    matcher (ตรึงด้วย match_parity.json) · galaxyGl (WebGL2) · story · findings · labels · useCapped · chunkError …
src/components/     Layout · Header · Footer · ErrorBoundary · DataBanner · PhaseBanner · ModuleFile · Figure (คำบรรยาย · แผนภูมิ/ตาราง · วิธีอ่าน · CSV)
                    StatTile · DataTable (primary/limit) · ListMore · Term/TermDef · HowNote · SourceLine · CsvButton · Steps · PhoneFold · StatusLegend · ProvinceMap …
src/charts/         SVG เขียนเอง: forest · portfolio · trend · multi-line + infographic (StatusWaffle · DotPlot · BarRank · ArcNetwork · ColumnChart · MixBar/SplitBar
                    · OpportunityQuadrant · StatusFlow · LineageKey · GoalTiles · BridgePairs · JournalScatter · PeriodMix · ChecklistBars · SmallMultiples)
                    คณิตการจัดวางแบบ pure + test: infographic.ts · execLayout.ts · editorLayout.ts
src/features/atlas/ แผนที่หัวข้อ (mapSpace, terrain, TerrainMap, Gazetteer)
src/embed/          กราฟฝัง + EmbedBoundary + ปุ่มคัดลอก <iframe> และลิงก์ฟีด (แสดงเมื่อ latest.feeds === true)
src/geo/            thProvinces.ts (ใช้ใน ProvinceMap/ProvinceLocator ของ /regions และ /province เท่านั้น — ไม่อยู่ใน entry)
src/content/        changelog · method · dictionary
src/pages/          หน้าละไฟล์ (+ pages/overview/)
fixtures/           รอบข้อมูลสังเคราะห์ (example + empty) — ไม่ใช่ข้อมูลจริง
e2e/                smoke.spec.ts · narrow.spec.ts
scripts/            build/offline (finish-offline) · check-bundle · gen-types · make-fixtures · stage-demo-data · brief-pdf · serve · make-province-map · vendor-fonts
```

## กฎสำคัญ (ฉบับเต็มใน `../CLAUDE.md` §6 และ `../DESIGN.md`)

- สีมาจาก token ใน `src/styles/tokens.css` เท่านั้น (`var(--…)`, ไม่มี Tailwind class แบบ dynamic) · สถานะแสดงด้วยรูปทรง + สี + ชื่อเสมอ (▲ ◆ ● ▼ ■ วงประ) และสีสถานะใช้กับสถานะเท่านั้น
- ห้ามตัวเอียงในภาษาไทย · ทุกข้อความต้องมีทั้ง `th` และ `en`
- ข้อความ 2 ชั้น: ชั้นแรกภาษาง่ายขึ้นด้วยตัวอย่าง ใช้ปีแทนช่วง ไม่มีศัพท์สถิติ/รหัสสถานะ; รายละเอียดอยู่หลัง "วิธีอ่าน", `HowNote` หรือ `Term` (DESIGN.md "Copy voice")
- กราฟใหม่: SVG ใน `src/charts/` ใน `Figure` มีแท็บตาราง คำบรรยายมีเลข และบรรทัด "ที่มา:"; ป้าย ≥ 14 px, ink + น้ำเงินเดียว, ไม่มีข้อมูล = ลายเส้น/เส้นประ, ไม่มีข้อมูลที่เห็นเฉพาะตอน hover
- งบ entry ≤ 180 KB gzip: หน้า/ส่วนใหม่เป็น lazy และเก็บข้อความในไฟล์ strings ของตัวเอง (`useStrings`, เพิ่มใน `LAZY` ของ `i18n.test.ts`)
- ไฟล์ `.tsx` export ได้เฉพาะ component — hook/context/helper อยู่ในไฟล์ `.ts`
- ห้ามใช้ `href="#id"` ในหน้า (HashRouter) — ใช้ `scrollToId()`
- ห้ามเผยแพร่ชื่อผู้แต่ง/บทคัดย่อ และข้อความที่วางใน `/match` ห้ามออกจากเบราว์เซอร์ (ไม่อยู่ใน URL, storage หรือ request)
- ห้าม commit ข้อมูลจริง — repo มีแต่ `fixtures/` ที่สังเคราะห์ขึ้น

## เว็บสาธิตและเว็บจริงบน GitHub Pages

`.github/workflows/pages.yml` รันเมื่อผู้ดูแลกด **Run workflow** เท่านั้น (push ไม่ทับรอบที่ขึ้นอยู่):

- `data_release` ว่าง → build แล้ว `npm run stage:demo -- dist` = **รอบสังเคราะห์** (ป้าย "ข้อมูลตัวอย่าง" ทุกหน้า, noindex)
- `data_release = data-<รอบ>` → ดาวน์โหลด `atlas-site-data-<รอบ>.zip` จาก GitHub Release ที่สร้างด้วย `bash scripts/package_release.sh --upload` (หลัง `atlas publish --site web/dist` หรือ `atlas quarterly`) แล้วแตกลง `dist/` — ปฏิเสธ zip ที่เป็นข้อมูลตัวอย่าง; ไม่มีข้อมูลใด commit เข้า repo
- host อื่น (IIS, Apache, Nginx, S3): อัปโหลด `../deploy/<รอบ>/site/` หรือแตก zip จาก `../deploy/` — ดู `../docs/OPERATIONS.md` §1.5
