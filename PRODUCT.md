# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **The public (ประชาชน), primary for the front door (confirmed 2026-10-23).** Curious citizens, students, journalists. They arrive with no training in bibliometrics, often on a phone. In about ten seconds they want to know what Thai research is about and which subjects are rising or falling.
- **Researchers:** looking for research gaps, rising topics, articles to cite and journals to send work to.
- **Journal editors:** want an overview of their field, their journal's scope over time and its peer journals.
- **Executives and policy makers:** need a national picture for decisions, such as institutions, provinces, SDG and national-plan alignment, and Thailand compared with the world. They pass the numbers on to others.

## Product Purpose

TCI Research Atlas maps the landscape of Thai research from Thai-Journal Citation Index (TCI) / ThaiJO articles. A quarterly batch pipeline clusters every article into topics, defines status for each topic (emerging, watch, hot, declining, stable, low data), forecasts trends, and publishes a versioned data release. The web reads that release and explains it.

Success means two things. An ordinary visitor leaves knowing what Thai research works on and what is rising. A specialist can find, check and cite the exact number they need.

## Positioning

It is the only public, quarter-by-quarter map of Thai-language research. It is built on TCI's own corpus and states uncertainty honestly: intervals, "too few articles" and "uncertain trend" are shown, never hidden. It is bilingual Thai/English.

## Operating Context

- **Data:** static site on GitHub Pages (HashRouter). Data files are `data/<release>/*.json` under contract v2, and a release is replaced without rebuilding the web.
- **Offline:** a single offline HTML file is also produced, and the brief prints to PDF.
- **Releases:** a new release arrives every quarter.
- **Demo data:** the demo site runs on synthetic data and must say so (banner + noindex).

## Capabilities and Constraints

- **Routes:** about 23 routes covering overview, topic map, topic pages, status, compare, journals, methods, changes, abstract match, institutions, provinces, SDG, global, gaps, article search, article galaxy, keyword trends, references, brief, open data, how to read, and embeds. Navigation is grouped by question: what's coming / who works on what / where Thailand stands / find research.
- **Status:** status is always shown as glyph + colour + label. The six status colours are reserved and pass a colour-vision-deficiency (CVD) and contrast test.
- **Charts:** every chart has a table tab, a numbered caption, a "ที่มา:" (source) line and CSV export.
- **Copy:** two layers. Layer 1 is plain, example-first and has a unit on every number. Layer 2 (method, statistics) sits behind "วิธีอ่าน" (how to read). Jargon is banned from layer 1.
- **Privacy:** no runtime third-party requests (fonts, CDN, analytics). No author names and no abstracts (PDPA). Text pasted into `/match` never leaves the browser.
- **Performance:** the entry bundle is at most 180 KB gzip, and pages beyond the core are lazy-loaded.
- **Language:** every string exists in th + en. Thai is never set in italics.

## Brand Commitments

- **Name and logos:** the name is "TCI Research Atlas" and the TCI logo is required. The partner logos for NECTEC and NSTDA (สวทช.) are also used. Files are self-hosted at `web/src/assets/brand/partners/{tci,nectec,nstda}.png`, downloaded from tciai.openservice.in.th on 2026-10-23.
- **Typeface:** Sarabun, the only typeface (owner's ruling 2026-10-23).
- **Colour:** TCI blue is the primary colour. Sampled from the TCI logo it is ≈ #283894; the logo's orange is ≈ #f89020.
- **Background:** white only. The owner did not keep dark mode in the 2026-10-23 redesign.
- **Owner's brief:** plain, digestible, concise language; airy type that is never cramped; Modern Minimal, quietly premium and professional; clean white background; crisp text; lead with examples; infographic-style visuals fitted to context; realistic rather than cartoonish; no AI-slop website patterns.

## Evidence on Hand

- The repo has synthetic fixture releases only (`web/fixtures/`). Real corpus data is never committed.
- There are no testimonials, customers or usage numbers, and none may be invented.

## Product Principles

1. **Answer the public's question first.** Show what is rising and what is falling before how it was measured.
2. **Lead with a real example from the data.** The method sits one layer down.
3. **Honest uncertainty.** Never show a number without its doubt where doubt exists.
4. **Every number can be traced.** Each one has a table, a source line and a download.
5. **One quiet, consistent system across 23 pages.** Specialists' depth must not leak complexity into the front door.

## Accessibility & Inclusion

- **Standard:** WCAG 2.2 AA, with an axe scan per page in e2e.
- **Interaction:** keyboard-complete with a visible focus ring. Tap targets are at least 44 px.
- **Data display:** status is never shown by colour alone, and the province map always has a full table.
- **Reading and motion:** Thai line height is at least 1.5. Reduced motion is respected.
