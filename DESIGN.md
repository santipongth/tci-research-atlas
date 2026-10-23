---
name: TCI Research Atlas
description: แผนที่ภูมิทัศน์งานวิจัยไทย — a public statistical release of Thai research topics, quarter by quarter, in Thai and English.
colors:
  civic-blue: "#0f3557"
  civic-blue-dark: "#0a2238"
  link-blue: "#1a5bb0"
  link-blue-hover: "#0d3c7a"
  link-blue-dark: "#8bbaf6"
  link-blue-hover-dark: "#b9d5fb"
  focus-yellow: "#ffd43b"
  highlighter: "#ffe07a"
  ink: "#0b0c0e"
  ink-secondary: "#474e55"
  paper: "#ffffff"
  paper-tint: "#f3f4f5"
  rule: "#b1b4b6"
  rule-light: "#dcdee0"
  ink-dark: "#f3f4f5"
  ink-secondary-dark: "#b9bfc4"
  paper-dark: "#0f1214"
  paper-tint-dark: "#1a1e21"
  rule-dark: "#5f676d"
  rule-light-dark: "#2d3338"
  go-green: "#00703c"
  go-green-hover: "#005a30"
  status-emerging: "#13a08a"
  status-watch: "#c47a0c"
  status-hot: "#a3124f"
  status-declining: "#5b74cf"
  status-stable: "#6f777b"
  status-emerging-dark: "#2da78c"
  status-watch-dark: "#c37511"
  status-hot-dark: "#ad3678"
  status-declining-dark: "#5468da"
  status-stable-dark: "#7b8389"
  tag-emerging: "#d7f0e9"
  tag-emerging-ink: "#0a4a3e"
  tag-watch: "#fcebc9"
  tag-watch-ink: "#573700"
  tag-hot: "#f7dae5"
  tag-hot-ink: "#680b32"
  tag-declining: "#e1e6f8"
  tag-declining-ink: "#22326d"
  tag-stable: "#eceeef"
  tag-stable-ink: "#363d43"
  map-sheet: "#f6f7f4"
  map-sheet-dark: "#111618"
  contour-brown: "#9a6a35"
  contour-brown-dark: "#c48d4f"
  series-1: "#2a78d6"
  series-2: "#eb6834"
  series-3: "#1baf7a"
  series-4: "#eda100"
  series-1-dark: "#3987e5"
  series-2-dark: "#d95926"
  series-3-dark: "#199e70"
  series-4-dark: "#c98500"
  seq-1: "#e4edf6"
  seq-2: "#b9d0e8"
  seq-3: "#7ea8d4"
  seq-4: "#3f74b5"
  seq-5: "#123f7c"
  seq-1-dark: "#1b2a3a"
  seq-2-dark: "#24466d"
  seq-3-dark: "#2f67a3"
  seq-4-dark: "#4f8fd6"
  seq-5-dark: "#a6caf3"
typography:
  h1:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "clamp(2rem, 1.25rem + 2.4vw, 2.875rem)"
    fontWeight: 700
    lineHeight: 1.5
  h2:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "clamp(1.5rem, 1.25rem + 0.9vw, 1.875rem)"
    fontWeight: 600
    lineHeight: 1.5
  lead:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "clamp(1.25rem, 1.1rem + 0.6vw, 1.5rem)"
    fontWeight: 400
    lineHeight: 1.6
  body:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "1.1875rem"
    fontWeight: 400
    lineHeight: 1.65
  body-phone:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.65
  meta:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  caption:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 600
    lineHeight: 1.5
  numeric-tile:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "clamp(2rem, 1.5rem + 1.2vw, 2.5rem)"
    fontWeight: 700
    lineHeight: 1.5
    fontFeature: "tnum"
  numeric-hero:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "clamp(2.5rem, 1.6rem + 2.6vw, 3.5rem)"
    fontWeight: 700
    lineHeight: 1.5
    fontFeature: "tnum"
rounded:
  none: "0px"
  tag: "2px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  group: "24px"
  block: "40px"
  section: "64px"
  group-phone: "16px"
  block-phone: "28px"
  section-phone: "44px"
components:
  header-band:
    backgroundColor: "{colors.civic-blue}"
    textColor: "{colors.paper}"
    padding: "14px 30px"
  button-primary:
    backgroundColor: "{colors.go-green}"
    textColor: "{colors.paper}"
    rounded: "{rounded.none}"
    padding: "8px 16px"
    height: "44px"
  button-primary-hover:
    backgroundColor: "{colors.go-green-hover}"
    textColor: "{colors.paper}"
  button-focus:
    backgroundColor: "{colors.focus-yellow}"
    textColor: "{colors.ink}"
  link:
    textColor: "{colors.link-blue}"
  tab:
    backgroundColor: "{colors.paper-tint}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    height: "44px"
  tab-selected:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    height: "44px"
  chip-emerging:
    backgroundColor: "{colors.tag-emerging}"
    textColor: "{colors.tag-emerging-ink}"
    rounded: "{rounded.none}"
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
---

