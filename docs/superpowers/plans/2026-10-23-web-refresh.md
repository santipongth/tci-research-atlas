# Web refresh — plain language + Modern Minimal infographics across every page — Implementation Plan

> **For agentic workers:** execute batch by batch (sequential; batches share CSS/components). Lean plan: each batch states goals, rulings, files and gates; implementers write the code. One end-of-refresh review (Critical/Important only).

**Owner brief (2026-10-23):** every dashboard page prettier, easier to read and scan, concise; language ordinary citizens understand; airy, never-cramped type; Modern Minimal, quietly premium, professional; clean white background, crisp text; lead with examples; infographic-style visuals fitted to context (charts, tables, diagrams, illustrations), realistic. **Keep the Civic modern world of `DESIGN.md`** (Sarabun, civic blue, white, square corners) — this is a refinement, not a new visual world. P4 is finished first (done: v2.0.0-p4).

## Critique summary (impeccable critique, dual assessment, 2026-10-23)
- **Method:** dual-agent (A: design review with 24 routes × desktop/phone screenshots; B: detector CLI + in-page overlay + measurements).
- **Detector:** 0 anti-patterns in source and on 5 live pages (1440/390). Not a clean bill: rule set does not cover density/IA.
- **Nielsen 26/40 (Acceptable).** Weakest: Match with real world (1 — statistician language), Recognition over recall (2), Aesthetic/minimalist (2).
- **Measured:** phone chrome ≈ 520–540 px before the h1 (nav wraps to 3 rows, no collapse, two stacked banners); main paragraphs ≈ 80–95 chars/line at 1440; 10–17 distinct font sizes per page (13…48 px); tap targets < 24 px (footer links 21 px, topic list links 18–21 px, search result titles 23 px); 72–98 text leaves < 14 px on overview/atlas; first search result ≈ 2 screens down on phone.
- **Strengths to keep:** cite-ready figure system (numbered captions, "ที่มา:", chart/table tabs, sortable tables, CSV); status = glyph + colour + name; the overview highlighter headline; the `/atlas` terrain map; example-first copy already in `/keywords` insight and `/compare` starters.
- **Bug:** `JournalPage.tsx` drift chart duplicate y ticks (1-decimal format on 0.05 steps).

## Global constraints (binding)
- `CLAUDE.md` §6 Web rules and `DESIGN.md` win; tokens only via `var(--…)`; no hex in `.tsx`; no dynamic Tailwind classes; every string th + en (`i18n.test.ts`); lazy pages keep their own strings file via `useStrings`; status always glyph + colour + Thai/English name; palette changes pass `palette.test.ts`; Thai: no italics, no letter-spacing, line-height ≥ 1.5 for Thai text; info never by colour alone; every chart keeps a table tab + numbered caption + "ที่มา:" line; sortable tables keep `aria-sort` + CSV; self-hiding sections; never a white page; no runtime third-party requests; entry ≤ 180 KB gzip (now ≈ 171).
- **Definitions do not change.** Status set, thresholds and `definition_version` stay; only the *wording* that explains them changes. Rule texts that embed numbers keep reading them from `web/src/lib/definition.ts` / manifest (`definitionStrings.test.ts`).
- **IA ruling:** keep the owner-approved persona groups (ผู้บริหาร / บรรณาธิการ / นักวิจัย) — they come from the P1/P3 decisions — but make the top level lighter and collapse everything into one menu on phones. No question-based renaming of the menu groups in this refresh (offer it to the owner afterwards).
- **Copy ruling — two layers:** layer 1 = one short plain sentence, example first ("เช่น …"), numbers filled from data; layer 2 = the technical definition behind "วิธีอ่าน" disclosures or a glossary `Term` popover. No English codes (LOW_DATA, EMERGING …) inside Thai prose — use the Thai status names. Jargon (ช่วงเชื่อมั่น, ช่วงฐาน, subfield, HHI, Jaccard, Jensen–Shannon, cosine, metadata, embedding) leaves headings, ledes and column headers.
- **Visual ruling:** realistic, quiet infographics built from the existing chart kit + tokens (no stock illustration, no emoji, no official SDG colours/icons). New chart forms are hand-written SVG in `web/src/charts/` with the dataviz conventions.
- Gate per batch (in `web/`): `npm run lint && npx tsc -b && npm test && npm run build && npm run check:bundle && npm run e2e`; one screenshot round desktop 1440 + phone 390 (light; one dark spot-check), fix what it shows once, stop. Screenshot gates: on phone the h1 and the first number sit above 400 px; no meaning-bearing text under 15 px (axis ticks may be 13–14).
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Implementers never push.

## Batches

