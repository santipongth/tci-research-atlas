# ROADMAP — แผนพัฒนาและไอเดียต่อยอด

> แผนหลักปัจจุบันอยู่ที่ `docs/superpowers/specs/2026-10-18-tci-atlas-v2-design.md` (เฟส P0–P4)

## Phase ที่เสร็จแล้ว (baseline ปัจจุบัน)

| Phase | รายละเอียด | ไฟล์หลัก |
|---|---|---|
| **1 — Embedding (batch)** | รองรับ 3 โหมด: API (OpenAI-compatible: OpenAI/Gemini/OpenRouter/vLLM/Ollama), local (sentence-transformers, default BGE-M3) และ lite (TF-IDF+SVD บน CPU สำหรับ CI/ทดสอบ); journal ทุก batch + store ทุก `checkpoint_every`; resume ได้หลัง Ctrl-C/ปิดหน้าต่าง/ไฟดับ; `atlas embed` (retry ไม่จำกัด, `--background`, `atlas status`) | `pipeline/atlas/embed.py` + `embed_runner.py` |
| **2 — Topic Clustering** | 2 ชั้น: fine (~หลายร้อย topic) + coarse (กลุ่มใหญ่บนแผนที่); fine = UMAP 10 มิติ + HDBSCAN (+ รวม cluster ที่ซ้ำ); outlier เข้าหัวข้อที่ใกล้ที่สุดเฉพาะเมื่อ cosine ≥ `outlier_min_similarity` (ไม่งั้น "ยังไม่จัดหมวด"); coarse = agglomerative clustering ของ centroid หัวข้อ (ไม่ใช่ HDBSCAN); c-TF-IDF ตัดคำด้วย pythainlp + author keywords (เหมาะกับไทย) | `pipeline/atlas/cluster.py` |
| **3 — Atlas web** | React bubble map (pan/zoom), drill-down, 2 ภาษา (ไทย/EN), insights ที่คำนวณจากข้อมูล, live loader + fallback | `web/` |
| **4 — Emerging Topic Analysis** | นิยาม TCI v3 (ดู EMERGING_SPEC.md: ช่วงเชื่อมั่น + ตัวกรองความกว้าง, 6 สถานะ), Kleinberg burst, novelty (สัดส่วนบทความในช่วง R + อายุหัวข้อ — lineage เทียบรอบก่อนผ่าน `state/releases/` มาใน P1), score 0–100, section "หัวข้อเกิดใหม่" บนเว็บ | `pipeline/atlas/emerging.py`, `web/src/pages/EmergingPage.tsx` |
| **5 — Research Trend Forecasting** | (P0) naive/OLS/Poisson ต่อ topic, เลือกโมเดลด้วย backtest, แสดงเฉพาะที่ผ่าน skill gate · (P1 Forecast v2) share × ยอดรวม, ช่วง 80/95 แบบ conformal, nowcast ของปีที่ยังไม่ครบ — ดู P1a ด้านล่าง | `pipeline/atlas/forecast.py`, `web/src/charts/TrendChart.tsx` |
| **+ LLM Labeling** | ตั้งชื่อ topic ไทย+อังกฤษ, cache ด้วย key = hash ของ model + prompt (รันใหม่ไม่เสียเงินซ้ำ); P1 ย้ายไป LLM runner (`llm_runner.py`) | `pipeline/atlas/label.py`, `prompts/` |
| **+ ThaiJO Markdown ingest (P0)** | parse ไฟล์ .md จาก ThaiJO (ซ่อม PUA/สระอำ, ปีจาก Published→DOI→issue, ผู้แต่ง/สังกัด/อ้างอิง), `atlas profile` | `pipeline/atlas/sources/thaijo_md.py`, `pipeline/atlas/profile.py` |
| **+ Synthetic e2e (P0)** | คลังสังเคราะห์ 20K เรื่อง ฝังหัวข้อ EMERGING/WATCH/HOT/DECLINING แล้วตรวจว่ากู้คืนได้ | `pipeline/atlas/synth.py`, `pipeline/tests/test_e2e_synth.py` |
| **+ CI (P0)** | GitHub Actions: ruff + pytest + JSON Schema drift, e2e (`pytest -m slow`), web (type drift + build) | `.github/workflows/ci.yml` |
| **+ Live dashboard** | เว็บอ่าน `data/latest.json` runtime ผ่าน DataSource (Http \| Embedded) — อัปเดตข้อมูลโดยไม่ build เว็บใหม่ | `web/src/data/{source,release}.ts` |
| **P1b/P1c Web v2** | 7 หน้า + brief, TH/EN, dark mode, URL state, offline HTML, PDF, GitHub Pages demo | `web/` |

