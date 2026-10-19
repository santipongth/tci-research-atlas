# CLAUDE.md — TCI Research Atlas

> ไฟล์นี้คือ "สมองกลาง" ของโปรเจกต์สำหรับ Claude Code — อ่านไฟล์นี้ก่อนทำอะไรทั้งสิ้น
> เอกสารเชิงลึกแยกอยู่ใน `docs/` — อ่านเฉพาะที่เกี่ยวกับงานที่กำลังทำ

## 1. โปรเจกต์นี้คืออะไร

**TCI Research Atlas** = แผนที่ภูมิทัศน์งานวิจัยไทย (discovery & insight tool) สำหรับ 3 กลุ่มผู้ใช้:

- **นักวิจัย** — หาช่องว่างงานวิจัย ดูหัวข้อที่กำลังโต
- **บรรณาธิการวารสาร** — เห็นภาพรวมสาขา วางแผนเชิงกลยุทธ์
- **ผู้บริหาร/นโยบาย** — dashboard ภาพรวมเพื่อการตัดสินใจระดับประเทศ

สถาปัตยกรรม: **batch pipeline (Python, รันทุก 3 เดือน)** → ส่งออก `data/<release>/*.json` + `data/latest.json` (contract v2, ผ่าน `atlas publish`) → **เว็บ (React)** โหลดไฟล์เหล่านั้นแล้วแสดงเป็น interactive dashboard โดยไม่ต้องแก้โค้ดเว็บ

## 2. โครงสร้าง repo

```
tci-research-atlas/
├── CLAUDE.md               ← ไฟล์นี้
├── README.md               ← ภาพรวมสำหรับทีม (ภาษาไทย)
├── DESIGN.md               ← ระบบดีไซน์ (tokens + กฎ) — ชนะ catalog ทั่วไปเสมอ
├── docs/
│   ├── ARCHITECTURE.md     ← การออกแบบระบบ + การไหลของข้อมูล
│   ├── DATA_SPEC.md        ← สเปก input (ThaiJO Markdown) และ output (atlas_data.json)
│   ├── EMERGING_SPEC.md    ← นิยาม "emerging" ของ TCI ฉบับเต็ม + สูตรคะแนน
│   ├── ROADMAP.md          ← ฟีเจอร์ทั้ง 5 phase + ของที่ควรทำต่อ
│   ├── OPERATIONS.md       ← วิธีรัน batch รายไตรมาส + import เข้าเว็บ + troubleshoot
│   └── superpowers/        ← specs + plans ของ v2 (แผนหลัก: specs/2026-10-18-tci-atlas-v2-design.md)
├── pipeline/               ← Python batch pipeline (Phase 1,2,4,5)
│   ├── atlas/              ← โมดูล pipeline: ingest→preprocess→embed→cluster→taxonomy→label
│   │                         →series→emerging→keywords→forecast→narrate→layout→methods→journals→match
│   │                         →export (P2: journals.py, journal_metrics.py, journal_topics.py, registry.py, methods.py, matcher.py, diff.py)
│   │   ├── sources/        ← parser ข้อมูลเข้า (thaijo_md.py)
│   │   └── schema/         ← data contract v2 (contract.py → JSON Schema)
│   ├── configs/ci.yaml     ← config สำหรับ CI
│   ├── registry/           ← ทะเบียนวารสารที่ TCI ให้ (journals.csv, git-ignored) — repo มีแต่ journals.example.csv
│   ├── state/              ← ข้อมูลถาวรข้ามรอบ (embedding store, LLM cache, ID หัวข้อ/ตำแหน่งแผนที่ต่อรอบ, งานอ้างอิง OpenAlex) — git-ignored, ห้ามลบ
│   ├── config.example.yaml ← คัดลอกเป็น config.yaml แล้วแก้
│   ├── tests/              ← pytest (มี test_emerging.py ครอบคลุมนิยาม emerging)
│   ├── scripts/            ← run_all.sh
│   └── requirements.txt    ← export จาก uv.lock สำหรับติดตั้งแบบไม่ใช้ uv (ทางหลักคือ `uv sync`)
├── web/                    ← เว็บ v2: React 19 + Vite + TS + Tailwind 4, HashRouter (ดู web/README.md)
│   ├── src/data/           ← contract.ts (generated) · source.ts (Http | Embedded) · release.ts (loader)
│   ├── src/styles/tokens.css ← design tokens light/dark (ค่าตาม DESIGN.md)
│   ├── src/strings/        ← ข้อความ UI ไทย+อังกฤษทุกตัว
│   ├── src/pages/          ← overview · atlas · topics/:id · emerging · compare · data · about · brief · journals · journals/:id · methods · changes · match (5 หน้าหลังเป็น React.lazy)
│   └── fixtures/           ← รอบข้อมูลสังเคราะห์ (example + empty) สำหรับ dev/test — ไม่ใช่ข้อมูลจริง
├── prompts/                ← LLM prompts ทั้งหมด (ฉบับเดียว — โค้ดอ่านไฟล์ตอนรัน)
└── scripts/
    ├── quarterly_run.sh    ← สคริปต์รัน batch รายไตรมาส (เรียกจาก cron)
    └── import_atlas.sh     ← build เว็บ + atlas publish --site web/dist (วาง data/ + ไฟล์ออฟไลน์)
```

