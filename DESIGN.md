---
name: TCI Research Atlas
description: แผนที่ภูมิทัศน์งานวิจัยไทย — a quarter-by-quarter data explainer of Thai research topics, in Thai and English.
colors:
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
  orange-mark: "#e07000"
  context-grey: "#b9bdcc"
  up-green: "#0b6b46"
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
  display:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "clamp(2.25rem, 1.3rem + 3vw, 3.25rem)"
    fontWeight: 700
    lineHeight: 1.45
  h1:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "clamp(2rem, 1.2rem + 2.6vw, 3rem)"
    fontWeight: 700
    lineHeight: 1.45
  h2:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "clamp(1.5rem, 1.25rem + 0.9vw, 1.875rem)"
    fontWeight: 700
    lineHeight: 1.5
  lead:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "clamp(1.25rem, 1.1rem + 0.6vw, 1.5rem)"
    fontWeight: 400
    lineHeight: 1.65
  body:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "1.1875rem"
    fontWeight: 400
    lineHeight: 1.7
  body-phone:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.7
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
    lineHeight: 1.45
    letterSpacing: "-0.02em"
    fontFeature: "tnum"
  tick:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    fontFeature: "tnum"
rounded:
  bar: "3px"
  control: "8px"
  segment: "10px"
  panel: "12px"
  pill: "999px"
spacing:
  group: "24px"
  block: "40px"
  section: "88px"
  group-phone: "16px"
  block-phone: "28px"
  section-phone: "56px"
  gutter-phone: "16px"
  gutter: "30px"
components:
  button-primary:
    backgroundColor: "{colors.tci-blue}"
    textColor: "{colors.paper}"
    rounded: "{rounded.control}"
    padding: "8px 20px"
    height: "44px"
  button-primary-hover:
    backgroundColor: "{colors.tci-blue-deep}"
    textColor: "{colors.paper}"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "4px 16px"
    height: "42px"
  button-secondary-pressed:
    backgroundColor: "{colors.tci-blue}"
    textColor: "{colors.paper}"
  view-switch:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-secondary}"
    rounded: "{rounded.segment}"
    padding: "3px"
  view-switch-selected:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.tci-blue}"
    height: "36px"
  input-search:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "6px 14px 6px 40px"
    height: "44px"
  language-switch:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-secondary}"
    rounded: "{rounded.pill}"
    padding: "3px"
  language-switch-selected:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.tci-blue}"
    height: "38px"
  nav-link:
    textColor: "{colors.ink}"
    padding: "0 12px"
    height: "52px"
  nav-link-current:
    textColor: "{colors.tci-blue}"
  notice-tag:
    backgroundColor: "{colors.tci-blue-soft}"
    textColor: "{colors.tci-blue}"
    rounded: "{rounded.pill}"
    padding: "1px 10px"
  notice-tag-sample:
    backgroundColor: "{colors.tag-watch}"
    textColor: "{colors.tag-watch-ink}"
  stat-value:
    textColor: "{colors.ink}"
    typography: "{typography.numeric-tile}"
  story-number:
    textColor: "{colors.tci-blue}"
    typography: "{typography.numeric-hero}"
  panel-soft:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.panel}"
    padding: "16px 20px"
  chip-emerging:
    backgroundColor: "{colors.tag-emerging}"
    textColor: "{colors.tag-emerging-ink}"
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
---

# Design System: TCI Research Atlas

## Overview

**Creative North Star: "The Data Explainer" (ข่าวข้อมูล)**

Every page is a short data story: a plain question as the headline, the answer in one sentence, one big number, then one large chart with its labels and notes written on the chart that proves it. The page is white, the type is Sarabun alone, and colour is spent like a newsroom spends it: TCI blue (from the logo) for the brand and for the data that answers the page's question, one orange mark for the single highlighted point, quiet greys for everything that is context. Numbers stand on the page with no boxes around them; structure comes from hairline rules and generous gaps, not from bands, boxed fields or card grids.

The front door (`/overview`) is the purest expression: the reader's question at display size, the answer, the hero number in TCI blue, a byline, then the fastest-rising topics drawn as one story chart. Tool pages (journals, institutions, search, the map) stay operate-clear inside the same world: the same hairlines, the same soft controls, the same chart/table figure. Specialists still find the table tab, the CSV, the "ที่มา:" line and the method behind "วิธีอ่าน" exactly where they were.

The world rejects two forms by name, both confirmed by the owner's choice (2026-10-23): the government statistical-release form (coloured header band, boxed fields, heavy ink rules, underlined links everywhere) and the SaaS dashboard (rows of bordered KPI cards, card grids, eyebrow chips over headings). There is one light theme; the dark theme was retired with the old world.

**Key Characteristics:**
- White ground, ink #14182b text, TCI blue for brand + answer data, one orange mark per view, grey context.
- Question headline → one-sentence answer → one number → the chart that proves it.
- Numbers on hairlines, never in boxes; no sparklines inside stat tiles.
- Soft, quiet controls: 8 px controls, 12 px panels, pill toggles and the search field.
- Every chart: chart/table switch, numbered caption, "ที่มา:" line, CSV.
- Status always glyph + colour + Thai name.
- One typeface (Sarabun 400/600/700), self-hosted.

