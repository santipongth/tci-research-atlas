---
name: TCI Research Atlas
description: แผนที่ภูมิทัศน์งานวิจัยไทย — one-glance dashboards of Thai research topics, places, journals and goals, quarter by quarter, in Thai and English.
colors:
  canvas: "#f3f5fa"
  paper: "#ffffff"
  surface: "#f5f6fa"
  ink: "#14182b"
  ink-secondary: "#4d536b"
  ink-tertiary: "#6b7088"
  rule: "#c9cddb"
  hairline: "#e6e8f0"
  field-border: "#8a8fa6"
  tci-blue: "#283894"
  tci-blue-deep: "#1a2466"
  tci-blue-soft: "#eef0fa"
  tci-blue-pale-ink: "#dfe3f4"
  tci-orange: "#f89020"
  orange-mark: "#e07000"
  orange-ink: "#a85400"
  context-grey: "#b9bdcc"
  up-green: "#0b6b46"
  tag-sample: "#e4e6ee"
  status-emerging: "#13a08a"
  status-watch: "#c47a0c"
  status-hot: "#a3124f"
  status-declining: "#5b74cf"
  status-stable: "#6f777b"
  tag-emerging: "#dcf3ec"
  tag-emerging-ink: "#0a4a3e"
  tag-watch: "#fcefd3"
  tag-watch-ink: "#573700"
  tag-hot: "#f9e2eb"
  tag-hot-ink: "#680b32"
  tag-declining: "#e6eafa"
  tag-declining-ink: "#22326d"
  tag-stable: "#eef0f2"
  tag-stable-ink: "#363d43"
  tag-low-data-ink: "#4d536b"
  map-sheet: "#f7f8fb"
  map-contour: "#9a6a35"
  series-1: "#283894"
  series-2: "#e07000"
  series-3: "#13866f"
  series-4: "#b8860b"
  seq-1: "#eceefa"
  seq-2: "#c5cbec"
  seq-3: "#8c97d6"
  seq-4: "#4b5ab4"
  seq-5: "#1f2c7a"
  cat-01: "#e8b5a6"
  cat-02: "#dbc99d"
  cat-03: "#c3d59c"
  cat-04: "#e8d095"
  cat-05: "#a8d1a4"
  cat-06: "#b1c4da"
  cat-07: "#d4bad6"
  cat-08: "#9ccfca"
  cat-09: "#bfd8e8"
  cat-10: "#e3bfcd"
  cat-11: "#cfd3a6"
  cat-12: "#d9cbb8"
typography:
  h1:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "clamp(1.25rem, 1.1rem + 0.5vw, 1.5rem)"
    fontWeight: 700
    lineHeight: 1.5
  card-title:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 700
    lineHeight: 1.5
  kpi-value:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "clamp(1.375rem, 1.2rem + 0.5vw, 1.625rem)"
    fontWeight: 700
    lineHeight: 1.5
    fontFeature: "tnum"
  body:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.7
  meta:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  caption:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.5
  tick:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
rounded:
  control: "8px"
  pill-item: "10px"
  panel: "12px"
  tile: "14px"
  card: "16px"
  pill: "999px"
spacing:
  group: "12px"
  block: "20px"
  section: "32px"
  card-pad: "20px"
  card-gap: "20px"
  card-pad-phone: "16px"
  card-gap-phone: "12px"
  sidebar: "248px"