## 3. แผนฟีเจอร์ 5 Phase (สถานะปัจจุบัน)

| Phase | ฟีเจอร์ | ที่ตั้ง | สถานะ |
|---|---|---|---|
| 1 | Embedding (batch, API **หรือ** local model) | `pipeline/atlas/embed.py` | ✅ พร้อมใช้ |
| 2 | Topic Clustering 2 ชั้น (UMAP+HDBSCAN, c-TF-IDF) | `pipeline/atlas/cluster.py` | ✅ พร้อมใช้ |
| 3 | Atlas web v2 (7 หน้า + brief, 2 ภาษา, dark mode, URL state, offline HTML, PDF) | `web/` | ✅ พร้อมใช้ |
| 4 | Emerging Topic Analysis (นิยาม v3 + burst + score) | `pipeline/atlas/emerging.py` + `web/src/pages/EmergingPage.tsx` | ✅ พร้อมใช้ |
| 5 | Research Trend Forecasting (Forecast v2, skill gate) | `pipeline/atlas/forecast.py` + `web/src/charts/TrendChart.tsx` | ✅ พร้อมใช้ |
| + | LLM labeling + merge duplicates | `pipeline/atlas/label.py` | ✅ พร้อมใช้ |
| + | Live dashboard (อ่าน data/latest.json ตอนเปิดหน้า, แถบแจ้งเมื่อโหลดไม่ได้) | `web/src/data/{source,release}.ts` | ✅ พร้อมใช้ |
| P1 | ID หัวข้อถาวร + lineage, OpenAlex taxonomy, Forecast v2, emerging keywords, แผนที่นิ่ง | `pipeline/atlas/{lineage,taxonomy,forecast,keywords,layout}.py` | ✅ |
| P1 | LLM ผ่าน API (label · merge · narrative · brief) + review/overrides | `pipeline/atlas/{llm,llm_runner,label,review,narrative}.py` | ✅ |
| P1 | Contract v2 release + validate + publish --site (+ offline HTML) | `pipeline/atlas/{export_v2,validate,publish}.py` | ✅ |
| P2 | Editors: journals (D1–D5, D7), methods (E11), what changed (E5), match my abstract (R3/R4) | `pipeline/atlas/{journals,methods,matcher,diff}.py` + `web/src/pages/{Journals,Journal,Methods,Changes,Match}Page.tsx` | ✅ |

สิ่งที่ยังไม่มี / ไอเดียต่อยอดอยู่ใน `docs/ROADMAP.md` (เช่น author network, journal view, compare mode, API backend)

## 4. คำสั่งที่ใช้บ่อย

### Pipeline (ทำงานใน `pipeline/`)