### Batch 1 — Foundation: type scale, rhythm, chrome
- Six-step type scale in `tokens.css` (caption 14 · meta 16 · body 19/phone 17 · lead/h3 24 · h2 30 weight 600 · h1 44–48) + numeric display (tile 40, hero 56); section rhythm tokens (24 / 40 / 64 desktop); measure tokens (lede 32em, body 38–40em); secondary text ≥ 15 px; English headings line-height ≈ 1.3 (Thai keeps ≥ 1.45 headings, 1.65 body); highlighted headline spans don't wrap mid-phrase.
- Phone chrome: one "เมนู / Menu" disclosure holding the groups + search + language/theme; the phase + sample banners merged into one compact line with a details toggle; "ในหน้านี้" collapsed under 900 px; tap targets ≥ 24 px (footer, list links).
- Footer → "what next" footer (อ้างอิง Atlas · ดาวน์โหลดข้อมูล · รอบก่อนหน้า · อ่านตัวเลขอย่างไร) + one small licence line.
- Update `DESIGN.md` (type, spacing, nav, footer) to match.
- Files: `web/src/styles/{tokens,base,layout,charts,executive}.css`, `components/{Header,Layout,PhaseBanner,OnThisPage,Footer}.tsx`, `strings/common.ts`, `DESIGN.md`, e2e (phone chrome height check).

### Batch 2 — Shared components
- `StatTile` (big number, delta, optional ink-only sparkline, plain label) replacing `dl` key-figure lists on topic/journal/institution/methods; overview tiles → 4 primary + "ดูเพิ่ม".
- Figure caption row: caption · tabs · "วิธีอ่าน" disclosure · small CSV button in one band; drop the repeated `csv.units` note (one short tooltip/footnote).
- `DataTable`: column priority (3–4 visible + "แสดงทุกคอลัมน์"), units in headers, phone cards show 3 fields + expand.
- `CiWhisker`: min width; text-first in tables ("+113% (101–129)"); CI text ≥ 14 px in ink-2. Forest plot whisker band ≥ 55% width, axis fitted to data.
- `StatusLegend` with one-line plain meanings; status selector as a horizontal scroll strip on phones (no 3-row wrap); no nested tabs.
- Glossary `Term` popover (`lib/glossary.ts` + strings).
- Chart tick precision fix in `MultiLineChart` / `charts/scale.ts` + the JournalPage drift axis.
- Files: `components/*`, new `components/{StatTile,Term}.tsx`, `charts/*`, `styles/{components,topic}.css`, tests.

### Batch 3 — Plain-language copy pass (all strings files)
- Apply the two-layer ruling everywhere; start from the critique's 28 rewrites (kept in this plan's appendix); status one-liners; nav labels ("วิธีการและนิยาม" → "อ่านตัวเลขอย่างไร", "กาแล็กซีบทความ" → "แผนที่บทความทุกเรื่อง"); release code explained ("รอบ 2026Q4 = ข้อมูลไตรมาส 4 ปี 2026").
- Files: `web/src/strings/*.ts`, tests.

### Batch 4 — Public front door: Overview, Brief, Topic, Emerging, Atlas (phone)
- Overview: headline → "3 เรื่องสำคัญรอบนี้" finding cards (big number + mini trend + example article/topic + plain sentence) → 4 KPI tiles → status overview as a 48-square waffle with glyphs → forest plot. "สรุป 1 หน้า" button in the header.
- Brief: one-page infographic (headline, 4 tiles, 3 finding cards, status waffle, top movers dot plot), print-friendly; `brief:pdf` still works.
- Topic: hero row (status chip + plain growth sentence + share tile + sparkline) + "เช่น" top representative article near the top; journals/institutions as mini bar rankings with table tabs.
- Emerging: one level of tabs; forest plot per status with wider whiskers.
- Atlas phone: sheet aspect fitted, top-N labels visible; "อ่านแผนที่นี้ใน 3 ขั้น" mini diagram.

### Batch 5 — Executive pages: tables → infographics
- Institutions: collaboration network (or chord) with table tab; countries as bars. Institution: yearly column chart, topic mix 100% bar, partner cards.
- Regions: lowest class distinct from no-data (hatch), ranked top-provinces bars beside the map.
- SDG: 17 goal tiles (number, Thai name, topic count, share bar; gaps outlined) — ink + one blue.
- Global + Gaps: shared opportunity quadrant scatter (world growth × Thai activity) with labelled zone; gaps as question cards with an example; concentration as stacked bar.
- Changes: status transition slope/flow chart + "ใหม่ / รวม / แยก / ไม่มีแล้ว" mini diagram.

### Batch 6 — Editors, researchers, IA cleanup
- Journals scatter (completeness × in-house share) + 4-column table; Journal topic-mix stacked bars; Methods bar chart; References collapse + per-journal bars; Keywords dictionary collapsed to 10 rows + risers; Match "ลองด้วยตัวอย่าง" sample abstract; Search: topic matches first then articles, result meta ≥ 15 px, results higher on phone; Galaxy side panel used (legend + try-these picks); Data split "ดาวน์โหลดง่าย ๆ" vs "สำหรับนักพัฒนา"; About pipeline diagram + status decision tree; Compare duplicate search removed.

