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
├── CITATION.cff            ← วิธีอ้างอิง Atlas (ผู้แต่ง = องค์กร TCI; CC-BY-4.0 เฉพาะข้อมูล — โค้ดยังไม่มี LICENSE)
├── DESIGN.md               ← ระบบดีไซน์ (tokens + กฎ) — ชนะ catalog ทั่วไปเสมอ
├── docs/
│   ├── ARCHITECTURE.md     ← การออกแบบระบบ + การไหลของข้อมูล
│   ├── DATA_SPEC.md        ← สเปก input (ThaiJO Markdown) และ output (atlas_data.json)
│   ├── EMERGING_SPEC.md    ← นิยาม "emerging" ของ TCI ฉบับเต็ม + สูตรคะแนน
│   ├── ROADMAP.md          ← ฟีเจอร์ทั้ง 5 phase + ของที่ควรทำต่อ
│   ├── OPERATIONS.md       ← รอบไตรมาสด้วยคำสั่งเดียว (`atlas quarterly`) step-by-step + embedding ครั้งใหญ่ + troubleshoot
│   ├── corpus/             ← คู่มือเตรียมคลังรูปแบบ 1.0 สำหรับทีมข้อมูล (README.md) + corpus.schema.json (generated) + validate_jsonl.py + example/ (สังเคราะห์)
│   └── superpowers/        ← specs + plans ของ v2 (แผนหลัก: specs/2026-10-18-tci-atlas-v2-design.md)
├── pipeline/               ← Python batch pipeline (Phase 1,2,4,5)
│   ├── atlas/              ← โมดูล pipeline: ingest→preprocess→embed→cluster→taxonomy→label
│   │                         →series→emerging→keywords→forecast→narrate→layout→methods→journals→match
│   │                         →institutions→sdg→benchmark→gaps→references→search→kwtrends
│   │                         →export (P2: journals.py, journal_metrics.py, journal_topics.py, registry.py, methods.py, matcher.py, diff.py;
│   │                         P3: places.py, institutions_ref.py, institutions.py, sdg.py, global_bench.py, gaps.py, export_exec.py;
│   │                         P4: references.py, search_index.py, kwtrends.py, export_research.py, feeds.py (ฟีด Atom ตอน publish))
│   │   ├── sources/        ← parser ข้อมูลเข้า (corpus_jsonl.py = คลังรูปแบบ 1.0 ที่แนะนำ · thaijo_md.py)
│   │   └── schema/         ← data contract v2 (contract.py → JSON Schema) · corpus.py (คลังรูปแบบ 1.0 → docs/corpus/corpus.schema.json)
│   │   (quarterly.py = `atlas quarterly` · corpus_convert.py = `atlas corpus convert` · companions.py = ตรวจ journals.csv / institutions_aliases.csv / province_population.csv / ror.zip ที่มากับคลัง)
│   ├── configs/ci.yaml     ← config สำหรับ CI
│   ├── atlas/data/         ← ข้อมูลอ้างอิงสาธารณะที่ commit: th_provinces.csv (77 จังหวัด ISO 3166-2:TH), frameworks.yaml (SDG/BCG/แผน ววน./หมุดหมายแผนฯ 13 + คำสำคัญ)
│   ├── registry/           ← ไฟล์ที่ผู้ดูแลคัดเอง (journals.csv, institutions_aliases.csv, province_population.csv — git-ignored) — repo มีแต่ *.example.csv
│   ├── state/              ← ข้อมูลถาวรข้ามรอบ (embedding store, LLM cache, ID หัวข้อ/ตำแหน่งแผนที่ต่อรอบ, งานอ้างอิง OpenAlex) — git-ignored, ห้ามลบ
│   ├── config.example.yaml ← คัดลอกเป็น config.yaml แล้วแก้
│   ├── tests/              ← pytest (มี test_emerging.py ครอบคลุมนิยาม emerging; fixtures/match_parity.json + search_parity.json ตรึงฝั่งเว็บ)
│   ├── scripts/            ← run_all.sh · make_search_parity.py (สร้าง tests/fixtures/search_parity.json)
│   └── requirements.txt    ← export จาก uv.lock สำหรับติดตั้งแบบไม่ใช้ uv (ทางหลักคือ `uv sync`)
├── web/                    ← เว็บ v2: React 19 + Vite + TS + Tailwind 4, HashRouter (ดู web/README.md)
│   ├── src/data/           ← contract.ts (generated) · source.ts (Http | Embedded) · release.ts (loader)
│   ├── src/styles/tokens.css ← design tokens (ธีมสว่างธีมเดียว ค่าตาม DESIGN.md)
│   ├── src/strings/        ← ข้อความ UI ไทย+อังกฤษทุกตัว
│   ├── src/pages/          ← overview · atlas · topics/:id · emerging · compare · data · about · brief · journals · journals/:id · methods · changes · match · institutions · institutions/:id · regions · sdg · global · gaps · search · galaxy · keywords · references · province · province/:code · ideas · story (atlas, brief และตั้งแต่ journals เป็น React.lazy; brief อยู่ในเลย์เอาต์ของเว็บแล้ว พิมพ์แล้วซ่อนส่วนหัว/เมนู; เมนูจัดตามคำถาม: อะไรกำลังมา · ใครทำเรื่องอะไร · ไทยอยู่ตรงไหน · หางานวิจัย (แต่ละหน้ามีบรรทัดคำถามใต้ชื่อในเมนูเดสก์ท็อป); ชื่อเมนู: about = "อ่านตัวเลขอย่างไร", galaxy = "แผนที่บทความทุกเรื่อง", gaps = "โอกาสที่ยังไม่มีใครทำ")
│   ├── src/components/     ← Figure (แถบคำบรรยาย + แผนภูมิ/ตาราง + วิธีอ่าน + CSV) · StatTile · DataTable (`primary`, `limit`) · Term/InfoPop · HowNote · SourceLine · CsvButton · Steps · PhoneFold · StatusLegend ฯลฯ
│   ├── src/charts/         ← SVG เขียนเอง: forest · portfolio · trend · multi-line + ชุด infographic (StatusWaffle, DotPlot, BarRank, ArcNetwork, ColumnChart, MixBar/SplitBar, OpportunityQuadrant, StatusFlow, LineageKey, GoalTiles, BridgePairs, JournalScatter, PeriodMix, ChecklistBars, SmallMultiples) — คณิตการจัดวางแบบ pure + test อยู่ใน `infographic.ts` · `execLayout.ts` · `editorLayout.ts`
│   ├── src/embed/          ← กราฟฝัง /embed/topic/:id · /embed/emerging (นอก app shell, lazy) + ปุ่มคัดลอก <iframe> และลิงก์ฟีด
│   ├── src/lib/            ← searchTokens.ts (คู่ของ atlas.search_index) · searchClient.ts · citation.ts (RIS/BibTeX) · galaxyGl.ts (WebGL2) · matcher.ts · urlState.ts ฯลฯ
│   ├── src/geo/thProvinces.ts ← เส้นขอบ 77 จังหวัด (Natural Earth, สาธารณสมบัติ; สร้างครั้งเดียวด้วย scripts/make-province-map.mjs)
│   └── fixtures/           ← รอบข้อมูลสังเคราะห์ (example + empty) สำหรับ dev/test — ไม่ใช่ข้อมูลจริง
├── prompts/                ← LLM prompts ทั้งหมด (ฉบับเดียว — โค้ดอ่านไฟล์ตอนรัน)
└── scripts/
    ├── quarterly_run.sh    ← = uv run atlas quarterly (cron) · quarterly_run.cmd = ดับเบิลคลิกบน Windows
    └── import_atlas.sh     ← build เว็บ + atlas publish --site web/dist (วาง data/ + ไฟล์ออฟไลน์)