components:
  card:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.card}"
    padding: "20px"
  kpi-card:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "16px 20px"
  kpi-icon:
    backgroundColor: "{colors.tci-blue-soft}"
    textColor: "{colors.tci-blue}"
    rounded: "{rounded.pill}"
    size: "46px"
  side-link:
    textColor: "{colors.ink-secondary}"
    typography: "{typography.meta}"
    rounded: "{rounded.pill-item}"
    padding: "6px 12px"
    height: "42px"
  side-link-active:
    backgroundColor: "{colors.tci-blue-soft}"
    textColor: "{colors.tci-blue}"
    rounded: "{rounded.pill-item}"
  button-primary:
    backgroundColor: "{colors.tci-blue}"
    textColor: "{colors.paper}"
    typography: "{typography.meta}"
    rounded: "{rounded.control}"
    padding: "4px 16px"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.tci-blue-deep}"
  button-quiet:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.meta}"
    rounded: "{rounded.control}"
    padding: "0 14px"
    height: "36px"
  see-all:
    textColor: "{colors.tci-blue}"
    typography: "{typography.meta}"
    rounded: "{rounded.control}"
    padding: "0 8px"
    height: "36px"
  see-all-hover:
    backgroundColor: "{colors.tci-blue-soft}"
    textColor: "{colors.tci-blue-deep}"
  segmented:
    backgroundColor: "{colors.canvas}"
    rounded: "{rounded.pill-item}"
    padding: "3px"
  segmented-option-on:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.tci-blue}"
    rounded: "7px"
    height: "32px"
  release-chip:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.caption}"
    rounded: "{rounded.pill}"
    padding: "2px 12px"
  rank-badge:
    backgroundColor: "{colors.tci-blue-soft}"
    textColor: "{colors.tci-blue}"
    rounded: "{rounded.control}"
    size: "26px"
  rank-badge-first:
    backgroundColor: "{colors.tci-blue}"
    textColor: "{colors.paper}"
  info-popover:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.meta}"
    rounded: "{rounded.panel}"
    padding: "14px 16px"
    width: "352px"
  chip-emerging:
    backgroundColor: "{colors.tag-emerging}"
    textColor: "{colors.tag-emerging-ink}"
    typography: "{typography.caption}"
    padding: "2px 8px 1px 6px"
  chip-watch:
    backgroundColor: "{colors.tag-watch}"
    textColor: "{colors.tag-watch-ink}"
  chip-hot:
    backgroundColor: "{colors.tag-hot}"
    textColor: "{colors.tag-hot-ink}"
  chip-declining:
    backgroundColor: "{colors.tag-declining}"
    textColor: "{colors.tag-declining-ink}"
  chip-stable:
    backgroundColor: "{colors.tag-stable}"
    textColor: "{colors.tag-stable-ink}"
  chip-low-data:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.tag-low-data-ink}"
  drawer:
    backgroundColor: "{colors.paper}"
    width: "min(560px, 94vw)"
---

# Design System: TCI Research Atlas

Normative sources: the frontmatter above and `web/src/styles/tokens.css` (they carry the same values; a change goes into both). Shell and dashboard rules live in `web/src/styles/dashboard.css`; status glyph and chip rules in `web/src/styles/status.css`. The direction contract is `.impeccable/surfaces/web-src.md`; product context is `PRODUCT.md`. Project rules for code are in `CLAUDE.md` §6 "Web"; this file and that section agree.

## Overview

**Creative North Star: "The TCI Dashboard"**

Every page is a one-glance dashboard. The few facts that matter sit in white cards on a soft blue-grey canvas, held between a white sidebar on the left and a white page bar on top; everything else is one click away: "ดูทั้งหมด" to the dashboard or detail page that has the rest, "แสดงเพิ่ม" for the next rows of a ranked list, an (i) button for the explanation. The world refuses two things: the long scrolling data story the site used to be, and the dense BI wall where every number has the same weight.

The type is compact Sarabun (body 15 px) so a dashboard fits in about 1.5–2 screens at 1440 × 900. Colour is spent sparingly: TCI blue (from the logo) for the brand and for the data that answers a card's question, one orange mark per view, quiet greys for context, and six reserved status colours that always travel with a glyph and a Thai name. Depth is one soft shadow under each card on the canvas; nothing else on the page is raised except things that float (popovers, the drawer).

Five dashboards (`/overview`, `/topics`, `/places`, `/journals`, `/goals`), four detail pages (`/topics/:id`, `/journals/:id`, `/institutions/:id`, `/province/:code`), the two maps (`/atlas`, `/galaxy`) and `/about` share one shell. The overview is also the executive brief: it prints as two A4 pages (`/brief` redirects to `/overview`).

