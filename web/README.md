# TCI Research Atlas — เว็บ v2

เว็บ static (React 19 + Vite 7 + TypeScript + Tailwind 4, HashRouter) ที่อ่านข้อมูลรอบล่าสุด **ตอนเปิดหน้า** — ไม่มี server ไม่มี API key และไม่โหลดอะไรจากบริการภายนอกตอนใช้งาน (ฟอนต์ self-hosted, ไม่มี CDN/analytics, ไม่เรียก AI)
ดีไซน์: `../DESIGN.md` (ชนะ catalog ทั่วไปเสมอ) — โลก **"TCI dashboard"** (เจ้าของเลือก 2026-10-24): เมนูซ้ายสีขาว (`SideNav`; มือถือเปิดเป็น drawer จากปุ่มเมนู) · แถบหัวสีขาวทุกหน้า (`PageBar`: ชื่อหน้า · บรรทัดย่อ 1 บรรทัด · ปุ่ม · ป้ายรอบ + ป้าย "ทดลองใช้"/"ข้อมูลตัวอย่าง") · พื้นงานเทาอมฟ้า `--canvas` (`#f3f5fa`) กับการ์ดขาวมุมโค้งในกริด 12 คอลัมน์ (`DashGrid`) · ตัวอักษรขนาดกะทัดรัด; ธีมสว่างธีมเดียว (ไม่มีโหมดมืด), ฟอนต์ Sarabun อย่างเดียว, น้ำเงิน TCI `#283894` + ส้ม TCI เฉพาะจุดเน้น; สัญญาทิศทาง `../.impeccable/surfaces/web-src.md`, ข้อมูลผลิตภัณฑ์ `../PRODUCT.md`
แบรนด์: `src/brand/brand.ts` จุดเดียว — โลโก้ TCI ที่หัวเมนูซ้าย (มือถือ: แถบบน) และ TCI · NECTEC · สวทช. ที่ส่วนท้าย (ไฟล์ใน `src/assets/brand/partners/`)

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
| `npm run e2e` | Playwright หลัง build (ครั้งแรก `npx playwright install chromium`) — `e2e/smoke.spec.ts`: ทุกหน้า × รอบตัวอย่าง/รอบว่าง + axe, ไม่มีกล่องค้นหาในหน้าใด, ลิงก์หน้าเก่าพาไปหน้าที่รับเนื้อหาแทน, ไม่มีหน้าขาวเมื่อไม่มีข้อมูล, ป้ายข้อมูลตัวอย่างที่แถบหัว, จอ 360 px ไม่เลื่อนข้าง, เมนูซ้ายบอกหน้าปัจจุบัน, ไฟล์ออฟไลน์ไม่มี network request, โมดูลที่ข้ามอธิบายตัวเอง, ลิงก์ฟีด · `e2e/narrow.spec.ts`: จอ 360/390 px (ปุ่มเมนูเปิด drawer, h1 อยู่สูง, ผัง size × growth, แผนที่) |
| `npm run fixtures` | สร้างรอบข้อมูลสังเคราะห์ใน `fixtures/` ใหม่ — CI ตรวจว่าไม่ drift |
| `npm run gen:types` | สร้าง `src/data/contract.ts` จาก `src/data/contract.schema.json` (หลัง `uv run atlas schema` ใน `pipeline/`) — CI ตรวจ drift |
| `npm run stage:demo -- dist` | วางรอบสังเคราะห์ลง `dist/` สำหรับเว็บสาธิต (ใส่ `robots noindex`; ไม่ยอมวางรอบที่ไม่ได้ติดป้ายตัวอย่าง) |
| `npm run brief:pdf -- [--data <โฟลเดอร์ data>] [--out <โฟลเดอร์>]` | พิมพ์หน้า `#/overview` (หน้าภาพรวม = สรุปผู้บริหาร, A4 2 หน้า) เป็น `brief-th.pdf` และ `brief-en.pdf` (ฟอนต์ไทยฝังในไฟล์) · ไม่มีข้อมูลจะหยุดพร้อมข้อความ · ลองในเครื่อง: `--data fixtures/example/data` |
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
- `atlas-offline.html` = เว็บทั้งหมดในไฟล์เดียว เปิดจาก `file://` ได้โดยไม่ต่อเน็ต (ข้อมูลฝังใน `<script type="application/json" id="atlas-data">`); ไม่มี `search/`, `galaxy.json` (และ `match.json` ถ้าเปิดสร้างไว้) — หน้า `/galaxy` ในไฟล์นี้บอกให้ใช้เว็บออนไลน์
- `dev` เสิร์ฟ `/data/*` จาก fixtures — `dist/` ที่ build แล้วไม่มีข้อมูลเลย (`public/data/` มีแค่ `.gitkeep`)

