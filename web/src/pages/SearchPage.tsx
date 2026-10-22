import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { EmptyState } from '../components/EmptyState'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { TopicLink } from '../components/TopicLink'
import { MODULE_FILES, type AtlasRelease } from '../data/release'
import type { SearchMeta, SearchVocab } from '../data/types'
import { toBibtex, toRis, type CiteRecord } from '../lib/citation'
import { downloadText, toCsv, type CsvColumn } from '../lib/csv'
import { fmtInt } from '../lib/format'
import { useI18n, useStrings } from '../lib/i18n'
import { facet, filterHits, popularWords, type SearchHit, type SearchOutcome } from '../lib/searchClient'
import { useArticleSearch, useSearchSource } from '../lib/useArticleSearch'
import { searchCodec, type SearchUrlState } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import { search } from '../strings/search'

const PAGE = 50
/** Thai script (U+0E00–U+0E7F), built from code points: the codebase never writes a backslash-u escape. */
const THAI = new RegExp(`[${String.fromCodePoint(0x0e00)}-${String.fromCodePoint(0x0e7f)}]`)

export default function SearchPage() {
  const s = useStrings(search)
  return (
    <RequireRelease title={s('title')}>
      {(release) => (
        <ModuleFile<SearchMeta> release={release} module="search" path={MODULE_FILES.search} title={s('title')}>
          {(meta) => <Search release={release} meta={meta} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

function Search({ release, meta }: { release: AtlasRelease; meta: SearchMeta }) {
  const s = useStrings(search)
  const { t } = useI18n()
  const [state, update] = useUrlState(searchCodec)
  const src = useSearchSource(meta)
  const result = useArticleSearch(src.source, state.q)
  const q = state.q.trim()
  return (
    <div className="container">
      <PageHeader title={s('title')} lede={s('lede', { n: fmtInt(meta.n_docs) })} />
      <QueryForm key={state.q} initial={state.q} disabled={src.status !== 'ready'} onSearch={(next) => update({ q: next })} onClear={() => update({ q: '' })} />
      {src.status === 'missing' ? (
        <EmptyState title={t('mod.missingFile')} />
      ) : src.status === 'error' ? (
        <p className="note">{t('mod.error')}</p>
      ) : !q ? (
        src.status === 'ready' ? <Tips vocab={src.vocab} /> : null
      ) : (
        <section className="sec srch-results" aria-labelledby="srch-results-h">
          <h2 id="srch-results-h">{s('res.h')}</h2>
          {result.status === 'ready' ? (
            <Results key={JSON.stringify([state.q, state.from, state.to, state.topic, state.journal])} release={release} meta={meta} outcome={result.outcome} state={state} update={update} />
          ) : result.status === 'error' ? (
            <p className="note" role="status">{s('res.error')}</p>
          ) : (
            <p className="loading" role="status">{s('res.loading')}</p>
          )}
        </section>
      )}
    </div>
  )
}

/** The draft lives here; the URL only changes on submit (each search fetches index shards). Remounted when q changes. */
function QueryForm({ initial, disabled, onSearch, onClear }: { initial: string; disabled: boolean; onSearch: (q: string) => void; onClear: () => void }) {
  const s = useStrings(search)
  const [draft, setDraft] = useState(initial)
  const submit = (e: FormEvent) => {
    e.preventDefault()
    onSearch(draft.trim())
  }
  return (
    <form className="srch-form" role="search" onSubmit={submit}>
      <label htmlFor="srch-q">{s('label')}</label>
      <div className="srch-row">
        <input
          id="srch-q"
          type="search"
          value={draft}
          placeholder={s('placeholder')}
          onChange={(e) => setDraft(e.target.value)}
          autoComplete="off"
          spellCheck={false}
          enterKeyHint="search"
          aria-describedby="srch-scope"
        />
        <button type="submit" className="btn" disabled={disabled}>{s('submit')}</button>
        {initial ? <button type="button" className="btn-secondary" onClick={onClear}>{s('clear')}</button> : null}
      </div>
      <p id="srch-scope" className="hint">{s('scope')}</p>
    </form>
  )
}

function Tips({ vocab }: { vocab: SearchVocab }) {
  const s = useStrings(search)
  const words = popularWords(vocab, 60)
  const tries = [...words.filter((w) => THAI.test(w)).slice(0, 4), ...words.filter((w) => !THAI.test(w)).slice(0, 3)]
  return (
    <section className="sec srch-tips" aria-labelledby="srch-tips-h">
      <h2 id="srch-tips-h">{s('tips.h')}</h2>
      <ul className="srch-tip-list">
        <li>{s('tips.1')}</li>
        <li>{s('tips.2')}</li>
        <li>{s('tips.3')}</li>
      </ul>
      {tries.length ? (
        <p className="srch-try">
          <span>{s('tips.try')}</span>
          {tries.map((w) => (
            <Link key={w} to={`/search?q=${encodeURIComponent(w)}`} lang={THAI.test(w) ? 'th' : 'en'}>{w}</Link>
          ))}
        </p>
      ) : null}
    </section>
  )
}

const quoted = (words: readonly string[]) => words.map((w) => `“${w}”`).join(', ')

function Results({ release, meta, outcome, state, update }: {
  release: AtlasRelease
  meta: SearchMeta
  outcome: SearchOutcome
  state: SearchUrlState
  update: (patch: Partial<SearchUrlState>) => void
}) {
  const s = useStrings(search)
  const { lang } = useI18n()
  const [shown, setShown] = useState(PAGE)
  const filtered = filterHits(outcome.hits, state)
  const capped = filtered.slice(0, meta.max_results)
  const filtering = state.from !== null || state.to !== null || state.topic !== null || state.journal !== ''
  const topicName = (id: string) => {
    const tp = release.topicById.get(id)
    return tp ? (lang === 'en' ? tp.en || tp.th : tp.th || tp.en) : id
  }

  if (outcome.known.length === 0) {
    return <p className="note" role="status">{outcome.unknown.length ? s('res.unknownOnly', { words: quoted(outcome.unknown) }) : s('res.none')}</p>
  }
  return (
    <>
      <div className="srch-summary">
        <p className="srch-count" role="status">
          {filtering ? s('res.countFiltered', { n: fmtInt(filtered.length), all: fmtInt(outcome.total) }) : s('res.count', { n: fmtInt(outcome.total) })}
        </p>
        <p className="hint">
          {s('res.words')}: {outcome.known.map((w, i) => <span key={w}>{i ? ' · ' : ''}<strong lang={THAI.test(w) ? 'th' : 'en'}>{w}</strong></span>)}
        </p>
        {outcome.unknown.length ? <p className="srch-unknown">{s('res.unknown', { words: quoted(outcome.unknown) })}</p> : null}
        {!outcome.complete ? <p className="srch-partial">{s('res.partial', { total: fmtInt(outcome.total), examined: fmtInt(outcome.examined) })}</p> : null}
      </div>
      {outcome.total > 0 ? <Filters release={release} meta={meta} outcome={outcome} state={state} update={update} topicName={topicName} /> : null}
      {outcome.total === 0 ? (
        <p className="note">{s('res.none')}</p>
      ) : filtered.length === 0 ? (
        <p className="note">{s('res.noneFiltered')}</p>
      ) : (
        <>
          <Exports release={release} rows={capped} topicName={topicName} />
          <p className="hint srch-order">
            {s('res.order')}
            {filtered.length > capped.length ? ` · ${s('res.capped', { n: fmtInt(capped.length) })}` : ''}
          </p>
          <ol className="srch-list">
            {capped.slice(0, shown).map((h) => <Hit key={h.ordinal} hit={h} release={release} />)}
          </ol>
          {capped.length > shown ? (
            <div className="srch-more">
              <p className="hint">{s('res.shown', { shown: fmtInt(shown), n: fmtInt(capped.length) })}</p>
              <button type="button" className="btn-secondary" onClick={() => setShown((n) => n + PAGE)}>
                {s('res.more', { n: fmtInt(Math.min(PAGE, capped.length - shown)) })}
              </button>
            </div>
          ) : null}
        </>
      )}
    </>
  )
}

function Filters({ release, meta, outcome, state, update, topicName }: {
  release: AtlasRelease
  meta: SearchMeta
  outcome: SearchOutcome
  state: SearchUrlState
  update: (patch: Partial<SearchUrlState>) => void
  topicName: (id: string) => string
}) {
  const s = useStrings(search)
  // each list counts the matches under the other filters, so an option never leads to an empty list unannounced
  const topics = facet(filterHits(outcome.hits, { ...state, topic: null }), (h) => (h.topic && release.topicById.has(h.topic) ? h.topic : null))
  const journals = facet(filterHits(outcome.hits, { ...state, journal: '' }), (h) => h.journal || null)
  if (state.topic && !topics.some(([id]) => id === state.topic)) topics.push([state.topic, 0])
  if (state.journal && !journals.some(([j]) => j === state.journal)) journals.push([state.journal, 0])
  const years = meta.years
  const year = (v: string) => (v ? Number(v) : null)
  const any = state.from !== null || state.to !== null || state.topic !== null || state.journal !== ''
  return (
    <fieldset className="srch-filters j-tools">
      <legend className="sr-only">{s('f.h')}</legend>
      <label>
        {s('f.from')}
        <select value={state.from ?? ''} onChange={(e) => update({ from: year(e.target.value) })}>
          <option value="">{s('f.any')}</option>
          {years.map((y) => <option key={y} value={y}>{y}</option>)}
        </select>
      </label>
      <label>
        {s('f.to')}
        <select value={state.to ?? ''} onChange={(e) => update({ to: year(e.target.value) })}>
          <option value="">{s('f.any')}</option>
          {years.map((y) => <option key={y} value={y}>{y}</option>)}
        </select>
      </label>
      <label>
        {s('f.topic')}
        <select value={state.topic ?? ''} onChange={(e) => update({ topic: e.target.value || null })}>
          <option value="">{s('f.any')}</option>
          {topics.map(([id, n]) => <option key={id} value={id}>{`${topicName(id)} (${fmtInt(n)})`}</option>)}
        </select>
      </label>
      <label>
        {s('f.journal')}
        <select value={state.journal} onChange={(e) => update({ journal: e.target.value })}>
          <option value="">{s('f.any')}</option>
          {journals.map(([j, n]) => <option key={j} value={j}>{`${j} (${fmtInt(n)})`}</option>)}
        </select>
      </label>
      {any ? <button type="button" className="btn-secondary" onClick={() => update({ from: null, to: null, topic: null, journal: '' })}>{s('f.reset')}</button> : null}
    </fieldset>
  )
}

const cite = (h: SearchHit): CiteRecord => ({ id: h.id, titleTh: h.titleTh, titleEn: h.titleEn, journal: h.journal, year: h.year, doi: h.doi, url: h.url })

function Exports({ release, rows, topicName }: { release: AtlasRelease; rows: readonly SearchHit[]; topicName: (id: string) => string }) {
  const s = useStrings(search)
  const rel = release.overview.release
  const base = `atlas-${rel}-search`
  const columns: CsvColumn<SearchHit>[] = [
    { header: 'article_id', value: (h) => h.id },
    { header: 'title_th', value: (h) => h.titleTh },
    { header: 'title_en', value: (h) => h.titleEn },
    { header: 'journal', value: (h) => h.journal },
    { header: 'year', value: (h) => h.year },
    { header: 'topic', value: (h) => h.topic ?? '' },
    { header: 'topic_name', value: (h) => (h.topic ? topicName(h.topic) : '') },
    { header: 'doi', value: (h) => h.doi ?? '' },
    { header: 'url', value: (h) => h.url ?? '' },
    { header: 'cited_in_tci', value: (h) => h.cited },
  ]
  const formats = [
    { key: 'x.csv' as const, file: `${base}.csv`, run: () => downloadText(`${base}.csv`, toCsv(rows, columns)) },
    { key: 'x.ris' as const, file: `${base}.ris`, run: () => downloadText(`${base}.ris`, toRis(rows.map(cite), rel), 'application/x-research-info-systems;charset=utf-8') },
    { key: 'x.bib' as const, file: `${base}.bib`, run: () => downloadText(`${base}.bib`, toBibtex(rows.map(cite), rel), 'application/x-bibtex;charset=utf-8') },
  ]
  return (
    <div className="srch-x" role="group" aria-labelledby="srch-x-h">
      <p id="srch-x-h" className="srch-x-h">{s('x.h')}</p>
      <div className="srch-x-btns">
        {formats.map((f) => (
          <button key={f.key} type="button" className="btn-secondary" aria-label={s('x.label', { n: fmtInt(rows.length), format: s(f.key) })} onClick={f.run}>{s(f.key)}</button>
        ))}
      </div>
      <p className="hint">{s('x.note')}</p>
    </div>
  )
}

function Hit({ hit, release }: { hit: SearchHit; release: AtlasRelease }) {
  const s = useStrings(search)
  const { t, lang } = useI18n()
  const [main, sub] = lang === 'en' ? [hit.titleEn || hit.titleTh, hit.titleEn ? hit.titleTh : ''] : [hit.titleTh || hit.titleEn, hit.titleTh ? hit.titleEn : '']
  const langOf = (text: string) => (THAI.test(text) ? 'th' : 'en')
  const topic = hit.topic ? release.topicById.get(hit.topic) : undefined
  return (
    <li className="srch-hit">
      <p className="srch-title" lang={langOf(main)}>
        {hit.url ? (
          <a href={hit.url} target="_blank" rel="noopener noreferrer">{main}<span className="sr-only"> {t('newTab')}</span></a>
        ) : main}
      </p>
      {sub ? <p className="srch-sub" lang={langOf(sub)}>{sub}</p> : null}
      <p className="srch-meta">
        <span>{hit.journal}</span>
        <span>{hit.year}</span>
        {topic ? <span><TopicLink topic={topic} /></span> : <span>{s('r.noTopic')}</span>}
        {hit.doi ? (
          <span>
            <a href={`https://doi.org/${hit.doi}`} target="_blank" rel="noopener noreferrer">{s('r.doi')} {hit.doi}<span className="sr-only"> {t('newTab')}</span></a>
          </span>
        ) : null}
        {hit.cited > 0 ? <span><span className="flag srch-cited">{s('r.cited', { n: fmtInt(hit.cited) })}</span></span> : null}
      </p>
    </li>
  )
}