```bash
cd pipeline
uv sync                                    # + --extra api / --extra local
cp config.example.yaml config.yaml         # แก้ input.path → โฟลเดอร์ .md
uv run atlas profile ../corpus             # ตรวจคุณภาพคลังก่อนเสมอ
uv run atlas run --config config.yaml      # ทั้งสาย
uv run atlas run -c config.yaml -s emerging -s forecast -s export
uv run atlas embed -c config.yaml [--check | --dry-run | --background]   # embedding ครั้งใหญ่: retry ไม่จำกัด, resume ได้
uv run atlas status -c config.yaml         # สถานะงานยาว (alias: atlas embed-status)
uv run atlas embed-stop -c config.yaml     # หยุดอย่างสุภาพ — ทำต่อ = รัน atlas embed เดิมซ้ำ
uv run atlas synth --out .ci/synth --n 20000
uv run pytest -q && uv run pytest -m slow -q
uv run atlas llm -c config.yaml --check | --dry-run      # ปลายทาง LLM / ประมาณ token+ค่าใช้จ่าย; ไม่ใส่ flag = รัน label + narrate (--background; หยุด: atlas llm-stop)
uv run atlas review export -c config.yaml                # CSV ให้บรรณาธิการตรวจชื่อ → atlas review import <csv>
uv run atlas validate -c config.yaml                     # exit 0/1/2
uv run atlas publish -c config.yaml --site ../web/dist   # data/<release>/ + data/latest.json + atlas-offline.html
uv run atlas bakeoff -c config.yaml --kind all           # เทียบ embedding/clustering
```
(key อยู่ใน env var เท่านั้น: `ATLAS_EMBED_API_KEY` สำหรับ embedding แบบ API, `ATLAS_LLM_API_KEY` สำหรับ LLM (ชื่อหัวข้อ · คู่ซ้ำ · คำอธิบาย · บทสรุป) — ใช้ key เดียวกันได้, `OPENALEX_API_KEY` ทางเลือกสำหรับ taxonomy; embed ครั้งใหญ่ดู `docs/OPERATIONS.md` §1A, LLM ดู §6, OpenAlex ดู §9)

### Web (ทำงานใน `web/`)

```bash
npm ci
npm run dev                  # dev server (ข้อมูลตัวอย่างจาก fixtures/example/data)
npm run lint && npx tsc -b && npm test
npm run build                # dist/ + dist/offline-template.html
npm run e2e                  # Playwright smoke (หลัง build; ครั้งแรก npx playwright install chromium)
npm run brief:pdf -- --data fixtures/example/data   # brief-th.pdf / brief-en.pdf (ไม่บังคับ)
```

### รอบรันรายไตรมาส (จาก root)

```bash
bash scripts/quarterly_run.sh [pipeline/config.yaml]      # profile คลัง + รัน pipeline ครบ
bash scripts/import_atlas.sh                              # build เว็บ + atlas publish --site web/dist
```

รายละเอียดเชิงปฏิบัติการทั้งหมดอยู่ใน `docs/OPERATIONS.md`

## 5. Data contract สำคัญที่สุด: contract v2 (`data/<release>/`)

**นี่คือสัญญาระหว่าง pipeline กับเว็บ — ห้ามเปลี่ยนโดยไม่แก้ทั้งสองฝั่ง**