## หน้าไม่มีวันขาว

- โหลดข้อมูลไม่ได้ / schema ไม่ใช่ 2.x / ไฟล์เสีย → แถบแจ้งเหตุผล (`DataBanner`) — ไม่มีข้อมูล bundle สำรอง
- render พัง (chunk เก่าหลัง redeploy, ข้อมูลผิดรูป) → `ErrorBoundary` ใน `Layout` แทนเฉพาะพื้นที่หน้า (ส่วนหัว/เมนูยังอยู่) และ reload ครั้งเดียวเมื่อ chunk หาย; `main.tsx` ครอบทั้งแอป; กราฟฝังมี `EmbedBoundary` ของตัวเอง
- ไฟล์ module ที่ไม่มี หรือโมดูลที่ pipeline ข้าม (`manifest.skipped_modules`) → หน้าที่ใช้ไฟล์เดียว (journals, galaxy) แสดง h1 พร้อมเหตุผลผ่าน `ModuleFile`; dashboard ที่ใช้หลายไฟล์ (overview, places, goals) แสดงเฉพาะการ์ดของไฟล์ที่มี และบอกเหตุผลเมื่อไม่มีสักไฟล์ (เช่น `/goals` เมื่อข้าม `global`)
- รอบที่ `embedding_provider` เป็น `fixture` หรือ `lite` → ป้าย "ข้อมูลตัวอย่าง" ที่แถบหัวทุกหน้า (`PageBar`)

## หน้า

เมนูซ้าย (`src/components/dashboard/SideNav.tsx`, ห่อด้วย `Layout`) มี 3 กลุ่ม — หน้าที่เลือกอยู่บนพื้นน้ำเงินอ่อน; มือถือกดปุ่มเมนูแล้วเปิดเป็น drawer (`Drawer`, ปิดด้วย Esc)

| กลุ่ม | หน้า |
|---|---|
| แดชบอร์ด | `#/overview` ภาพรวม (KPI 4 การ์ด, หัวข้อแยกตามสถานะ, หัวข้อที่โตเร็วที่สุด, จังหวัดและสถาบัน, ข้อสรุปรอบนี้, ตัวเลขอื่น; เป็นสรุปผู้บริหารด้วย — ปุ่ม "พิมพ์ / บันทึก PDF" พิมพ์ได้ A4 2 หน้า) · `#/topics` หัวข้อวิจัย (ปุ่มสถานะเป็นตัวกรอง, หัวข้อแต่ละสถานะเรียงตามการเติบโตหรือขนาดทีละ 10, อะไรเปลี่ยนจากรอบก่อน, ผัง size × growth, คำสำคัญที่กำลังโต, หัวข้อที่มีสถาบันทำน้อย, หัวข้อต่อสาขา) · `#/places` สถาบันและจังหวัด (KPI, แผนที่จังหวัด + 10 อันดับ, บทความตามภาค, ประเทศที่ร่วมงาน, อันดับสถาบัน, เส้นความร่วมมือ, ทุกจังหวัดตามภาคเป็นลิงก์) · `#/journals` วารสาร (KPI, ผังความครบของข้อมูล × ผู้เขียนจากสถาบันเจ้าของ, tier, อันดับวารสาร, หัวข้อน่าทำฉบับพิเศษ, วิธีวิจัยที่ใช้มาก, บทความที่ถูกอ้างใน TCI มากที่สุด) · `#/goals` เป้าหมายชาติและโลก (ช่องเป้าหมาย SDG/BCG/แผนชาติ พร้อมปุ่มสลับกรอบ, เป้าหมายที่ยังไม่มีงานวิจัย, ผังไทยเทียบโลก, เรื่องที่โลกโตเร็วแต่ไทยยังทำน้อย, เรื่องที่ไทยทำมากกว่าโลก, หัวข้อที่พึ่งสถาบันหรือวารสารเดียว; บอกเหตุผลเมื่อข้าม `global`) |
| แผนที่ | `#/atlas` แผนที่หัวข้อ · `#/galaxy` แผนที่บทความทุกเรื่อง (WebGL2) |
| คำอธิบาย | `#/about` อ่านตัวเลขอย่างไร (ที่รวมคำอธิบายทั้งหมด: ขั้นตอน + ทางตัดสินสถานะ + นิยาม + changelog + อ้างอิง Atlas) |

