import { useMemo, useRef, useState, type FormEvent, type RefObject } from 'react'
import { JournalLink } from '../components/JournalLink'
import { ModuleFile } from '../components/ModuleFile'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { ShareBar } from '../components/ShareBar'
import { TopicLink } from '../components/TopicLink'
import { useReleaseFile, useTopicDetail } from '../data/atlasContext'
import { hasModule, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { JournalsFile, MatchIndex, Topic } from '../data/types'
import { fmtInt, fmtPct } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { prepareIndex, queryLength, rankJournals, rankTopics, type JournalFit, type TopicHit } from '../lib/matcher'

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

/** The pasted text lives in component state only: never in the URL, storage or a request. */
function Match({ release, index }: { release: AtlasRelease; index: MatchIndex }) {
  const { t } = useI18n()
  const prepared = useMemo(() => prepareIndex(index), [index])
  const [text, setText] = useState('')
  const [result, setResult] = useState<Result | null>(null)
  const [short, setShort] = useState(false)
  const resultsRef = useRef<HTMLHeadingElement>(null)
  const need = index.min_query_chars
  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (queryLength(text) < need) {
      setShort(true)
      setResult(null)
      return
    }
    setShort(false)
    const hits = rankTopics(prepared, text).filter((h) => release.topicById.has(h.id))
    setResult({ hits, journals: rankJournals(index, hits) })
    window.setTimeout(() => resultsRef.current?.focus(), 0)
  }
  return (
    <div className="container">
      <PageHeader title={t('mt.title')} lede={t('mt.lede')}>
        <p className="privacy">{t('mt.privacy')}</p>
      </PageHeader>
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
          <button type="button" className="btn-secondary" onClick={() => { setText(''); setResult(null); setShort(false) }}>{t('mt.clear')}</button>
        </div>
      </form>
      {result ? <Results release={release} index={index} result={result} headingRef={resultsRef} /> : null}
    </div>
  )
}

function Results({ release, index, result, headingRef }: { release: AtlasRelease; index: MatchIndex; result: Result; headingRef: RefObject<HTMLHeadingElement | null> }) {
  const { t, lang } = useI18n()
  const top = result.hits[0] ? (release.topicById.get(result.hits[0].id) as Topic) : null
  const jf = useReleaseFile<JournalsFile>(hasModule(release, 'journals') && result.journals.length ? MODULE_FILES.journals : null)
  const byId = new Map((jf.status === 'ready' ? jf.data.journals : []).map((j) => [j.id, j]))
  const topicOf = (id: string) => release.topicById.get(id) as Topic
  return (
    <section className="sec" aria-labelledby="match-results">
      <h2 id="match-results" ref={headingRef} tabIndex={-1}>{t('mt.topics.h')}</h2>
      <p className="hint" role="status">{t('mt.resultsN', { n: fmtInt(result.hits.length) })}</p>
      {result.hits.length === 0 ? (
        <p className="note">{t('mt.none')}</p>
      ) : (
        <>
          <p className="intro">{t('mt.topics.intro')}</p>
          <ol className="hits">
            {result.hits.map((h) => (
              <li key={h.id}>
                <TopicLink topic={topicOf(h.id)} showStatus />
                <ShareBar value={h.score} />
              </li>
            ))}
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