### Finish
- End-of-refresh review (Critical/Important only), docs (`DESIGN.md`, `web/README.md`, `docs/ROADMAP.md`), push, Pages redeploy.

## Appendix — copy rewrites from the critique (th / en)
Keys refer to `web/src/strings/*.ts`; numbers in braces are filled from data/definition.
1. `common.noBaseline`: "หัวข้อใหม่ — ช่วง {base} ยังไม่มีงานเรื่องนี้" / "New — no articles on this in {base}".
2. `common.ciRange`: "น่าจะอยู่ระหว่าง {lo} ถึง {hi}" / "Likely between {lo} and {hi}" (CI term in "วิธีอ่าน").
3. `common.col.ratio`: "มากขึ้นกี่เท่าจากช่วง {base}" / "× its {base} share".
4. `common.journalDriven`: "โตเร็ว แต่มาจากวารสารหรือสถาบันไม่กี่แห่ง — อย่าเพิ่งสรุปว่าเป็นกระแส" / "Growing fast, but from only a few journals or institutions — not a national trend yet".
5. `common.journalDrivenBody`: "เช่น งานส่วนใหญ่มาจากวารสารเดียว ถ้าวารสารนั้นหยุดรับเรื่องนี้ ตัวเลขจะเปลี่ยนมาก เกณฑ์: อย่างน้อย {j} วารสาร {o} สถาบัน" / "For example, most articles come from one journal; if it stops, the trend disappears. Bar: at least {j} journals and {o} institutions".
6. `common.csv.units` → tooltip "ตัวเลขในไฟล์เป็นทศนิยม (0.10 = 10%)" / "Numbers in the file are decimals (0.10 = 10%)".
7. `common.autoSummary.template`, `executive.brief.execNote`: "ระบบเขียนประโยคนี้จากตัวเลขในหน้านี้" / "Written automatically from the figures on this page".
8. `common.col.score`: "คะแนนสัญญาณ (0–100)" / "Signal score (0–100)" + Term.
9. `common.phase.text` + `sample.text` merged: "ทดลองใช้ · ตัวเลขชุดนี้เป็นข้อมูลตัวอย่าง ยังไม่ใช้อ้างอิง" / "Beta · sample figures, not for citing" (+ details).
10. `overview.ov.status.intro`: example-first, e.g. "เช่น "{topic}" มีบทความเพิ่มปีละราว {g} จึงเป็นหัวข้อกำลังเกิดใหม่ …" (filled from data).
11. `overview.ov.forest.axis`, `ov.pf.y`: "ส่วนแบ่งบทความเพิ่ม/ลดต่อปี" / "Change in share of articles per year".
12. `overview.ov.howCI.body`: poll analogy — "ตัวเลขการเติบโตเป็นค่าประมาณ เหมือนโพลที่บอกช่วงคะแนน …" / "Growth is an estimate, like a poll that gives a range …".
13–15. `emerging.rule.EMERGING|WATCH|DECLINING`: plain rules ("แม้คิดแบบระวังที่สุดยังโตเกิน {bar} ต่อปี …"), numbers from definition.ts.
16. `about.about.def.intro`: Thai status names, no codes.
17–19. `executive.gl.def`, `gl.col.subfield` ("สาขาย่อย"), `gl.col.ai` ("ไทยทำมากแค่ไหนเทียบโลก (1 = เท่าโลก)").
20–21. `executive.gp.bridge.*` ("สองหัวข้อที่ใกล้กันแต่ยังไม่มีใครทำร่วม" + data example), `gp.risk.*` ("หัวข้อที่พึ่งแหล่งเดียว").
22–24. `journals.jr.drift.*` ("วารสารเปลี่ยนแนวแค่ไหน"), `col.inhouse` ("ผู้เขียนจากเจ้าของวารสาร"), `col.effOrgs` ("ผู้เขียนมาจากราวกี่สถาบัน"), `col.completeness` ("ข้อมูลบทความครบ (เต็ม 100)"), `jr.peers.intro` ("วารสารที่ตีพิมพ์เรื่องคล้ายกัน (1 = เหมือนกันทุกเรื่อง)").
25. `methods.me.mono`: "ใช้วิธีเดียวเป็นหลัก" / "Mostly one method".
26. `executive.ov.exec.h`: "ข้อสังเกตสำหรับการวางนโยบาย"; `overview.ov.kpi.h`: "รอบนี้ในตัวเลข" / "This release in numbers".
27. `changes.ch.retired.h`: "หัวข้อที่ไม่มีแล้วในรอบนี้"; `ch.restructured.h`: "หัวข้อที่รวมหรือแยก".
28. nav: "อ่านตัวเลขอย่างไร" / "How to read the numbers"; galaxy "แผนที่บทความทุกเรื่อง" / "Map of every article".