หน้ารายละเอียด (การ์ดในกริด เข้าจาก "ดูทั้งหมด" หรือชื่อในรายการ): `#/topics/:id` หัวข้อ · `#/journals/:id` วารสาร · `#/institutions/:id` สถาบัน (ระดับสถาบันเท่านั้น) · `#/province/:code` จังหวัด
นอกเมนู: กราฟฝัง `#/embed/topic/:id` และ `#/embed/emerging` (นอก app shell มีลิงก์ที่มา; กราฟ emerging ลิงก์ไป `#/topics`) · หน้า 404
**หน้าที่เลิกใช้ (2026-10-24)** เปลี่ยนทางด้วย `MovedTo` ใน `App.tsx` ลิงก์เก่าและฟีดจึงไม่เสีย: `/emerging` → `/topics` (คง `?status=`) · `/changes` `/gaps` `/ideas` `/keywords` → `/topics` · `/story` `/brief` → `/overview` · `/institutions` `/regions` `/province` → `/places` · `/methods` `/references` → `/journals` · `/sdg` `/global` → `/goals` · `/search` `/compare` `/match` `/data` → `/overview`
โหลดพร้อม entry: overview และ about — หน้าอื่นทั้งหมดเป็น `React.lazy` และไฟล์ข้อมูลของหน้า lazy เป็น optional
สถานะตัวกรอง/การเลือกอยู่ใน URL เสมอ (`useUrlState`, เช่น `#/topics?status=WATCH`) แชร์ลิงก์ได้
ไม่มีกล่องค้นหาในหน้าใดเลย (e2e ตรวจ) — ใช้รายการจัดอันดับ + "แสดงเพิ่ม", ปุ่มกรอง (`Segmented`, ปุ่มสถานะ) หรือรายการแยกกลุ่มแทน; ไม่มีแท็บกราฟ⇄ตาราง ปุ่ม CSV บรรทัด "ที่มา:" หรือเลข "แผนภูมิ n" บนหน้า คำอธิบายอยู่หลังปุ่ม ⓘ (`InfoPop`, เปิดด้วยการคลิก/แตะ) ข้างชื่อการ์ดหรือแถบหัว

## ข้อมูลขนาดจริง

ออกแบบสำหรับหัวข้อ ~1,500 · วารสาร ~2,000 · สถาบัน ~10,000: รายการยาวใช้ `RankRows` + `usePaged`/`MoreRows` (ทีละ 6–10 รายการ "แสดงเพิ่มอีก k"), ชื่อยาวตัดบรรทัดเดียว (ชื่อเต็มอยู่ใน title และหน้าของมันเอง), ตารางที่อาจยาวส่ง `limit` ให้ `DataTable`, ป้ายชื่อบนแผนที่วางด้วยกล่องที่วัดจริง (`lib/labels.ts`); dashboard สูงไม่เกินราว 1.5–2 จอบนเดสก์ท็อป 1440×900

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
src/lib/            urlState/useUrlState · format · i18n · definition (ค่าคงที่ของนิยามที่เว็บแสดง) · usePaged · galaxyDocs (แถวบทความของ /galaxy จาก search/meta.json + docs-*.json)
                    galaxyGl (WebGL2) · citation ("อ้างอิง Atlas นี้" ใน /about ไม่มีผู้แต่ง) · story · findings · labels · chunkError …
src/components/     Layout (เมนูซ้าย / แถบบนมือถือ + drawer) · Footer · ErrorBoundary · DataBanner · ModuleFile · MovedTo (เปลี่ยนทางหน้าเก่า)
                    dashboard/ (SideNav · PageBar · Card/DashGrid/DashStack/SeeAll · KpiCard/KpiRow · RankRows/MoreRows · Segmented · Drawer · Icon)
                    Figure (กราฟอย่างเดียว) · Section (= การ์ด) · DataTable (limit) · Term/InfoPop · StatusGlyph/StatusChip · StatusLegend · ProvinceMap …
src/charts/         SVG เขียนเอง: forest · portfolio · trend · multi-line · StatusDonut · StoryLines + infographic (BarRank · ArcNetwork · ColumnChart · MixBar
                    · OpportunityQuadrant · GoalTiles · JournalScatter · PeriodMix · ChecklistBars · SmallMultiples)
                    คณิตการจัดวางแบบ pure + test: infographic.ts · execLayout.ts · editorLayout.ts · donut.ts · scale.ts · series.ts