# Design System: TCI Research Atlas

## Overview

**Creative North Star: "The Public Statistical Release" (แถลงสถิติสาธารณะ)**

The Atlas reads like a statistics release from a national public body: a civic-blue header band, plain white pages, numbered figures and tables that can be cited, every chart paired with its table, every figure carrying a "ที่มา:" source line. That civic base runs on every page. Two signatures sit on top of it, each on one page only. The **Overview** opens with an editorial headline sentence whose figures are marked with a turmeric highlighter, and it shows growth honestly as a CI forest plot against the +10 %/yr bar. The **map page** (`/atlas`) is a topographic sheet: tinted field terrain with density contours, topics as settlements with A–J × 1–6 grid references, and a gazetteer that repeats every place in text.

Density is moderate and calm. Numbers are large and tabular, prose is short, and uncertainty is always visible (intervals, "แนวโน้มไม่แน่นอน", "ข้อมูลน้อย"). Thai and English are equal citizens; Thai sets the rhythm (Sarabun, generous line height, no italics).

**Key Characteristics:**
- Civic structure: header band, one compact notice line, page title + release metadata, "ในหน้านี้" rail, numbered figures/tables with source lines, a "what next" footer.
- Every chart has a Chart/Table tab; tables sort and become label/value cards on phones.
- Status is always glyph + colour + label (▲ ◆ ● ▼ ■ and a dashed ring).
- Flat, square-cornered surfaces; depth only for floating layers.
- One typeface (Sarabun) for everything.

## Colors

A sober civic palette — near-black ink on white, one deep blue for the institution, one link blue, one yellow that only ever means "keyboard focus" — plus a reserved six-colour status set and quiet terrain tints for the map.

