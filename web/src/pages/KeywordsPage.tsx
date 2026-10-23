import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react'
import { CsvButton } from '../components/CsvButton'
import { DataTable, type Column, type SortState } from '../components/DataTable'
import { EmptyState } from '../components/EmptyState'
import { Figure } from '../components/Figure'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { riserOf } from '../charts/editorLayout'
import { MultiLineChart, type LineSeries } from '../charts/MultiLineChart'
import { tickDecimals } from '../charts/scale'
import { assignSlots, SERIES_DASHES } from '../charts/series'
import { MODULE_FILES, type AtlasRelease } from '../data/release'
import type { GlossaryItem, KeywordTrend, KwTrendsFile } from '../data/types'
import { comboKey } from '../lib/comboKeys'
import { toCsv } from '../lib/csv'
import { fmtInt, fmtPct, yearSpan } from '../lib/format'
import { useI18n, useStrings } from '../lib/i18n'
import { figureCsv } from '../lib/tableCsv'
import { kwInsight, kwKey, matchKeywords, risingKeywords, shareOf, type KwOption } from '../lib/kwtrends'
import { foldText } from '../lib/search'
import { sortBy } from '../lib/sort'
import { tableCsvColumns } from '../lib/tableCsv'
import { KEYWORD_MAX, keywordsCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import { keywords as KW } from '../strings/keywords'

const DEFAULT_PICK = 3
const GLOSSARY_PAGE = 10
const RISERS = 6

export default function KeywordsPage() {
  const s = useStrings(KW)
  return (
    <RequireRelease title={s('title')}>
      {(release) => (
        <ModuleFile<KwTrendsFile> release={release} module="kwtrends" path={MODULE_FILES.kwtrends} title={s('title')}>
          {(file) => <Keywords release={release} file={file} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

/** A share as text: two decimals under 1 % so small keywords do not read as 0 %. */
const sharePct = (v: number) => fmtPct(v, v < 0.01 ? 2 : 1)

function Swatch({ slot }: { slot: number }) {
  return (
    <svg className="cmp-swatch" width="28" height="10" aria-hidden="true" focusable="false">
      <line x1="0" x2="28" y1="5" y2="5" style={{ stroke: `var(--series-${slot + 1})` }} strokeWidth="3" strokeDasharray={SERIES_DASHES[slot]} />
    </svg>
  )
}

function LangTag({ lang }: { lang: KeywordTrend['lang'] }) {
  const s = useStrings(KW)
  return <span className="kw-lang">{s(lang === 'th' ? 'lang.th' : 'lang.en')}</span>
}

interface YearRow {
  year: number
  share: (number | null)[]
  count: number[]
}

function Keywords({ release, file }: { release: AtlasRelease; file: KwTrendsFile }) {
  const s = useStrings(KW)
  const { t } = useI18n()
  const [state, update] = useUrlState(keywordsCodec)
  const byKey = useMemo(() => new Map(file.keywords.map((k) => [kwKey(k), k])), [file])
  // no k in the URL → the most used keywords, so the page never opens on an empty chart
  const keys = (state.k ?? file.keywords.slice(0, DEFAULT_PICK).map(kwKey)).filter((k) => byKey.has(k))
  const chosen = keys.map((k) => byKey.get(k) as KeywordTrend)
  // slots the visitor has already seen, so removing a keyword never repaints the others
  const [seenSlots, setSeenSlots] = useState<Record<string, number>>({})
  const slots = assignSlots(keys, seenSlots)
  const setKeys = (next: string[]) => {
    setSeenSlots(assignSlots(next, slots))
    update({ k: next })
  }
  const focusNext = useRef<number | 'hint' | null>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const hintRef = useRef<HTMLParagraphElement>(null)
  const add = (key: string) => {
    const next = [...keys.filter((x) => x !== key), key].slice(0, KEYWORD_MAX)
    if (next.length >= KEYWORD_MAX) focusNext.current = 'hint'
    setKeys(next)
  }
  const remove = (key: string) => {
    const left = keys.filter((x) => x !== key)
    focusNext.current = Math.min(keys.indexOf(key), left.length - 1)
    setKeys(left)
  }
  const keysId = keys.join('|')
  useEffect(() => {
    const target = focusNext.current
    if (target === null) return
    focusNext.current = null
    if (target === 'hint') hintRef.current?.focus()
    else if (target < 0) document.getElementById('kw-pick')?.focus()
    else listRef.current?.querySelectorAll<HTMLButtonElement>('.cmp-remove')[target]?.focus()
  }, [keysId])

  const full = chosen.length >= KEYWORD_MAX
  const exclude = new Set(keys)
  const top = file.keywords.filter((k) => !exclude.has(kwKey(k))).slice(0, 4)
  const risers = risingKeywords(file, RISERS)
  const years = file.years
  const series: LineSeries[] = chosen.map((k) => ({ id: kwKey(k), label: k.term, slot: slots[kwKey(k)], values: shareOf(file, k) }))
  const first = chosen[0]
  const insight = first ? kwInsight(years, series[0].values) : null
  const rows: YearRow[] = years.map((year, i) => ({ year, share: series.map((x) => x.values[i] ?? null), count: chosen.map((k) => k.counts[i] ?? 0) }))
  const yearColumns: Column<YearRow>[] = [
    { key: 'year', csvHeader: 'year', header: t('col.year'), rowHeader: true, cell: (r) => String(r.year), csv: (r) => r.year },
    ...chosen.flatMap((k, j): Column<YearRow>[] => [
      { key: `s-${kwKey(k)}`, csvHeader: `share:${kwKey(k)}`, header: s('col.share', { k: k.term }), numeric: true, cell: (r) => (r.share[j] === null ? '–' : sharePct(r.share[j] as number)), csv: (r) => r.share[j] },
      { key: `n-${kwKey(k)}`, csvHeader: `articles:${kwKey(k)}`, header: s('col.count', { k: k.term }), numeric: true, cell: (r) => fmtInt(r.count[j]), csv: (r) => r.count[j] },
    ]),
  ]
  const figTitle = s('fig.title', { a: years[0] ?? '', b: years[years.length - 1] ?? '' })
  const rel = release.overview.release
  const suggest = (label: string, list: readonly KeywordTrend[]) =>
    list.length ? (
      <p className="kw-try">
        <span>{label}</span>
        {list.map((k) => (
          <button key={kwKey(k)} type="button" className="linkbtn" lang={k.lang} aria-label={s('try.add', { k: k.term })} disabled={full} onClick={() => add(kwKey(k))}>
            {k.term}
          </button>
        ))}
      </p>
    ) : null

  return (
    <div className="container">
      <PageHeader title={s('q')} lede={s('lede', { release: release.overview.release, n: fmtInt(file.keywords.length) })} />
      <div className="cmp-picker kw-picker">
        <KeywordPicker file={file} exclude={exclude} disabled={full} onPick={add} />
        {full ? <p className="hint" ref={hintRef} tabIndex={-1}>{s('pick.max')}</p> : null}
        {chosen.length ? (
          <ul className="cmp-chips" ref={listRef} aria-label={s('pick.chosen')}>
            {chosen.map((k) => (
              <li key={kwKey(k)} className="cmp-chip">
                <Swatch slot={slots[kwKey(k)]} />
                <span className="kw-chip-term" lang={k.lang}>{k.term}</span>
                <LangTag lang={k.lang} />
                <button type="button" className="cmp-remove" aria-label={s('pick.remove', { k: k.term })} onClick={() => remove(kwKey(k))}>
                  <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" focusable="false"><path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="2" /></svg>
                </button>
              </li>
            ))}
          </ul>
        ) : null}
        <div className="kw-suggest">
          {suggest(s('try.top'), top)}
        </div>
      </div>
      {risers.length && years.length ? <Risers file={file} risers={risers} chosen={exclude} full={full} onAdd={add} /> : null}

      <Section id="kw-trend" title={s('chart.h')}>
        {chosen.length === 0 || years.length === 0 ? (
          <EmptyState title={s('none.h')}><p>{s('none.body')}</p></EmptyState>
        ) : (
          <>
            {first && insight ? (
              <p className="kw-insight">
                <span>{s(insight.dir === 'up' ? 'insight.up' : insight.dir === 'down' ? 'insight.down' : 'insight.flat', { k: first.term, a: insight.a, b: insight.b, p1: sharePct(insight.p1), p2: sharePct(insight.p2) })}</span>
                <span className="kw-insight-base">{s('insight.base', { l: s(first.lang === 'th' ? 'insight.th' : 'insight.en') })}</span>
              </p>
            ) : null}
            <Figure
              id="fig-kw"
              number={1}
              title={figTitle}
              tableTitle={t('table.n', { n: 1, title: s('table.title') })}
              csv={figureCsv(`atlas-${rel}-keyword-trends.csv`, rows, yearColumns)}
              source={t('source.line', { release: rel })}
              view={state.view}
              onView={(view) => update({ view })}
              legend={
                <div className="legend">
                  {series.map((x, k) => (
                    <span key={x.id}>
                      <Swatch slot={x.slot ?? k} />
                      <span lang={chosen[k].lang}>{x.label}</span>
                    </span>
                  ))}
                </div>
              }
              chart={<MultiLineChart years={years} series={series} format={sharePct} axisFormat={(v, step) => fmtPct(v, tickDecimals(step, 100))} label={figTitle} />}
              table={
                <DataTable
                  caption={t('table.n', { n: 1, title: s('table.title') })}
                  rows={rows}
                  columns={yearColumns}
                  rowKey={(r) => String(r.year)}
                  stack={false}
                />
              }
              note={<p className="note">{s('fig.how')}</p>}
            />
          </>
        )}
      </Section>

      <Glossary file={file} release={release} query={state.gq} onQuery={(gq) => update({ gq })} />
    </div>
  )
}

/** "คำที่กำลังมา": the fastest-rising keywords as chips — the word, an ink sparkline of its share and the change in
 *  numbers; pressing one adds it to the chart. A suggestion strip, not a statistic (risingKeywords). */
function Risers({ file, risers, chosen, full, onAdd }: { file: KwTrendsFile; risers: readonly KeywordTrend[]; chosen: ReadonlySet<string>; full: boolean; onAdd: (key: string) => void }) {
  const s = useStrings(KW)
  const years = file.years
  return (
    <section className="kr" aria-labelledby="kr-h">
      <h2 id="kr-h" className="kr-h">{s('kr.h')}</h2>
      <p className="kr-intro">{s('kr.intro', { a: yearSpan(years[0], years[1]), b: yearSpan(years[years.length - 2], years[years.length - 1]) })}</p>
      <ul className="kr-list" aria-label={s('kr.label')}>
        {risers.map((k) => {
          const shares = shareOf(file, k)
          const r = riserOf(years, shares)
          const on = chosen.has(kwKey(k))
          return (
            <li key={kwKey(k)}>
              <button
                type="button"
                className={on ? 'kr-chip is-on' : 'kr-chip'}
                disabled={on || full}
                onClick={() => onAdd(kwKey(k))}
              >
                <span className="kr-term"><span className="sr-only">{s('kr.addSr')} </span><span lang={k.lang}>{k.term}</span></span>
                {r ? <span className="kr-d">{sharePct(r.from)} → <b>{sharePct(r.to)}</b></span> : null}
                {on ? <span className="kr-on">{s('kr.shown')}</span> : null}
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

/** ARIA 1.2 combobox over every published keyword, Thai and English (and each one's glossary partner). */
function KeywordPicker({ file, exclude, disabled, onPick }: { file: KwTrendsFile; exclude: ReadonlySet<string>; disabled: boolean; onPick: (key: string) => void }) {
  const s = useStrings(KW)
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const results: KwOption[] = useMemo(() => matchKeywords(file, query, exclude), [file, query, exclude])
  const hasQuery = query.trim() !== ''
  const showList = open && hasQuery && results.length > 0
  const pick = (key: string) => {
    setQuery('')
    setOpen(false)
    setActive(0)
    onPick(key)
  }
  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    const a = comboKey(e.key, { open, showList, active, count: results.length, hasQuery })
    if (a.prevent) e.preventDefault()
    if (a.open !== undefined) setOpen(a.open)
    if (a.active !== undefined) setActive(a.active)
    if (a.clear) setQuery('')
    const hit = results[active]
    if (a.pick && hit) pick(kwKey(hit.keyword))
  }
  const id = 'kw-pick'
  return (
    <div className="search kw-search">
      <label htmlFor={id} className="search-label">{s('pick.label')}</label>
      <input
        id={id}
        type="search"
        role="combobox"
        aria-expanded={showList}
        aria-controls={`${id}-list`}
        aria-autocomplete="list"
        aria-activedescendant={showList ? `${id}-opt-${active}` : undefined}
        autoComplete="off"
        spellCheck={false}
        placeholder={s('pick.placeholder')}
        value={query}
        disabled={disabled}
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
          setActive(0)
        }}
        onKeyDown={onKeyDown}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
      />
      <ul id={`${id}-list`} role="listbox" aria-label={s('pick.label')} className="search-list" hidden={!showList}>
        {results.map((o, i) => (
          <li
            key={kwKey(o.keyword)}
            id={`${id}-opt-${i}`}
            role="option"
            aria-selected={i === active}
            className={i === active ? 'is-active' : undefined}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => pick(kwKey(o.keyword))}
          >
            <LangTag lang={o.keyword.lang} />
            <span className="search-name" lang={o.keyword.lang}>{o.keyword.term}</span>
            <span className="search-alt">
              {s('pick.articles', { n: fmtInt(o.keyword.n) })}
              {o.via ? <> · {s('pick.via', { k: o.via })}</> : null}
            </span>
          </li>
        ))}
      </ul>
      <div className="sr-only" role="status" aria-live="polite">
        {hasQuery ? (results.length ? s('pick.count', { n: results.length }) : s('pick.none', { q: query })) : ''}
      </div>
      {open && hasQuery && results.length === 0 ? <p className="search-none">{s('pick.none', { q: query })}</p> : null}
    </div>
  )
}

function Glossary({ file, release, query, onQuery }: { file: KwTrendsFile; release: AtlasRelease; query: string; onQuery: (q: string) => void }) {
  const s = useStrings(KW)
  return (
    <Section id="kw-glossary" title={s('gl.h')} intro={s('gl.intro', { n: fmtInt(file.glossary_min_pairs) })}>
      {file.glossary.length === 0 ? (
        <p className="note">{s('gl.empty')}</p>
      ) : (
        <>
          <div className="search kw-gl-filter">
            <label htmlFor="kw-gl-q" className="search-label">{s('gl.filter')}</label>
            <input id="kw-gl-q" type="search" value={query} placeholder={s('gl.filterPh')} autoComplete="off" spellCheck={false} onChange={(e) => onQuery(e.target.value)} />
          </div>
          <GlossaryTable key={query} file={file} release={release} query={query} />
        </>
      )}
    </Section>
  )
}

/** Remounted per filter text, so "show more" starts again from the first page. */
function GlossaryTable({ file, release, query }: { file: KwTrendsFile; release: AtlasRelease; query: string }) {
  const s = useStrings(KW)
  const { t } = useI18n()
  const [shown, setShown] = useState(GLOSSARY_PAGE)
  const [sort, setSort] = useState<SortState>({ key: 'n', dir: 'desc' })
  const q = foldText(query)
  const filtered = q ? file.glossary.filter((g) => foldText(g.th).includes(q) || foldText(g.en).includes(q)) : file.glossary
  const columns: Column<GlossaryItem>[] = [
    { key: 'th', csvHeader: 'th', header: s('gl.th'), rowHeader: true, cell: (g) => <span lang="th">{g.th}</span>, sortValue: (g) => g.th },
    { key: 'en', csvHeader: 'en', header: s('gl.en'), cell: (g) => <span lang="en">{g.en}</span>, sortValue: (g) => g.en.toLowerCase(), csv: (g) => g.en },
    { key: 'n', csvHeader: 'n', header: s('gl.n'), numeric: true, cell: (g) => fmtInt(g.n), sortValue: (g) => g.n },
  ]
  const col = columns.find((c) => c.key === sort.key)
  const sorted = col?.sortValue ? sortBy(filtered, col.sortValue, sort.dir) : [...filtered]
  const page = sorted.slice(0, shown)
  const rel = release.overview.release
  return (
    <>
      <p className="hint kw-gl-count" role="status">
        {filtered.length > page.length ? s('gl.count', { shown: fmtInt(page.length), n: fmtInt(filtered.length) }) : s('gl.countAll', { n: fmtInt(filtered.length) })}
      </p>
      {filtered.length ? (
        <div className="tbl-tools">
          <CsvButton filename={`atlas-${rel}-glossary.csv`} text={() => toCsv(sorted, tableCsvColumns(columns))} />
        </div>
      ) : null}
      <DataTable
        caption={t('table.n', { n: 2, title: s('gl.table') })}
        rows={page}
        columns={columns}
        rowKey={(g) => `${g.th}|${g.en}`}
        sort={sort}
        onSort={setSort}
        stack={false}
        empty={s('gl.none', { q: query })}
      />
      {filtered.length > page.length ? (
        <p className="kw-gl-more">
          <button type="button" className="btn-secondary" onClick={() => setShown((n) => n + 50)}>{s('gl.more', { n: fmtInt(Math.min(50, filtered.length - page.length)) })}</button>
        </p>
      ) : null}
    </>
  )
}
