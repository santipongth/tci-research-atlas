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
- **Offline:** a single offline HTML file is also produced, and the overview (which is also the executive brief) prints to PDF on two A4 pages.
- **Releases:** a new release arrives every quarter.
- **Demo data:** the demo site runs on synthetic data and must say so (banner + noindex).

## Capabilities and Constraints

- **Routes (dashboard redesign, 2026-10-24):** five dashboards (overview, which is also the executive brief; research topics; institutions and provinces; journals; national and global goals), four detail pages (topic, journal, institution, province), two maps (topic map, map of every article), how to read the numbers, and two embeds. A white left sidebar groups them as dashboards / maps / help; on phones a menu button opens it in a drawer. Retired routes (status, changes, gaps, ideas, keywords, story, brief, institutions, regions, province, methods, references, SDG, global, search, compare, match, open data) redirect to the dashboard that now carries their content.
- **Status:** status is always shown as glyph + colour + label. The six status colours are reserved and pass a colour-vision-deficiency (CVD) and contrast test.
- **Cards:** each card shows only its title, its chart or ranked list, and "ดูทั้งหมด" (see all) to the matching dashboard or detail page. There are no search boxes, chart/table tabs, CSV buttons, "ที่มา:" lines or chart numbers on the pages; numbers a chart shows are printed as labels or a list beside it.
- **Copy:** two layers. Layer 1 is plain, short and has a unit on every number. Layer 2 (method, statistics) sits behind a small (i) button beside each card or page title (opened by click or tap), and in full on the how-to-read page. Jargon is banned from layer 1.
- **Privacy:** no runtime third-party requests (fonts, CDN, analytics). No author names and no abstracts (PDPA).
- **Performance:** the entry bundle is at most 180 KB gzip, and pages beyond the core are lazy-loaded.
- **Language:** every string exists in th + en. Thai is never set in italics.

## Brand Commitments

- **Name and logos:** the name is "TCI Research Atlas" and the TCI logo is required. The partner logos for NECTEC and NSTDA (สวทช.) are also used. Files are self-hosted at `web/src/assets/brand/partners/{tci,nectec,nstda}.png`, downloaded from tciai.openservice.in.th on 2026-10-23.
- **Typeface:** Sarabun, the only typeface (owner's ruling 2026-10-23).
- **Colour:** TCI blue is the primary colour. Sampled from the TCI logo it is ≈ #283894; the logo's orange is ≈ #f89020.
- **Background:** a white sidebar, page bar and cards on a soft blue-grey canvas (#f3f5fa), still one light theme (owner's choice for the 2026-10-24 dashboard). The owner did not keep dark mode in the 2026-10-23 redesign.
- **Owner's brief:** plain, digestible, concise language; airy type that is never cramped; Modern Minimal, quietly premium and professional; clean white background; crisp text; lead with examples; infographic-style visuals fitted to context; realistic rather than cartoonish; no AI-slop website patterns.

## Evidence on Hand

- The repo has synthetic fixture releases only (`web/fixtures/`). Real corpus data is never committed.
- There are no testimonials, customers or usage numbers, and none may be invented.

## Product Principles

1. **Answer the public's question first.** Show what is rising and what is falling before how it was measured.
2. **Lead with a real example from the data.** The method sits one layer down.
3. **Honest uncertainty.** Never show a number without its doubt where doubt exists.
4. **Every number can be traced.** Each one has its definition behind the card's (i) button and on the how-to-read page, and "see all" leads to the page that holds the detail.
5. **One quiet, consistent dashboard system across every page.** Show only what matters and keep scrolling short. Specialists' depth must not leak complexity into the front door.

## Accessibility & Inclusion

- **Standard:** WCAG 2.2 AA, with an axe scan per page in e2e.
- **Interaction:** keyboard-complete with a visible focus ring. Tap targets are at least 44 px.
- **Data display:** status is never shown by colour alone, and the province map always has its numbers in a list beside it (top 10, plus every province by region).
- **Reading and motion:** Thai line height is at least 1.5. Reduced motion is respected.