- ฝั่งผลิต: contract v2 เขียนโดย `pipeline/atlas/export_v2.py` และ `atlas publish` (schema เต็มใน `docs/DATA_SPEC.md`); `atlas_data.json` schema 1.1 จาก `export.py` เก็บไว้เพื่อความเข้ากันได้เท่านั้น เว็บไม่อ่านแล้ว (`meta.definition_version = 3`)
- ฟิลด์ใหม่ของ 1.1 ต่อหัวข้อ: `share_growth`, `share_growth_lo`, `share_growth_hi`, `n_journals_R`, `n_orgs_R`, `journal_driven`, `orgs_unverified`, `coherence`, `forecast_uncertain` (+ `meta.assigned_articles`, `meta.unassigned_articles`, `meta.as_of_year`, `meta.trimmed_years`, `meta.n_orgs_unverified`); status มี 6 ค่า (EMERGING | WATCH | HOT | DECLINING | STABLE | LOW_DATA); `forecast` เป็น null เว้นแต่ผ่าน skill gate และสถานะไม่ใช่ LOW_DATA
- data contract v2 อยู่ที่ `pipeline/atlas/schema/contract.py` → ต้องสร้างใหม่พร้อมกัน: `uv run atlas schema` แล้ว `npm run gen:types` (ใน `web/`) — CI ตรวจ drift ทั้งสองขั้น
- contract v2 ถูกเขียนจริงแล้ว (P1): `output/data/<release>/*.json` + `output/data/latest.json` (รายละเอียดใน `docs/DATA_SPEC.md` §6) — ช่วงเชื่อมั่นใช้ชื่อ `*_lo/*_hi` เสมอ ระดับอยู่ใน `manifest.ci_level`; `share_ratio` เป็น null เมื่อ `no_baseline`; `definition_version` ยังเป็น 3
- ฝั่งบริโภค (เว็บ v2): `web/src/data/source.ts` (HttpSource อ่าน `./data/latest.json` → `./data/<release>/*.json` แบบ path สัมพัทธ์จาก `BASE_URL`; EmbeddedSource อ่าน `{latest, files}` ที่ `atlas publish` ฝังใน `atlas-offline.html`) + `web/src/data/release.ts` (`loadRelease`: ตรวจ schema major = 2 ด้วย zod, โหลดไฟล์หลัก, `overview.json` ของรอบก่อนสำหรับ Δ, `topics/<id>.json` เมื่อเปิดหัวข้อ)
- ชนิดข้อมูลเว็บมาจาก `web/src/data/contract.ts` ที่ generate เท่านั้น ผ่าน `web/src/data/types.ts` (ชนิดซ้อนดึงด้วย indexed access เช่น `TopicsFile['topics'][number]` เพราะชื่อ interface ที่ generate ไม่คงที่)
- ข้อเท็จจริงที่ UI ใช้: share/growth เป็นทศนิยม (0.10 = 10%), ระดับช่วงเชื่อมั่นคือ `manifest.ci_level`, `share_ratio: null` + `no_baseline: true` → "ใหม่ — ไม่มีในช่วงฐาน", `low_data_reason ∈ {few_articles, not_estimable}`, `forecast.show === false` → "แนวโน้มไม่แน่นอน", นิยามสถานะแสดงจาก `manifest.definition_version` (ตอนนี้ 3)
- **contract 2.1 (P2, เพิ่มอย่างเดียว):** ไฟล์เสริม `journals.json`, `journals/<id>.json`, `methods.json`, `diff.json`, `match.json` ที่ประกาศใน `manifest.modules` — ทุกไฟล์ optional; เว็บตรวจ major 2 เท่านั้น และหน้าที่ต้องใช้ไฟล์เหล่านี้ต้องอธิบายตัวเองเมื่อไม่มี (`ModuleFile`); `match.json` ไม่อยู่ใน HTML ออฟไลน์ (`export.offline_exclude`)
- โหลดไม่ได้ / schema ผิด major / ไฟล์เสีย → แถบแจ้งเหตุผล (หน้าเว็บไม่มีวันขาว) — **ไม่มีข้อมูล bundle สำรองแล้ว**
- **การอัปเดตข้อมูล = `uv run atlas publish --site <เว็บที่ build แล้ว>` หรือคัดลอกโฟลเดอร์ `data/` ใหม่ — ไม่ต้อง build เว็บใหม่**; `atlas_data.json` (schema 1.1) ยังถูกเขียนโดย pipeline แต่เว็บ v2 ไม่อ่านแล้ว

## 6. กฎการพัฒนา (Do / Don't)

### Pipeline