## P1a — core analytics v2 (เสร็จ)

ID หัวข้อถาวร + lineage · กลุ่มตาม OpenAlex fields · Forecast v2 (share × ยอดรวม, conformal 80/95, nowcast ของปีที่ยังไม่ครบ) · emerging keywords · แผนที่นิ่งข้ามรอบ + galaxy · LLM ทุกงานผ่าน API (runner + งบ + review/overrides) · คำอธิบายและบทสรุปที่ตรวจตัวเลข · contract v2 + `atlas validate` + `atlas publish --site` · bake-off · ingest แบบเป็นชุด

## P1b/P1c — เว็บ v2 + ช่องทางเผยแพร่ (เสร็จ, 2026-10-19)

ดีไซน์ hybrid (Civic + พาดหัว Editorial + แผนที่ Cartographic) · `/overview` `/atlas` `/emerging` `/topics/:id` `/compare` `/data` `/about` `/brief` · TH/EN · โหมดมืด · มือถือ · WCAG 2.2 AA (axe) · HTML เดี่ยว offline · PDF สรุปผู้บริหาร · GitHub Pages สาธิต (ข้อมูลสังเคราะห์, กดรันเอง) — แผน `docs/superpowers/plans/2026-10-19-p1bc-web-v2.md`

### งานค้างเล็ก ๆ หลัง P1 (จากรีวิว — ไม่บล็อกการใช้งาน)
- **ก่อนเปิด LLM เขียนเรื่องเล่าในรุ่นสาธารณะ:** ประโยคทิศทางที่ไม่มีตัวเลข/คำบอกอัตรา ("หัวข้อนี้เติบโต") ยังไม่ถูกตรวจ; ประโยคใน brief ที่เอ่ยถึง ≥ 2 หัวข้อตรวจเฉพาะกรณีมีตัวเลขอัตราเดียว
- Forecast: ยอดคาดการณ์รายหัวข้อไม่ได้ปรับให้รวมเท่ายอดทั้งคลัง (share × N̂ แยกกัน); เกณฑ์ `min_month_share` ของ nowcast อ่อนเมื่อคลังเล็กมาก; เทสต์เชิงสถิติใช้ seed เดียว
- Bake-off: คอลัมน์ `ari_vs_first` ของอัลกอริทึมแรกเป็น 1.0 เสมอ / NPMI จาก seed แรก — อธิบายในรายงาน
- Label: `n_labels_fallback` นับรวมหัวข้อที่บรรณาธิการแก้ชื่อภายหลัง; รายการที่ fallback จะถูกถาม LLM ใหม่ทุกรอบ (ตั้งใจ)
- Runner: ค่าใช้จ่ายรอบ repair อาจเกินค่าประมาณหนึ่งครั้ง (งบเป็น soft cap); `atlas llm --background` ไม่มีหัว log
- Checkpoint fingerprint ตรวจเฉพาะ article_id/ลำดับ ไม่ตรวจการเปลี่ยน doc_text ที่ id เดิม; `hdbscan_backend: fast` ที่ไม่ได้ติดตั้ง extra ได้ error ดิบ
- เว็บ: ~~`offline-template.html` บน Pages ไม่มี noindex~~ (ทำแล้วใน P4); หมายเหตุหน่วยของ CSV อยู่ข้างปุ่ม ไม่ได้อยู่ในไฟล์; ค่า `group_name` ใน CSV เปลี่ยนตามภาษา; ชื่อกลุ่ม fallback ภาษาไทยในหน้าอังกฤษยังไม่ครอบ `lang="th"`; headline linker ไม่ใช้ word boundary กับชื่ออังกฤษ (ควรให้ brief ส่ง topic id ใน P2); เทสต์ line-height ยังไม่สแกน shorthand `font:`
- ~~Bundle เว็บเป็นก้อนเดียว ~163 KB gzip — แยก lazy route `/atlas` `/brief`~~ (ทำแล้วใน P4)

## P2 — บรรณาธิการ (เสร็จ, 2026-10-19)

แผน: `docs/superpowers/plans/2026-10-19-p2-editors.md` · หน้าใหม่ 5 หน้า (`/journals`, `/journals/:id`, `/methods`, `/changes`, `/match`) + `pipeline/atlas/{journals,journal_metrics,journal_topics,registry,methods,matcher,diff}.py` + contract 2.1 (ไฟล์เสริม optional) · ฟีเจอร์: ตัวชี้วัดวารสาร D1–D5/D7, วิธีวิจัย E11, อะไรเปลี่ยนจากรอบก่อน E5, วางบทคัดย่อ R3/R4