**Key Characteristics:**
- White sidebar (248 px) + white page bar + soft canvas (#f3f5fa) + white cards (16 px radius, one soft shadow, no border).
- 12-column card grid; cards span 3/4/5/6/7/8/12; one column under 760 px.
- Compact Sarabun only: body 15 px, card titles 16 px/700, page h1 20–24 px/700, KPI values 22–26 px/700.
- KPI cards: drawn icon in a soft-blue circle, label, value, change since the previous release.
- Ranked rows with "แสดงเพิ่ม" in steps of 6–10; "ดูทั้งหมด" to the page with everything.
- Explanations only behind (i) buttons (click/tap); no tabs, "วิธีอ่าน", CSV, source lines or figure numbers on the page; no search boxes.
- Status always glyph + colour + Thai name; one light theme.

## Colors

A white-and-blue-grey dashboard: TCI blue carries brand and answers, one orange mark per view, greys for everything that is context.

### Primary
- **TCI Blue** (`--brand`, `--link`, `--btn`, `--focus`, `--series-1`): the logo blue. The brand, links, the primary button, the focus ring, the active sidebar item, the first rank badge, bars in ranked bar lists, and the data series that answers a card's question.
- **TCI Blue Deep** (`--link-hover`, `--btn-hover`, `--btn-edge`): hover state for links and the primary button.
- **TCI Blue Soft** (`--brand-soft`): tinted backgrounds only: the active sidebar pill, the KPI icon circle, rank badges after the first, the "ดูทั้งหมด" hover, the sidebar brief box, the beta tag.
- **TCI Blue Pale Ink** (`--brand-ink-2`): secondary text on TCI blue.

### Secondary
- **Orange Mark** (`--accent-mark`, `--series-2`): the one highlighted mark per view: the end dot of the focused line on the overview chart, a ring on the province locator, a single annotated point. A mark, never a fill or a text colour.
- **TCI Orange** (`--accent`): the logo orange; brand artwork only. It never sits on white as text or as a small mark (contrast below 3:1).
- **Orange Ink** (`--accent-ink`): orange text when orange text is unavoidable.
- **Up Green** (`--up`): the change since the previous release when it rises (KPI cards, fact rows), always with a ▲ arrow. A fall is Ink Secondary with ▼; green is never used for anything else.

### Neutral
- **Canvas** (`--canvas`): the work area behind the cards; also the hover fill of sidebar links and icon buttons, the segmented-control track, the release chip, mini-stat tiles.
- **Paper** (`--bg`): cards, KPI cards, sidebar, page bar, phone bar, drawer, popovers.
- **Surface** (`--surface`): bar tracks inside charts, the language-switch track.
- **Ink** (`--ink`): headings, values, names. **Ink Secondary** (`--ink-2`): labels, sub lines, inactive nav text, falling changes. **Ink Tertiary** (`--ink-3`): sidebar group headings, idle icons and (i) buttons, card notes, percentages.
- **Hairline** (`--border-2`): row dividers inside cards, the sidebar and page-bar edges, print card borders. **Rule** (`--border`): chart baselines, the dashed LOW_DATA outline, scrollbars. **Field Border** (`--field-border`): the few form controls that remain (map filters).
- **Context Grey** (`--context`): data that is context, not the answer (grey lines behind the focus line, other dots).
- **Sample Tag** (`--tag-sample-bg` / `--tag-sample-ink`): the "ข้อมูลตัวอย่าง" tag beside the release chip; neutral, never a status colour.

### Status (reserved)
`--st-EMERGING`, `--st-WATCH`, `--st-HOT`, `--st-DECLINING`, `--st-STABLE` and `--st-LOW_DATA` (same grey as STABLE; LOW_DATA is told apart by its dashed, hollow glyph) colour the status glyphs and marks; `--tag-*-bg` / `--tag-*-ink` pairs colour the status chips. LOW_DATA's chip is white with a 1 px Rule outline.

### Data
- **Sequential ramp** `seq-1…seq-5`: the province choropleth (5 quantile classes) and one-hue mixes, light to dark TCI blue.
- **Series** `series-1…4`: up to four compared lines (topic years on a journal page); series 1 is TCI blue, series 2 is the orange mark.
- **Field tints** `cat-01…cat-12`: background terrain on the topic map only; the data names them by token key.
- **Map sheet / contour** (`--map-sheet`, `--map-contour`, `--map-grid`, `--map-dot`): the `/atlas` terrain map.

### Named Rules
**The Answer Is Blue Rule.** In a card's chart, TCI blue marks the data that answers the card's question; everything else is grey context. If two things are blue in one chart and they do not answer the same question, one of them is wrong.

**The One Orange Rule.** At most one orange mark per view, in Orange Mark (#e07000), as a dot or ring, never a fill or text. The logo orange stays in the logo.

**The Reserved Status Rule.** The six status colours mean status and nothing else, and a status is never shown by colour alone: glyph (▲ กำลังเกิดใหม่ · ◆ จับตา · ● กำลังมาแรง · ▼ ลดลง · ■ คงที่ · dashed hollow circle ข้อมูลน้อย) + colour + Thai name, every time. Any colour change passes `web/src/styles/palette.test.ts` (CVD separation between status colours, text contrast of the chip ink on its tag, and no dark-theme block).

**The Token-Only Rule.** Components use `var(--token)` from `tokens.css`; a hex value in a component is a bug. Group colours arrive from the data as token keys (`cat-07`), never hex. No dynamic Tailwind colour classes; write every variant in CSS (`chip-${status}`).

## Typography

**Font:** Sarabun (400 / 600 / 700, self-hosted), falling back to Noto Sans Thai, Leelawadee UI, system-ui. One family for everything, Thai and English.

**Character:** compact and even; hierarchy comes from weight and a few size steps, not from contrast of faces. The owner asked for smaller type and more on one screen (2026-10-24).

### Hierarchy
- **Page h1** (700, `--fs-h1` clamp 20→24 px, 1.5): the page title in the page bar, one per page, with its (i).
- **Card title** (700, `--fs-lead` 16 px, 1.5, balanced wrap): the h2 of every card and section card; the drawer title.
- **KPI value** (700, `--fs-tile` clamp 22→26 px, 1.5, tabular): KPI cards and the status-picker counts; 22 px on phones. Mini-stat values and phone KPI values are 22 px (1.375rem).
- **Lead** (`--fs-lead` 16 px): emphasised values in fact rows.
- **Body** (400, `--fs-body` 15 px, 1.7): prose: findings, policy notes, topic summaries; max 72ch inside cards.
- **Meta** (400–700, `--fs-meta` 14 px, 1.5): sidebar links, buttons, "ดูทั้งหมด", ranked-row names and values, fact labels, popover text, chart titles inside cards (600, Ink Secondary).
- **Caption** (400–700, `--fs-caption` 13 px, 1.5): the floor for anything that carries meaning: page-bar sub line, chips, the release chip, KPI changes, rank badges, row meta, map keys, sidebar group headings, card notes.
- **Tick** (`--fs-tick` 13 px, the same value as `LABEL_PX.tick`): SVG axis ticks only.

`--fs-h2` (18 px), `--fs-display` and `--fs-hero` remain in `tokens.css` for older page bodies (`/about` prose and a few lazy visual blocks); new cards and pages do not use them.

### Named Rules
**The Compact Floor Rule.** Nothing on a page is set under 13 px (`--fs-caption`, and `--fs-tick` for SVG axis ticks). Sizes come from `--fs-*` only.

**The Thai Line-Height Rule.** Thai stacks marks above and below the line: body 1.7, headings and labels ≥ 1.5; only English-only rules (`:lang(en)`) close headings to 1.3 with −0.01em tracking. `web/src/styles/lineHeight.test.ts` enforces it.

**The Upright Thai Rule.** Thai has no true italic: `em`, `i`, `cite`, `dfn`, `var`, `address` render upright; emphasis is weight 600/700. No letter-spacing and no case transforms on Thai.

**The Arabic Numerals Rule.** Both languages use Arabic digits with en-US grouping (60,773), the true minus sign (−), and Gregorian years; numbers that align are tabular.

## Layout

**Shell.** At ≥ 1024 px: a grid of the sticky white sidebar (`--side-w` 248 px, full height, 1 px Hairline right edge) and the page column. Under 1024 px the sidebar is gone: a sticky white phone bar (menu button 44 px, logo, ไทย/EN) opens the same navigation in a left drawer; the product name beside the logo hides under 560 px.

**Page.** Every page opens with exactly one page bar (`PageBar`, or `PageHeader` which wraps it): white, Hairline bottom edge, content max 1480 px, padding 14 × 28 px (12 × 16 under 760 px). Below it the dashboard body (`.dash`): max 1480 px, padding 24 / 28 px (12 px under 760 px), blocks separated by `--card-gap`. Older pages written as `.container` are coerced into the same column of cards.

**Grid.** `DashGrid` is 12 equal columns with `--card-gap` (20 px; 12 px under 641 px), rows stretch so cards in a row share a height. Spans and their collapse:

| Span | ≥ 1280 px | 761–1279 px | ≤ 760 px |
|---|---|---|---|
| 3, 4 | 3 / 4 cols | half (6) | full |
| 5, 7, 8 | 5 / 7 / 8 cols | full (12) | full |
| 6 | half | half | full |
| 12 | full | full | full |

Common pairings: 8 + 4 (a chart beside its ranked list), 4 + 4 + 4, 7 + 5 (a map beside its top list), 6 + 6. `DashStack` puts two or three short cards in one column of the grid; the last one takes the leftover height; a 4- or 5-span stack goes full width under 1280 px.

**KPI row.** `KpiRow`: as many 220 px-minimum columns as fit above 1100 px (four on a dashboard), two columns at ≤ 1100 px, a compact tile at ≤ 560 px (28 px icon beside the label, value below).

**Breakpoints in use.** 1280 (spans collapse), 1100 (KPI row 4 → 2), 1024 (sidebar ↔ phone bar + drawer), 760 (one column, tighter page padding, phones drop the overview line chart), 640 (card padding 16, gap 12, section space 24; bar lists keep name · bar · number on one line), 560 (compact KPI tiles, status picker 2 columns, big province map above its list), 480 (row sparklines hide), 360 (donut stacks above its list).

**Height budget.** A dashboard is about 1.5–2 screens tall at 1440 × 900 and about 3 screens on a 390 px phone. Lists start short (6–10 rows) and grow on request; detail moves to its own page rather than lengthening a card.

**Rhythm.** `--sp-group` 12 px (card head → content), `--sp-block` 20 px (between figures inside a card; 18 px between two charts in one card), `--sp-section` 32 px (long prose pages, above the footer). Footer sits on the canvas: partner logos (TCI · NECTEC · สวทช., 34 px tall) left, licence line right, Hairline top edge.

## Elevation & Depth

Layered, with one soft step. The canvas is the floor; cards and KPI cards sit one soft step above it; floating things (popovers, page-bar notice, drawer) sit clearly above. Rows, charts, chips and tiles inside a card are flat.

### Shadow Vocabulary
- **Card rest** (`--card-shadow`: `0 1px 2px rgba(20,24,43,.04), 0 4px 14px rgba(40,56,148,.05)`): every card, KPI card, status-picker button and map card. No border.
- **Card lift** (`--card-shadow-hover`: `0 2px 4px rgba(20,24,43,.05), 0 10px 24px rgba(40,56,148,.1)`): hover on a card that has "ดูทั้งหมด" and on status-picker buttons; the only card motion.
- **Floating** (`--shadow`: `0 14px 36px rgba(20,24,43,.14), 0 2px 6px rgba(20,24,43,.06)`): (i) popovers, the release notice, map zoom stack.
- **Drawer** (`-12px 0 40px rgba(20,24,43,.16)`, mirrored for the left drawer) over a `rgba(20,24,43,.36)` backdrop.
- **Pressed segment** (`0 1px 3px rgba(20,24,43,.12)`): the selected option of `Segmented` and the language switch.

### Named Rules
**The One Step Rule.** A card has exactly one rest shadow and no border; nothing inside a card casts a shadow. In print the shadow becomes a 1 px Hairline border.

## Shapes

Soft and rounded, scaled by size: 16 px cards and KPI cards, 14 px status-picker buttons and the sidebar brief box, 12 px popovers, mini-stat tiles and alerts, 10 px sidebar pills, icon buttons and segmented tracks (7 px inside), 8 px buttons, rank badges and "ดูทั้งหมด", full pills for the release chip, beta tag and language switch, circles for KPI icons and policy-note numbers. Status chips keep square corners. Dividers are 1 px Hairline rows; there are no thick rules and no coloured side bars.

Icons are one drawn set (`components/dashboard/Icon.tsx`): 24-unit grid, 1.75 stroke, round caps and joins, `currentColor`, always `aria-hidden`. Sidebar 20 px, KPI 22 px, (i) 14–18 px, arrows 16 px. No icon fonts, no emoji, no glyph characters as icons.

## Components

### Page bar (`PageBar` / `PageHeader`)
White bar opening every page. Left: h1 + (i) (`info` = what the page shows and how), one short sub line (`sub`, caption, Ink Secondary: data years, update date, which release the changes compare with). Right: page actions (`btn-quiet`, e.g. the overview's print button), the release chip + beta/sample tag (a `<details>` whose popover holds the full notice), and ไทย/EN on desktop. No search field, no breadcrumb trail, no lede paragraph.

### Sidebar (`SideNav`)
TCI logo above the product name and subline (44 px logo), then three groups with caption headings: แดชบอร์ด (five dashboards), แผนที่ (two maps), คำอธิบาย (/about). Each link: drawn icon + name, 42 px tall, 10 px pill; hover Canvas; current page TCI Blue Soft pill, TCI blue text 700, blue icon. The same content fills the phone drawer.

### Card (`Card`, `Section`)
The unit of every page. Head row: h2 title (16 px/700) + optional (i) on the left; optional action ("ดูทั้งหมด", `SeeAll`) on the right; 12 px under the head. Then the content: a chart, a ranked list, a fact list, prose. `Section` is the same card with an `id` for scroll targets (`scrollToId()`, never `href="#id"`). Pass `span` inside a `DashGrid`. A card renders only when its data exists (self-hiding); a missing module shows the page h1 with the reason, never a blank page. `.card-note` (caption, Ink Tertiary) at the card foot is for one short necessary fact, not an explanation.

### KPI card (`KpiRow` + `KpiCard`)
For the 3–4 key numbers at the top of a dashboard or detail page. Soft-blue 46 px circle with a drawn icon, the label (meta, Ink Secondary; (i) beside it when the figure needs explaining), the value (KPI value), then either the change since the previous release (caption 600, Up Green with ▲ or Ink Secondary with ▼; no arrow when the printed change is zero; the release compared with is said once in the page bar and repeated only for screen readers) or one short sub line (truncated to one line). A `<dl>`; each card is a dt/dd pair. Use KPI cards, not label/value lists, for headline numbers; secondary numbers go in a fact list card (`.facts`: label left, bold value + change right, Hairline rows).

### Ranked rows (`RankRows` + `MoreRows` / `usePaged`)
The shared list of every dashboard. A 26 px rank badge (first TCI blue with white digits, the rest TCI Blue Soft), the name as a link to its page (meta 600, one line, full name in `title`), a meta line (status chip, field), the value right-aligned (meta 700, tabular; growth in TCI blue, falls in Ink Secondary), an optional 56 × 24 sparkline (decorative; the number carries the fact; hidden under 480 px). `numbered={false}` drops the badge. Start with 6–10 rows; "แสดงเพิ่ม k (เหลือ n)" adds the next step, "แสดงน้อยลง" resets. Ranked bar lists (`BarRank`, `.br-row`) are the variant for amounts: name · 12 px TCI-blue bar on a Surface track · number.

### "ดูทั้งหมด" (`SeeAll`)
Text button/link in TCI blue (meta 600) with a 16 px arrow that nudges 2 px on hover over a Soft fill. Goes to the dashboard or detail page that has everything, or opens the full list in the right drawer. It is how detail is reached; cards never grow to show everything.

### Segmented switch (`Segmented`)
Two or three views of one card (กำลังมา / ลดลง; ข้อค้นพบ / สำหรับผู้วางนโยบาย; articles / per 100,000 people). Canvas track, 32 px buttons, the pressed one white with TCI blue text and the pressed-segment shadow; a labelled group of `aria-pressed` buttons, not tabs; the choice lives in the URL (`useUrlState`). Never a chart ⇄ table switch.

### Status picker (`/topics`)
Six buttons, one per status, each a card-like tile (14 px radius, card shadow): glyph + Thai name, count (KPI value), one-line meaning (hidden under 560 px). Pressed = 2 px TCI blue outline. 6 → 3 → 2 columns at 1280 / 560.

### Status chip and glyph (`StatusChip`, `StatusGlyph`)
Glyph (11–12 px) + Thai name on the tag background, caption 700, square corners. Use the chip wherever a status appears in a list or row (`TopicLink showStatus`); use the bare glyph only beside a written status name.

### (i) info popover (`InfoPop` via `Card info`, `Section intro`, `PageBar info`, `KpiCard info`)
The only place explanations live on a page: what the card counts, its years, how to read it, definitions. A 28 px Ink Tertiary icon button (hover/open: Canvas fill, TCI blue); opens on click/tap or Enter/Space, closes on Escape (focus returns) or a click elsewhere; 352 px wide panel (never wider than the screen minus 32 px), Paper, Hairline border, 12 px radius, Floating shadow, meta 1.6. Never hover-only. `Term` is the same popover for a glossary word inside running text.

### Drawer (`Drawer`)
Native modal `<dialog>`: focus is trapped, Escape and a backdrop click close it, focus returns to the opener. Right drawer (min(560 px, 94vw)) for a card's full list; left drawer (min(300 px, 86vw)) for the phone menu. Slides 24 px in over 220 ms (`cubic-bezier(0.16,1,0.3,1)`); no motion under reduced motion.

### Buttons
- **Primary** (`btn-primary`): TCI blue, white text, 40 px, 8 px radius; hover TCI Blue Deep. Rare: one per surface at most (the sidebar brief box).
- **Quiet** (`btn-quiet`): white, Hairline border, Ink text, 36 px, 8 px radius; hover border and text TCI blue. Page-bar actions (print / save PDF).
- **Icon** (`icon-btn`): 36 px transparent square, 10 px radius; hover Canvas. Close, menu (44 px).
- **Language switch**: pill track on Surface, pressed option white with TCI blue text.

### Charts inside cards (`Figure`)
`Figure` renders a quiet chart title (meta 600, Ink Secondary), an optional legend, the chart and an optional note; nothing else. Its older props (`table`, `how`, `csv`, `source`, `number`, `view`) are accepted and ignored. See Do's and Don'ts for the chart rules.

### Signature: the focus line (overview)
`StoryLines` in "หัวข้อที่โตเร็วที่สุด" (8 columns beside the 4-column moves list): every small fast-growing topic as a grey line, the one in focus TCI blue with an orange end dot, a direct label + value at each line end, one on-chart note. Pointing at or tabbing to a series moves the focus. Lines draw once on arrival (1100 ms ease-out-expo; drawn instantly under reduced motion). Left out on phones: the ranked list beside it carries the same topics with their trend lines.

### Maps
`ProvinceMap`: `seq-1…5` quantile classes, white province strokes, "no data" as a hatch (white with diagonal Rule lines), a key with every class range, and always a ranked list with numbers beside the map (top 5 on the overview, top 10 + every province by region on `/places`). Province outlines load only in lazy chunks. The `/atlas` terrain map and `/galaxy` are one board card each: a bar on top (status and layer chips on `/atlas`; year presets and the shown count on `/galaxy`, no drop-downs), a 340 px side column (the selected item, then a ranked topic list or the field list that doubles as the field filter) beside the map, and a foot with the key; under 1023 px the map comes first. Map keyboard hints are screen-reader-only (the page (i) says the same).

## Do's and Don'ts

### Do:
- **Do** open every page with one `PageBar`, then a `KpiRow` when the page has headline numbers, then `Card`/`Section` in a `DashGrid`; give each card a `span` and let it collapse by the table in Layout.
- **Do** make each card answer one question with a chart or a ranked list, and send the rest to "ดูทั้งหมด" (the matching dashboard or detail page, or the drawer).
- **Do** put every explanation (years, method, definitions) behind the (i) beside the page, card or KPI title; the full method lives on `/about`.
- **Do** show long lists as `RankRows` with "แสดงเพิ่ม" in steps of 6–10, names on one line with the full name in `title`; use `limit` on any `DataTable` that could be long.
- **Do** filter with buttons (`Segmented`, the status picker) or grouped lists (every province by region), with the state in the URL.
- **Do** draw new chart forms as SVG in `web/src/charts/`, with layout maths in a tested `.ts` file: labels ≥ 13 px (`--fs-caption`; ticks 12 px), ink + one TCI blue + greys, status colours only for statuses, no data as a diagonal hatch or dashed outline (never the lightest ramp step), direct labels over legends, and the numbers printed beside the chart (labels, a list, a key) so nothing is hover-only.
- **Do** show status as glyph + colour + Thai name, and pass `palette.test.ts` for any colour change.
- **Do** write on-page text in plain Thai (and English): short, example first ("เช่น …"), a unit on every number, years instead of windows ("ปี 2022–2024", "ใหม่ — ปี 2016–2020 ยังไม่มีงานเรื่องนี้"), Thai status names (กำลังเกิดใหม่ · จับตา · กำลังมาแรง · ลดลง · คงที่ · ข้อมูลน้อย); a necessary technical word is a `Term`.
- **Do** keep the 3 px TCI-blue focus ring (2 px offset) on every interactive element, a skip link, real landmarks (`nav`, `main`, `section` labelled by its h2) and `dl` for KPI and fact pairs.
- **Do** let a section shrink away when its data is missing; a page is never blank (`ErrorBoundary` in `Layout`, `ModuleFile` and skipped-module reasons).
- **Do** keep the overview printable as the two-page A4 executive brief: shell, drawer, (i) buttons, "ดูทั้งหมด" and switches hidden; cards become 1 px Hairline boxes packed into a dense 12-column grid (wide cards across, the rest in halves), root size 12.5 px.
- **Do** keep TCI · NECTEC · สวทช. logos in the footer and the TCI logo at the top of the sidebar/phone bar.

### Don't:
- **Don't** put chart ⇄ table tabs, "วิธีอ่าน", CSV download buttons, "ที่มา:" source lines or figure numbers ("แผนภูมิ n", "ตาราง n") on a page.
- **Don't** add a search box or search field anywhere (the e2e tests check).
- **Don't** explain in hover-only tooltips; the (i) opens by click, tap or keyboard.
- **Don't** add a dark theme or any second theme.
- **Don't** put an eyebrow or kicker label above a heading, a thick coloured side border on a card or row, or gradient text.
- **Don't** use a status colour for anything that is not a status, or show a status without its glyph and name.
- **Don't** colour context data blue, fill an area with orange, or put the logo orange (#f89020) on white as a mark or text.
- **Don't** set meaningful text under 13 px, use italics on Thai, or letter-space Thai.
- **Don't** add borders to cards or shadows to anything inside a card.
- **Don't** use in on-page text: ช่วงเชื่อมั่น, ช่วงฐาน, ช่วงล่าสุด, subfield, HHI, Jaccard, Jensen–Shannon, cosine, metadata, embedding, or status codes (EMERGING, LOW_DATA …) inside Thai sentences.
- **Don't** load fonts or anything else from a third-party server at runtime.
- **Don't** show abstracts or author names, or rank individual people.
- **Don't** use stock illustration, emoji, icon fonts, or the official SDG colours and icons.

### Retired (the "data explainer" world, 2026-10-23, replaced 2026-10-24)
These belonged to the previous world and are now banned or gone: the white top bar with a horizontal question-grouped menu; the question-as-h1 story hero with a one-sentence answer, a 52–56 px hero number and a byline; numbers standing on hairlines with no box (`StatTile` as the headline pattern); the 19 px body and large type scale; every chart's chart ⇄ table tabs, "วิธีอ่าน" (`HowNote`), CSV button, "ที่มา:" line (`SourceLine`) and figure numbers; the topic search field, `/search` and the pill search input; `StatusWaffle`, `DotPlot`, `StatusFlow`, `LineageKey`, `BridgePairs`, `Steps`, `PhoneFold` and `ShareBar`; the "Flat Page" rule (cards now carry one soft shadow). From the world before that: civic blue #0f3557, focus yellow, highlighter #ffe07a, 2 px heavy ink frames and the dark theme.
