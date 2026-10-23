import { useMemo, useRef, useState, type FormEvent, type RefObject } from 'react'
import { JournalLink } from '../components/JournalLink'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { ShareBar } from '../components/ShareBar'
import { StatusChip } from '../components/StatusGlyph'
import { Steps } from '../components/Steps'
import { TopicLink } from '../components/TopicLink'
import { useReleaseFile, useTopicDetail } from '../data/atlasContext'
import { hasModule, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { JournalsFile, MatchIndex, Topic } from '../data/types'
import { fmtWindow, windows } from '../lib/definition'
import { fmtInt, fmtPct } from '../lib/format'
import { useI18n, useStrings } from '../lib/i18n'
import { prepareIndex, queryLength, rankJournals, rankTopics, type JournalFit, type TopicHit } from '../lib/matcher'
import { statusName } from '../lib/topicText'
import { editorViz } from '../strings/editorViz'

export default function MatchPage() {
  const { t } = useI18n()
  return (
    <RequireRelease title={t('mt.title')}>
      {(release) => (
        <ModuleFile<MatchIndex> release={release} module="match" path={MODULE_FILES.match} title={t('mt.title')}>
          {(index) => <Match release={release} index={index} />}
        </ModuleFile>
      )}
    </RequireRelease>
  )
}

interface Result {
  hits: TopicHit[]
  journals: JournalFit[]
}

function PasteArt() {
  return (
    <svg width="48" height="36" viewBox="0 0 48 36" focusable="false">
      <rect x="6" y="2" width="30" height="32" className="sa-sheet" />
      {[10, 16, 22].map((y) => <line key={y} x1="11" x2="31" y1={y} y2={y} className="sa-line" />)}
      <line x1="11" x2="23" y1="28" y2="28" className="sa-line" />
      <path d="M40 14v14M34 22l6 6 6-6" className="sa-arrow" />
    </svg>
  )
}

function TopicsArt() {
  return (
    <svg width="48" height="36" viewBox="0 0 48 36" focusable="false">
      {[[10, 12], [17, 8], [14, 19], [34, 22], [40, 15], [36, 28]].map(([x, y]) => <circle key={`${x}-${y}`} cx={x} cy={y} r="3" className="sa-dot" />)}
      <circle cx="14" cy="13" r="10" className="sa-ring" />
      <circle cx="24" cy="18" r="2.5" className="sa-dot is-you" />
    </svg>
  )
}

function JournalArt() {
  return (
    <svg width="48" height="36" viewBox="0 0 48 36" focusable="false">
      {[4, 16, 28].map((x, i) => <rect key={x} x={x} y={6 + i * 2} width="10" height={28 - i * 2} className={i === 0 ? 'sa-book is-pick' : 'sa-book'} />)}
    </svg>
  )
}

/** The pasted text lives in component state only: never in the URL, storage or a request. */
function Match({ release, index }: { release: AtlasRelease; index: MatchIndex }) {
  const { t } = useI18n()
  const s = useStrings(editorViz)
  const prepared = useMemo(() => prepareIndex(index), [index])
  const [text, setText] = useState('')
  const [result, setResult] = useState<Result | null>(null)
  const [short, setShort] = useState(false)
  const resultsRef = useRef<HTMLHeadingElement>(null)
  const need = index.min_query_chars
  const run = (value: string) => {
    if (queryLength(value) < need) {
      setShort(true)
      setResult(null)
      return
    }
    setShort(false)
    const hits = rankTopics(prepared, value).filter((h) => release.topicById.has(h.id))
    setResult({ hits, journals: rankJournals(index, hits) })
    window.setTimeout(() => resultsRef.current?.focus(), 0)
  }
  const submit = (e: FormEvent) => {
    e.preventDefault()
    run(text)
  }
  // a made-up abstract from the strings file: filled in and matched here, like a pasted one
  const tryExample = () => {
    const sample = s('ms.sample')
    setText(sample)
    run(sample)
  }
  return (
    <div className="container">
      <PageHeader title={t('mt.title')} lede={t('mt.lede')}>
        <p className="privacy">{t('mt.privacy')}</p>
      </PageHeader>
      <div className="ms-steps">
        <Steps
          label={s('ms.steps')}
          current={result ? (result.journals.length ? 2 : 1) : 0}
          items={[
            { title: s('ms.1t'), body: s('ms.1b'), art: <PasteArt /> },
            { title: s('ms.2t'), body: s('ms.2b'), art: <TopicsArt /> },
            { title: s('ms.3t'), body: s('ms.3b'), art: <JournalArt /> },
          ]}
        />
      </div>
      <form className="match-form" onSubmit={submit}>
        <label htmlFor="match-text">{t('mt.label')}</label>
        <textarea
          id="match-text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          aria-describedby={short ? 'match-short' : undefined}
          autoComplete="off"
          spellCheck={false}
        />
        {short ? <p id="match-short" className="hint" role="alert">{t('mt.tooShort', { n: fmtInt(need), have: fmtInt(queryLength(text)) })}</p> : null}
        <div className="match-actions">
          <button type="submit" className="btn">{t('mt.submit')}</button>
          <button type="button" className="btn-secondary" aria-describedby="match-try-hint" onClick={tryExample}>{s('ms.try')}</button>
          <button type="button" className="btn-secondary" onClick={() => { setText(''); setResult(null); setShort(false) }}>{t('mt.clear')}</button>
        </div>
        <p id="match-try-hint" className="hint">{s('ms.tryHint')}</p>
      </form>
      {result ? <Results release={release} index={index} result={result} headingRef={resultsRef} /> : null}
    </div>
  )
}

function Results({ release, index, result, headingRef }: { release: AtlasRelease; index: MatchIndex; result: Result; headingRef: RefObject<HTMLHeadingElement | null> }) {
  const { t, lang } = useI18n()
  const s = useStrings(editorViz)
  const top = result.hits[0] ? (release.topicById.get(result.hits[0].id) as Topic) : null
  const jf = useReleaseFile<JournalsFile>(hasModule(release, 'journals') && result.journals.length ? MODULE_FILES.journals : null)
  const byId = new Map((jf.status === 'ready' ? jf.data.journals : []).map((j) => [j.id, j]))
  const topicOf = (id: string) => release.topicById.get(id) as Topic
  const recent = fmtWindow(windows(release.overview.last_complete_year).R)
  return (
    <section className="sec match-res" aria-labelledby="match-results">
      <h2 id="match-results" ref={headingRef} tabIndex={-1}>{t('mt.topics.h')}</h2>
      <p className="hint" role="status">{t('mt.resultsN', { n: fmtInt(result.hits.length) })}</p>
      {result.hits.length === 0 ? (
        <p className="note">{t('mt.none')}</p>
      ) : (
        <>
          <p className="intro">{t('mt.topics.intro')}</p>
          <ol className="ms-cards" aria-label={s('ms.cards')}>
            {result.hits.map((h, i) => {
              const tp = topicOf(h.id)
              return (
                <li key={h.id} className={i === 0 ? 'ms-card is-first' : 'ms-card'}>
                  <span className="ms-rank" aria-hidden="true">{i + 1}</span>
                  <div className="ms-body">
                    <p className="ms-name">
                      <span className="sr-only">{s('ms.rank', { n: i + 1 })} </span>
                      <TopicLink topic={tp} />
                    </p>
                    <p className="ms-meta">
                      <StatusChip status={tp.status} label={statusName(t, tp.status)} small />
                      <span>{s('ms.size', { n: fmtInt(tp.metrics.count_recent), r: recent })}</span>
                    </p>
                  </div>
                  <div className="ms-sim">
                    <span className="ms-bar" aria-hidden="true"><i style={{ width: `${Math.max(2, Math.min(1, h.score) * 100)}%` }} /></span>
                    <span className="ms-val">{s('ms.sim', { p: fmtPct(h.score, 0) })}</span>
                  </div>
                </li>
              )
            })}
          </ol>
          {top ? <Works topic={top} /> : null}
          {result.journals.length && jf.status === 'ready' ? (
            <Section id="match-journals" title={t('mt.journals.h')} intro={t('mt.journals.intro', { n: fmtInt(index.fit_topics) })}>
              <ol className="hits">
                {result.journals.filter((j) => byId.has(j.id)).map((j) => (
                  <li key={j.id}>
                    <span><JournalLink journal={byId.get(j.id)!} /></span>
                    <ShareBar value={j.fit} />
                    <span className="topic-sub">
                      {t('mt.fitTopics', { list: j.topics.map((x) => `${lang === 'en' ? topicOf(x.id).en || topicOf(x.id).th : topicOf(x.id).th} ${fmtPct(x.share, 0)}`).join(' · ') })}
                    </span>
                  </li>
                ))}
              </ol>
            </Section>
          ) : null}
        </>
      )}
    </section>
  )
}

function Works({ topic }: { topic: Topic }) {
  const { t, name } = useI18n()
  const detail = useTopicDetail(topic.id)
  const arts = detail.status === 'ready' ? detail.detail.articles.slice(0, 5) : []
  if (arts.length === 0) return null
  return (
    <Section id="match-works" title={t('mt.works.h')} intro={t('mt.works.intro', { topic: name(topic) })}>
      <ol className="articles">
        {arts.map((a) => (
          <li key={a.article_id}>
            {a.url ? <a href={a.url} target="_blank" rel="noopener noreferrer">{a.title}<span className="sr-only"> {t('newTab')}</span></a> : <span>{a.title}</span>}
            <span className="art-meta">{[a.journal, a.year ? String(a.year) : ''].filter(Boolean).join(' · ')}</span>
          </li>
        ))}
      </ol>
    </Section>
  )
}
