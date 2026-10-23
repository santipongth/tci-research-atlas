---
version: 1
slug: "web-src"
primary_target: "web/src"
related_targets: []
---

# Surface brief — TCI Research Atlas web (all routes)

Scope: every route of `web/` (front door `/overview` first, then the shared shell, components and charts so all 23 routes inherit). Visitor mode: Read (front door is a data story; tool pages stay Operate-clear inside the same world). Audience and constraints: PRODUCT.md.

## Direction contract

THESIS: Every page is a short data story — a plain question as the headline, the answer in one sentence, one big number, then one large chart with its labels and notes written on the chart that proves it. It refuses both the government statistical-release form (bands, boxed fields, underlined links everywhere) and the SaaS dashboard (rows of bordered KPI cards, eyebrow chips, card grids).

OWN-WORLD: White ground; ink #14182b; secondary ink ≈ #4d536b; context data in quiet greys; TCI blue #283894 only for the data that answers the page's question and for the brand; TCI orange #f89020 reserved for the single highlighted point / annotation per view (never text on white below 3:1 use). Sarabun only: 800 for question headlines, 700 for numbers, 400 for reading text at 18–19 px / 1.7. Numbers stand on the page (no boxes): big numeral + one short unit line. Hairline rules, generous gaps, 8 px radius on controls only. Direct labels and leader-line notes on charts instead of legends. Status keeps glyph + colour + Thai name. TCI · NECTEC · สวทช. logos in the footer band; TCI logo in the top bar.

STORY: The visitor reads the question, gets the answer in one sentence and one number, sees the chart prove it, then follows a plain "อ่านต่อ" to the deeper page. Specialists find the table tab, CSV, source line and method behind "วิธีอ่าน" exactly where they were.

FIRST VIEWPORT: (/overview at 1440×900) white top bar: TCI logo + name left, search and ไทย/EN right; under it one hairline navigation row holding the owner-approved menu (2026-10-23: ภาพรวม · สรุปผู้บริหาร · the four question menus · ข้อมูลเปิด · อ่านตัวเลขอย่างไร — eight entries do not fit one row beside the logo and search at 1200 px, so the bar keeps two rows); then one quiet notice line with a single chip. Below, two columns on the 1200 grid: left ~420 px — h1 question "งานวิจัยไทยเรื่องไหนกำลังมา" (≈52 px, 800), one answer sentence, a byline (ข้อมูลถึงปี … · อัปเดต …), and one hero number in TCI blue with its unit line; right ~720 px — the large chart of the fastest-rising topics: the leader in TCI blue with an orange end dot and an on-chart label, the rest grey with direct labels, one annotation. Phone: question, sentence, number, then the chart full width.

SIGNATURE: the focus line — pointing at or tabbing to any series in a story chart turns it TCI blue, greys the rest and writes its label + value on the chart; the table tab is the keyboard/screen-reader equivalent. Motion: story charts draw once when they enter the view (reduced motion: drawn already).

FORM: chosen = "ข่าวข้อมูล (Data explainer)", the IMPECCABLE'S PICK card (position 1 on my ordered grounded list; the roll assigned position 4, "Line & Station"); seed:6ff13bce7ce3c503

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Unresolved
- Official high-resolution logo files (current PNGs from tciai.openservice.in.th, 227–425 px wide).
