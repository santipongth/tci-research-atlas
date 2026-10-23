# ROADMAP — แผนพัฒนาและไอเดียต่อยอด

> แผนหลักของ v2 อยู่ที่ `docs/superpowers/specs/2026-10-18-tci-atlas-v2-design.md` (เฟส P0–P4) · สถานะสรุปอยู่ใน `CLAUDE.md` §3 · สิ่งที่ยังเปิดอยู่รวมไว้ที่ [งานที่ยังเปิดอยู่](#งานที่ยังเปิดอยู่) ท้ายเอกสาร

## Phase ที่เสร็จแล้ว (baseline)

| Phase | รายละเอียด | ไฟล์หลัก |
|---|---|---|
| **1 — Embedding (batch)** | 3 โหมด: local (sentence-transformers, ดีฟอลต์ BGE-M3), API (OpenAI-compatible: OpenAI/Gemini/OpenRouter/vLLM/Ollama) และ lite (TF-IDF+SVD สำหรับ CI/ทดสอบ); store แบบเขียนต่อท้ายใน `state_dir` (ข้อความเดิมไม่ฝังซ้ำข้ามไตรมาส); `atlas embed` (retry ไม่จำกัด, `--background`, `atlas status`, `atlas embed-stop`) ทำต่อหลัง Ctrl-C/ไฟดับได้ | `pipeline/atlas/embed.py`, `embed_runner.py`, `embed_store.py` |
| **2 — Topic Clustering** | 2 ชั้น: fine (หลายร้อยหัวข้อ, UMAP 10 มิติ + HDBSCAN หรือ Leiden, รวม cluster ที่ซ้ำด้วย `merge_similarity`) + กลุ่มใหญ่บนแผนที่; outlier เข้าหัวข้อใกล้สุดเฉพาะเมื่อ cosine ≥ `outlier_min_similarity`; c-TF-IDF ตัดคำด้วย pythainlp + คำสำคัญของผู้แต่ง | `pipeline/atlas/cluster.py` |
| **3 — Atlas web** | เว็บ v2 (ดูแถว P1b/P1c และ Redesign) | `web/` |
| **4 — Emerging Topic Analysis** | นิยาม TCI v3 (ช่วงเชื่อมั่น + ตัวกรองความกว้าง, 6 สถานะ), Kleinberg burst, novelty, score 0–100 | `pipeline/atlas/emerging.py`, `web/src/pages/EmergingPage.tsx` |
| **5 — Research Trend Forecasting** | Forecast v2: share × ยอดรวม, naive/drift/NB GLM/damped ETS, rolling-origin CV, skill gate, ช่วง 80/95 แบบ conformal, nowcast ของปีที่ยังไม่ครบ | `pipeline/atlas/forecast.py`, `web/src/charts/TrendChart.tsx` |
| **+ LLM** | ชื่อหัวข้อ TH/EN, คู่ที่อาจซ้ำ, คำอธิบายหัวข้อ, บทสรุปผู้บริหาร, บันทึกวิธีวิจัย — ผ่าน runner ตัวเดียว (cache, งบ, หยุด/ทำต่อ) + review/overrides ของบรรณาธิการ | `pipeline/atlas/{llm,llm_runner,label,review,narrative}.py`, `prompts/` |
| **+ ThaiJO Markdown ingest (P0)** | parse .md จาก ThaiJO (ซ่อม PUA/สระอำ, ปีจาก Published→DOI→issue, ผู้แต่ง/สังกัด/อ้างอิง), `atlas profile` | `pipeline/atlas/sources/thaijo_md.py`, `profile.py` |
| **+ Synthetic e2e (P0)** | คลังสังเคราะห์ 20K เรื่อง ฝังสัญญาณแต่ละสถานะแล้วตรวจว่ากู้คืนได้ + รับรอง 2 ไตรมาส | `pipeline/atlas/synth.py`, `pipeline/tests/test_e2e_synth.py` |
| **+ CI (P0)** | GitHub Actions: ruff + pytest + schema drift + e2e (`pytest -m slow`); web: type drift, fixtures, build, งบ bundle, Playwright smoke (a11y, จอมือถือ, ไฟล์ออฟไลน์); brief PDF | `.github/workflows/ci.yml` |
| **+ Live dashboard** | เว็บอ่าน `data/latest.json` ตอนเปิดหน้า (Http \| Embedded) — อัปเดตข้อมูลโดยไม่ build เว็บใหม่ | `web/src/data/{source,release}.ts` |
| **P1b/P1c Web v2** | 7 หน้า + brief, TH/EN, URL state, HTML ออฟไลน์, PDF, GitHub Pages สาธิต (โหมดมืดของรุ่นนี้ถูกตัดออกตอน Redesign) | `web/` |

## P1a — core analytics v2 (เสร็จ)

ID หัวข้อถาวร + lineage · กลุ่มตาม OpenAlex fields · Forecast v2 · emerging keywords · **แผนที่นิ่งข้ามรอบ** (UMAP เริ่มจากตำแหน่งรอบก่อน + Procrustes + anchor, `pipeline/atlas/layout.py`) + กาแล็กซีบทความ · LLM ทุกงานผ่าน API (runner + งบ + review/overrides) · **คำอธิบายหัวข้อและบทสรุปผู้บริหารอัตโนมัติที่ตรวจตัวเลข** (`narrative.py`, `prompts/topic_narrative.th.md`, `prompts/executive_brief.th.md`) · contract v2 + `atlas validate` + `atlas publish --site` · bake-off · ingest แบบเป็นชุด

## P1b/P1c — เว็บ v2 + ช่องทางเผยแพร่ (เสร็จ, 2026-10-19)

`/overview` `/atlas` `/emerging` `/topics/:id` `/compare` `/data` `/about` `/brief` · TH/EN · มือถือ · WCAG 2.2 AA (axe) · HTML เดี่ยวออฟไลน์ · PDF สรุปผู้บริหาร · GitHub Pages สาธิต (ข้อมูลสังเคราะห์, กดรันเอง) — แผน `docs/superpowers/plans/2026-10-19-p1bc-web-v2.md` · (ดีไซน์ hybrid Civic ของรุ่นนี้ถูกแทนด้วยโลก "ข่าวข้อมูล" แล้ว — ดู Redesign)

### งานค้างเล็ก ๆ หลัง P1 (จากรีวิว — ไม่บล็อกการใช้งาน)
- **ก่อนเปิด LLM เขียนเรื่องเล่าในรุ่นสาธารณะ:** ประโยคบอกทิศทางที่ไม่มีตัวเลข/คำบอกอัตรา ("หัวข้อนี้เติบโต") ยังไม่ถูกตรวจ; ประโยคใน brief ที่เอ่ยถึง ≥ 2 หัวข้อตรวจเฉพาะกรณีมีตัวเลขอัตราเดียว
- Forecast: ยอดคาดการณ์รายหัวข้อไม่ได้ปรับให้รวมเท่ายอดทั้งคลัง (share × N̂ แยกกัน); เกณฑ์ `min_month_share` ของ nowcast อ่อนเมื่อคลังเล็กมาก; เทสต์เชิงสถิติใช้ seed เดียว
- Bake-off: คอลัมน์ `ari_vs_first` ของอัลกอริทึมแรกเป็น 1.0 เสมอ / NPMI จาก seed แรก — อธิบายในรายงาน
- Label: `n_labels_fallback` นับรวมหัวข้อที่บรรณาธิการแก้ชื่อภายหลัง; รายการที่ fallback จะถูกถาม LLM ใหม่ทุกรอบ (ตั้งใจ)
- Runner: ค่าใช้จ่ายรอบ repair อาจเกินค่าประมาณหนึ่งครั้ง (งบเป็น soft cap); `atlas llm --background` ไม่มีหัว log
- Checkpoint fingerprint ตรวจเฉพาะ article_id/ลำดับ ไม่ตรวจการเปลี่ยน doc_text ที่ id เดิม; `hdbscan_backend: fast` ที่ไม่ได้ติดตั้ง extra ได้ error ดิบ
- เว็บ: หมายเหตุหน่วยของ CSV อยู่ข้างปุ่ม ไม่ได้อยู่ในไฟล์; ค่า `group_name` ใน CSV เปลี่ยนตามภาษา; ชื่อกลุ่ม fallback ภาษาไทยในหน้าอังกฤษยังไม่ครอบ `lang="th"`; เทสต์ line-height ยังไม่สแกน shorthand `font:`
- ~~`offline-template.html` บน Pages ไม่มี noindex~~ (ทำแล้วใน P4) · ~~Bundle เว็บเป็นก้อนเดียว~~ (P4 แยก `/atlas` `/brief` เป็น lazy) · ~~headline linker ไม่ใช้ word boundary~~ (ทำแล้ว: ลิงก์หัวข้อในพาดหัวตัดที่ขอบคำด้วย `Intl.Segmenter` ทั้งไทยและอังกฤษ)

## P2 — บรรณาธิการ (เสร็จ, 2026-10-19)

แผน: `docs/superpowers/plans/2026-10-19-p2-editors.md` · หน้าใหม่ 5 หน้า (`/journals`, `/journals/:id`, `/methods`, `/changes`, `/match`) + `pipeline/atlas/{journals,journal_metrics,journal_topics,registry,methods,matcher,diff}.py` + contract 2.1 · ฟีเจอร์: **มุมมองวารสาร** (ตัวชี้วัด D1–D5/D7: หัวข้อที่วารสารรับ, ขอบเขตที่เลื่อน, วารสารใกล้เคียง, ความครบของข้อมูล), วิธีวิจัย E11, **อะไรเปลี่ยนจากรอบก่อน** E5 (`diff.json` จาก snapshot ของรอบก่อนใน `state_dir`: หัวข้อใหม่ เปลี่ยนสถานะ รวม/แตก ตัวที่ขยับมากสุด), วางบทคัดย่อ R3/R4

**ต่อยอดจาก P2:**
- ทะเบียนวารสาร: ตอนนี้ทีมข้อมูลส่ง `journals.csv` มากับคลัง (corpus format 1.0) และ `atlas quarterly` ใช้ให้เอง — ยังเปิดอยู่: นำเข้าจากทะเบียนอย่างเป็นทางการของ TCI โดยตรง (คำถามเจ้าของ Q2: ยืนยันว่าไม่ต้อง scrape หน้าวารสาร ThaiJO)
- ตั้ง `journals.inhouse_flag_share` เมื่อ TCI ยืนยันเกณฑ์สัดส่วนผู้แต่งในสถาบันเจ้าของ (คำถามเจ้าของ Q1; ตอนนี้ null = ไม่มีเครื่องหมาย)
- ชุดตรวจความแม่นยำที่คนติดป้าย (สเปก "P2+"): วิธีวิจัย 200 บทความ, สังกัด/ผู้แต่งต่างประเทศ 500 บทความ — ยังไม่มี ตัวเลข coverage ที่เผยแพร่คู่กับทุกสัดส่วนคือสิ่งที่ใช้แทนตอนนี้
- ผู้แต่งต่างประเทศ: P3 ใช้ ROR ระบุตัวสถาบันแล้ว และ corpus format 1.0 มีช่อง `country` ต่อผู้แต่ง แต่คลัง Markdown ยังใช้ lexicon ประเทศที่เน้นความแม่น (ข้อความไทยนับเป็นต่างประเทศเมื่อมีคำว่า "ประเทศ" เท่านั้น)
- Matcher แบบความหมาย (embedding) เป็นตัวเลือกภายหลัง — ตอนนี้เทียบถ้อยคำด้วย trigram และหน้าเว็บบอกข้อจำกัดนี้
- ~~แยก `/atlas` และ `/brief` เป็น lazy route~~ (P4) · ~~แถบความใกล้เคียงใน `/match` ชิดขวาสุดบนจอกว้าง~~ (P4)

## P3 — ผู้บริหาร (เสร็จ, 2026-10-19)

แผน: `docs/superpowers/plans/2026-10-19-p3-executives.md` · หน้าใหม่ 6 หน้า (`/institutions`, `/institutions/:id`, `/regions`, `/sdg`, `/global`, `/gaps`) + ประโยคเชิงนโยบายในภาพรวม/brief + `pipeline/atlas/{places,institutions_ref,institutions,sdg,global_bench,gaps,export_exec}.py` + contract 2.2 · ฟีเจอร์: สถาบัน/เครือข่ายความร่วมมือ/แผนที่จังหวัด E6–E7 D6 R6, SDG และกรอบไทย E8, ไทยเทียบโลก E9, ช่องว่าง R5, ความเสี่ยงกระจุกตัว E10

**ต่อยอดจาก P3:**
- ให้ LLM ยืนยันการจับคู่หัวข้อ → เป้าหมาย (ปิดเป็นดีฟอลต์; ตอนนี้ใช้คำสำคัญหรือ embedding เท่านั้น)
- KPI เทียบรอบก่อน (YoY, 4 ไตรมาสย้อนหลัง) ในภาพรวมเชิงนโยบาย
- จังหวัดระดับวิทยาเขต (ตอนนี้แต่ละสถาบันมีจังหวัดเดียว: จังหวัดที่พบบ่อยที่สุดในแถวสังกัดของสถาบันนั้น — ช่อง `province` ของ corpus format 1.0 ช่วยบอก — หรือจังหวัดของสำนักงานใหญ่)
- ชุดตรวจความแม่นยำที่คนติดป้าย (สังกัด 500 บทความ, SDG 300 หัวข้อ) ตามสเปก "P2+"
- ทะเบียนสถาบันอย่างเป็นทางการของ TCI แทน `institutions_aliases.csv` ที่ผู้ดูแลคัดเอง
- ~~เครือข่ายความร่วมมือแบบ node-link~~ (web refresh: `ArcNetwork`) · ~~ชิป SDG ในหน้าหัวข้อ~~ (P4) · ~~`check:bundle` บังคับ lazy chunk~~ · ~~ตัวช่วยตั้งเกณฑ์ `sdg.min_similarity`~~ (P4: `atlas sdg-scores`)

## P4 — นักวิจัย (เสร็จ, 2026-10-23)

แผน: `docs/superpowers/plans/2026-10-19-p4-researchers.md` · หน้าใหม่ (lazy): `/search`, `/galaxy`, `/keywords`, `/references`, กราฟฝัง `/embed/topic/:id` และ `/embed/emerging` + `pipeline/atlas/{references,search_index,kwtrends,export_research,feeds}.py` + contract 2.3 · ฟีเจอร์: ค้นหาบทความทั้งคลัง R2 (ดัชนี static แบ่ง shard จากชื่อเรื่อง + คำสำคัญผู้แต่ง, export CSV/RIS/BibTeX), กาแล็กซีบทความ R8 (WebGL2), แนวโน้มคำสำคัญ + อภิธานศัพท์ไทย↔อังกฤษ R7, แนวปฏิบัติการอ้างอิงรายวารสาร D7 + "ถูกอ้างใน TCI" R12, RIS/BibTeX + "อ้างอิง Atlas นี้" + `CITATION.cff` R9, ฟีด Atom ต่อรอบและต่อหัวข้อ R11, ชิป SDG ในหน้าหัวข้อ, `atlas sdg-scores` · ไม่มีชื่อผู้แต่งและบทคัดย่อในไฟล์ใด

**ข้อตัดสินที่ต่างจากแผน:** RIS ใส่ชื่อเรื่องภาษาอังกฤษใน `TT` และชื่อวารสารใน `T2` (แผน Ruling 10 ให้ชื่อเรื่องภาษาที่สองอยู่ใน `T2`) เพื่อให้ Zotero/EndNote/Mendeley อ่านวารสารถูก · หน้า `/keywords` เทียบได้ครั้งละ 4 คำ (แผนเขียน ≤ 5) ให้ตรงกับสีเส้น 4 สี

**ต่อยอดจาก P4:**
- คำค้นกว้างใน `/search`: โหลด doc shard ≤ 6 ไฟล์ต่อคำค้น ผลที่กระจายมากกว่านั้นแสดงจากบางส่วน (หน้าบอกผู้อ่าน) — ทางเลือก: เรียง ordinal ตามปี/หัวข้อแทน article_id หรือทำดัชนีชื่อเรื่องแยก
- การเรียงตาราง (คอลัมน์/ทิศ) ยังไม่อยู่ใน URL — ลิงก์ที่แชร์ได้ตัวกรองแต่ไม่ได้ลำดับการเรียง
- HTML ออฟไลน์ไม่มีกราฟฝัง ค้นหา และกาแล็กซี (ตั้งใจ: ขนาดไฟล์) — ต้องใช้เว็บออนไลน์

## Web refresh — ภาษาง่าย + infographic (เสร็จ, 2026-10-23)

แผน: `docs/superpowers/plans/2026-10-23-web-refresh.md` · **นิยามสถานะ, `definition_version` 3 และ data contract ไม่เปลี่ยน**

- **พื้นฐาน:** type scale (`--fs-*`), จังหวะ `--sp-*`, ความยาวบรรทัด `--measure-*`; มือถือมีปุ่ม "เมนู" ปุ่มเดียว; แถบแจ้งรวมเป็นบรรทัดเดียว; ส่วนท้าย "ทำอะไรต่อ"
- **ชิ้นส่วนกลาง:** `StatTile` + sparkline, แถบคำบรรยาย `Figure` (แผนภูมิ/ตาราง · วิธีอ่าน · CSV), `DataTable` (`primary`, `limit`), `CsvButton`, `SourceLine`, `Term`/`InfoPop`, `HowNote`, `StatusLegend`
- **ภาษา:** ข้อความ 2 ชั้นทุกหน้า, ใช้ปีแทน "ช่วงฐาน/ช่วงล่าสุด", ชื่อสถานะไทย, ชื่อเมนู "อ่านตัวเลขอย่างไร" (`/about`), "แผนที่บทความทุกเรื่อง" (`/galaxy`), "โอกาสที่ยังไม่มีใครทำ" (`/gaps`)
- **กราฟชุด infographic:** waffle สถานะ, dot plot ใน brief, `ArcNetwork`, `ColumnChart`, `MixBar`/`SplitBar`, `OpportunityQuadrant`, `StatusFlow` + `LineageKey`, `GoalTiles`, `BridgePairs`, `JournalScatter`, `PeriodMix`, `ChecklistBars`, `SmallMultiples` — คณิตการจัดวางแยกไฟล์ `.ts` ที่มี test
- **pipeline:** ประโยคแม่แบบทุกชนิดใช้ภาษาง่ายและผ่าน `narrative.jargon_in` (ตรวจใน `test_release.py`); prompt `topic_narrative` / `executive_brief` / `topic_methods` มีกฎน้ำเสียง; ข้อความจาก LLM ผ่านทั้ง `grounding_error` และ `jargon_in` (ไม่ผ่าน = เขียนใหม่ 1 ครั้ง แล้วใช้ประโยคแม่แบบ)
- ✅ **สัดส่วนหัวข้อรายปีของวารสาร** (contract 2.4 `JournalDetail.topic_years` → small multiples บน `/journals/:id`)
- ✅ **เมนูแบบคำถาม:** ภาพรวม · สรุปผู้บริหาร · **อะไรกำลังมา** (5 เรื่องน่ารู้รอบนี้, สถานะหัวข้อ, แนวโน้มคำสำคัญ, อะไรเปลี่ยน, โอกาสที่ยังไม่มีใครทำ, หัวข้อน่าทำ) · **ใครทำเรื่องอะไร** (สถาบัน, วารสาร, วิธีวิจัย, การอ้างอิง) · **ไทยอยู่ตรงไหน** (งานวิจัยในจังหวัดของฉัน, แผนที่จังหวัด, ไทยเทียบโลก, SDG และแผนชาติ) · **หางานวิจัย** (ค้นหาบทความ, แผนที่หัวข้อ, แผนที่บทความทุกเรื่อง, เปรียบเทียบ, วางบทคัดย่อ) · ข้อมูลเปิด · อ่านตัวเลขอย่างไร — URL ไม่เปลี่ยน

## Redesign + พร้อมข้อมูลจริง (เสร็จ, 2026-10-23)

**เว็บ**
- **โลกดีไซน์ "ข่าวข้อมูล" (data explainer)** แทน Civic modern (เจ้าของเลือก): หน้าแรกเป็นเรื่องเล่าข้อมูล (คำถามเป็น h1 · คำตอบ 1 ประโยค · ตัวเลข 1 ตัว · กราฟเส้นที่เน้นได้), แถบบนสีขาว + โลโก้ TCI, ส่วนท้ายมีโลโก้ TCI · NECTEC · สวทช., palette ใหม่ (น้ำเงิน/ส้ม TCI), **ตัดโหมดมืด** — กฎอยู่ใน `DESIGN.md`
- **หน้าใหม่:** `/story` (5 เรื่องน่ารู้รอบนี้ พร้อมภาพสี่เหลี่ยมสำหรับแชร์ที่วาดในเบราว์เซอร์), `/ideas` (หัวข้อน่าทำรายสาขา + คู่หัวข้อที่น่าเชื่อม), `/province` และ `/province/:code` (งานวิจัยในจังหวัดของฉัน — ใช้ contract 2.5 หัวข้อเด่นรายจังหวัด) · brief อยู่ในเลย์เอาต์ของเว็บ (พิมพ์แล้วซ่อนหัว/เมนู)
- **SEO และการแชร์:** canonical, Open Graph/Twitter card, schema.org WebSite + Organization + Dataset, `robots.txt`, `sitemap.xml` จาก `ATLAS_SITE_URL` (`web/vite.config.ts`); เว็บสาธิตและ `offline-template.html` เป็น noindex
- **พร้อมข้อมูลขนาดจริง** (~1,500 หัวข้อ, ~2,000 วารสาร, ~10,000 สถาบัน): ตารางและรายการมีเพดานและบอกจำนวนที่ตรง/ที่แสดง (`DataTable` `limit`, `ListMore`, `useCapped`), waffle/flow ปรับสเกล, LRU cache ของ doc shard, มือถือแสดงตาราง 10 แถว
- **ไม่มีหน้าขาว:** error boundary ครอบทั้งแอป พื้นที่หน้า และกราฟฝัง (chunk หายหลัง deploy = reload ให้ 1 ครั้ง); ลิงก์หัวข้อในพาดหัวตัดที่ขอบคำไทย; entry chunk ≈ 167 KB gzip (งบ 180 KB)

**pipeline และการปฏิบัติการ**
- **Corpus format 1.0** (JSON Lines, `pipeline/atlas/schema/corpus.py` + `sources/corpus_jsonl.py`, คู่มือ `docs/corpus/README.md`) + `atlas corpus schema` / `atlas corpus convert` (แปลงคลัง .md โดยคง id เดิม)
- **Companion files** (`journals.csv`, `institutions_aliases.csv`, `province_population.csv`, `ror.zip`) วางข้างคลังแล้วถูกใช้ให้เอง; `atlas profile` ตรวจด้วยตัวอ่านเดียวกับ pipeline และเขียน CSV รายการสังกัดที่ยังไม่มีในตาราง alias
- **รอบรายไตรมาสด้วยคำสั่งเดียว** `atlas quarterly` (`scripts/quarterly_run.sh` / `.cmd`): config → บันทึกคลัง → profile → embed → LLM (ต้องยืนยันก่อนจ่าย) → run → validate → build เว็บ → publish → แพ็กพร้อมอัปโหลด (`runs/<release>/`, `deploy/<release>/`) — รันซ้ำ = ทำต่อ
- **ด่าน PDPA** (`pipeline/atlas/privacy.py`): `atlas validate`/`publish` หาอีเมล ORCID และชื่อผู้แต่งที่ปนในชื่อหน่วยงานในทุกไฟล์ที่จะเผยแพร่ (ยกเว้นได้ด้วย `validation.privacy_allow`)
- **เว็บไม่โตทุกไตรมาส:** รอบเก่าบนเว็บถูกลดขนาด (`publish.keep_full_releases`) แต่ยังเก็บไฟล์ที่ฟีดและการเทียบรอบใช้ ปลอดภัยต่อ rollback; รอบก่อนที่หายจากเว็บถูกกู้จาก `output/data/`; HTML ออฟไลน์มีงบ `export.offline_max_mb`
- **ขึ้นข้อมูลจริงบน GitHub Pages:** `scripts/package_release.sh` สร้าง GitHub Release ที่แนบ `atlas-site-data-<release>.zip` แล้ว workflow Pages (กดรันเอง) วางข้อมูลนั้น และปฏิเสธข้อมูลตัวอย่าง
- อ่านเฉพาะคอลัมน์ที่ต้องใช้จากตารางใหญ่ (รองรับคลัง 500K บทความ)

## งานที่ยังเปิดอยู่

### ต้องปรับกับข้อมูลจริงรอบแรก (ค่าตั้งต้นทดสอบกับข้อมูลสังเคราะห์)

ไม่ใช่การเปลี่ยนนิยามสถานะ — แต่ถ้าการปรับกระทบตัวเลขที่ผู้บริหารใช้ ให้ถามเจ้าของก่อน

- **`clustering.merge_similarity`** (ตอนนี้ 0.8): ดูคู่ที่อาจซ้ำใน `05_merge_suggestions` และรายงาน review — ถ้าซ้ำเยอะ ลดค่าในรอบ refit ถัดไป (ไม่รวมหัวข้ออัตโนมัติกลางปี)
- **`search.min_df`** (ตอนนี้ 1 = ทุกคำ): ถ้า `atlas validate` เตือนว่า `search/vocab.json` ใหญ่ (เบราว์เซอร์โหลดทั้งไฟล์ก่อนค้นครั้งแรก) ให้ตั้ง 2
- **ความแม่นของคำสำคัญ SDG** (`sdg.method: lexical`, คำใน `pipeline/atlas/data/frameworks.yaml`, `min_article_share`): สุ่มตรวจหัวข้อที่จับคู่ได้ ตัดคำที่กว้างเกิน; จะเปลี่ยนเป็น `embedding` ต้องตั้ง `sdg.min_similarity` ด้วย `atlas sdg-scores` ก่อน
- **ชื่อสถาบันที่เขียนเป็นตัวย่ออย่างเดียว** (เช่น "KKU"): ROR ไม่จับคู่ตัวย่อโดยตั้งใจ (กำกวม) จึงกลายเป็นสถาบันแยกจากชื่อเต็ม — ต้องเติมในตาราง alias (`atlas profile` ทำรายการที่พบบ่อยให้)
- **ด่าน PDPA:** ดูว่ามีชื่อหน่วยงานที่บังเอิญตรงกับชื่อผู้แต่งไหม (คนตรวจแล้วจึงใส่ `validation.privacy_allow`)
- **รายการอ้างอิง:** ตรวจ coverage กับคลังจริง — ถ้าต่ำกว่า `references.min_coverage` หน้า `/references` แสดงเหตุผลแทนข้อมูล (ปรับตัวอ่านใน ingest ก่อน ห้ามลดเกณฑ์เพื่อให้หน้าแสดงผล)
- **ภาพ:** ขนาด/ความทึบของจุดใน `/galaxy` (`pointSize`/`pointAlpha` ใน `web/src/lib/galaxyGl.ts`), หัวข้อแนะนำให้ลอง, ชั้นสี quantile และลายเส้นทแยงของ `/regions` — แก้โค้ดเว็บแล้ว build ใหม่ครั้งเดียว
- **LLM:** ดูอัตราที่ข้อความตกไปใช้ประโยคแม่แบบ (ไม่ผ่าน grounding/jargon) ในรอบ `atlas llm` จริงรอบแรก — รัน `--dry-run` ก่อนเสมอ

### ฟีเจอร์และงานโครงสร้าง

1. **URL แบบ path เพื่อให้ search engine เก็บทุกหน้า** — เว็บใช้ HashRouter และ `sitemap.xml` มีแค่หน้าแรก
   - วิธี: เวอร์ชันออนไลน์ใช้ BrowserRouter โดยตั้ง `basename` เป็นที่อยู่ย่อยของ Pages, เพิ่ม `404.html` ที่ส่งต่อไปหน้าเดิม และให้ `atlas publish` สร้าง sitemap รายหน้า (หัวข้อ จังหวัด วารสาร สถาบัน) จาก `data/latest.json`
   - ต้องมี title/description แยกต่อหน้า; HTML ออฟไลน์และกราฟฝังยังใช้ hash ได้ (ลิงก์ `#/…` เดิมต้องเปลี่ยนทางไปหน้าใหม่ได้)
2. **ไฟล์ LICENSE ของโค้ด** — `CITATION.cff` ระบุ CC-BY-4.0 เฉพาะข้อมูลที่เผยแพร่ เจ้าของต้องเลือกสัญญาอนุญาตของโค้ด
3. **ดาวน์โหลดรูปแผนที่หัวข้อเป็น PNG** — ตอนนี้มี CSV ทุกกราฟ/ตาราง และภาพแชร์ของ `/story` แต่แผนที่ `/atlas` ยังไม่มีปุ่มบันทึกรูป
4. **สำรวจบนกราฟด้วยแป้นพิมพ์** — ช่อง waffle เส้นโค้งเครือข่าย และแท่ง column chart โฟกัสไม่ได้ (ตั้งใจ: แท็บตารางคือทางของแป้นพิมพ์และ screen reader) ถ้าต้องการต้องออกแบบ roving focus
5. **ตั้งชื่อหัวข้อใหม่ด้วยภาษาง่าย** — `prompts/topic_label.th.md` ไม่ได้แก้โดยตั้งใจ (แก้ template = `prompt_version` เปลี่ยน = ตั้งชื่อทุกหัวข้อใหม่และเสียค่า LLM ทั้งชุด) ทำพร้อมรอบ refit รายปี
6. **Co-citation edges** — รายการอ้างอิงถูก parse แล้ว (P4 ใช้ทำ D7/R12) แต่ยังไม่ได้ใช้เป็น edge ระหว่างหัวข้อ ซึ่งอาจมีคุณภาพดีกว่าความคล้ายเชิงความหมาย
7. **API backend + auth** — ถ้าต้องการ saved views, การแจ้งเตือน ("แจ้งเมื่อหัวข้อ X เข้าเกณฑ์กำลังเกิดใหม่"), ค้นหาบทคัดย่อเต็ม หรือข้อมูลที่ห้ามเปิดสาธารณะ (ตอนนี้ฟีด Atom ต่อหัวข้อใช้แทนการแจ้งเตือนได้บางส่วน)
8. **Clustering แบบ incremental เต็มรูป** — ตอนนี้ไตรมาสปกติ assign บทความใหม่เข้าหัวข้อเดิม (`topics.mode: auto`) และ embedding ไม่ฝังซ้ำ แต่ refit ยังทำทั้งคลัง; ถ้าคลังโตเป็นหลายล้านเรื่องค่อยทำ online clustering

## แนวคิดเชิงนโยบายที่ข้อมูลพร้อมจะตอบ

- **ช่องว่างงานวิจัย** — มีแล้วใน `/gaps` และ `/ideas` (หัวข้อที่โลกโตแต่ไทยยังเล็ก, หัวข้อที่กำลังเกิดแต่มีสถาบันทำน้อย, คู่หัวข้อที่น่าเชื่อม)
- **จับคู่งานวิจัยกับวารสาร** — มีแล้วใน `/journals/:id` (หัวข้อที่วารสารรับ, สัดส่วนรายปี, โอกาสเปิดฉบับพิเศษ)
- **ภาพรวมระดับประเทศรายปี** — share ของแต่ละกลุ่มเทียบปี + KPI ใน `/overview` และ `/brief`; ยังขาด KPI เทียบรอบก่อนแบบ 4 ไตรมาสย้อนหลัง (ดูต่อยอดจาก P3)
- **Early warning** — หัวข้อที่ลดลงหลายไตรมาสติดในสาขาสำคัญของประเทศ: ข้อมูลรายรอบมีอยู่ใน `diff.json` ทุกรอบ แต่ยังไม่มีมุมมองข้ามหลายไตรมาส

## สิ่งที่ตั้งใจไม่ทำ (และเหตุผล)

| ไม่ทำ | เพราะ |
|---|---|
| Real-time updates | ข้อมูล TCI เปลี่ยนช้า — รายไตรมาสเพียงพอ, static site เสถียรกว่า |
| Login/user accounts (ตอนนี้) | เป็นเครื่องมือสาธารณะ — เพิ่มภายหลังได้ถ้าต้องการ saved views |
| ทำนายยาว > 2 ปี | ข้อมูลมี backfill lag — ทำนายยาวจะสร้างความมั่นใจเทียม |
| Score เทียบข้ามรอบรัน | score เป็น percentile ภายในรอบโดยออกแบบ — ใช้มิติดิบถ้าจะเทียบข้ามรอบ |
| ข้อมูลระดับบุคคล (ชื่อผู้แต่ง, เครือข่ายผู้แต่งร่วม, อันดับนักวิจัย) | PDPA — เผยแพร่เฉพาะตัวเลขรวมและระดับสถาบัน; เครือข่ายความร่วมมือทำในระดับสถาบันแทน |
| เผยแพร่บทคัดย่อหรือข้อความรายการอ้างอิง | สิทธิ์ในเนื้อหา + PDPA — ค้นหาใช้ชื่อเรื่องและคำสำคัญ, "วางบทคัดย่อ" เก็บแค่น้ำหนัก trigram |
| เรียก API/LLM หรือโหลดของจากเซิร์ฟเวอร์ภายนอกตอนเปิดเว็บ | ความเป็นส่วนตัวของผู้อ่าน, ไม่มีค่าใช้จ่ายต่อการเข้าชม, ทำงานออฟไลน์ได้ |
| รวมหัวข้อซ้ำอัตโนมัติ | LLM เสนอคู่ที่อาจซ้ำเท่านั้น — คนตัดสินผ่าน overrides หรือรอ refit (ID และ lineage ต้องนิ่ง) |
| โหมดมืด | เจ้าของเลือกโลกดีไซน์ "ข่าวข้อมูล" ธีมสว่างธีมเดียว (2026-10-23) |
| ลดเกณฑ์ `references.min_coverage` / `min_internal_matches` เพื่อให้หน้าแสดงผล | coverage ต่ำทำให้ตัวเลขรายวารสารหลอกตา — แก้ที่ตัวอ่านหรือถามเจ้าของข้อมูล |
