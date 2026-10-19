import { Fragment } from 'react'
import { Link } from 'react-router'
import type { Segment } from '../lib/highlight'

/** Headline/bullet text: figures under the highlighter band, topic names as links. */
export function SegmentText({ segments, mark = true }: { segments: readonly Segment[]; mark?: boolean }) {
  return (
    <>
      {segments.map((s, i) => {
        if (s.kind === 'text') return <Fragment key={i}>{s.text}</Fragment>
        if (s.kind === 'figure') return mark ? <mark key={i}>{s.text}</mark> : <strong key={i}>{s.text}</strong>
        return (
          <Link key={i} to={`/topics/${s.id}`}>
            {mark ? <mark>{s.text}</mark> : s.text}
          </Link>
        )
      })}
    </>
  )
}
