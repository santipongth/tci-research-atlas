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
| `npm run e2e` | Playwright smoke: ทุกหน้า × ข้อมูลตัวอย่าง/ข้อมูลว่าง · axe · จอ 360 px · ไฟล์ออฟไลน์ไม่มี network (ต้อง build ก่อน; ครั้งแรกรัน `npx playwright install chromium`) |
| `npm run lint` · `npx tsc -b` | ตรวจโค้ด |
| `npm run fixtures` | สร้างข้อมูลทดสอบ (สังเคราะห์ ไม่ใช่ข้อมูลจริง) ใหม่ — CI ตรวจว่าไม่ drift |
| `npm run gen:types` | สร้าง `src/data/contract.ts` จาก `contract.schema.json` (หลัง `uv run atlas schema` ใน `pipeline/`) |
| `npm run brief:pdf -- [--data <โฟลเดอร์ data>] [--out <โฟลเดอร์>]` | พิมพ์หน้า `#/brief` เป็น `brief-th.pdf` และ `brief-en.pdf` (ฟอนต์ไทยฝังในไฟล์) · ไม่มีข้อมูลจะหยุดทันทีพร้อมข้อความ · ลองในเครื่อง: `--data fixtures/example/data` |
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

`#/overview` ภาพรวม (KPI + Δ, ประโยคสรุป, ประเด็นผู้บริหาร, สถานะ + forest plot, ผัง size × growth) · `#/atlas` แผนที่ + ดัชนีหัวข้อ · `#/topics/:id` หัวข้อ · `#/emerging` ตารางสถานะ · `#/compare` เปรียบเทียบ 2–4 หัวข้อ · `#/data` ข้อมูลเปิด + ความโปร่งใส · `#/about` วิธีการ + นิยาม + changelog · `#/brief` หน้าพิมพ์ PDF
สถานะของตัวกรอง/การเลือกอยู่ใน URL เสมอ (เช่น `#/emerging?status=WATCH&sort=journals`) แชร์ลิงก์ได้

## โครงสร้างโค้ด

```
src/brand/       wordmark ชั่วคราว (สลับเป็นโลโก้ทางการที่ brand.ts จุดเดียว)
src/styles/      tokens.css (สีทั้งหมด light/dark) · fonts.css · CSS ของแต่ละส่วน · palette.test.ts (CVD + contrast)
src/strings/     ข้อความ UI ทุกตัว ไทย + อังกฤษ (i18n.test.ts ตรวจครบคู่)
src/data/        contract.ts (generated) · types.ts · source.ts (Http | Embedded) · release.ts (loader) · atlasContext.ts
src/lib/         format · highlight · urlState · csv · search (ตัดวรรณยุกต์ + Intl.Segmenter) · definition · theme · i18n
src/components/  ชุด UI (tabs, figure, table, whisker, search, tooltip, …)
src/charts/      forest plot · portfolio · trend · multi-line
src/features/atlas/  แผนที่ (mapSpace, terrain, TerrainMap, Gazetteer)
src/pages/       หน้าละไฟล์
fixtures/        รอบข้อมูลสังเคราะห์สำหรับ dev/test (example + empty) — ไม่ใช่ข้อมูลจริง
e2e/smoke.spec.ts  Playwright smoke spec เดียว
```

## กฎสำคัญ (ฉบับเต็มใน `../CLAUDE.md` §6 และ `../DESIGN.md`)

- สีมาจาก token ใน `src/styles/tokens.css` เท่านั้น · สถานะแสดงด้วยรูปทรง + สี + ชื่อเสมอ (▲ ◆ ● ▼ ■ วงประ)
- ห้ามตัวเอียงในภาษาไทย · ทุกข้อความต้องมีทั้ง `th` และ `en`
- ไฟล์ `.tsx` export ได้เฉพาะ component — hook/context/helper อยู่ในไฟล์ `.ts`
- ห้ามใช้ `href="#id"` ในหน้า (HashRouter) — ใช้ `scrollToId()`
- ห้าม commit ข้อมูลจริง — repo มีแต่ `fixtures/` ที่สังเคราะห์ขึ้น