src/features/atlas/ แผนที่หัวข้อ (mapSpace, terrain, TerrainMap, Gazetteer = รายชื่อหัวข้อตามสถานะพร้อมพิกัดกริด ไม่มีช่องค้นหา)
src/embed/          กราฟฝัง + EmbedBoundary + ลิงก์ฟีด `FeedLink` (แถบหัวของ /topics และหน้าหัวข้อ แสดงเมื่อ latest.feeds === true)
src/geo/            thProvinces.ts (ใช้ใน ProvinceMap/ProvinceLocator ของ chunk lazy เท่านั้น: การ์ดจังหวัดของภาพรวม, /places, /province/:code — ไม่อยู่ใน entry)
src/content/        changelog · method
src/pages/          หน้าละไฟล์ (+ pages/overview/, topic/, about/)
fixtures/           รอบข้อมูลสังเคราะห์ (example + empty) — ไม่ใช่ข้อมูลจริง
e2e/                smoke.spec.ts · narrow.spec.ts
scripts/            build/offline (finish-offline) · check-bundle · gen-types · make-fixtures · stage-demo-data · brief-pdf · serve · make-province-map · vendor-fonts
```

## กฎสำคัญ (ฉบับเต็มใน `../CLAUDE.md` §6 และ `../DESIGN.md`)

- สีมาจาก token ใน `src/styles/tokens.css` เท่านั้น (`var(--…)`, ไม่มี Tailwind class แบบ dynamic) · สถานะแสดงด้วยรูปทรง + สี + ชื่อเสมอ (▲ ◆ ● ▼ ■ วงประ) และสีสถานะใช้กับสถานะเท่านั้น
- ห้ามตัวเอียงในภาษาไทย · ทุกข้อความต้องมีทั้ง `th` และ `en`
- ข้อความบนหน้าภาษาง่าย สั้น ใช้ปีแทนช่วง ไม่มีศัพท์สถิติ/รหัสสถานะ; คำอธิบายวิธีคิดอยู่หลังปุ่ม ⓘ (`Card info` / `Section intro` / `PageBar info`) หรือ `Term`, ฉบับเต็มอยู่ที่ `/about`
- ทุกหน้าใช้ชิ้นส่วน dashboard ชุดเดียวกัน (`PageBar`, `KpiRow`/`KpiCard`, `Card`/`Section` ใน `DashGrid`, `RankRows` + `MoreRows`, `Segmented`); ห้ามมีกล่องค้นหา แท็บกราฟ⇄ตาราง "วิธีอ่าน" ปุ่ม CSV บรรทัด "ที่มา:" หรือเลข "แผนภูมิ n" บนหน้า
- กราฟใหม่: SVG ใน `src/charts/`; ป้าย ≥ 12 px, ink + น้ำเงินเดียว, ไม่มีข้อมูล = ลายเส้น/เส้นประ, ไม่มีข้อมูลที่เห็นเฉพาะตอน hover (ตัวเลขพิมพ์เป็นป้ายหรือรายการข้างกราฟ)
- งบ entry ≤ 180 KB gzip (ตอนนี้ ≈ 147 KB): หน้า/ส่วนใหม่เป็น lazy และเก็บข้อความในไฟล์ strings ของตัวเอง (`useStrings`, เพิ่มใน `LAZY` ของ `i18n.test.ts`)
- ไฟล์ `.tsx` export ได้เฉพาะ component — hook/context/helper อยู่ในไฟล์ `.ts`
- ห้ามใช้ `href="#id"` ในหน้า (HashRouter) — ใช้ `scrollToId()`
- ห้ามเผยแพร่ชื่อผู้แต่ง/บทคัดย่อ
- ห้าม commit ข้อมูลจริง — repo มีแต่ `fixtures/` ที่สังเคราะห์ขึ้น

## เว็บสาธิตและเว็บจริงบน GitHub Pages

`.github/workflows/pages.yml` รันเมื่อผู้ดูแลกด **Run workflow** เท่านั้น (push ไม่ทับรอบที่ขึ้นอยู่):

- `data_release` ว่าง → build แล้ว `npm run stage:demo -- dist` = **รอบสังเคราะห์** (ป้าย "ข้อมูลตัวอย่าง" ทุกหน้า, noindex)
- `data_release = data-<รอบ>` → ดาวน์โหลด `atlas-site-data-<รอบ>.zip` จาก GitHub Release ที่สร้างด้วย `bash scripts/package_release.sh --upload` (หลัง `atlas publish --site web/dist` หรือ `atlas quarterly`) แล้วแตกลง `dist/` — ปฏิเสธ zip ที่เป็นข้อมูลตัวอย่าง; ไม่มีข้อมูลใด commit เข้า repo
- host อื่น (IIS, Apache, Nginx, S3): อัปโหลด `../deploy/<รอบ>/site/` หรือแตก zip จาก `../deploy/` — ดู `../docs/OPERATIONS.md` §1.5
