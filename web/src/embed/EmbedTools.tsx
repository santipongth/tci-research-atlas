import { useEffect, useRef, useState } from 'react'
import type { AtlasRelease } from '../data/release'
import { useI18n, useStrings } from '../lib/i18n'
import { embed } from '../strings/embed'
import { embedSrc, feedHref, iframeSnippet, siteUrl } from './embedUrl'

/*
 * Small sharing tools loaded on demand by the topic, emerging, changes and about pages: a read-only text box with a
 * copy button, the "embed this chart" disclosure and the Atom feed link.
 */

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

/** "ฝังกราฟ / Embed" — the <iframe> code for a widget of this site. Hidden in the offline file (no public address).
 *  `title` (the iframe's accessible name) defaults to the widget's own heading. */
export function EmbedSnippet({ kind, path, title, height }: { kind: 'topic' | 'emerging'; path: string; title?: string; height: number }) {
  const s = useStrings(embed)
  const { lang } = useI18n()
  const site = siteUrl()
  if (!site) return null
  const code = iframeSnippet({ src: embedSrc(site, path, lang), title: title ?? `${s('em.title')} — TCI Research Atlas`, width: 640, height })
  return (
    <details className="embed-snip no-print">
      <summary>{s(kind === 'topic' ? 'snip.topic' : 'snip.emerging')}</summary>
      <div className="embed-snip-body">
        <p>{s('snip.intro')}</p>
        <CopyField id={`embed-code-${kind}`} label={s('snip.label')} text={code} rows={4} />
        <p className="hint">{s('snip.lang')}</p>
      </div>
    </details>
  )
}

/** Atom feed of new releases or of one topic — shown only when `atlas publish` wrote the feeds (latest.json.feeds). */
export function FeedLink({ release, kind, topicId }: { release: AtlasRelease; kind: 'releases' | 'topic'; topicId?: string }) {
  const s = useStrings(embed)
  if (release.latest.feeds !== true || (kind === 'topic' && !topicId)) return null
  const href = feedHref(kind === 'releases' ? 'releases.xml' : `topics/${topicId}.xml`)
  return (
    <p className="feed-link no-print">
      <svg className="feed-ic" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">
        <circle cx="3" cy="13" r="2" />
        <path d="M1 7.5a7.5 7.5 0 0 1 7.5 7.5M1 2a13 13 0 0 1 13 13" />
      </svg>
      <a href={href} type="application/atom+xml">{s(kind === 'releases' ? 'feed.releases' : 'feed.topic')}</a>
      <span className="hint">{s('feed.hint')}</span>
    </p>
  )
}