**ต่อยอดจาก P2:**
- นำเข้าทะเบียนวารสารอย่างเป็นทางการของ TCI แทน `registry/journals.csv` (คำถามเจ้าของ Q2: ยืนยันว่าไม่ต้อง scrape หน้าวารสาร ThaiJO)
- ตั้ง `journals.inhouse_flag_share` เมื่อ TCI ยืนยันเกณฑ์สัดส่วนผู้แต่งในสถาบันเจ้าของ (คำถามเจ้าของ Q1; ตอนนี้ null = ไม่มีเครื่องหมาย)
- ชุดตรวจความแม่นยำที่คนติดป้าย (สเปก "P2+"): วิธีวิจัย 200 บทความ, สังกัด/ผู้แต่งต่างประเทศ 500 บทความ — ยังไม่มีชุดนี้ ตัวเลข coverage ที่เผยแพร่คู่กับทุกสัดส่วนคือสิ่งที่ใช้แทนตอนนี้
- ตรวจผู้แต่งต่างประเทศด้วย ROR ใน P3 (ตอนนี้ lexicon ประเทศเน้นความแม่น: ข้อความไทยระบุประเทศต่างประเทศเมื่อมีคำว่า "ประเทศ" เท่านั้น)
- Matcher แบบความหมาย (embedding) เป็นตัวเลือกภายหลัง — ตอนนี้เทียบถ้อยคำด้วย trigram และหน้าเว็บบอกข้อจำกัดนี้
- ~~แยก `/atlas` และ `/brief` เป็น lazy route เพื่อลด entry chunk~~ (ทำแล้วใน P4 — entry ≈ 171 KB gzip จากงบ 180 KB หลังเพิ่มหน้า P4)
- ~~แถบความใกล้เคียงใน `/match` ชิดขวาสุดบนจอกว้าง~~ (P4 จำกัดความกว้างรายการแล้ว)

## P3 — ผู้บริหาร (เสร็จ, 2026-10-19)

แผน: `docs/superpowers/plans/2026-10-19-p3-executives.md` · หน้าใหม่ 6 หน้า (`/institutions`, `/institutions/:id`, `/regions`, `/sdg`, `/global`, `/gaps`) + เมนูแบ่งกลุ่ม + ประโยคเชิงนโยบายในภาพรวม/brief + `pipeline/atlas/{places,institutions_ref,institutions,sdg,global_bench,gaps,export_exec}.py` + contract 2.2 · ฟีเจอร์: สถาบัน/เครือข่าย/แผนที่จังหวัด E6–E7 D6 R6, SDG และกรอบไทย E8, ไทยเทียบโลก E9, ช่องว่าง R5, ความเสี่ยงกระจุกตัว E10

**ต่อยอดจาก P3:**
- ให้ LLM ยืนยันการจับคู่หัวข้อ → เป้าหมาย (งานแบบปิดเป็นดีฟอลต์; ตอนนี้ใช้ embedding หรือคำสำคัญเท่านั้น)
- วาดเครือข่ายความร่วมมือแบบ node-link (ตอนนี้เป็นตารางคู่สถาบัน ประเทศคู่ และคู่ต่อสถาบัน)
- KPI เทียบรอบก่อน (YoY, 4 ไตรมาสย้อนหลัง) ในภาพรวมเชิงนโยบาย
- ~~ชิป SDG ในหน้าหัวข้อ~~ (ทำแล้วใน P4)
- จังหวัดระดับวิทยาเขต (ตอนนี้ใช้จังหวัดของสำนักงานใหญ่ของสถาบัน)
- ชุดตรวจความแม่นยำที่คนติดป้าย (สังกัด 500 บทความ, SDG 300 หัวข้อ) ตามสเปก "P2+"
- ทะเบียนวารสารและสถาบันอย่างเป็นทางการของ TCI แทนไฟล์ที่ผู้ดูแลคัดเอง
- ~~`check:bundle` บังคับ lazy chunk ของหน้าใหม่~~ (ตอนนี้ตรวจทุก `lazy(() => import('./pages/…' | './embed/…'))` ใน `App.tsx`)
- ~~ตัวช่วยตั้งเกณฑ์ `sdg.min_similarity`~~ (P4: `atlas sdg-scores`)

## P4 — นักวิจัย (เสร็จ, 2026-10-23)

