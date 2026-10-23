# TCI Research Atlas — เว็บ v2

เว็บ static (React 19 + Vite 7 + TypeScript + Tailwind 4) ที่อ่านข้อมูลรอบล่าสุด **ตอนเปิดหน้า** — ไม่มี server ไม่มี API key และไม่เรียก AI หรือบริการภายนอกใด ๆ
ดีไซน์อยู่ใน `../DESIGN.md` (Civic modern เป็นฐาน · ประโยคหัวเรื่องแบบ Editorial + forest plot ในหน้าภาพรวม · แผนที่ภูมิประเทศแบบ Cartographic ในหน้าแผนที่) · แบรนด์อยู่ที่ `src/brand/` จุดเดียว

## คำสั่ง

| คำสั่ง | ทำอะไร |
|---|---|
| `npm ci` | ติดตั้ง (ทุกเวอร์ชันล็อกไว้ใน `package-lock.json`) |
| `npm run dev` | dev server http://localhost:3000 อ่านข้อมูลตัวอย่างจาก `fixtures/example/data` (เปลี่ยนด้วย env `ATLAS_DATA_DIR`) |
| `npm run build` | `dist/` (วางบน static host ใดก็ได้) + `dist/offline-template.html` (ต้นแบบไฟล์เดียวให้ `atlas publish`) |
| `npm test` | unit tests (vitest) |
| `npm run check:bundle` | เช็กงบ bundle หลัง build: entry chunk ≤ 180 KB gzip และหน้า editors ทั้ง 5 ต้องเป็น lazy chunk แยก (ล้มถ้าหน้าใดหลุดเข้า entry) |
| `npm run e2e` | Playwright smoke: ทุกหน้า × ข้อมูลตัวอย่าง/ข้อมูลว่าง · axe · จอ 360 px · ไฟล์ออฟไลน์ไม่มี network (ต้อง build ก่อน; ครั้งแรกรัน `npx playwright install chromium`) |
| `npm run lint` · `npx tsc -b` | ตรวจโค้ด |
| `npm run fixtures` | สร้างข้อมูลทดสอบ (สังเคราะห์ ไม่ใช่ข้อมูลจริง) ใหม่ — CI ตรวจว่าไม่ drift |
| `npm run gen:types` | สร้าง `src/data/contract.ts` จาก `contract.schema.json` (หลัง `uv run atlas schema` ใน `pipeline/`) |
| `npm run brief:pdf -- [--data <โฟลเดอร์ data>] [--out <โฟลเดอร์>]` | พิมพ์หน้า `#/brief` เป็น `brief-th.pdf` และ `brief-en.pdf` (ฟอนต์ไทยฝังในไฟล์) · ไม่มีข้อมูลจะหยุดทันทีพร้อมข้อความ · ลองในเครื่อง: `--data fixtures/example/data` |
| `node scripts/make-province-map.mjs <ne_admin1.geojson>` | สร้าง `src/geo/thProvinces.ts` (เส้นขอบ 77 จังหวัดจาก Natural Earth 1:10m admin-1 v5.1.2, สาธารณสมบัติ) — รันครั้งเดียว ไฟล์ที่ได้ถูก commit แล้ว; geojson ~40 MB ดาวน์โหลดไว้นอก repo (ดูหัวสคริปต์) |
| `npm run vendor:fonts` | คัดลอก Sarabun (woff2, OFL) เข้า `src/assets/fonts/` |

## ข้อมูลเข้าเว็บอย่างไร

```
web: npm run build ──► dist/  (+ offline-template.html)
pipeline: uv run atlas publish -c config.yaml --site ../web/dist
          ──► dist/data/<release>/*.json · dist/data/latest.json · dist/atlas-offline.html
```

- เว็บอ่าน `./data/latest.json` → `./data/<release>/manifest.json` → ไฟล์หลัก (path สัมพัทธ์จาก `BASE_URL` จึงวางใต้ sub-path ได้ เช่น GitHub Pages)
- **อัปเดตรายไตรมาส = คัดลอกโฟลเดอร์ `data/` ใหม่ขึ้น host** — ไม่ต้อง build เว็บใหม่ ไม่ต้องมี Node บนเครื่องผู้รัน
- `atlas-offline.html` = เว็บทั้งหมดในไฟล์เดียว เปิดจาก `file://` ได้โดยไม่ต่อเน็ต (ข้อมูลฝังใน `<script type="application/json" id="atlas-data">`)
- โหลดข้อมูลไม่ได้ / schema ไม่ใช่ 2.x / ไฟล์เสีย → แถบแจ้งเหตุผล (ไม่มีหน้าขาว) · รอบที่ `embedding_provider` เป็น `fixture` หรือ `lite` → แถบ "ข้อมูลตัวอย่าง"

## หน้า