- **DO** เพิ่ม step ใหม่โดยสร้างโมดูลใน `atlas/` ที่อ่าน checkpoint ของ step ก่อนจาก `work_dir` และเขียน checkpoint ของตัวเอง — pipeline ต้อง stop/resume ได้ทุกจุด
- **DO** ใช้ `io_utils.read_table/write_table` (รองรับ parquet→pickle fallback) อย่าเรียก `pd.read_parquet` ตรง ๆ
- **DO** เก็บค่าพารามิเตอร์ทุกตัวใน `config.yaml` — ห้าม hardcode threshold
- **DO** รัน `uv run pytest -q` ก่อนส่งงาน — โดยเฉพาะถ้าแก้ `emerging.py` (นิยาม emerging มี unit test ล็อกไว้)
- **DO** เก็บข้อมูลถาวรเฉพาะใน `state_dir` (`work_dir` ต้องลบได้เสมอ)
- **DO** สถานะมี 6 ค่าเท่านั้น (ชุดเดียวกันตั้งแต่ v2; นิยามปัจจุบัน v3) และต้องเพิ่ม `definition_version` ทุกครั้งที่นิยามเปลี่ยน
- **DO** ค่าดีฟอลต์ `embedding.provider` คือ `local`; `lite` ใช้เฉพาะ CI/ทดสอบ (`make_cfg` ใน tests ตั้งให้เอง)
- **DO** เขียนอักษรไทยในซอร์สเป็น `\N{THAI CHARACTER ...}` หรือ `chr(0x...)` — ห้ามใช้ backslash-u escape
- **DO** pandas 3: ห้ามทดสอบ `dtype == object`; normalise คอลัมน์ข้อความด้วย `.fillna("").astype(str)`
- **DO** ใส่เครื่องหมายคำพูดให้ `"off"` ใน YAML (`provider: "off"`) — `off` เปล่า ๆ ถูกอ่านเป็น false
- **DON'T** แก้นิยาม EMERGING/WATCH/HOT/DECLINING โดยไม่อัปเดต `docs/EMERGING_SPEC.md` + `config.example.yaml` + `web/src/lib/definition.ts` (ค่าคงที่ของนิยามที่เว็บแสดง) + ทดสอบให้ตรงกัน
- **DON'T** ใส่ API key ลงไฟล์ใด ๆ — ใช้ env var เสมอ (`ATLAS_EMBED_API_KEY` embedding, `ATLAS_LLM_API_KEY` LLM, `OPENALEX_API_KEY` ถ้ามี; ชื่ออยู่ใน `api_key_env` ของ config)
- **DO** แถวผู้แต่งอ่านได้เฉพาะใน `journal_metrics` / `journals` — เผยแพร่เฉพาะตัวเลขรวม (จำนวน สัดส่วน ความหลากหลายสถาบัน) ห้ามมีชื่อบุคคล แถวต่อผู้แต่ง หรืออันดับบุคคล (PDPA); ห้ามเผยแพร่ข้อความบทคัดย่อ (match.json เก็บแค่น้ำหนัก trigram)
- **DO** เรียก LLM ผ่าน `atlas.llm_runner.run_job` เท่านั้น (cache, งบ, หยุด/ต่อ, repair, fallback; lock/progress/stop ใช้ `atlas.jobs` ของ P0 ตัวเดียวกับ embedding) — งาน LLM เป็นระดับหัวข้อ ไม่เรียกต่อบทความ
- **DO** ตัวเลขในข้อความที่ LLM เขียนต้องมาจาก pipeline และผ่าน `narrative.grounding_error` (ปฏิเสธตัวเลขที่ไม่อยู่ในข้อมูล, คำบอกจำนวนเท่าที่ไม่มีที่มา, และทิศทางผิดในประโยคอัตรา; เขียนใหม่ 1 ครั้ง แล้วใช้ประโยคแม่แบบ) — ห้ามเผยแพร่ข้อความ LLM ที่ไม่ได้ตรวจ
- **DON'T** ใช้ชื่อรอบ (release) นอกรูป YYYYQn, ใช้ ID หัวข้อซ้ำ หรือรันรอบที่เก่ากว่ารอบที่มีอยู่ — โค้ดปฏิเสธอยู่แล้ว อย่าเลี่ยง

### Web

- **DO** อ่าน `DESIGN.md` ก่อนทำ UI — ชนะ catalog ทั่วไปเสมอ; งาน UI ใช้ skill `impeccable` ก่อน และกราฟใช้ skill `dataviz`
- **DO** ใช้ design tokens จาก `web/src/styles/tokens.css` เท่านั้น (`var(--…)`): ฐาน Civic modern — ฟอนต์ **Sarabun** อย่างเดียว (self-hosted, `src/assets/fonts/`), civic blue `#0f3557`, link blue `#1a5bb0`, focus yellow `#ffd43b` (ใช้กับ focus เท่านั้น), ink `#0b0c0e`, พื้นขาว, มุมเหลี่ยม; ไฮไลต์ประโยคหัวเรื่อง `#ffe07a` แบบแถบครึ่งล่าง; สีสาขาเป็น token `cat-01…cat-12` — tokens เดิม `#f5f6f2`/`#161611`/`#FF5F1F` และ IBM Plex/Noto Serif **เลิกใช้แล้ว**
- **DO** แสดงสถานะด้วยรูปทรง + สี + ชื่อเสมอ (▲ EMERGING · ◆ WATCH · ● HOT · ▼ DECLINING · ■ STABLE · วงประ LOW_DATA); สีสถานะใช้กับสถานะเท่านั้น; เปลี่ยนสีต้องผ่าน `web/src/styles/palette.test.ts` (CVD + contrast ทั้ง light/dark)
- **DO** รองรับ 2 ภาษาทุกสตริง — เพิ่ม key ใน `web/src/strings/<หน้า>.ts` ทั้ง `th` และ `en` (`i18n.test.ts` ตรวจ)
- **DO** ทุกกราฟมีแท็บตาราง + คำบรรยายมีเลข ("แผนภูมิ n", "ตาราง n") + บรรทัด "ที่มา:"; ตารางเรียงได้ (`aria-sort`) และ export CSV ได้
- **DO** หน้าที่ใช้ไฟล์ module (journals/methods/diff/match) เรนเดอร์ผ่าน `ModuleFile` — ถ้าไม่มีโมดูลต้องแสดง h1 พร้อมเหตุผล ไม่ใช่หน้าขาว; ข้อความที่วางใน `/match` ต้องไม่ออกจากเบราว์เซอร์ (ไม่อยู่ใน URL, storage หรือ request) และ `web/src/lib/matcher.ts` ต้องตรงกับ `pipeline/tests/fixtures/match_parity.json`
- **DO** ทำให้ section "หดตัวเอง" (ไม่ render) เมื่อข้อมูลไม่มีฟิลด์นั้น; หน้าเว็บไม่มีวันขาว
- **DO** เก็บสถานะตัวกรอง/การเลือกไว้ใน URL ผ่าน `useUrlState` + codec ใน `web/src/lib/urlState.ts`
- **DO** ไฟล์ `.tsx` export ได้เฉพาะ component (กฎ react-refresh) — hook/context/helper อยู่ใน `.ts`; ห้าม setState แบบ synchronous ใน effect และห้ามอ่าน `ref.current` ระหว่าง render (react-hooks v7)
- **DON'T** ใช้ Tailwind class แบบ dynamic (`bg-[${color}]`) — ใช้ inline style `var(--…)` หรือ class ที่เขียนไว้ใน CSS ครบทุกค่า (`chip-${status}`)
- **DON'T** ใช้ `href="#id"` ในหน้า (HashRouter จะเปลี่ยน route) — ใช้ `scrollToId()`
- **DON'T** โหลดอะไรจากเซิร์ฟเวอร์ภายนอกตอน runtime (ฟอนต์, CDN, analytics) และไม่เรียก API/LLM จากเว็บ
- **DON'T** commit ข้อมูลจริง — repo มีแต่ `web/fixtures/` (สังเคราะห์); ข้อมูลจริงวางด้วย `atlas publish --site` ตอน deploy

