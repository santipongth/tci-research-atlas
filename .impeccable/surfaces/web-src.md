---
version: 1
slug: "web-src"
primary_target: "web/src"
related_targets: []
---

# Surface brief — TCI Research Atlas web (all routes)

Scope: every route of `web/`. Five dashboards (`/overview`, `/topics`, `/places`, `/journals`, `/goals`), four detail pages (`/topics/:id`, `/journals/:id`, `/institutions/:id`, `/province/:code`), the two maps (`/atlas`, `/galaxy`), `/brief` and `/about`, all sharing one app shell. Visitor mode: Operate (scan the key facts, open the detail on demand). Audience and constraints: PRODUCT.md.

## Direction contract

THESIS: Each page is a one-glance dashboard: the few facts that matter sit in white cards on a soft blue-grey canvas, and everything else stays one click away ("ดูทั้งหมด", a side drawer, the table view). It refuses the long scrolling data story the site used to be, and it also refuses the dense BI wall where every number has the same weight.

OWN-WORLD (pinned by the owner 2026-10-24 from a reference dashboard image + the TCI brand):
- Canvas #f3f5fa (`--canvas`). Cards are white, 16 px radius, with one soft offset shadow (0 1px 2px + 0 4px 16px, low alpha) and no border. 20 px card padding, 16–20 px grid gap.
- White left sidebar, 248 px: TCI logo and the page list (five dashboards · two maps · the reading guide). The active item sits on a light-blue pill (#eef0fa) in TCI blue with a drawn icon. Under 1024 px the sidebar becomes a drawer behind a menu button in a white phone bar (logo, language switch).
- White page bar on every page (`PageBar`): h1 with an (i), one short line, page actions, the release chip + beta/sample tag, and on desktop the ไทย/EN switch. No search box anywhere.
- Type is compact (owner, 2026-10-24: "smaller fonts, more room"): Sarabun only. Body 15 px, meta 13 px (never smaller for meaning), card titles 16 px/600, page h1 22–24 px/700, KPI values 26–28 px/700.
- Colour: ink #14182b; TCI blue #283894 for the data that answers the card's question and for the brand; one orange mark (--accent-mark) per view. Context data is grey. Status keeps glyph + colour + Thai name.
- KPI cards: an icon in a soft-tinted circle, a label (an (i) when the figure needs explaining), the value, then Δ vs the previous release in green with ▲ (the release compared with is named once, in the page bar) or one short line.
- Card header: the title and its (i) on the left; "ดูทั้งหมด" (to the dashboard or detail page that has everything) on the right. Long lists in a card show 6–10 ranked rows with "แสดงเพิ่ม"; switches between views of one card are a small segmented control. No chart/table switch, no "วิธีอ่าน", no CSV, no source line or figure number on the page (owner, 2026-10-24).

STORY: A visitor lands on ภาพรวม and gets the national picture in one screen: four KPIs, what is rising or falling, the status mix, where the work happens, and the release in brief (findings / notes for policy makers). Each card answers one question. "ดูทั้งหมด" goes to the dashboard that has the rest; every detail is one click away and every explanation sits behind an (i); the full method is on /about. ภาพรวม is also the executive brief: it prints on two A4 pages.

FIRST VIEWPORT: (/overview at 1440×900) sidebar left; page bar "ภาพรวม" + print button + release chip + ไทย/EN; a row of 4 KPI cards; then a 12-column grid with the rising-topics line chart (8 columns) beside the rising/falling list (4); then the status ring, provinces and institutions; then the release in brief and the other figures. About 1.6 screens tall. Phone: one column, KPI cards 2×2, the line chart left out (the ranked list beside it carries the same topics with trend lines), about 3 screens.

SIGNATURE: the focus line stays. Pointing at or tabbing to a series in the rising chart (small fast-growing topics; a large hot topic would flatten them) turns it TCI blue and writes its label + value on the chart. Card motion is a single soft lift on hover for cards with "ดูทั้งหมด"; nothing animates on load except the chart draw (reduced motion: none).

FORM: chosen = owner-pinned "TCI dashboard" (two reference dashboard images + the TCI brand); seed: none (the roll was set aside because the owner pinned the world).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Unresolved
- Official high-resolution logo files (current PNGs from tciai.openservice.in.th, 227–425 px wide).