## Colors

A white page with one institutional blue that does double duty as the answer colour, one orange reserved for the highlighted mark, a cool-grey ink family, and a reserved six-colour status set that never means anything else.

### Primary
- **TCI Blue** (#283894): the logo's blue. The wordmark name, links, the primary button, current navigation item, selected tab and view switch, focus ring, the hero number, finding-card numbers, the focused series in a story chart, bars in `BarRank` and `ColumnChart`, sparklines in tables. It names the institution *and* marks the answer, so it is never used for decoration or for context data.
- **TCI Blue Deep** (#1a2466): hover for links and the primary button.
- **TCI Blue Soft** (#eef0fa): selection, the active search option, the current item in a menu, the beta tag, the selected story key on phones, the open goal tile, the `/match` privacy strip.

### Secondary
- **Orange Mark** (#e07000): the single highlighted mark per view: the end dot of the focused story line. It is the logo orange (#f89020) deepened until it reaches 3:1 on white; the logo orange itself is never put on white as a mark or as text.
- **Up Green** (#0b6b46): the "up" change under a stat value. Down changes are Ink Secondary, never red.

### Neutral
- **Ink** (#14182b): text, headings, stat values, on-chart notes.
- **Ink Secondary** (#4d536b): ledes, labels, secondary text, axis titles, sort buttons at rest.
- **Ink Tertiary** (#6b7088): source lines, bylines, axis ticks, unfocused series labels, the licence line.
- **Surface** (#f5f6fa): soft panels ("วิธีอ่าน", HowNote, uncertain box, empty state, cite box), the notice line, table row hover, the view switch and language switch tracks.
- **Rule** (#c9cddb) and **Hairline** (#e6e8f0): Rule for table header lines, secondary-button and CSV outlines, chart baselines; Hairline for every structural line (header bottom, nav bottom, figure caption row, stat and finding tops, table row dividers, footer top, gridlines).
- **Field Border** (#8a8fa6): the 1 px border of inputs (3:1 on white).
- **Context Grey** (#b9bdcc): the context lines of a story chart. Deliberately below 3:1 (the palette test asserts it): context never carries the answer.

### Status (reserved)
EMERGING #13a08a · WATCH #c47a0c · HOT #a3124f · DECLINING #5b74cf · STABLE and LOW_DATA #6f777b. Tag pairs (background / ink, ≥ 4.5:1) are in the frontmatter; LOW_DATA is a white tag with a 1 px Rule ring and a dashed glyph.

### Data
- **Series** (`series-1…4`: #283894, #e07000, #13866f, #b8860b): compare and keyword views only, validated as adjacent pairs, always with a dash pattern and a direct label.
- **Sequential** (`seq-1…5`: #eceefa → #1f2c7a, one TCI-blue hue): quantities that are not statuses: the province choropleth, mix-bar parts (largest = seq-5, "อื่น ๆ" = Surface with a Rule ring), the dominant part of a split bar, the quadrant zone (seq-1).
- **Map terrain** (`/atlas`): sheet #f7f8fb, contours #9a6a35, grid rgba(20,24,43,.08), unnamed dots rgba(20,24,43,.4); field tints `cat-01…cat-12` (frontmatter). Fallback groups (`G…`) take the neutral dot tint (#c9cddb) so they never read as a real field.

### Named Rules
**The Answer Is Blue Rule.** In a chart, TCI blue marks the data that answers the page's question; everything else is grey context. If two things are blue, one of them is wrong.
**The One Orange Rule.** At most one orange highlight per view: a mark (dot, end point) in Orange Mark, never a fill. The logo orange (#f89020) never sits on white below 3:1.
**The Reserved Status Rule.** The six status colours mean status and nothing else; a status is never shown by colour alone — glyph + colour + Thai name, every time. Any colour change passes `web/src/styles/palette.test.ts` (CVD separation, contrast, one light theme only).
**The Token-Only Rule.** Components use `var(--token)` from `web/src/styles/tokens.css`; a hex value in a component is a bug. Group colours arrive from the data as token keys (`cat-07`), never hex.
**The Terrain Is Not Data Rule.** Field tints are background terrain; fields are always named by labels and in the gazetteer.

## Typography

**Display / Body / Label Font:** Sarabun (with Noto Sans Thai, Leelawadee UI, system-ui), self-hosted woff2 in `src/assets/fonts/`, Thai + Latin subsets, weights 400 / 600 / 700 only.

**Character:** Sarabun descends from TH Sarabun, the face of Thai public documents: familiar and legible in both scripts. Set at 700 for questions and numbers and 400 at 19 px / 1.7 for reading, it reads like a newsroom explainer rather than a form.

### Hierarchy
Text steps and numeric steps live in `tokens.css` (`--fs-*`); components never set a raw size.
- **Display** (700, `--fs-display` clamp 36 → 52 px, 1.45): the front door's question headline only.
- **h1** (700, `--fs-h1` clamp 32 → 48 px, 1.45; max 24ch): every other page's question headline.
- **h2** (700, `--fs-h2` clamp 24 → 30 px, 1.5; max 30ch): section headings.
- **Lead** (400, `--fs-lead` clamp 20 → 24 px, 1.65): the lede and the story answer (Ink Secondary / Ink), figure titles (700), h3, card topics.
- **Body** (400, `--fs-body` 19 px; 17 px under 641 px, 1.7): prose, max 38em.
- **Meta** (400–700, `--fs-meta` 16 px): navigation, buttons, table cells, source lines, notes, chart names and on-chart notes. The floor for anything that carries meaning on its own.
- **Caption** (600–700, `--fs-caption` 14 px): chips and tags, tab counts, interval ranges, stacked-table labels, the licence line. Never smaller.
- **Numeric tile** (700, `--fs-tile` clamp 32 → 40 px, tabular): stat values, finding-card numbers.
- **Numeric hero** (700, `--fs-hero` clamp 40 → 56 px, tabular, −0.02em): at most one per page, in TCI blue.
- **Tick** (`--fs-tick` 13 px): SVG axis ticks and edge values only. Chart labels that carry meaning use Caption (values) and Meta (names); measuring code reads the same numbers from `web/src/lib/labelSizes.ts`. Axis labels never repeat (`tickDecimals`, repeated labels blanked).

The direction contract asked for 800 on question headlines; the build ships 700 (no 800 face is loaded), and 700 is the system value.

### Named Rules
**The Thai Line-Height Rule.** Thai stacks marks above and below the line: body 1.7, headings ≥ 1.5, display headings ≥ 1.45; only English-only rules (`:lang(en)`) close up to 1.25–1.3. `web/src/styles/lineHeight.test.ts` enforces it.
**The Upright Thai Rule.** Thai has no true italic: `em`, `i`, `cite`, `dfn`, `var`, `address` render upright; emphasis is weight 600/700. No letter-spacing and no case transforms on Thai — negative tracking and caps are English-only.
**The Arabic Numerals Rule.** Both languages use Arabic digits with en-US grouping (248,310), the true minus sign (−), and Gregorian years (ค.ศ.), matching the data; numbers are tabular wherever they align.

## Layout

A 1200 px container with 16 px gutters on phones and 30 px from 900 px (safe-area aware). Reading pages: page header (h1, lede, a one-line byline of release facts separated by middots, an action row), then a main column beside a 240 px "ในหน้านี้" rail with a 48 px gap; under 900 px the rail moves above the content and folds into one closed 44 px disclosure row. The front door's story is a two-column grid (text up to 400 px, chart takes the rest, 72 px gap) that stacks under 1100 px: question, answer, number, then the chart full width. `/atlas` uses the full container: map sheet plus a side column from 1100 px.

**Rhythm** (`--sp-*`): group 24 px (heading to content) · block 40 px (between figures) · section 88 px (between sections; the footer sits a section + 24 px below). Phones: 16 / 28 / 56. **Measure** (`--measure-*`): lede 32em, body 38em, headline 30ch. No horizontal page scroll at 360 px. Breakpoints in use: 520 (wordmark text hides), 640 (phone: tables stack, body 17 px), 700 (finding cards stack), 760 (`PhoneFold`), 900 (navigation folds into the menu), 1100 (story stacks, four-up stats become two-up).

**Targets:** every control is at least 44 px (nav links 52 px, menu rows 48 px); standalone links get at least 24 px from their own line box, never by shrinking text. Links inside a sentence are exempt.

**Phone chrome budget:** the top bar, the closed menu button and the one notice line together keep the page `h1` and its first number above 400 px at 390 px wide; the e2e test `narrow.spec.ts` holds the overview `h1` under 300 px. "ในหน้านี้" stays a closed row under 900 px and supporting step diagrams fold (`PhoneFold`).

**Entry budget:** the entry chunk stays ≤ 180 KB gzip (`npm run check:bundle`); pages beyond the core, the story's lazy sections, glossary definitions and province outlines load as their own chunks.

## Elevation & Depth

Flat by default: depth comes from hairlines, Surface panels and white space. Shadows appear only on things that float or are raised by state: the floating shadow for popovers, tooltips, the search listbox, desktop group menus and the map zoom control; a 1 px lift under the selected half of a segmented switch or language toggle; a soft drop under the opened phone navigation.

### Shadow Vocabulary
- **Floating** (`box-shadow: 0 14px 36px rgba(20,24,43,.14), 0 2px 6px rgba(20,24,43,.06)`): popovers (`Term`, source details), tooltip, search listbox, nav group menus, map zoom.
- **Raised segment** (`box-shadow: 0 1px 3px rgba(20,24,43,.12)`): the selected option in the chart/table switch and the language switch.
- **Phone menu** (`box-shadow: 0 12px 24px rgba(20,24,43,.08)`): the open navigation under 900 px.

### Named Rules
**The Flat Page Rule.** Stat tiles, finding cards, tables and figures never cast shadows; if something has a shadow it is temporary or selected.

## Shapes

Soft but quiet. Controls (buttons, CSV button, text fields, menu rows, search options, story keys) use the 8 px control radius; soft panels (how-to-read, HowNote, uncertain, empty state, popovers, tooltip, menus, map sheet, goal tiles) use 12 px; toggles that sit in a track (language switch, the phone menu button, the search field, notice tags, flags, topic badges) are pills. The chart/table switch is a 10 px track holding 7 px segments. Bars round their end by 3 px (column tops by 4 px). Step numbers are 36 px circles on TCI Blue Soft. Status chips keep square corners so the glyph reads as the shape. Lines are always 1 px (hairline or rule) except the 3 px TCI-blue indicator under the current nav item and selected tab (rounded top) and the 2 px dashed reference markers in charts. The focus ring is a 3 px TCI-blue outline, 2 px offset, 4 px radius.

## Components

### Top bar and navigation
White top bar with a hairline bottom, never a band: the TCI logo (48 px tall; 40 px under 900 px) then a hairline divider and the name "TCI Research Atlas" in TCI blue 700 over a Caption subtitle (text hidden under 521 px); the topic search (pill, up to 340 px) and the language switch (two pill toggles in a Surface track; the chosen one white, TCI blue, raised) on the right. Under it one hairline navigation row: text links at Meta 600, hover and current page in TCI blue with the 3 px indicator (`aria-current="page"`), and the four question disclosure groups. The bar keeps two rows because eight entries do not fit beside the logo and search at 1200 px. Under 900 px the bar holds the logo and one pill **"เมนู / Menu"** button (TCI-blue filled while open, `aria-expanded` + `aria-controls="site-nav"`) that opens the navigation in flow below (no overlay, no scroll lock): search first, then every page as a 48 px row with hairline dividers, group names in TCI blue 700 as labelled lists, the current page marked by a 3 px left bar, then the language buttons. Escape closes and returns focus; choosing a page closes it. The logo files and partner logos are defined once in `web/src/brand/brand.ts`.

**Page names** are plain words, not method words (`web/src/strings/*` `nav.*`): top-level ภาพรวม · สรุปผู้บริหาร … ข้อมูลเปิด · **อ่านตัวเลขอย่างไร** / How to read the numbers (`/about`). Between them the menu is grouped by **the question a reader brings, not by who they are** (owner's ruling 2026-10-23): **อะไรกำลังมา** / What's coming — สถานะหัวข้อ · แนวโน้มคำสำคัญ · อะไรเปลี่ยน · **โอกาสที่ยังไม่มีใครทำ** / Untapped opportunities (`/gaps`); **ใครทำเรื่องอะไร** / Who works on what — สถาบัน · วารสาร · วิธีวิจัย · การอ้างอิง; **ไทยอยู่ตรงไหน** / Where Thailand stands — แผนที่จังหวัด · ไทยเทียบโลก · SDG และแผนชาติ; **หางานวิจัย** / Find research — ค้นหาบทความ · แผนที่หัวข้อ · **แผนที่บทความทุกเรื่อง** / Map of every article (`/galaxy`) · เปรียบเทียบ · วางบทคัดย่อ. Group menus (desktop) are a disclosure pattern, not an ARIA menu: a white 12 px floating panel; each item is the page name over one plain Meta hint line (`nav.hint.*`, Ink Secondary, the link's `aria-describedby`) saying the question the page answers; the current item sits on TCI Blue Soft; a menu that would cross the right edge opens leftwards (`.is-flipped`, measured on open). Routes did not change.

### Notice line
One quiet line on a Surface strip under the navigation (a `<details>`): one pill tag — "รุ่นทดลอง" on TCI Blue Soft, or the WATCH-tinted "ข้อมูลตัวอย่าง" on test releases (visible on every page) — one short sentence and a "รายละเอียด" toggle with a chevron; the full texts open beneath. The data error banner (`role="alert"`) is separate and never folded: HOT tag background and ink, 8 px radius, a bold reason and what to do.

### Buttons
- **Primary:** TCI blue fill, white 700 Meta text, 8 px radius, 44 px; hover TCI Blue Deep.
- **Secondary:** white with a 1 px Rule outline, Ink 600 text, 42 px; hover turns border and text TCI blue; pressed (`aria-pressed`) is TCI-blue filled.
- **CSV:** the secondary form at 40 px in Ink Secondary with a drawn download icon.
- **Focus:** the global 3 px TCI-blue ring with a white gap.

### Chips (status tags)
Square tag at Caption 700: the status glyph, the tinted background and dark ink (≥ 4.5:1), the Thai status name. A small variant for tables and tooltips. LOW_DATA is white with a 1 px Rule ring and a dashed glyph.

### Tabs
Page-level ARIA tabs are text tabs on a hairline: Ink Secondary at rest, the selected one TCI blue with the 3 px indicator; arrow keys, Home and End move between tabs. Status tabs (`/emerging`) stay on one line on phones and scroll sideways with a white fade at the right edge.

### Figures
The figure is the unit of evidence. One caption row over a hairline: "แผนภูมิ n: …" (or "ตาราง n: …" in the table view) at Lead 700 on the left; on the right the **chart/table switch** — one soft segmented control (Surface 10 px track, 36 px segments, the chosen view white, TCI blue, raised; a figure inside another tab panel uses pressed buttons instead of a nested tablist) — the "วิธีอ่าน" toggle (link-coloured, opens a 12 px Surface panel: the encoding in words, then "คำที่ใช้:" glossary terms) and the CSV button. Then the legend (glyph + label), the chart, and the short source line in Ink Tertiary "ที่มา: TCI Research Atlas · รอบ {release} · รายละเอียด", where "รายละเอียด" opens a popover with the provenance and the status definition version (printed inline only in the brief and the embeds).

### Tables
Caption numbered "ตาราง n:", a 1 px Rule header line with Ink Secondary 600 headers (units in the header at 400, e.g. "สัดส่วน (%)"; headers balance onto at most two lines), hairline row dividers, Surface row hover, right-aligned tabular numbers. Sortable headers are buttons with an up/down glyph and `aria-sort`, TCI blue when sorted. A CSV button sits above every data table; what the numbers mean ("0.10 = 10%") is its tooltip and accessible description. Wide tables mark 3–4 main columns (`primary`); the rest hide behind "แสดงทุกคอลัมน์ (n)", the sorted column always shows, the CSV always has every column. Under 640 px rows become two-column label/value cards (`data-label`) with a "เพิ่มเติม" toggle per row. Long lists pass `limit` and end with "แสดงทั้งหมด (n)". A table outside a `Figure` ends with `SourceLine`. Interval cells are text first ("+101.4% ถึง +129.4%", Caption) with a whisker under them; a whisker narrower than 96 px is not drawn.

### Stat tiles (numbers on hairlines)
Key figures are `StatTile`s in a `StatGrid`, never label/value lists and never boxes: a 1 px hairline above, a Meta 600 Ink Secondary label, the value at Numeric tile in Ink (a long text value such as "ใหม่ — ปี 2016–2020 ยังไม่มีงานเรื่องนี้" drops to Lead), then optionally the change vs the previous release (Up Green with an arrow, or Ink Secondary when down), one Meta line of context, and a "เช่น …" example. **No sparkline inside a tile**: a trend gets its own figure. Grids of 2, 3 or 4 columns (four-up becomes two-up under 1100 px; two on phones) with 28 × 32 px gaps; a `wide` tile spans two columns (the whole row on phones), and tiles are ordered so no row ends with one tile beside an empty cell. The Overview shows four tiles and folds the rest under "ดูตัวเลขเพิ่ม (n)".

### Story hero (signature, front door)
`pages/overview/StoryHero.tsx`. Left column: the question as the page `h1` at Display ("งานวิจัยไทย | เรื่องไหนกำลังมา", breaking only between its halves in Thai), the answer in one Lead sentence with the leading topic as a bold link, the hero number in TCI blue at Numeric hero with one Meta unit line ("2.1 เท่า" once the share at least doubles, else "+29%"), and a byline on a hairline in Ink Tertiary (articles · data to year · updated). Action links follow (e.g. the brief as a secondary button). Right column: Figure 1, the story chart of the fastest-rising topics with its table tab and CSV, then one plain "อ่านต่อ" link to `/emerging`.

### Story chart and the focus line (signature)
`charts/StoryLines.tsx`. Context series are 2.25 px Context Grey lines; the focused series is a 4 px TCI-blue line ending in one Orange Mark dot with a 3 px white ring. Names and values are direct labels at the line ends (Meta; focused name TCI blue 700, focused value Ink 700, the rest Ink Tertiary) joined by Rule leader lines; one on-chart note (Meta 600 Ink with a white halo, dashed Ink Secondary leader) states the rise in words ("จาก 18 เรื่องในปี 2022 เป็น 95 เรื่องในปี 2024"). Pointing at or tabbing to any series or label makes it the focus line; the table tab is the keyboard/screen-reader equivalent. On phones the names move under the chart as 44 px tappable keys (the selected key on TCI Blue Soft). Lines draw once when they enter the view (1100 ms, `cubic-bezier(0.16, 1, 0.3, 1)`); with reduced motion they are already drawn. No legend: the labels are on the chart.

### Finding cards
`pages/overview/FindingCards.tsx` (Overview + brief): "3 เรื่องสำคัญรอบนี้" as three columns on hairlines (subgrid-aligned from 900 px, one per row under 700 px): the kind (Meta), one number in TCI blue at Numeric tile with its likely range in Caption, the example topic as a Lead link, one plain sentence, and the topic's articles a year as a small TCI-blue sparkline with its first and last year. Every number from the release; renders nothing without findings.

### Topic hero
`/topics/:id`: status chip with its one-line meaning, one plain growth sentence, the growth with its likely range (the growth word is a `Term`) and a fitted whisker, beside `StatTile`s; the top representative article follows as "เช่น …". Journals and institutions below are `BarRank`s with table tabs.

### Inputs and search
Text fields: 1 px Field Border, 44 px, 8 px radius; the topic search and the article search are pills (the article search 52 px at Body size) with a drawn magnifier; hover darkens the border to Ink Tertiary, focus turns it TCI blue inside the global ring. The topic search is an ARIA combobox with a 12 px floating listbox showing glyph, name and the other-language name; the active option sits on TCI Blue Soft.

### Glossary terms and how notes
Jargon in running text is a `Term`: the word with a dotted underline; pressing it (button, `aria-expanded`) opens a 12 px floating popover right below it with the term in bold and a plain definition, example first, its figures from the release. Escape closes and returns focus, a click elsewhere closes, nothing opens on hover; definitions load as their own small chunk. `HowNote` is the section-level twin of a figure's "วิธีอ่าน": a `<details>` whose 12 px Surface panel holds the method fine print. Use it when a section has no `Figure`; never put layer-2 text in a lede.

### Notes, flags and empty states
Uncertain box ("แนวโน้มไม่แน่นอน"), cite box and empty state are 12 px Surface panels; the WATCH inset is a 12 px panel on the WATCH tag colours. Text marks (`.flag`: "อนุมาน", "สูงกว่าเกณฑ์", "วิธีกระจุก") are Surface pills at Caption 600; the concentration mark (`.flag-on`, "กระจุกตัว / Concentrated") is a WATCH-tinted pill at 700 beside the share bar — never colour alone. A page whose module is not in the release, or was left out of the offline file, shows its h1 and an empty state saying why (never a white page, never `role="alert"`), reading skipped reasons from `manifest.skipped_modules`.

### Steps and phone folds
`Steps` is a short numbered sequence (3–4) whose order carries meaning: a row joined by a rule on wide screens, a vertical list on phones, 36 px circular numbers on TCI Blue Soft; `current` marks one step (`aria-current="step"`). `PhoneFold` turns a supporting section into one closed disclosure under 760 px.

### Footer
White with a hairline top, a section + 24 px below the content: "ทำอะไรต่อ / What next" (Lead 700) over four next steps (4 columns; 2 under 900 px; 1 under 481 px), each a bold Body link and one Meta hint: อ้างอิง Atlas (opens `/about` at its cite section through route state — never `href="#id"`), ดาวน์โหลดข้อมูล, รอบก่อนหน้า, อ่านตัวเลขอย่างไร. Then the one-sentence description of the data with the release line; then, over a hairline, the partner band — one Meta line and the TCI · NECTEC · สวทช. logos (48 px tall, 38 px on small phones, in the owner's order); then one Caption licence line (CC BY 4.0 · ไม่จัดอันดับบุคคล (PDPA)).

### CI forest plot (/emerging)
One row per topic: name (+ field) | whisker on a shared axis | value with its interval. The whisker is the interval at `manifest.ci_level`, capped (arrow when clipped), in the status colour with the status glyph at the estimate; a dashed line marks the +10 %/yr EMERGING bar and a solid Rule line marks zero. Grouped by status with each group's rule in one sentence.

### Terrain map (signature, /atlas only)
Canvas terrain on the 12 px map sheet: field tints by density, contour lines (every third heavier), faint 10 × 6 grid with A–J / 1–6 references on the frame (references as Surface tags), unnamed topics as dots. Signal-status topics are focusable SVG glyphs; labels have a sheet-colour halo and never collide. Layer toggles, zoom buttons (+, −, reset; a floating 12 px stack), drag to pan, Ctrl + wheel to zoom; nothing requires dragging. The gazetteer repeats every signal-status topic in text. On phones the sheet takes a taller aspect and an "อ่านแผนที่นี้ใน 3 ขั้น" `Steps` diagram explains the reading order.

### Province choropleth (/regions)
`ProvinceMap` fills provinces with the `seq-1…5` ramp: 5 quantile classes, province strokes white. "No data" is a hatch (white with diagonal Rule lines), never a ramp step, so the lowest class never reads as missing. The map never carries a number alone: a key with the range of every class, a title naming province and value, chart ⇄ table tabs with the table complete for all 77 provinces; the measure switch (articles / per 100,000 people) is a radio group. Province outlines live only in the `/regions` chunk.

### Infographic kit (`web/src/charts/`)
Quiet, realistic marks built from the tokens — no stock illustration, no emoji, no official SDG colours or icons. Layout maths lives in pure, unit-tested files (`charts/infographic.ts`, `charts/execLayout.ts`, `charts/editorLayout.ts`, `lib/story.ts`); the `.tsx` files only draw. Rules for every form:
- **Table alternative:** each sits inside a `Figure` (or beside a full table) whose table tab has every number; marks are decorative where the numbers are printed next to them (`aria-hidden`), otherwise the SVG has `role="img"` and a sentence `aria-label`.
- **Labels ≥ 14 px:** names and values at Caption/Meta (`LABEL_PX` 14/16); only axis ticks use the 13 px Tick. Labels never overlap a mark or each other (`placeLabels`); on phones fewer are named, the rest are in the tooltip and table.
- **Direct labels over legends:** name series and points on the chart; a legend is for glyph keys (status) and ramps.
- **Status = glyph + colour + name**, everywhere a status appears; status colours are used for nothing else.
- **TCI blue + quiet greys** for quantities that are not statuses: bars and columns are TCI blue on a Surface track, mixes and zones use the `seq-*` ramp, context is grey.
- **No data is a hatch or a dashed outline**, never the lightest ramp step (province hatch, dashed empty goal tile, dashed checklist box, dashed bridge link, dashed LOW_DATA square).
- **No hover-only information:** hover/focus only highlights or repeats; every value is printed, in the key or in the table. Placed in percent where possible, so charts reflow and print without measuring.

| Component | Purpose · when to use | Key rules |
|---|---|---|
| `StoryLines` | The front door's story chart (Overview). | Context grey, one TCI-blue focus line with one orange end dot, direct labels, one on-chart note; phones: keys under the chart. |
| `StatusWaffle` | Every topic by status, one square per topic (Overview, brief). | One row per status: glyph, name, count, % in text (+ the plain meaning, not in `compact`). LOW_DATA squares are a dashed outline. |
| `DotPlot` | Top movers on one axis (the printed brief). | Name \| status glyph at the estimate joined to zero by a hairline \| value with its range in text; solid zero line, dashed reference line with its label. |
| `BarRank` | Short ranked lists (a topic's journals and institutions, countries, methods, top provinces). | 12 px TCI-blue bar on a Surface track scaled to the largest, the number always printed; names link; under 640 px bar and number sit under the name. |
| `ArcNetwork` | Institution collaboration (`/institutions`). | Institutions as HTML rows, each pair a TCI-blue arc (40 % opacity at rest); stroke width and the number at the peak = joint articles; max 10 nodes; table lists every pair. |
| `ColumnChart` | One value per year on a zero baseline (`/institutions/:id`). | TCI-blue columns (4 px top radius), recessive gridlines, numbers on first, latest and largest; every figure in the tooltip and table. |
| `MixBar` / `SplitBar` | A 100 % split: topic mix / reliance on one source (`/gaps`, `/references`). | Mix: largest first, "อื่น ๆ" last, one blue dark→light, key repeats every part with its number. Split: dominant part vs the rest with a dashed threshold marker; the share printed. |
| `OpportunityQuadrant` | World growth × Thai activity per subfield (`/global`, `/gaps`). | Linear axes, dashed reference lines at 1, the seq-1 zone from the data file's thresholds; dots in the criteria filled, the rest hollow; opportunities labelled first. |
| `StatusFlow` | Status transitions since the previous release (`/changes`). | Previous status left, current right (glyph + name + count both sides); band thickness = topics, tinted with the new status. |
| `LineageKey` | The four ways a topic changes: ใหม่ / รวม / แยก / ไม่มีแล้ว (`/changes`). | Dot before → after drawing, name, one-line meaning, this release's count. |
| `GoalTiles` | 17 SDGs and each national framework (`/sdg`). | 12 px Surface tile: goal number, Thai name, topic count, share bar with the % printed; opens in place (full row, TCI Blue Soft); a goal with no topic is a dashed outline that says so. |
| `BridgePairs` | Topic pairs close in content but not yet worked on together (`/gaps`); `directed` for citing → cited (`/references`). | Topic — link — topic, the link labelled with institutions on both (dashed when none) and the closeness under it. |
| `JournalScatter` | Complete records × in-house share per journal (`/journals`). | The band above the in-house bar shaded and named; inferred owners hollow; every journal in the tooltip and table. |
| `PeriodMix` | A journal's change of course: then vs now (`/journals/:id`). | Two 100 % bars, same topics, same order, same shade; the key repeats both shares and the change ("+9 จุด"). |
| `ChecklistBars` | Which record fields a journal fills (`/journals/:id`). | Drawn ✓ / partial / ✗ / dashed-unknown box **and its word**, the field, a bar of the share, the share. |
| `SmallMultiples` | Compare 2–4 topics without a tangle (`/compare`). | One panel per topic on the same scale, own line in its series colour + dash, the others faint grey context, latest value printed at the end. |

`ForestPlot`, `PortfolioMatrix`, `TrendChart` and `MultiLineChart` keep their earlier specs in the new tokens; tick decimals follow the step so no axis repeats a label.

## Copy voice (น้ำเสียงของข้อความ)

The reader is an ordinary citizen first; the researcher and the executive read the same words. Strings live in `web/src/strings/*.ts` (lazy pages: their own file read with `useStrings`), always `th` + `en`.
- **Questions as headlines.** A page headline asks the reader's question in plain words; the first sentence under it answers it with a number from the release.
- **Two layers.** Layer 1 (headings, ledes, column headers, chart titles, cards, tooltips, on-chart notes): one short plain sentence, **example first** ("เช่น …"), numbers filled from the data with a unit on every number. Layer 2 (the exact rule, the method, the statistics word): behind a figure's "วิธีอ่าน", a `HowNote`, or a `Term` popover — never in layer 1.
- **Banned in layer 1:** ช่วงเชื่อมั่น, ช่วงฐาน, ช่วงล่าสุด, ฐานเปรียบเทียบ, เกณฑ์ความกว้าง, subfield, HHI, Jaccard, Jensen–Shannon, cosine, metadata, embedding, and the status codes (EMERGING, LOW_DATA …) inside Thai prose. Say instead: "น่าจะอยู่ระหว่าง {lo} ถึง {hi}" / "likely between", "สาขาย่อย", "ข้อมูลบทความครบ", "เนื้อหาใกล้กัน (เต็ม 1)". The glossary (`lib/glossary.ts`: ci, baseline, recent, shareGrowth, score, hhi, jaccard, jsd, cosine, activity, metadata, embedding) is where these words are explained.
- **Years, not windows:** write the years ("ปี 2017–2021 → ปี 2022–2024", "ใหม่ — ปี 2016–2020 ยังไม่มีงานเรื่องนี้"), never "ช่วงฐาน / ช่วงล่าสุด"; the years come from `definition.ts` / the release. A release code is explained where it is shown ("2026Q4 (ออกไตรมาส 4 ปี 2026)").
- **Thai status names** (web and pipeline): กำลังเกิดใหม่ · จับตา · กำลังมาแรง · ลดลง · คงที่ · ข้อมูลน้อย (English: Emerging · Watch · Hot · Declining · Stable · Low data), each with its one-line meaning (`stat.mean.*`). Definitions and `definition_version` 3 did not change; rule texts read their numbers from `definition.ts`.
- **Signals are questions, not verdicts** (/gaps, /global, possible partners); automatic sentences say so ("ระบบเขียนประโยคนี้จากตัวเลขในหน้านี้").
- The pipeline follows the same voice for every public sentence (template and LLM sentences pass `narrative.jargon_in`; the narrative/brief/method prompts carry the same banned list).

## Do's and Don'ts

### Do:
- **Do** open a page with the reader's question, answer it in one sentence, give one number, then show the chart that proves it.
- **Do** keep TCI blue (#283894) for the brand and the answer data, grey (#b9bdcc) for context, and at most one orange (#e07000) mark per view.
- **Do** pair every chart with the chart/table switch, a numbered caption ("แผนภูมิ n" / "ตาราง n"), a "ที่มา:" source line and CSV; tables sort (`aria-sort`).
- **Do** label charts directly and write the one note on the chart; keep labels ≥ 14 px.
- **Do** set numbers on hairlines (1 px #e6e8f0) with a short unit line, not in boxes.
- **Do** show status as glyph + colour + Thai name, and pass `palette.test.ts` for any colour change.
- **Do** show uncertainty: intervals at `manifest.ci_level`, "แนวโน้มไม่แน่นอน" when a forecast is not shown, "ใหม่ — ปี {base} ยังไม่มีงานเรื่องนี้" when the baseline years had no articles.
- **Do** set sizes only from `--fs-*`, spacing from `--sp-*`, colours from tokens; body 1.7, Thai headings ≥ 1.45/1.5.
- **Do** keep 44 px controls and the 3 px TCI-blue focus ring on every interactive element.
- **Do** lead with an example and plain words (Copy voice); put the exact rule behind "วิธีอ่าน", `HowNote` or a `Term`.
- **Do** build new chart forms from the infographic kit's rules: table tab, direct labels, TCI blue + greys, hatch or dashed outline for no data.

### Don't:
- **Don't** bring back a coloured header band, boxed form fields, heavy ink rules or a dark theme.
- **Don't** build rows of bordered KPI cards or card grids, or put eyebrow labels or kicker chips above headings.
- **Don't** put a sparkline inside a stat tile; a trend gets its own figure.
- **Don't** use a status colour for anything that is not a status, or a status without its glyph and name.
- **Don't** colour context data blue, fill an area with orange, or put the logo orange (#f89020) on white as a mark or text.
- **Don't** use italics, letter-spacing or case transforms on Thai text.
- **Don't** add shadows to tiles, cards, tables or figures; shadows are for floating or selected things only.
- **Don't** load fonts or anything else from a third-party server.
- **Don't** show abstracts or author names, or rank individual people.
- **Don't** put information only in a hover or only in colour, or jargon and status codes in a heading, lede or column header.
- **Don't** use the official SDG colours or icons, stock illustration or emoji.