```

## 3. แผนฟีเจอร์ 5 Phase (สถานะปัจจุบัน)

| Phase | ฟีเจอร์ | ที่ตั้ง | สถานะ |
|---|---|---|---|
| 1 | Embedding (batch, API **หรือ** local model) | `pipeline/atlas/embed.py` | ✅ พร้อมใช้ |
| 2 | Topic Clustering 2 ชั้น (UMAP+HDBSCAN, c-TF-IDF) | `pipeline/atlas/cluster.py` | ✅ พร้อมใช้ |
| 3 | Atlas web v2 (7 หน้า + brief, 2 ภาษา, URL state, offline HTML, PDF) | `web/` | ✅ พร้อมใช้ |
| 4 | Emerging Topic Analysis (นิยาม v3 + burst + score) | `pipeline/atlas/emerging.py` + `web/src/pages/EmergingPage.tsx` | ✅ พร้อมใช้ |
| 5 | Research Trend Forecasting (Forecast v2, skill gate) | `pipeline/atlas/forecast.py` + `web/src/charts/TrendChart.tsx` | ✅ พร้อมใช้ |
| + | LLM labeling + merge duplicates | `pipeline/atlas/label.py` | ✅ พร้อมใช้ |
| + | Live dashboard (อ่าน data/latest.json ตอนเปิดหน้า, แถบแจ้งเมื่อโหลดไม่ได้) | `web/src/data/{source,release}.ts` | ✅ พร้อมใช้ |
| P1 | ID หัวข้อถาวร + lineage, OpenAlex taxonomy, Forecast v2, emerging keywords, แผนที่นิ่ง | `pipeline/atlas/{lineage,taxonomy,forecast,keywords,layout}.py` | ✅ |
| P1 | LLM ผ่าน API (label · merge · narrative · brief) + review/overrides | `pipeline/atlas/{llm,llm_runner,label,review,narrative}.py` | ✅ |
| P1 | Contract v2 release + validate + publish --site (+ offline HTML) | `pipeline/atlas/{export_v2,validate,publish}.py` | ✅ |
| P2 | Editors: journals (D1–D5, D7), methods (E11), what changed (E5), match my abstract (R3/R4) | `pipeline/atlas/{journals,methods,matcher,diff}.py` + `web/src/pages/{Journals,Journal,Methods,Changes,Match}Page.tsx` | ✅ |
| P4 | Researchers: ค้นหาบทความทั้งคลัง (R2) + RIS/BibTeX (R9), กาแล็กซีบทความ WebGL2 (R8), แนวโน้มคำสำคัญ + อภิธานศัพท์ไทย↔อังกฤษ (R7), การอ้างอิงรายวารสาร + ถูกอ้างใน TCI (D7, R12), ฟีด Atom (R11), กราฟฝัง, อ้างอิง Atlas + `CITATION.cff`, `atlas sdg-scores`, `/atlas` `/brief` lazy | `pipeline/atlas/{references,search_index,kwtrends,export_research,feeds}.py` + `web/src/pages/{Search,Galaxy,Keywords,References}Page.tsx` + `web/src/embed/` | ✅ |
| P3 | Executives: สถาบัน + เครือข่ายความร่วมมือ + แผนที่จังหวัด (E6, E7, D6, R6), SDG/BCG/แผน ววน./แผนฯ 13 (E8), ไทยเทียบโลก (E9), ช่องว่างงานวิจัย + ความเสี่ยงกระจุกตัว (R5, E10), KPI ครบ + ประโยคเชิงนโยบายในภาพรวม/brief | `pipeline/atlas/{places,institutions_ref,institutions,sdg,global_bench,gaps,export_exec}.py` + `web/src/pages/{Institutions,Institution,Regions,Sdg,Global,Gaps}Page.tsx` | ✅ |
| Redesign | โลก "ข่าวข้อมูล": หน้าแรกเป็นเรื่องเล่าข้อมูล (คำถามเป็น h1 · คำตอบ 1 ประโยค · ตัวเลข 1 ตัว · กราฟเส้นที่เน้นได้ `StoryLines` ใน `pages/overview/StoryHero.tsx`, `lib/story.ts`), แถบบนสีขาวพร้อมโลโก้ TCI, ส่วนท้ายมีโลโก้ TCI · NECTEC · สวทช., ตัด dark mode, palette ใหม่ทั้งชุด | `web/src/{styles,components,charts}/` + `PRODUCT.md` + `.impeccable/surfaces/web-src.md` | ✅ |
| Refresh | ภาษาง่าย 2 ชั้น + infographic ทุกหน้า (type scale, เมนูมือถือ, StatTile, Term, finding cards, waffle, เครือข่ายความร่วมมือ, goal tiles, quadrant ฯลฯ) + ประโยคแม่แบบ/prompt ภาษาง่ายใน pipeline — นิยามและ contract ไม่เปลี่ยน | `web/src/{components,charts,strings}/` + `pipeline/atlas/narrative.py` + `prompts/` (แผน `docs/superpowers/plans/2026-10-23-web-refresh.md`) | ✅ |

สิ่งที่ยังไม่มี / ไอเดียต่อยอดอยู่ใน `docs/ROADMAP.md` (หัวข้อ "ต่อยอดจาก P2/P3/P4" และ "ต่อยอดจาก web refresh" เช่น ปรับแผนที่บทความ/แผนที่จังหวัดกับข้อมูลจริง, LICENSE ของโค้ด, API backend)

## 4. คำสั่งที่ใช้บ่อย

### Pipeline (ทำงานใน `pipeline/`)

```bash
cd pipeline
uv sync                                    # + --extra api / --extra local
cp config.example.yaml config.yaml         # แก้ input.path → โฟลเดอร์ .md
uv run atlas quarterly --corpus <คลัง> --release 2026Q4   # รอบไตรมาสครบในคำสั่งเดียว → runs/<รอบ>/ + deploy/<รอบ>/site (ถามก่อนจ่ายค่า LLM; --prepare = หยุดหลังตรวจคลัง)
uv run atlas profile ../corpus             # ตรวจคุณภาพคลังก่อนเสมอ (ดูรูปแบบจากโฟลเดอร์เอง: articles/*.jsonl → corpus_jsonl, ไม่งั้น .md; exit 1 เมื่อบรรทัดผิดเกินเพดาน)
uv run atlas corpus schema                 # docs/corpus/corpus.schema.json (หลังแก้ atlas/schema/corpus.py)
uv run atlas corpus convert <โฟลเดอร์ .md> --out <คลังใหม่>   # คลัง .md → รูปแบบ 1.0 (รหัสบทความเดิม)
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
uv run atlas publish -c config.yaml --site ../web/dist   # data/<release>/ + data/latest.json + atlas-offline.html (+ data/feeds/ เมื่อตั้ง publish.site_url)
uv run atlas sdg-scores -c config.yaml                   # ตั้งเกณฑ์ sdg.min_similarity: ควอนไทล์ cosine + จำนวนคู่ต่อเกณฑ์ 0.30…0.60 (อ่านอย่างเดียว; ต้อง sdg.method embedding)
uv run atlas bakeoff -c config.yaml --kind all           # เทียบ embedding/clustering
uv run python scripts/make_search_parity.py              # หลังแก้การตัดคำของ search_index → สร้าง tests/fixtures/search_parity.json ใหม่ (แล้วแก้ web/src/lib/searchTokens.ts ให้ตรง)
```
(ฟีด Atom เขียนเฉพาะเมื่อตั้ง `publish.site_url` = ที่อยู่สาธารณะของเว็บ — ไม่ตั้ง = publish บอกว่าไม่มีฟีด; ดู `docs/OPERATIONS.md` §19)
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
bash scripts/quarterly_run.sh --corpus <คลัง> --release 2026Q4   # = atlas quarterly (Windows: scripts\quarterly_run.cmd)
bash scripts/import_atlas.sh                              # (ทำเอง) build เว็บ + atlas publish --site web/dist
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
- ข้อเท็จจริงที่ UI ใช้: share/growth เป็นทศนิยม (0.10 = 10%), ระดับช่วงเชื่อมั่นคือ `manifest.ci_level`, `share_ratio: null` + `no_baseline: true` → "ใหม่ — ปี {B} ยังไม่มีงานเรื่องนี้", `low_data_reason ∈ {few_articles, not_estimable}`, `forecast.show === false` → "แนวโน้มไม่แน่นอน", นิยามสถานะแสดงจาก `manifest.definition_version` (ตอนนี้ 3)
- **contract 2.1 (P2, เพิ่มอย่างเดียว):** ไฟล์เสริม `journals.json`, `journals/<id>.json`, `methods.json`, `diff.json`, `match.json` ที่ประกาศใน `manifest.modules` — ทุกไฟล์ optional; เว็บตรวจ major 2 เท่านั้น และหน้าที่ต้องใช้ไฟล์เหล่านี้ต้องอธิบายตัวเองเมื่อไม่มี (`ModuleFile`); `match.json` ไม่อยู่ใน HTML ออฟไลน์ (`export.offline_exclude`)
- **contract 2.2 (P3, เพิ่มอย่างเดียว):** ไฟล์เสริม `institutions.json`, `institutions/<id>.json`, `regions.json`, `sdg.json`, `global.json`, `gaps.json` ใน `manifest.modules`; `Kpis` เพิ่ม `pct_international`, `pct_multi_institution`, `provinces` (เป็นเปอร์เซ็นต์ เหมือน `pct_abstract_en`); `Overview.executive` (ประโยคแม่แบบ ไม่ใช้ LLM); `Manifest.skipped_modules` (โมดูลที่ข้ามพร้อมเหตุผล เช่น `global` เมื่อ OpenAlex ใช้ไม่ได้); `CountItem.id` ลิงก์สถาบันได้ด้วย — สถาบันที่มีบทความน้อยกว่า `institutions.min_articles` ไม่ถูกเผยแพร่/ลิงก์
- **contract 2.3 (P4, เพิ่มอย่างเดียว):** ไฟล์เสริม `references.json`, `search/meta.json`, `search/vocab.json`, `search/idx-<NNN>.json`, `search/docs-<NNN>.json`, `galaxy.json`, `kwtrends.json` — โมดูล `references`, `search`, `galaxy`, `kwtrends` ใน `manifest.modules` หรือเหตุผลใน `manifest.skipped_modules` (เช่น coverage ของรายการอ้างอิงต่ำกว่า `references.min_coverage`, `layout.galaxy is false`); `TopicDetail` เพิ่ม `cited_in_tci` และ `glossary` (**null = ไม่เผยแพร่, [] = ไม่พบ**); `Latest` เพิ่ม `feeds` (true เมื่อ publish เขียน `data/feeds/releases.xml` + `data/feeds/topics/<id>.xml` — ต้องตั้ง `publish.site_url`); checkpoint `19_*` (references) · `20_*` (search + galaxy) · `21_*` (kwtrends); ลำดับ step `… gaps → references → search → kwtrends → export`; `search/` และ `galaxy.json` ไม่อยู่ใน HTML ออฟไลน์ (`export.offline_exclude`); ordinal บทความ (`search_index.doc_order`) ใช้ร่วมกันระหว่าง doc shard และ galaxy; references เผยแพร่เมื่อ coverage ≥ `min_coverage` และส่วน "ถูกอ้างใน TCI" เมื่อจับคู่ได้ ≥ `min_internal_matches` (ไม่ถึง → `internal: null` + `internal_reason`)
- **contract 2.4 (เพิ่มอย่างเดียว):** `JournalDetail.topic_years` = สัดส่วนหัวข้อรายปีของวารสาร (`years`, `articles`, `min_articles`, `topics[{topic, shares}]`, `other`; **null = ไม่เผยแพร่** เช่นวารสารข้อมูลน้อย) จาก checkpoint `13_journal_topic_years`; config `journals.year_mix_topics` (0–4, เท่าจำนวนแบบเส้นของเว็บ) + `journals.year_mix_min_articles` (ปีที่บทความน้อยกว่านี้ = null ไม่ใช่ศูนย์)
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
- **DO** แถวผู้แต่งอ่านเพื่อ **สังกัด** เท่านั้นใน `institutions_ref` / `institutions` (คอลัมน์ชื่อบุคคลถูกทิ้งตอนอ่าน) — สถาบันที่มีบทความในช่วงต่ำกว่า `institutions.min_articles` ถูกนับในยอดรวมแต่ไม่เคยถูกแสดงเป็นรายการ ลิงก์ หรือจับคู่ในเครือข่าย; ตารางชื่อสถาบัน (`registry/institutions_aliases.csv`) และตารางประชากร (`province_population.csv`) เป็นไฟล์ในเครื่อง git-ignored
- **DO** เรียก LLM ผ่าน `atlas.llm_runner.run_job` เท่านั้น (cache, งบ, หยุด/ต่อ, repair, fallback; lock/progress/stop ใช้ `atlas.jobs` ของ P0 ตัวเดียวกับ embedding) — งาน LLM เป็นระดับหัวข้อ ไม่เรียกต่อบทความ
- **DO** ตัวเลขในข้อความที่ LLM เขียนต้องมาจาก pipeline และผ่าน `narrative.grounding_error` (ปฏิเสธตัวเลขที่ไม่อยู่ในข้อมูล, คำบอกจำนวนเท่าที่ไม่มีที่มา, และทิศทางผิดในประโยคอัตรา; เขียนใหม่ 1 ครั้ง แล้วใช้ประโยคแม่แบบ) — ห้ามเผยแพร่ข้อความ LLM ที่ไม่ได้ตรวจ
- **DO** ไฟล์ P4 (ค้นหา กาแล็กซี การอ้างอิง RIS/BibTeX) เผยแพร่ข้อมูลบทความได้แค่ id, ชื่อเรื่อง TH/EN, ปี, ชื่อวารสาร, หัวข้อ, DOI, ลิงก์ ThaiJO, จำนวนถูกอ้างใน TCI — ไม่มีชื่อผู้แต่ง ไม่มีบทคัดย่อ ไม่มีข้อความรายการอ้างอิง; ดัชนีค้นหาสร้างจาก `title_th/en` + `keywords_th/en` เท่านั้น (`test_release` สแกนหาชื่อผู้แต่ง/บทคัดย่อ)
- **DO** แก้การตัดคำของ `atlas.search_index` (normalisation, stopword, กฎ token) = รัน `scripts/make_search_parity.py` ใหม่ + แก้ `web/src/lib/searchTokens.ts` ให้ได้ผลเดียวกัน + เพิ่ม `TOKENIZER_VERSION` ทั้งสองฝั่ง — `search_parity.json` ตรึงทั้ง pytest และ vitest
- **DON'T** ลดเกณฑ์ `references.min_coverage` / `min_internal_matches` เพียงเพื่อให้หน้าแสดงผล — คลังที่รายการอ้างอิงครอบคลุมต่ำทำให้ตัวเลขรายวารสารหลอกตา (ถามเจ้าของข้อมูล)
- **DO** ประโยคที่ pipeline เขียนให้สาธารณะ (brief, `overview.executive`, คำอธิบายหัวข้อแบบแม่แบบ, เหตุผลความกว้าง, บันทึกวิธีวิจัย, สรุปในฟีด) ใช้ภาษาง่าย: เขียนปีแทน "ช่วงฐาน/ช่วงล่าสุด", มีหน่วยทุกตัวเลข, ชื่อสถานะไทย/อังกฤษจาก `narrative.STATUS_TH/STATUS_EN` (ไม่ใช่รหัส) และต้องผ่าน `narrative.jargon_in` (คำต้องห้าม `JARGON_TH/JARGON_EN` + รหัสสถานะ; `test_release.py::test_published_template_sentences_are_plain_language` ตรวจทุกไฟล์ที่เผยแพร่) — ตัวเลขและข้อเท็จจริง "(x เท่า)" ห้ามเปลี่ยน
- **DO** คลังรูปแบบ 1.0: แก้ช่องข้อมูล = แก้ `atlas/schema/corpus.py` + `atlas corpus schema` + `docs/corpus/README.md` + ตัวอย่างใน `docs/corpus/example/` พร้อมกัน (`test_corpus_jsonl` ตรวจ drift และอ่านตัวอย่าง); เพิ่มได้อย่างเดียวภายใน 1.x — รหัสบทความที่ได้จากกฎ id ห้ามเปลี่ยน (ประวัติหัวข้อและ store embedding ผูกกับมัน)
- **DO** ชื่อสถาบันที่เผยแพร่ต้องผ่าน `orgs.publishable_name` (ไม่มีอีเมล/ที่อยู่ และมีคำบอกองค์กร); หน้าหัวข้อแสดงเฉพาะสถาบันที่เผยแพร่ (≥ `institutions.min_articles`); `atlas validate`/`publish` สแกนรอบจริงหาอีเมล ORCID และชื่อผู้แต่ง (`atlas/privacy.py`) — error = ห้ามเผยแพร่; ห้ามลดด่านนี้เพื่อให้ผ่าน
- **DO** วารสารระบุด้วย `journal_key` (`registry.journal_keys`) ในทุกการนับ/กลุ่ม ไม่ใช่ `journal_name`; ตัดซ้ำในชั้นชื่อเรื่อง+ปีใช้ชื่อเรื่องทั้งชื่อ (`ingest._drop_title_year_duplicates`)
- **DON'T** ใช้ชื่อรอบ (release) นอกรูป YYYYQn, ใช้ ID หัวข้อซ้ำ หรือรันรอบที่เก่ากว่ารอบที่มีอยู่ — โค้ดปฏิเสธอยู่แล้ว อย่าเลี่ยง

### Web

- **DO** อ่าน `DESIGN.md` ก่อนทำ UI — ชนะ catalog ทั่วไปเสมอ; งาน UI ใช้ skill `impeccable` ก่อน และกราฟใช้ skill `dataviz`
- **DO** ใช้ design tokens จาก `web/src/styles/tokens.css` เท่านั้น (`var(--…)`): โลกดีไซน์ **"ข่าวข้อมูล" (data explainer)** (เจ้าของเลือก 2026-10-23 แทน Civic modern; สัญญาทิศทางอยู่ใน `.impeccable/surfaces/web-src.md`, ข้อมูลผลิตภัณฑ์ใน `PRODUCT.md`) — พื้นขาว **ธีมเดียว (ไม่มีโหมดมืด)**, ฟอนต์ **Sarabun** อย่างเดียว (self-hosted), **น้ำเงิน TCI `#283894`** (จากโลโก้) สำหรับแบรนด์และข้อมูลที่ตอบคำถามของหน้า, **ส้ม TCI** (`--accent-mark #e07000`) เฉพาะจุดเน้นจุดเดียวต่อมุมมอง, ข้อมูลประกอบเป็นเทา (`--context`), ink `#14182b`; เส้น hairline, มุมโค้ง 8 px เฉพาะปุ่ม/ช่องกรอก (แผงอ่อน 12 px), ตัวเลขยืนบนหน้าไม่มีกรอบ; focus = วงแหวนน้ำเงิน 3 px; โลโก้ TCI · NECTEC · สวทช. อยู่ที่ `src/assets/brand/partners/` (`brand/brand.ts`); สีสาขาเป็น token `cat-01…cat-12` — civic blue `#0f3557`, focus yellow, highlighter `#ffe07a` และกรอบหมึกหนา 2 px **เลิกใช้แล้ว**; ห้ามมี eyebrow/kicker เหนือหัวข้อ, การ์ดขนาดเท่ากันเป็นโครงหน้า, แถบสีข้าง (border-left หนา) และ gradient text
- **DO** แสดงสถานะด้วยรูปทรง + สี + ชื่อเสมอ (▲ EMERGING · ◆ WATCH · ● HOT · ▼ DECLINING · ■ STABLE · วงประ LOW_DATA); สีสถานะใช้กับสถานะเท่านั้น; เปลี่ยนสีต้องผ่าน `web/src/styles/palette.test.ts` (CVD + contrast; ทดสอบด้วยว่าไม่มีบล็อกธีมมืด)
- **DO** รองรับ 2 ภาษาทุกสตริง — เพิ่ม key ใน `web/src/strings/<หน้า>.ts` ทั้ง `th` และ `en` (`i18n.test.ts` ตรวจ)
- **DO** เขียนข้อความ 2 ชั้น (DESIGN.md "Copy voice"): ชั้น 1 (หัวข้อ, lede, หัวคอลัมน์, ชื่อกราฟ, การ์ด) = ประโยคสั้นภาษาง่าย **ขึ้นด้วยตัวอย่าง** ("เช่น …") ตัวเลขจากข้อมูลพร้อมหน่วย; ชั้น 2 (กฎเต็ม, วิธีคิด, ศัพท์สถิติ) อยู่หลัง "วิธีอ่าน" ของ `Figure`, `HowNote` หรือ `Term` — ห้ามมีในชั้น 1: ช่วงเชื่อมั่น, ช่วงฐาน, ช่วงล่าสุด, subfield, HHI, Jaccard, Jensen–Shannon, cosine, metadata, embedding และรหัสสถานะ (EMERGING, LOW_DATA …) ในประโยคไทย; ใช้ปีแทนช่วง และชื่อสถานะไทย (กำลังเกิดใหม่ · จับตา · กำลังมาแรง · ลดลง · คงที่ · ข้อมูลน้อย)
- **DO** ใช้แพตเทิร์นเดิม: กราฟอยู่ใน `Figure`, ตัวเลขสำคัญเป็น `StatTile`/`StatGrid` (ไม่ใช่รายการ label/value), ศัพท์เป็น `Term` (คำอธิบายใน `strings/glossaryDefs.ts`), รายละเอียดวิธีคิดนอก figure เป็น `HowNote`, ตาราง/แผนที่นอก figure จบด้วย `SourceLine`; กราฟรูปแบบใหม่เขียนเป็น SVG ใน `web/src/charts/` ตามกฎ infographic kit ใน DESIGN.md (แท็บตาราง, ป้าย ≥ 14 px, ink + น้ำเงินเดียว, ลายเส้นทแยง/เส้นประเมื่อไม่มีข้อมูล, ไม่มีข้อมูลที่เห็นได้เฉพาะตอน hover) และย้ายคณิตการจัดวางไปไฟล์ `.ts` ที่มี test
- **DO** ทุกกราฟมีแท็บตาราง + คำบรรยายมีเลข ("แผนภูมิ n", "ตาราง n") + บรรทัด "ที่มา:"; ตารางเรียงได้ (`aria-sort`) และ export CSV ได้
- **DO** หน้าที่ใช้ไฟล์ module (journals/methods/diff/match) เรนเดอร์ผ่าน `ModuleFile` — ถ้าไม่มีโมดูลต้องแสดง h1 พร้อมเหตุผล ไม่ใช่หน้าขาว; ข้อความที่วางใน `/match` ต้องไม่ออกจากเบราว์เซอร์ (ไม่อยู่ใน URL, storage หรือ request) และ `web/src/lib/matcher.ts` ต้องตรงกับ `pipeline/tests/fixtures/match_parity.json`
- **DO** โมดูลที่ pipeline ข้าม (เช่น `global` ตอน offline) ต้องอธิบายตัวเองผ่าน `ModuleFile` โดยอ่านเหตุผลจาก `manifest.skipped_modules`; แผนที่จังหวัด (`ProvinceMap`) ไม่สื่อตัวเลขด้วยสีอย่างเดียว — มีมุมมองตารางครบทุกจังหวัดเสมอ และเส้นขอบจังหวัดอยู่ใน chunk ของ `/regions` เท่านั้น (entry ≤ 180 KB gzip)
- **DO** ทำให้ section "หดตัวเอง" (ไม่ render) เมื่อข้อมูลไม่มีฟิลด์นั้น; หน้าเว็บไม่มีวันขาว
- **DO** หน้า/ส่วน/กราฟใหม่ที่ lazy เก็บข้อความในไฟล์ `src/strings/<หน้า>.ts` ของตัวเองแล้วอ่านด้วย `useStrings(dict)` (`src/lib/i18n.ts`; เช่น `execViz`, `editorViz`, `openViz`, `glossaryDefs` — เพิ่มไฟล์ใหม่ใน `LAZY` ของ `i18n.test.ts`) — import เฉพาะในหน้า lazy นั้น ไม่ใช่ใน dictionary กลาง เพื่อรักษางบ entry ≤ 180 KB gzip (หลัง P4 ≈ 171 KB; `npm run check:bundle` ตรวจงบ + ทุก lazy import ใน `App.tsx` เป็น chunk แยก)
- **DO** `/search` ใช้ `searchTokens.ts` ที่ต้องตรงกับ `pipeline/tests/fixtures/search_parity.json` (คำที่ไม่อยู่ใน vocab ต้องบอกผู้ใช้ ไม่ทิ้งเงียบ) และโหลด doc shard ≤ 6 ไฟล์ต่อคำค้น (`MAX_DOC_SHARDS`) — ผลจากบางส่วนต้องบอกผู้อ่าน; RIS/BibTeX (`citation.ts`) ไม่มีบรรทัดผู้แต่ง — RIS ใส่ชื่อเรื่องอังกฤษใน `TT` และวารสารใน `T2`
- **DO** กราฟฝัง (`/embed/*`) อยู่นอก app shell (ไม่มีเมนู/ส่วนท้าย) แต่ต้องมีลิงก์ที่มา "TCI Research Atlas" และป้ายข้อมูลตัวอย่างเมื่อเป็นข้อมูลสังเคราะห์; ลิงก์ฟีดแสดงเฉพาะเมื่อ `latest.feeds === true`
- **DO** เก็บสถานะตัวกรอง/การเลือกไว้ใน URL ผ่าน `useUrlState` + codec ใน `web/src/lib/urlState.ts`
- **DO** ไฟล์ `.tsx` export ได้เฉพาะ component (กฎ react-refresh) — hook/context/helper อยู่ใน `.ts`; ห้าม setState แบบ synchronous ใน effect และห้ามอ่าน `ref.current` ระหว่าง render (react-hooks v7)
- **DO** ออกแบบสำหรับข้อมูลขนาดจริง (หัวข้อ ~1,500 · วารสาร ~2,000 · สถาบัน ~10,000): ตารางที่อาจยาวต้องส่ง `limit` ให้ `DataTable`, รายการ/กราฟที่ยาวใช้ `useCapped` + `ListMore` (แสดง 20–25 รายการ + "แสดงทั้งหมด (n)"), ช่องของ `StatusWaffle` รวมหลายหัวข้อเมื่อเกิน 300 (`waffleUnit`), ป้ายชื่อบนแผนที่วางด้วยกล่องที่วัดจริง (`lib/labels.ts`); มี `ErrorBoundary` ใน `Layout` (หน้าไม่ขาวแม้ chunk หาย/ข้อมูลผิดรูป); หน้าหลักขึ้นต้นด้วยคำถามเป็น h1 และประโยคแรกของ lede เป็นคำตอบพร้อมเลขรอบ; สถานะในตาราง/ลิสต์ต้องมีชื่อกำกับเสมอ (`TopicLink showStatus` / `StatusChip`)
- **DON'T** ใช้ Tailwind class แบบ dynamic (`bg-[${color}]`) — ใช้ inline style `var(--…)` หรือ class ที่เขียนไว้ใน CSS ครบทุกค่า (`chip-${status}`)
- **DON'T** ใช้ `href="#id"` ในหน้า (HashRouter จะเปลี่ยน route) — ใช้ `scrollToId()`
- **DON'T** โหลดอะไรจากเซิร์ฟเวอร์ภายนอกตอน runtime (ฟอนต์, CDN, analytics) และไม่เรียก API/LLM จากเว็บ
- **DON'T** commit ข้อมูลจริง — repo มีแต่ `web/fixtures/` (สังเคราะห์); ข้อมูลจริงวางด้วย `atlas publish --site` ตอน deploy