### Primary
- **Civic Blue** (#0f3557; dark #0a2238): the header band, the drawer-style headers and the phase tag. It names the institution; never used for data.
- **Link Blue** (#1a5bb0; dark #8bbaf6): links, link-buttons, sort buttons, the 10 px rule under the header band, and the single-series trend line.

### Secondary
- **Focus Yellow** (#ffd43b): keyboard focus only (background + ink bar under links, outline + inset ink ring on controls). Also the skip link.
- **Turmeric Highlighter** (#ffe07a; dark rgba(214,150,20,.42)): the lower-half band behind figures and topic names in the Overview headline sentence. Nowhere else.
- **Go Green** (#00703c, hover #005a30): the primary action button ("ดูบทความใน ThaiJO", downloads) and positive KPI deltas (#00703c light, #4cc38a dark).

### Neutral
- **Ink** (#0b0c0e; dark #f3f4f5): text, axes, table header rules (2 px), form-field borders.
- **Ink Secondary** (#474e55; dark #b9bfc4): secondary text, source lines, tick labels.
- **Paper** (#ffffff; dark #0f1214) and **Paper Tint** (#f3f4f5; dark #1a1e21): page and panel backgrounds (findings, inactive tabs, footer, uncertain box).
- **Rules** (#b1b4b6 and #dcdee0; dark #5f676d and #2d3338): borders and row dividers. Decorative only — interactive boundaries use Ink.

### Status (reserved)
EMERGING #13a08a / dark #2da78c · WATCH #c47a0c / #c37511 · HOT #a3124f / #ad3678 · DECLINING #5b74cf / #5468da · STABLE and LOW_DATA #6f777b / #7b8389. Tag pairs (background / ink) are in the frontmatter; dark tags: EMERGING #12372f/#a3e6d2, WATCH #3d2a07/#f6d08c, HOT #3f1427/#f4aecb, DECLINING #1d2649/#bcc8f6, STABLE #262b2f/#d5d9dc, LOW_DATA uses the page background with a 1 px rule ring.

### Map
Map sheet #f6f7f4 / dark #111618; contour brown #9a6a35 / #c48d4f; grid rgba(11,12,14,.09) / rgba(226,233,229,.07); unnamed-topic dots rgba(11,12,14,.42) / rgba(226,233,229,.38). Field tints `cat-01…cat-12` (light → dark): #e8b5a6→#5b3229, #dbc99d→#4d4329, #c3d59c→#39492a, #e8d095→#544423, #a8d1a4→#284732, #b1c4da→#293c52, #d4bad6→#46314c, #9ccfca→#1f4746, #bfd8e8→#213f50, #e3bfcd→#4e2e3a, #cfd3a6→#3f4425, #d9cbb8→#463d31.
Fallback groups (`G…`, in a release that also has OpenAlex fields) take the neutral `--dot` tint (#c7cbce / #3b4247) instead of a `cat-*` colour, so they never read as a real field.

### Series (compare only)
series-1…4 = #2a78d6, #eb6834, #1baf7a, #eda100 (dark #3987e5, #d95926, #199e70, #c98500) — the dataviz reference order, validated as adjacent pairs; always with a dash pattern and a direct label.

### Sequential (one blue)
seq-1…5 = #e4edf6, #b9d0e8, #7ea8d4, #3f74b5, #123f7c (dark #1b2a3a → #a6caf3, light to strong reversed for the dark page). One hue for quantities that are not statuses: the province choropleth, the parts of a mix bar (largest = seq-5, "อื่น ๆ" = Paper Tint with a rule ring), the dominant part of a split bar and the shaded zone of the quadrant/scatter charts.

### Named Rules
**The Reserved Status Rule.** The six status colours mean status and nothing else; a status is never shown by colour alone — glyph + colour + label, every time.
**The Yellow Means Focus Rule.** A full yellow background appears only on the focused element. The headline highlighter is a lower-half band, never a full fill.
**The Token-Only Rule.** Components use `var(--token)`; a hex value in a component is a bug. Group colours arrive from the data as token keys (`cat-07`), never hex.
**The Terrain Is Not Data Rule.** Field tints are background terrain; fields are always named by labels and in the gazetteer, so tint repetition beyond 12 groups is harmless.

## Typography

**Display / Body / Label Font:** Sarabun (with Noto Sans Thai, Leelawadee UI, system-ui), self-hosted woff2, Thai + Latin subsets, weights 400/600/700.

**Character:** Sarabun descends from TH Sarabun, the standard face of Thai government documents — familiar, plain and legible in both scripts; one family keeps the release sober.

### Hierarchy
Six text steps and two numeric display steps — nothing else. Tokens live in `web/src/styles/tokens.css` (`--fs-*`); components never set a raw size.
- **h1** (700, `--fs-h1` clamp 32 → 46 px): the page `h1`, max 34ch.
- **h2** (600, `--fs-h2` clamp 24 → 30 px): section headings.
- **Lead / h3** (400–700, `--fs-lead` clamp 20 → 24 px): the lede under the h1 (max 32em), h3, footer headings.
- **Body** (400, `--fs-body` 19 px; 17 px under 641 px, 1.65): prose, figure titles, table captions, max 38em.
- **Meta** (400–700, `--fs-meta` 16 px): secondary text, source lines, table cells, buttons, notes, the notice line. The floor for anything that carries meaning on its own.
- **Caption** (600–700, `--fs-caption` 14 px): chips and tags, tab counts, CI ranges under a value, field sub-names, stacked-table labels, the licence line. Never smaller.
- **Numeric tile** (700, `--fs-tile` clamp 32 → 40 px, tabular): KPI values, status counts, and the Overview headline sentence (24 px on phones).
- **Numeric hero** (700, `--fs-hero` clamp 40 → 56 px, tabular): at most one hero number per page.
- SVG axis ticks and edge values use `--fs-tick` (13 px); chart labels that carry meaning (point, end, map and quadrant-count labels) use `--fs-caption` (14 px) and names `--fs-meta` (16 px). Code that measures label boxes reads the same numbers from `web/src/lib/labelSizes.ts`. Axis labels never repeat: decimals follow the tick step (`tickDecimals`), and a repeated label is blanked.

Line height: Thai body 1.65, Thai headings ≥ 1.45 (1.5 by default); English headings close up to 1.3 through `:lang(en)` (the stylesheet test allows < 1.5 only for English-only rules). Highlighted figures and topic names in the headline sentence are atomic (`display: inline-block`): the sentence wraps between them, never inside one, unless a single name is longer than a line.

### Named Rules
**The Upright Thai Rule.** Thai has no true italic: `em`, `i`, `cite`, `dfn`, `var`, `address` render upright; emphasis is weight 600/700. No letter-spacing and no case transforms on Thai — English-only caps use `[lang="en"]`.
**The Arabic Numerals Rule.** Both languages use Arabic digits with en-US grouping (248,310), the true minus sign (−), and Gregorian years (ค.ศ.), matching the data.

## Layout

A 1200 px max container with 16 px gutters on phones and 30 px from 900 px. Reading pages use a two-thirds column plus a 240 px "ในหน้านี้" rail; under 900 px the rail moves above the content and "ในหน้านี้" folds into one closed disclosure row (44 px). `/atlas` uses the full container: map sheet plus a 320 px side column (key, layers, selection) from 1100 px, stacked below on smaller screens. Breakpoints: 640 (phone ↔ tablet; tables stack into label/value cards; body 17 px), 900 (navigation folds into the menu; rail above content), 1100.

**Rhythm** (`--sp-*`): group 24 px (heading to content, related blocks) · block 40 px (figures and sub-blocks; the page header's top) · section 64 px (between sections; above the footer). Phones: 16 / 28 / 44. Section `h2`s have 8 px below them and a full section step above. **Measure** (`--measure-*`): lede 32em, body 38em (about 60–75 characters a line at 1440 px), headline 30ch. No horizontal page scroll at 360 px.

**Targets:** every control is 44 px; standalone links (list items, table links, DOI and journal links, search result titles, footer links) get at least 24 px from their own line box (`inline-block` / `min-height`), never by shrinking text. Links inside a sentence are exempt.

## Elevation & Depth

Flat by default: depth comes from borders, tints (Paper Tint panels) and the header band. A single shadow (`0 8px 28px rgba(11,12,14,.18)`, dark `rgba(0,0,0,.6)`) is used only for floating layers: the tooltip, the search listbox and the map's zoom control.

### Named Rules
**The Flat Page Rule.** Cards, KPI tiles and tables never cast shadows; if something floats, it is temporary.

## Shapes

Square corners everywhere (0 px): buttons, tabs, chips, panels, inputs. The only rounding is 2 px on map grid-reference tags. The header band ends with a 10 px Link Blue rule; tables have a 2 px Ink header rule and 1 px Rule Light row dividers; KPI tiles have a 1 px Rule border.

## Components

### Header band and navigation
Civic Blue band: the wordmark (temporary "TCI" box + name + Thai subtitle; the official logo swaps in at `web/src/brand/brand.ts`), language switch (two pressed-state buttons) and theme toggle (44 px, 2 px white outline). From 900 px, a white navigation row follows: text links (current page: 4 px Link Blue underline, `aria-current="page"`), the four question disclosure groups, and the topic search — on the same row from 1280 px when it fits (tighter link padding, search at least 180 px), otherwise wrapped under the links. Under 900 px the band holds only the wordmark (subtitle hidden under 421 px) and one **"เมนู / Menu"** button (same outline language; filled while open; drawn three-line / cross icon) with `aria-expanded` + `aria-controls="site-nav"`. It opens the navigation in flow below the band (no overlay, no scroll lock): the topic search first, then every page as a 44 px row — the question groups become labelled lists (no nested disclosures; the hint lines are desktop-only) — then the language and theme buttons in ink. Escape closes it and returns focus to the button; choosing a page closes it. Phone chrome budget: the band, the closed menu button and the one notice line together keep the page `h1` and its first number above 400 px at 390 px wide (the e2e test `narrow.spec.ts` holds the overview `h1` under 300 px); "ในหน้านี้" stays a closed row under 900 px and supporting step diagrams fold (`PhoneFold`).

**Page names** are plain words, not method words (`web/src/strings/*` `nav.*`): top-level ภาพรวม · สรุปผู้บริหาร … ข้อมูลเปิด · **อ่านตัวเลขอย่างไร** / How to read the numbers (`/about`, was "วิธีการและนิยาม"). Between them the menu is grouped by **the question a reader brings, not by who they are** (owner's ruling 2026-10-23, replacing the P1/P3 persona groups): **อะไรกำลังมา** / What's coming — สถานะหัวข้อ · แนวโน้มคำสำคัญ · อะไรเปลี่ยน · **โอกาสที่ยังไม่มีใครทำ** / Untapped opportunities (`/gaps`, was "ช่องว่างงานวิจัย"); **ใครทำเรื่องอะไร** / Who works on what — สถาบัน · วารสาร · วิธีวิจัย · การอ้างอิง; **ไทยอยู่ตรงไหน** / Where Thailand stands — แผนที่จังหวัด · ไทยเทียบโลก · SDG และแผนชาติ; **หางานวิจัย** / Find research — ค้นหาบทความ · แผนที่หัวข้อ · **แผนที่บทความทุกเรื่อง** / Map of every article (`/galaxy`, was "กาแล็กซีบทความ") · เปรียบเทียบ · วางบทคัดย่อ. In the desktop menu each page name carries one plain hint line (`nav.hint.*`, 16 px ink-2, the link's `aria-describedby`, not part of its name) saying the question that page answers, e.g. สถานะหัวข้อ — "เรื่องไหนกำลังโต เรื่องไหนลดลง". Routes did not change.

### Notice line
One compact line under the navigation (a `<details>`): the Civic Blue "รุ่นทดลอง" tag, the WATCH-tinted "ข้อมูลตัวอย่าง" tag on test releases (visible on every page), one short sentence and a "รายละเอียด" toggle; the full beta and sample-data texts open beneath with a 4 px rule. The data error banner (`role="alert"`) is separate and never folded.

### Buttons
- **Shape:** square, 44 px tall.
- **Primary:** Go Green fill, white 700 text, 2 px darker bottom edge (#002d18).
- **Hover / Focus:** hover #005a30; focus = yellow fill, ink text, ink bottom edge.
- **Secondary:** 2 px Ink outline on Paper, 600 text; pressed state = Ink fill, Paper text.

### Chips (status tags)
Square tag with the status glyph, tinted background and dark ink (≥ 8:1). Small variant for tables and tooltips. LOW_DATA uses a 1 px rule ring and a dashed glyph.

### Tabs
ARIA tabs: Paper Tint inactive tabs, the selected tab joins its bordered panel (Paper, 1 px Rule). Arrow keys, Home and End move between tabs. Status tabs (`/emerging`) stay on one line on phones and scroll sideways, with a paper-coloured fade at the right edge as the overflow hint. A figure's "แผนภูมิ / ตาราง" switch is a segmented pair in its caption row (2 px Ink outline, the selected half Ink-filled); a figure that sits inside another tab panel uses pressed buttons (`aria-pressed`) instead of a nested tablist.

### Tables
Caption numbered "ตาราง n:", 2 px Ink header rule, right-aligned tabular numbers, sortable headers as link-blue buttons with an up/down glyph and `aria-sort`; units sit in the header in Ink Secondary ("สัดส่วน (%)"), and headers balance onto at most two lines. A small secondary "ดาวน์โหลด CSV" button (1 px Ink outline, download icon) sits above every data table; what the numbers in the file mean ("0.10 = 10%") is its tooltip and accessible description, never a note under every button. Wide tables mark 3–4 **main columns** (`primary`): the rest hide behind "แสดงทุกคอลัมน์ (n)", the sorted column always shows, and the CSV always has every column. Under 640 px rows become two-column label/value cards (`data-label`) showing the main fields with a "เพิ่มเติม" toggle per row. Long lists pass `limit`: the first n rows in the current order, then "แสดงทั้งหมด (n)" (the CSV still has every row). A table outside a `Figure` ends with `SourceLine` (the same "ที่มา: … · รายละเอียด" line). Interval cells are text first ("+101.4% ถึง +129.4%", Caption, Ink Secondary) with a 128 px whisker under them; a whisker narrower than 96 px is not drawn.

### Figures
One caption row over a 2 px Ink rule: "แผนภูมิ n: …" (or the table's "ตาราง n: …" in the table view) on the left; the chart/table switch, a "วิธีอ่าน" disclosure (opens a Paper Tint panel under the row: the encoding in words, then "คำที่ใช้:" glossary terms) and the CSV button on the right. Then the legend (glyph + label; the status legend may add each status's one-line meaning), the chart, and the short source line "ที่มา: TCI Research Atlas · รอบ {release} · รายละเอียด", where "รายละเอียด" opens a popover with where the figures come from and the status definition version (printed inline only in the brief and the embeds).

### Stat tiles
Key figures are tiles, never label/value lists: a 1 px Rule border on Paper, a plain Meta 600 label, the value at Numeric tile (a long text value such as "ใหม่ — ปี 2016–2020 ยังไม่มีงานเรื่องนี้" drops to Lead), then optionally the change vs the previous release (Go Green up / Ink Secondary down, with an arrow), an ink-only 120 × 28 sparkline (2 px Ink Secondary line, Ink end dot, aria-hidden, the yearly numbers in screen-reader text), one Meta line of context, and a "เช่น …" example under a hairline. Grids of 2, 3 or 4 columns (2 on phones); a `wide` tile spans two columns (the whole row on phones; `wide="phone"` only there), and tiles are ordered so no row ends with one tile beside an empty cell. A whisker inside a tile fits the tile (`FitCiWhisker`). The Overview shows four tiles and folds the rest under "ดูตัวเลขเพิ่ม (n)".

### Glossary terms
Jargon in running text is a `Term`: the word with a dotted underline; pressing it (button, `aria-expanded`) opens a popover right below it (2 px Ink border, the floating shadow) with the term in bold and a plain definition, example first, its figures (interval level, baseline and recent years) from the release. Escape closes and returns focus, a tap or click elsewhere closes, nothing opens on hover. Definitions load as their own small chunk.

### Inputs / search
2 px Ink border, square, 44 px; focus = 3 px yellow outline + inset ink ring. The topic search is an ARIA combobox with a floating listbox (shadow) showing glyph, name and the other-language name.

### Banners and notices
Notice line: see above. Error banner (`role="alert"`): 4 px left rule in HOT ink on Paper Tint, a bold reason and what to do. Uncertain box ("แนวโน้มไม่แน่นอน"): 4 px left Rule on Paper Tint. WATCH inset: 2 px WATCH border on the WATCH tag background.

### Editors' pages (P2)
Share bars: 64 × 8 px, `--ink-2` fill on `--surface` with a 1 px inset rule, the number always printed next to the bar (the bar never carries the value alone). Text marks (`.flag`): 1 px ink border, no fill, bold small text: "อนุมาน / inferred", "สูงกว่าเกณฑ์ / above the bar", "วิธีกระจุก / narrow methods" — never colour alone. Journal name rule: registry name; else the other language's name with `lang`; else the OJS name followed by "ยังไม่มีชื่อเต็มในทะเบียนวารสาร". Paste box (`/match`): the privacy note first, set on a Paper Tint strip with the brand rule, one labelled 12 rem textarea, primary + secondary buttons, and the results heading takes focus after a search. A page whose module is not in the release, or was left out of the offline file, shows its h1 and an empty state saying why (never a white page, never `role="alert"`).

### Executives' pages (P3)
Grouped navigation (from 900 px): four question disclosure buttons (อะไรกำลังมา / ใครทำเรื่องอะไร / ไทยอยู่ตรงไหน / หางานวิจัย) between the top-level links — a disclosure pattern, not an ARIA menu. Buttons and menu items are at least 44 px high (an item is the page name over its hint line); a menu that would cross the right edge opens leftwards (`.is-flipped`, measured on open because the row wraps differently at each width); the group holding the current page carries the 4 px link-blue underline (inside the menu, the current item an inset 4 px rule); Enter or Space toggles, Escape closes and returns focus to the button, leaving the group or choosing a page closes it. Under 900 px the same groups are labelled lists inside the phone menu. Sequential ramp `--seq-1…--seq-5` (one blue hue; light and dark values in tokens.css) for the province choropleth: 5 quantile classes, "no data" is a hatch (paper with diagonal rule lines; never a ramp step, so the lowest class never reads as missing), province strokes are `--bg`. Choropleth rule: the table view is complete and the map never carries a number alone — a legend with the range of every class, a title (hover) naming province and value, and chart ⇄ table tabs like every figure; the measure switch (articles / per 100,000 people) is a radio group. `.flag-on` marks a concentrated unit: 2 px ink border, bold small text "กระจุกตัว / Concentrated" beside the share bar. Possible partners (R6) are worded as a suggestion from the data — similarity and shared topics shown, never a ranking and never an endorsement; signals on /gaps are questions to explore, not verdicts.

### Footer ("what next")
Paper Tint band, a section step below the content. "ทำอะไรต่อ / What next" (Lead) over four next steps in a row (2 columns under 900 px, 1 under 481 px), each a 2 px ink top rule, a bold Body link and one Meta hint: อ้างอิง Atlas (opens `/about` and scrolls to its cite section through route state — never `href="#id"`), ดาวน์โหลดข้อมูล (`/data`), รอบก่อนหน้า (`/changes`), อ่านตัวเลขอย่างไร (`/about`). Then the one-sentence description of the data with the release line, and one Caption licence line: CC BY 4.0 · ไม่จัดอันดับบุคคล (PDPA) · the temporary-wordmark note.

### Headline sentence (signature, Overview only)
The release's brief headline at the Numeric-tile size (600; 24 px on phones), figures and topic names under the turmeric lower-half band (topic names are links), followed by a small note that the sentence was generated automatically from the system's figures (template or AI, numbers checked).

### CI forest plot (signature, Overview and /emerging)
One row per topic: name (+ field, 24 % of the width) | whisker on a shared axis (at least 55 % of the width) | value with its interval (9 rem). The whisker is the interval at `manifest.ci_level`, capped (arrow when clipped), with the status glyph at the estimate; a dashed vertical line marks the +10 %/yr EMERGING bar and a solid line marks zero. Grouped by status with each group's rule in one sentence.

### Terrain map (signature, /atlas only)
Canvas terrain on the map sheet: field tints by density, contour brown lines (every third line heavier), faint 10 × 6 grid with A–J / 1–6 references on the frame edges, unnamed topics as dots. EMERGING/WATCH/HOT/DECLINING topics are focusable SVG glyphs with grid references; labels have a sheet-colour halo and never collide. Layer toggles (statuses, contours, tints, names), zoom buttons (+, −, reset), drag to pan, Ctrl + wheel to zoom; nothing requires dragging. The gazetteer repeats every signal-status topic in text; other topics are found with search. On phones the sheet takes a taller aspect, the top-N names stay visible, and an "อ่านแผนที่นี้ใน 3 ขั้น" `Steps` diagram explains the reading order.

### How notes (layer 2 outside a figure)
`HowNote` is the section-level twin of a figure's "วิธีอ่าน": a `<details>` with the "วิธีอ่าน" summary holding the method fine print (rules with their numbers, data caveats). Use it when a section has no `Figure` of its own; never put layer-2 text in a lede.

### Finding cards and topic hero
- **Finding cards** (`pages/overview/FindingCards.tsx`, Overview + brief): "3 เรื่องสำคัญรอบนี้", one card per finding — what it is (Meta 600), one big number at Numeric tile with its likely range under it in Caption, the example topic as a link, one plain sentence, and the topic's articles a year as an ink `Sparkline` with its first and last year. Every number from the release; renders nothing without findings.
- **Topic hero** (`/topics/:id`): status chip with its one-line meaning, one plain growth sentence, the growth with its likely range (the growth word is a `Term`) and a fitted whisker, beside two `StatTile`s with sparklines (share of articles, articles in the recent years); the top representative article follows as "เช่น …". Journals and institutions below are `BarRank`s with table tabs.

### Steps and phone folds
`Steps` is a short numbered sequence (3–4) whose order carries meaning: a row joined by a rule on wide screens, a vertical list on phones, square 36 px number boxes (2 px ink), optional small drawing and a `foot` (e.g. the statuses a step decides); `current` marks one step (`aria-current="step"`). Used for "อ่านแผนที่นี้ใน 3 ขั้น" (`/atlas`), the emerging steps (`/emerging`), the pipeline diagram and the status decision path (`/about`), and the three steps of `/match` (current step marked). `PhoneFold` turns a supporting section (a step diagram) into one closed disclosure under 760 px so the page's own content comes first; from 760 px it is an ordinary section with its h2.

### Infographic kit (`web/src/charts/`)
Quiet, realistic marks built from the tokens — no stock illustration, no emoji, no official SDG colours or icons. Layout maths lives in pure, unit-tested files (`charts/infographic.ts` waffle/dot/rank; `charts/execLayout.ts` arcs, column axis, mix segments, quadrant + label placement, status flow, goal tiles; `charts/editorLayout.ts` journal scatter, then-vs-now mix, checklist states, keyword risers, galaxy picks, weighted mean); the `.tsx` files only draw. Rules for every form:
- **Table alternative:** each sits inside a `Figure` (or beside a full table) whose table tab has every number; marks are decorative where the numbers are printed next to them (`aria-hidden`), otherwise the SVG has `role="img"` and a sentence `aria-label`.
- **Labels ≥ 14 px:** names and values at `--fs-caption`/`--fs-meta` (code measures with `LABEL_PX` 14/16); only axis ticks use `--fs-tick` 13 px. Labels never overlap a mark or each other (`placeLabels`); on phones fewer are named, the rest are in the tooltip and table.
- **Status = glyph + colour + name**, everywhere a status appears (waffle rows, dot plot marks, flow nodes); status colours are used for nothing else.
- **Ink + one blue** for quantities that are not statuses: bars are `--ink-2`, mixes and zones use the `--seq-*` ramp, SDG/plan tiles are ink with one blue share bar.
- **No data is a hatch or a dashed outline**, never the lightest ramp step (province map hatch, dashed empty goal tile, dashed checklist box, dashed bridge link).
- **No hover-only information:** hover/focus only highlights or repeats; every value is printed, in the key or in the table. Placed in percent where possible, so charts reflow and print without measuring.

| Component | Purpose · when to use | Key rules |
|---|---|---|
| `StatusWaffle` | Every topic by status, one square per topic (Overview, brief). | One row per status: glyph, name, count, % of all topics in text (+ the plain meaning, not in `compact`). Squares aria-hidden; LOW_DATA squares are a dashed outline; pointing shows the topic, pressing opens it. |
| `DotPlot` | Top movers on one axis (the printed brief, where a forest plot is too dense). | Name \| status glyph at the estimate joined to zero by a hairline \| value with its range in text. Solid zero line, dashed `refValue` line (the emerging bar) with its label. |
| `BarRank` | Short ranked lists (a topic's journals and institutions, countries and institutions, methods, top provinces beside the map). | Ink bar scaled to the largest, the number always printed; names link when `href` gives a path; under 640 px bar and number sit under the name. |
| `ArcNetwork` | Institution collaboration (`/institutions`). | Institutions as HTML rows (wrap, link), each pair as an arc; stroke width and the number at the peak = joint articles. Deterministic, max 10 nodes; pointing or focusing a row highlights its arcs. Table tab lists every pair. |
| `ColumnChart` | One value per year on a zero baseline (`/institutions/:id`). | `--ink-2` columns, recessive gridlines, numbers on first, latest and largest column; every column's figure in the hover tooltip and in the table; sparse labels under ~40 px per column (latest always kept). |
| `MixBar` / `SplitBar` | A 100 % split: an institution's topic mix (`/institutions/:id`) / reliance on one source (`/gaps` concentration, `/references`). | Mix: largest first, "อื่น ๆ" last, one blue dark→light, 2 px paper gaps, key repeats every part with its number. Split: dominant part vs the rest with a dashed threshold marker; the share printed beside. |
| `OpportunityQuadrant` | World growth × Thai activity per subfield (`/global`, `/gaps`). | Linear axes, dashed reference lines at 1 ("เท่าโลก" / "โลกไม่โต"), the shaded top-left zone from the data file's thresholds; dots in the criteria filled blue, the rest hollow ink; opportunities labelled first; key under the chart. |
| `StatusFlow` | Status transitions since the previous release (`/changes`). | Previous status left, current right (glyph + name + count both sides); one band per transition, thickness = topics, tinted with the new status; pointing names the topics; table tab lists every change. |
| `LineageKey` | The four ways a topic changes: ใหม่ / รวม / แยก / ไม่มีแล้ว (`/changes`). | Ink-dot before → after drawing, name, one-line meaning, this release's count. |
| `GoalTiles` | 17 SDGs and each national framework (`/sdg`). | Goal number, Thai name, topic count as the big number, a share bar with the % printed; a tile with topics opens in place (native `<details>`, full row while open) to list them; a goal with no topic is a dashed outline that says so. |
| `BridgePairs` | Topic pairs close in content but not yet worked on together (`/gaps`); `directed` for citing → cited (`/references`). | Topic — link — topic; the link labelled with institutions working on both (dashed when none) and the closeness under it; side by side wide, stacked on phones. |
| `JournalScatter` | Complete records × in-house share per journal (`/journals`). | x 0–100, y share; the band above the in-house bar shaded and named; inferred owners hollow; largest journals and those above the bar named; every journal in the tooltip and the table. |
| `PeriodMix` | A journal's change of course: then vs now (`/journals/:id`). | Two 100 % bars (earlier years over recent years), same topics, same order, same shade; the key repeats both shares and the change ("+9 จุด"). |
| `ChecklistBars` | Which record fields a journal fills (`/journals/:id`). | Drawn ✓ / partial / ✗ / dashed-unknown box **and its word**, the field, a bar of the share, the share; the table has the counts. |
| `SmallMultiples` | Compare 2–4 topics without a tangle (`/compare`, lazy). | One panel per topic on the same vertical scale, own line in its series colour + dash, the others as faint grey context, first/last year, latest value printed at the end. |

`ForestPlot`, `PortfolioMatrix`, `TrendChart` and `MultiLineChart` keep their earlier specs; tick decimals follow the step (`tickDecimals`) so no axis repeats a label.

## Copy voice (น้ำเสียงของข้อความ)

The reader is an ordinary citizen first; the researcher and the executive read the same words. Strings live in `web/src/strings/*.ts` (lazy pages: their own file read with `useStrings`), always `th` + `en`.
- **Two layers.** Layer 1 (headings, ledes, column headers, chart titles, cards, tooltips): one short plain sentence, **example first** ("เช่น …"), numbers filled from the data with a unit on every number. Layer 2 (the exact rule, the method, the statistics word): behind a figure's "วิธีอ่าน", a `HowNote`, or a `Term` popover — never in layer 1.
- **Banned in layer 1:** ช่วงเชื่อมั่น, ช่วงฐาน, ช่วงล่าสุด, ฐานเปรียบเทียบ, เกณฑ์ความกว้าง, subfield, HHI, Jaccard, Jensen–Shannon, cosine, metadata, embedding, and the status codes (EMERGING, LOW_DATA …) inside Thai prose. Say instead: "น่าจะอยู่ระหว่าง {lo} ถึง {hi}" / "likely between", "สาขาย่อย", "ข้อมูลบทความครบ", "เนื้อหาใกล้กัน (เต็ม 1)". The glossary (`lib/glossary.ts`: ci, baseline, recent, shareGrowth, score, hhi, jaccard, jsd, cosine, activity, metadata, embedding) is where these words are explained.
- **Years, not windows:** write the years ("ปี 2017–2021 → ปี 2022–2024", "ใหม่ — ปี 2016–2020 ยังไม่มีงานเรื่องนี้"), never "ช่วงฐาน / ช่วงล่าสุด"; the years come from `definition.ts` / the release. A release code is explained where it is shown ("2026Q4 (ออกไตรมาส 4 ปี 2026)").
- **Thai status names** (web and pipeline): กำลังเกิดใหม่ · จับตา · **กำลังมาแรง** · **ลดลง** · คงที่ · ข้อมูลน้อย (English: Emerging · Watch · Hot · Declining · Stable · Low data), each with its one-line meaning (`stat.mean.*`: เล็กแต่โตเร็ว · โตเร็ว แต่มาจากไม่กี่วารสารหรือสถาบัน · ใหญ่และยังโต · สัดส่วนบทความลดลงชัดเจน · ยังไม่เห็นการเปลี่ยนแปลงชัด · บทความยังน้อยเกินจะสรุป). Definitions and `definition_version` 3 did not change — only the words that explain them; rule texts read their numbers from `definition.ts`.
- **Signals are questions, not verdicts** (/gaps, /global, possible partners); automatic sentences say so ("ระบบเขียนประโยคนี้จากตัวเลขในหน้านี้").
- The pipeline follows the same voice for every public sentence (template sentences pass `narrative.jargon_in`; the narrative/brief/method prompts carry the same banned list).

## Do's and Don'ts

### Do:
- **Do** pair every chart with a table tab, a numbered caption and a "ที่มา:" source line.
- **Do** show uncertainty: intervals at `manifest.ci_level`, "แนวโน้มไม่แน่นอน" when a forecast is not shown, "ใหม่ — ปี {base} ยังไม่มีงานเรื่องนี้" (the baseline years) when the baseline window had no articles.
- **Do** keep body line-height at 1.65 and text measure ≤ 38em; set sizes only from the `--fs-*` steps and spacing from `--sp-*`.
- **Do** read colours from tokens and group colours from `cat-NN` keys.
- **Do** keep 44 px controls and the yellow focus treatment on every interactive element.
- **Do** lead with an example and plain words (Copy voice); put the exact rule behind "วิธีอ่าน", `HowNote` or a `Term`.
- **Do** build new chart forms from the infographic kit's rules: table tab, labels ≥ 14 px, ink + one blue, hatch or dashed outline for no data.

### Don't:
- **Don't** use italics, letter-spacing or uppercase on Thai text.
- **Don't** use a status colour for anything that is not a status, or a status without its glyph and label.
- **Don't** fill a background with yellow except for keyboard focus.
- **Don't** add shadows to cards, tiles or tables, or round their corners.
- **Don't** load fonts or anything else from a third-party server.
- **Don't** show abstracts or rank individual people.
- **Don't** put information only in a hover or only in colour, or jargon and status codes in a heading, lede or column header.
- **Don't** use the official SDG colours or icons, stock illustration or emoji.
