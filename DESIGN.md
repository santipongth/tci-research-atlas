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
typography:
  display:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "clamp(2rem, 1.4rem + 2.2vw, 3rem)"
    fontWeight: 700
    lineHeight: 1.5
  headline:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "clamp(1.5rem, 1.1rem + 1.6vw, 2.5rem)"
    fontWeight: 600
    lineHeight: 1.5
  title:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "clamp(1.5rem, 1.2rem + 1vw, 2.25rem)"
    fontWeight: 700
    lineHeight: 1.5
  body:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "1.1875rem"
    fontWeight: 400
    lineHeight: 1.65
  body-phone:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 600
    lineHeight: 1.5
  numeric:
    fontFamily: "Sarabun, Noto Sans Thai, Leelawadee UI, system-ui, sans-serif"
    fontSize: "clamp(1.75rem, 1.4rem + 1vw, 2.375rem)"
    fontWeight: 700
    lineHeight: 1.25
    fontFeature: "tnum"
rounded:
  none: "0px"
  tag: "2px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "40px"
  xxl: "64px"
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
- Civic structure: header band, phase banner, page title + release metadata, "ในหน้านี้" rail, numbered figures/tables with source lines.
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

### Named Rules
**The Reserved Status Rule.** The six status colours mean status and nothing else; a status is never shown by colour alone — glyph + colour + label, every time.
**The Yellow Means Focus Rule.** A full yellow background appears only on the focused element. The headline highlighter is a lower-half band, never a full fill.
**The Token-Only Rule.** Components use `var(--token)`; a hex value in a component is a bug. Group colours arrive from the data as token keys (`cat-07`), never hex.
**The Terrain Is Not Data Rule.** Field tints are background terrain; fields are always named by labels and in the gazetteer, so tint repetition beyond 12 groups is harmless.

## Typography

**Display / Body / Label Font:** Sarabun (with Noto Sans Thai, Leelawadee UI, system-ui), self-hosted woff2, Thai + Latin subsets, weights 400/600/700.

**Character:** Sarabun descends from TH Sarabun, the standard face of Thai government documents — familiar, plain and legible in both scripts; one family keeps the release sober.

### Hierarchy
- **Display** (700, clamp(2rem, 1.4rem + 2.2vw, 3rem), 1.5): the page `h1`, max 34ch.
- **Headline** (600, clamp(1.5rem, 1.1rem + 1.6vw, 2.5rem), 1.5): the Overview headline sentence only, max 30ch.
- **Title** (700, clamp(1.5rem, 1.2rem + 1vw, 2.25rem), 1.5): section `h2`.
- **Body** (400, 19 px ≥ 641 px wide / 16 px on phones, 1.65): prose, max 40em.
- **Label** (600, 0.875–1rem, 1.5): table headers, tab labels, chip text, KPI labels.
- **Numeric** (700, clamp(1.75rem, 1.4rem + 1vw, 2.375rem), 1.25, tabular figures): KPI values and finding stats.

### Named Rules
**The Upright Thai Rule.** Thai has no true italic: `em`, `i`, `cite`, `dfn`, `var`, `address` render upright; emphasis is weight 600/700. No letter-spacing and no case transforms on Thai — English-only caps use `[lang="en"]`.
**The Arabic Numerals Rule.** Both languages use Arabic digits with en-US grouping (248,310), the true minus sign (−), and Gregorian years (ค.ศ.), matching the data.

## Layout

A 1200 px max container with 16 px gutters on phones and 30 px from 900 px. Reading pages use a two-thirds column plus a 240 px "ในหน้านี้" rail (rail moves above the content under 900 px). `/atlas` uses the full container: map sheet plus a 320 px side column (key, layers, selection) from 1100 px, stacked below on smaller screens. Breakpoints: 640 (phone ↔ tablet; tables stack into label/value cards), 900, 1100. Spacing rhythm 4/8/16/24/40/64; sections are separated by 40 px; the footer starts 64 px below content. No horizontal page scroll at 360 px.

## Elevation & Depth

Flat by default: depth comes from borders, tints (Paper Tint panels) and the header band. A single shadow (`0 8px 28px rgba(11,12,14,.18)`, dark `rgba(0,0,0,.6)`) is used only for floating layers: the tooltip, the search listbox and the map's zoom control.

### Named Rules
**The Flat Page Rule.** Cards, KPI tiles and tables never cast shadows; if something floats, it is temporary.

## Shapes

Square corners everywhere (0 px): buttons, tabs, chips, panels, inputs. The only rounding is 2 px on map grid-reference tags. The header band ends with a 10 px Link Blue rule; tables have a 2 px Ink header rule and 1 px Rule Light row dividers; KPI tiles have a 1 px Rule border.

## Components

### Header band and navigation
Civic Blue band: the wordmark (temporary "TCI" box + name + Thai subtitle; the official logo swaps in at `web/src/brand/brand.ts`), language switch (two pressed-state buttons) and theme toggle (44 px, 2 px white outline). Below it, a white navigation row of text links (current page: 4 px Link Blue underline, `aria-current="page"`) and the topic search. A phase banner ("รุ่นทดลอง") and, for test releases, a "ข้อมูลตัวอย่าง" tag follow.