### LLM prompts

- Prompts อยู่ใน `prompts/*.md` เท่านั้น (block ใต้ "Prompt (master)") — โค้ดอ่านไฟล์ตอนรัน ไม่มีสำเนาในโค้ด; แก้ prompt = แก้ไฟล์เดียวแล้วบอกใน commit
- cache key = sha256(model + `prompt_version` + prompt ที่เติมค่าแล้ว)[:16] ใน `state_dir/llm_cache/<task>.jsonl` — `prompt_version` คือ hash ของ template เท่านั้น (แก้หมายเหตุนอก block ไม่ทำให้จ่ายซ้ำ)
- ไฟล์: `topic_label.th` (label), `topic_merge.th` (merge), `topic_narrative.th` (narrative), `executive_brief.th` (brief), `topic_methods.th` (บันทึกวิธีวิจัย)
- prompt ที่เขียนข้อความสาธารณะ (narrative, brief, methods) มีบล็อก "ภาษาและน้ำเสียง" ใน "Prompt (master)": ภาษาง่าย เริ่มด้วยตัวอย่าง หน่วยทุกตัวเลข ปีแทนช่วง ชื่อสถานะไทย/อังกฤษ และรายการคำต้องห้ามชุดเดียวกับ `narrative.JARGON_*` — แก้รายการต้องแก้ทั้งสองที่; `topic_label.th` ไม่ได้แก้โดยตั้งใจ (แก้ = ตั้งชื่อทุกหัวข้อใหม่และเสียค่า LLM ทั้งชุด) · ข้อความจาก LLM ผ่านทั้ง `grounding_error` และ `jargon_in` (`narrative._checker`; ไม่ผ่าน = เขียนใหม่ 1 ครั้ง แล้วใช้ประโยคแม่แบบ)

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