### LLM prompts

- Prompts อยู่ใน `prompts/*.md` เท่านั้น (block ใต้ "Prompt (master)") — โค้ดอ่านไฟล์ตอนรัน ไม่มีสำเนาในโค้ด; แก้ prompt = แก้ไฟล์เดียวแล้วบอกใน commit
- cache key = sha256(model + `prompt_version` + prompt ที่เติมค่าแล้ว)[:16] ใน `state_dir/llm_cache/<task>.jsonl` — `prompt_version` คือ hash ของ template เท่านั้น (แก้หมายเหตุนอก block ไม่ทำให้จ่ายซ้ำ)
- ไฟล์: `topic_label.th` (label), `topic_merge.th` (merge), `topic_narrative.th` (narrative), `executive_brief.th` (brief)

## 7. บริบทภาษาไทยที่ต้องรู้

- ข้อความไทยจาก PDF อาจมีอักษร Private-Use (U+F700–F71A) — `atlas.thai.clean_text` ซ่อมให้; ห้ามลบทิ้ง
- ข้อมูล TCI เป็นไทย+อังกฤษปนกัน — embedding ต้อง multilingual (default: API `text-embedding-3-large` หรือ local `BAAI/bge-m3`)
- c-TF-IDF ตัดคำไทยด้วย pythainlp (newmm) และนับคำสำคัญของผู้เขียน (author keywords) เป็นวลีทั้งก้อน — `char_wb` n-gram (2–4) ใช้เฉพาะ embedder โหมด `lite` (TF-IDF + SVD) ไม่ใช่ c-TF-IDF
- ปีในข้อมูลอาจเป็น พ.ศ. — `ingest.py` แปลงเป็น ค.ศ. แล้ว (ทุกอย่าง downstream เป็น ค.ศ.)
- UI ภาษาไทยห้ามใช้ italic (ภาษาไทยไม่มีตัวเอียงแท้)

## 8. เมื่อไม่แน่ใจ

1. ดู `docs/ARCHITECTURE.md` ก่อน — เข้าใจการไหลของข้อมูล
2. ดู `docs/DATA_SPEC.md` — schema ทุกไฟล์ checkpoint
3. ดู `docs/OPERATIONS.md` — ถ้าเป็นเรื่องรันงานจริง
4. ถามผู้ใช้ถ้าการตัดสินใจกระทบ "นิยาม" (เช่น เปลี่ยน threshold ของ emerging) เพราะผู้บริหารใช้ตัวเลขเหล่านี้สื่อสารต่อ