### Buttons
- **Shape:** square, 44 px tall.
- **Primary:** Go Green fill, white 700 text, 2 px darker bottom edge (#002d18).
- **Hover / Focus:** hover #005a30; focus = yellow fill, ink text, ink bottom edge.
- **Secondary:** 2 px Ink outline on Paper, 600 text; pressed state = Ink fill, Paper text.

### Chips (status tags)
Square tag with the status glyph, tinted background and dark ink (≥ 8:1). Small variant for tables and tooltips. LOW_DATA uses a 1 px rule ring and a dashed glyph.

### Tabs
ARIA tabs: Paper Tint inactive tabs, the selected tab joins its bordered panel (Paper, 1 px Rule). Arrow keys, Home and End move between tabs. Every figure has a "แผนภูมิ / ตาราง" tab pair.

### Tables
Caption numbered "ตาราง n:", 2 px Ink header rule, right-aligned tabular numbers, sortable headers as link-blue buttons with an up/down glyph and `aria-sort`. A "ดาวน์โหลด CSV" button sits above every data table. Under 640 px rows become two-column label/value cards (`data-label`).

### Figures
Title "แผนภูมิ n: …", legend (glyph + label), the chart, then "ที่มา: TCI Research Atlas … รอบ {release} · นิยามสถานะฉบับที่ {v}". A "วิธีอ่านแผนภูมินี้" disclosure explains the encoding in words.

### Inputs / search
2 px Ink border, square, 44 px; focus = 3 px yellow outline + inset ink ring. The topic search is an ARIA combobox with a floating listbox (shadow) showing glyph, name and the other-language name.

### Banners and notices
Phase banner: Civic Blue tag + text. Error banner (`role="alert"`): 4 px left rule in HOT ink on Paper Tint, a bold reason and what to do. Uncertain box ("แนวโน้มไม่แน่นอน"): 4 px left Rule on Paper Tint. WATCH inset: 2 px WATCH border on the WATCH tag background.

### Editors' pages (P2)
Share bars: 64 × 8 px, `--ink-2` fill on `--surface` with a 1 px inset rule, the number always printed next to the bar (the bar never carries the value alone). Text marks (`.flag`): 1 px ink border, no fill, bold small text: "อนุมาน / inferred", "สูงกว่าเกณฑ์ / above the bar", "วิธีกระจุก / narrow methods" — never colour alone. Journal name rule: registry name; else the other language's name with `lang`; else the OJS name followed by "ยังไม่มีชื่อเต็มในทะเบียนวารสาร". Paste box (`/match`): the privacy note first, set on a Paper Tint strip with the brand rule, one labelled 12 rem textarea, primary + secondary buttons, and the results heading takes focus after a search. A page whose module is not in the release, or was left out of the offline file, shows its h1 and an empty state saying why (never a white page, never `role="alert"`).

### Executives' pages (P3)
Grouped navigation: three disclosure buttons (สำหรับผู้บริหาร / บรรณาธิการ / นักวิจัย) between the top-level links — a disclosure pattern, not an ARIA menu. Buttons and menu items are 44 px high; the group holding the current page carries the 4 px link-blue underline (inside the menu, the current item an inset 4 px rule); Enter or Space toggles, Escape closes and returns focus to the button, leaving the group or choosing a page closes it; at 360 px the menu spans the gutters. Sequential ramp `--seq-1…--seq-5` (one blue hue; light and dark values in tokens.css) for the province choropleth: 5 quantile classes, "no data" is `--surface` (never a ramp step), province strokes are `--bg`. Choropleth rule: the table view is complete and the map never carries a number alone — a legend with the range of every class, a title (hover) naming province and value, and chart ⇄ table tabs like every figure; the measure switch (articles / per 100,000 people) is a radio group. `.flag-on` marks a concentrated unit: 2 px ink border, bold small text "กระจุกตัว / Concentrated" beside the share bar. Possible partners (R6) are worded as a suggestion from the data — similarity and shared topics shown, never a ranking and never an endorsement; signals on /gaps are questions to explore, not verdicts.

### Headline sentence (signature, Overview only)
The release's brief headline in Headline type, figures and topic names under the turmeric lower-half band (topic names are links), followed by a small note that the sentence was generated automatically from the system's figures (template or AI, numbers checked).

### CI forest plot (signature, Overview and /emerging)
One row per topic: name (+ field) | whisker on a shared axis | value. The whisker is the interval at `manifest.ci_level`, capped (arrow when clipped), with the status glyph at the estimate; a dashed vertical line marks the +10 %/yr EMERGING bar and a solid line marks zero. Grouped by status with each group's rule in one sentence.

### Terrain map (signature, /atlas only)
Canvas terrain on the map sheet: field tints by density, contour brown lines (every third line heavier), faint 10 × 6 grid with A–J / 1–6 references on the frame edges, unnamed topics as dots. EMERGING/WATCH/HOT/DECLINING topics are focusable SVG glyphs with grid references; labels have a sheet-colour halo and never collide. Layer toggles (statuses, contours, tints, names), zoom buttons (+, −, reset), drag to pan, Ctrl + wheel to zoom; nothing requires dragging. The gazetteer repeats every signal-status topic in text; other topics are found with search.

## Do's and Don'ts

### Do:
- **Do** pair every chart with a table tab, a numbered caption and a "ที่มา:" source line.
- **Do** show uncertainty: intervals at `manifest.ci_level`, "แนวโน้มไม่แน่นอน" when a forecast is not shown, "ใหม่ — ไม่มีในช่วงฐาน" when the baseline window had no articles.
- **Do** keep body line-height at 1.65 and text measure ≤ 40em.
- **Do** read colours from tokens and group colours from `cat-NN` keys.
- **Do** keep 44 px controls and the yellow focus treatment on every interactive element.

### Don't:
- **Don't** use italics, letter-spacing or uppercase on Thai text.
- **Don't** use a status colour for anything that is not a status, or a status without its glyph and label.
- **Don't** fill a background with yellow except for keyboard focus.
- **Don't** add shadows to cards, tiles or tables, or round their corners.
- **Don't** load fonts or anything else from a third-party server.
- **Don't** show abstracts or rank individual people.