แผน: `docs/superpowers/plans/2026-10-19-p4-researchers.md` · หน้าใหม่ (lazy): `/search`, `/galaxy`, `/keywords`, `/references`, กราฟฝัง `/embed/topic/:id` และ `/embed/emerging` + `pipeline/atlas/{references,search_index,kwtrends,export_research,feeds}.py` + contract 2.3 · ฟีเจอร์: ค้นหาบทความทั้งคลัง R2 (ดัชนีสถิตแบ่ง shard จากชื่อเรื่อง + คำสำคัญผู้แต่ง, export CSV/RIS/BibTeX), กาแล็กซีบทความ R8 (WebGL2, คลิกจุดเพื่อดูบทความ), แนวโน้มคำสำคัญ + อภิธานศัพท์ไทย↔อังกฤษ R7, แนวปฏิบัติการอ้างอิงรายวารสาร D7 + "ถูกอ้างใน TCI" R12 (เผยแพร่เมื่อ coverage ถึงเกณฑ์), RIS/BibTeX + "อ้างอิง Atlas นี้" ใน `/about` + `CITATION.cff` R9, ฟีด Atom ต่อรอบและต่อหัวข้อ R11 (`publish.site_url`), ชิป SDG ในหน้าหัวข้อ, `atlas sdg-scores`, `/atlas` และ `/brief` เป็น lazy · ไม่มีชื่อผู้แต่งและบทคัดย่อในไฟล์ใด (RIS/BibTeX ไม่มีผู้แต่ง — DOI ใช้หาการอ้างอิงเต็ม)

**ข้อตัดสินที่ต่างจากแผน:** RIS ใส่ชื่อเรื่องภาษาอังกฤษใน `TT` และชื่อวารสารใน `T2` (แผน Ruling 10 ให้ชื่อเรื่องภาษาที่สองอยู่ใน `T2`) เพื่อให้ Zotero/EndNote/Mendeley อ่านวารสารถูก · หน้า `/keywords` เทียบได้ครั้งละ 4 คำ (แผนเขียน ≤ 5) ให้ตรงกับสีเส้น 4 สี

**ต่อยอดจาก P4:**
- ปรับขนาด/ความทึบของจุดกาแล็กซี (`pointSize`/`pointAlpha` ใน `web/src/lib/galaxyGl.ts`) กับข้อมูลจริงรอบแรก — ค่าตั้งต้นทดสอบกับข้อมูลสังเคราะห์ ~600 จุดเท่านั้น (`docs/OPERATIONS.md` §17)
- คำค้นกว้างใน `/search`: โหลด doc shard ≤ 6 ไฟล์ต่อคำค้น ผลที่กระจายมากกว่านั้นแสดงจากบางส่วน (หน้าบอกผู้อ่าน) — ทางเลือก: จัดเรียง ordinal ตามปี/หัวข้อแทน article_id หรือดัชนีชื่อเรื่องแยก เพื่อให้ผลอันดับต้นอยู่ใน shard น้อยลง
- ยังไม่มีไฟล์ LICENSE ของโค้ด — `CITATION.cff` ระบุ CC-BY-4.0 เฉพาะข้อมูลที่เผยแพร่ เจ้าของต้องเลือกสัญญาอนุญาตของโค้ด
- การเรียงตาราง (คอลัมน์/ทิศ) ยังไม่อยู่ใน URL — ลิงก์ที่แชร์ได้ตัวกรองแต่ไม่ได้ลำดับการเรียง
- HTML ออฟไลน์ไม่มีกราฟฝัง (`/embed/*`) ค้นหา และกาแล็กซี (ตั้งใจ: ขนาดไฟล์) — ต้องใช้เว็บออนไลน์
- ตรวจ coverage ของรายการอ้างอิงกับคลังจริง — ถ้าต่ำกว่า `references.min_coverage` หน้า `/references` จะแสดงเหตุผลแทนข้อมูล (ปรับ parser ใน ingest ก่อนคิดลดเกณฑ์)
- **ถัดไป (วางแผนแล้ว):** ปรับภาษาให้เข้าใจง่ายและปรับภาพทั้งเว็บ (plain-language + visual refresh) ทุกหน้าทั้ง 3 กลุ่มผู้ใช้

## งานแนะนำลำดับถัดไป (เรียงตาม value/effort)

### 🟢 ทำได้เร็ว คุ้ม (1–3 วัน)

1. **Search box บนแผนที่** — ค้นหาหัวข้อ/คำสำคัญ (ไทย+อังกฤษ) แล้วไฮไลต์บนแผนที่
   - ทำที่ `web/` ล้วน (filter `data.nodes` ตาม `th/en/keywords`) ไม่ต้องแตะ pipeline
2. **Export รูป/ข้อมูลจากเว็บ** — ปุ่ม download PNG ของแผนที่ + CSV ของรายการ emerging
   - `svg → canvas → png` ฝั่ง client ล้วน