`#/overview` ภาพรวม (3 เรื่องสำคัญรอบนี้, 4 KPI + ดูตัวเลขเพิ่ม, ประโยคสรุป, ข้อสังเกตสำหรับการวางนโยบาย, waffle สถานะ + forest plot, ผัง size × growth) · `#/atlas` แผนที่หัวข้อ + ดัชนีหัวข้อ · `#/topics/:id` หัวข้อ · `#/emerging` สถานะหัวข้อ · `#/compare` เปรียบเทียบ 2–4 หัวข้อ · `#/data` ข้อมูลเปิด (ดาวน์โหลดง่าย ๆ / สำหรับนักพัฒนา) · `#/about` อ่านตัวเลขอย่างไร (ขั้นตอน + ทางตัดสินสถานะ + นิยาม + changelog + อ้างอิง Atlas) · `#/brief` สรุปผู้บริหาร 1 หน้า (พิมพ์ PDF) · P2 (lazy): `#/journals` วารสาร · `#/journals/:id` โปรไฟล์วารสาร · `#/methods` วิธีวิจัย · `#/changes` อะไรเปลี่ยน · `#/match` วางบทคัดย่อ (คำนวณในเบราว์เซอร์; ไม่มีในไฟล์ออฟไลน์) · P3 (lazy; เมนูแบ่งกลุ่มผู้บริหาร/บรรณาธิการ/นักวิจัย): `#/institutions` สถาบัน · `#/institutions/:id` · `#/regions` แผนที่จังหวัด · `#/sdg` SDG และแผนชาติ · `#/global` ไทยเทียบโลก · `#/gaps` โอกาสที่ยังไม่มีใครทำ · P4 (lazy): `#/search` ค้นหาบทความ · `#/galaxy` แผนที่บทความทุกเรื่อง · `#/keywords` แนวโน้มคำสำคัญ · `#/references` การอ้างอิง — ไฟล์ข้อมูลของหน้า lazy เป็น optional และแต่ละหน้าอธิบายตัวเองเมื่อไม่มี
สถานะของตัวกรอง/การเลือกอยู่ใน URL เสมอ (เช่น `#/emerging?status=WATCH&sort=journals`) แชร์ลิงก์ได้

## โครงสร้างโค้ด

```
src/brand/       wordmark ชั่วคราว (สลับเป็นโลโก้ทางการที่ brand.ts จุดเดียว)
src/styles/      tokens.css (สีทั้งหมด light/dark) · fonts.css · CSS ของแต่ละส่วน · palette.test.ts (CVD + contrast)
src/strings/     ข้อความ UI ทุกตัว ไทย + อังกฤษ (i18n.test.ts ตรวจครบคู่)
src/data/        contract.ts (generated) · types.ts · source.ts (Http | Embedded) · release.ts (loader) · atlasContext.ts
src/lib/         format · highlight · urlState · csv · search (ตัดวรรณยุกต์ + Intl.Segmenter) · definition · glossary · findings · theme · i18n
src/components/  ชุด UI: Figure (คำบรรยาย · แผนภูมิ/ตาราง · วิธีอ่าน · CSV) · StatTile · DataTable (primary/limit) · Term/InfoPop · HowNote · SourceLine · Steps · PhoneFold · tabs · whisker · search · tooltip …
src/charts/      forest plot · portfolio · trend · multi-line + infographic: StatusWaffle · DotPlot · BarRank · ArcNetwork · ColumnChart · MixBar/SplitBar · OpportunityQuadrant · StatusFlow · LineageKey · GoalTiles · BridgePairs · JournalScatter · PeriodMix · ChecklistBars · SmallMultiples
                 (คณิตการจัดวางแบบ pure + test: infographic.ts · execLayout.ts · editorLayout.ts)
src/features/atlas/  แผนที่ (mapSpace, terrain, TerrainMap, Gazetteer)
src/pages/       หน้าละไฟล์
fixtures/        รอบข้อมูลสังเคราะห์สำหรับ dev/test (example + empty) — ไม่ใช่ข้อมูลจริง
e2e/             smoke.spec.ts (ทุกหน้า) · narrow.spec.ts (จอ 360/390 px: เมนูมือถือ, h1 อยู่สูง, แผนที่)
```

## กฎสำคัญ (ฉบับเต็มใน `../CLAUDE.md` §6 และ `../DESIGN.md`)

- สีมาจาก token ใน `src/styles/tokens.css` เท่านั้น · สถานะแสดงด้วยรูปทรง + สี + ชื่อเสมอ (▲ ◆ ● ▼ ■ วงประ)
- ห้ามตัวเอียงในภาษาไทย · ทุกข้อความต้องมีทั้ง `th` และ `en`
- ข้อความ 2 ชั้น: ชั้นแรกภาษาง่ายขึ้นด้วยตัวอย่าง ไม่มีศัพท์สถิติ/รหัสสถานะ; รายละเอียดอยู่หลัง "วิธีอ่าน", `HowNote` หรือ `Term` (DESIGN.md "Copy voice")
- กราฟใหม่: SVG ใน `src/charts/` มีแท็บตาราง ป้าย ≥ 14 px ink + น้ำเงินเดียว (สีสถานะใช้กับสถานะเท่านั้น) ไม่มีข้อมูล = ลายเส้น/เส้นประ และไม่มีข้อมูลที่เห็นเฉพาะตอน hover
- ไฟล์ `.tsx` export ได้เฉพาะ component — hook/context/helper อยู่ในไฟล์ `.ts`
- ห้ามใช้ `href="#id"` ในหน้า (HashRouter) — ใช้ `scrollToId()`
- ห้าม commit ข้อมูลจริง — repo มีแต่ `fixtures/` ที่สังเคราะห์ขึ้น

## เว็บสาธิต (GitHub Pages)

`.github/workflows/pages.yml` build เว็บแล้ววาง **รอบข้อมูลสังเคราะห์** (`npm run stage:demo -- dist`) — ทุกหน้ามีแถบ "ข้อมูลตัวอย่าง" เพราะ manifest ระบุ `embedding_provider: fixture` (สคริปต์ไม่ยอมวางรอบที่ไม่ได้ติดป้ายตัวอย่าง)
เมื่อมีรอบข้อมูลจริง: ใช้ `uv run atlas publish --site web/dist` แทนขั้น stage:demo แล้ว deploy โฟลเดอร์เดิม (ผู้ดูแลเป็นผู้สั่ง deploy)
