import { useEffect, useRef, useState } from 'react'
import type { AtlasRelease } from '../data/release'
import { useStrings } from '../lib/i18n'
import { embed } from '../strings/embed'
import { feedHref } from './embedUrl'

/* Small sharing tools: a read-only text box with a copy button (the citation on /about) and the Atom feed link. */

/** Read-only text (embed code, a citation) with a copy button; when the clipboard is blocked the text is selected
 *  so Ctrl+C works, and the status line says so. */
export function CopyField({ id, label, text, rows = 3 }: { id: string; label: string; text: string; rows?: number }) {
  const s = useStrings(embed)
  const box = useRef<HTMLTextAreaElement>(null)
  const timer = useRef<number | undefined>(undefined)
  const [state, setState] = useState<'idle' | 'done' | 'fail'>('idle')
  useEffect(() => () => window.clearTimeout(timer.current), [])
  const finish = (next: 'done' | 'fail') => {
    setState(next)
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => setState('idle'), 4000)
  }
  const fallback = () => {
    box.current?.focus()
    box.current?.select()
    finish('fail')
  }
  const copy = () => {
    if (!navigator.clipboard?.writeText) return fallback()
    navigator.clipboard.writeText(text).then(() => finish('done'), fallback)
  }
  return (
    <div className="copy-field">
      <label htmlFor={id}>{label}</label>
      <textarea id={id} ref={box} readOnly rows={rows} value={text} spellCheck={false} onFocus={(e) => e.currentTarget.select()} />
      <div className="copy-row">
        <button type="button" className="btn-secondary" onClick={copy}>
          {s('copy')}
          <span className="sr-only"> {label}</span>
        </button>
        <span className={state === 'fail' ? 'copy-st is-fail' : 'copy-st'} role="status">
          {state === 'done' ? s('copy.done') : state === 'fail' ? s('copy.fail') : ''}
        </span>
      </div>
    </div>
  )
}

/** Atom feed of new releases or of one topic — shown only when `atlas publish` wrote the feeds (latest.json.feeds). */
export function FeedLink({ release, kind, topicId }: { release: AtlasRelease; kind: 'releases' | 'topic'; topicId?: string }) {
  const s = useStrings(embed)
  if (release.latest.feeds !== true || (kind === 'topic' && !topicId)) return null
  const href = feedHref(kind === 'releases' ? 'releases.xml' : `topics/${topicId}.xml`)
  // a page-bar link; its title says what a feed reader does with it
  return (
    <a className="see-all no-print" href={href} type="application/atom+xml" title={s('feed.hint')}>
      <svg className="feed-ic" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">
        <circle cx="3" cy="13" r="2" />
        <path d="M1 7.5a7.5 7.5 0 0 1 7.5 7.5M1 2a13 13 0 0 1 13 13" />
      </svg>
      {s(kind === 'releases' ? 'feed.releases' : 'feed.topic')}
    </a>
  )
}