3. **Topic detail เจาะลึกขึ้น** — แสดง top journals, ตัวอย่างชื่อบทความล่าสุด (ต้องเพิ่มฟิลด์ใน export.py — มี metadata พร้อมอยู่แล้ว)
4. **โหมดเปรียบเทียบ 2 หัวข้อ** — overlay เส้นกราฟ 2 เส้นในแผง detail

### 🟡 ปานกลาง (1–2 สัปดาห์)

5. **Map stability ข้ามรอบรัน** — ตอนนี้ตำแหน่ง node เปลี่ยนทุกไตรมาส ผู้ใช้จำแผนที่เดิมไม่ได้
   - วิธี: init UMAP 2D ของรอบใหม่ด้วยตำแหน่งรอบก่อน (เฉพาะ topic ที่ match ได้ด้วย centroid similarity ≥ 0.7)
   - แตะ `pipeline/atlas/layout.py` + เก็บ layout เดิมใน `work/prev/`
6. **Journal view** — หน้า/โหมดแสดงวารสาร: วารสาร X มีบทความกระจายใน topic ไหนบ้าง (ใช้ `journal_name` ที่ ingest เก็บไว้)
   - เพิ่ม aggregation step ใน pipeline + หน้าใหม่ในเว็บ
7. **Diff รอบรัน ("อะไรเปลี่ยนตั้งแต่ไตรมาสก่อน")** — หัวข้อใหม่, หัวข้อที่เปลี่ยนสถานะ, mover ที่ score ขึ้นแรงสุด
   - ข้อมูล prev centroids มีอยู่แล้ว; เพิ่มการเก็บ snapshot status รอบก่อน + section เล็กในเว็บ
8. **Emerging narrative อัตโนมัติ** — ให้ LLM เขียนย่อหน้าสรุป "ทำไมหัวข้อนี้ emerging" จาก metric + ตัวอย่างบทความ (prompt ใช้งานจริงที่ `prompts/topic_narrative.th.md` + `prompts/executive_brief.th.md`)

### 🔵 ใหญ่ ต้องวางแผน (เดือนขึ้นไป)

9. **Author / affiliation network** — metadata มี authors+affiliations อยู่แล้ว; ทำ co-authorship graph ต่อ topic (ใครคุยกับใครในเรื่องนี้)
10. **Co-citation edges** — ถ้า export TCI มี references จะได้ edge คุณภาพสูงกว่า semantic similarity
11. **API backend + auth** — ถ้าต้องการ saved views, alerts ("แจ้งเตือนเมื่อหัวข้อ X เข้าเกณฑ์ EMERGING"), หรือข้อมูลที่ห้าม public
    - แนวทาง Kimi platform: backend-building (Hono + tRPC + Drizzle + MySQL, Kimi login ในตัว)
12. **ลงทะเบียน incremental** — ตอนนี้รันทั้ง corpus ใหม่ทุกไตรมาส (200K เรื่องยังสบาย); ถ้าโตเป็นล้านเรื่องค่อยทำ online clustering

## แนวคิดเชิงนโยบายที่ข้อมูลพร้อมจะตอบ (เสนอผู้บริหารได้เลย)

- **ช่องว่างงานวิจัย** — คู่ topic ที่อยู่ใกล้กันเชิงความหมายแต่ไทยทำน้อยทั้งคู่ (หางยาวของแผนที่)
- **จับคู่งานวิจัยกับวารสาร** — บรรณาธิการเห็นว่าหัวข้อ emerging ไปลงวารสารไหน → ตัดสินใจเปิด section ใหม่
- **ภาพรวมระดับประเทศรายปี** — สถิติ share ของแต่ละกลุ่มเทียบปี = วัตถุดิบรายงานนโยบาย
- **Early warning** — topic ที่ DECLINING หลายไตรมาสติดในสาขาสำคัญของประเทศ

## สิ่งที่ตั้งใจไม่ทำ (และเหตุผล)

| ไม่ทำ | เพราะ |
|---|---|
| Real-time updates | ข้อมูล TCI เปลี่ยนช้า — รายไตรมาสเพียงพอ, static site เสถียรกว่า |
| Login/user accounts (ตอนนี้) | เป็นเครื่องมือสาธารณะ — เพิ่มภายหลังได้ถ้าต้องการ saved views |
| ทำนายยาว > 2 ปี | ข้อมูลมี backfill lag — ทำนายยาวจะสร้างความมั่นใจเทียม |
| Score เทียบข้ามรอบรัน | score เป็น percentile ภายในรอบโดยออกแบบ — ใช้มิติดิบถ้าจะเทียบข้ามรอบ |
