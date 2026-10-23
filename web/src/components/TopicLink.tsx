import { Link } from 'react-router'
import type { Topic } from '../data/types'
import { useI18n } from '../lib/i18n'
import { statusName } from '../lib/topicText'
import { StatusGlyph } from './StatusGlyph'
import { TopicName } from './TopicName'

/** A topic's name as a link. With `showStatus` the status is written too (glyph in the link, its name beside it) — never a bare glyph. */
export function TopicLink({ topic, showStatus = false }: { topic: Topic; showStatus?: boolean }) {
  const { t } = useI18n()
  const link = (
    <Link to={`/topics/${topic.id}`} className="topic-link">
      {showStatus ? <StatusGlyph status={topic.status} size={12} /> : null}
      <span><TopicName topic={topic} /></span>
    </Link>
  )
  if (!showStatus) return link
  return (
    <span className="topic-ref">
      {link}
      <span className="topic-st">{statusName(t, topic.status)}</span>
    </span>
  )
}
