import { Link } from 'react-router'
import type { Topic } from '../data/types'
import { useI18n } from '../lib/i18n'
import { StatusGlyph } from './StatusGlyph'

export function TopicLink({ topic, showStatus = false }: { topic: Topic; showStatus?: boolean }) {
  const { name } = useI18n()
  return (
    <Link to={`/topics/${topic.id}`} className="topic-link">
      {showStatus ? <StatusGlyph status={topic.status} size={12} /> : null}
      <span>{name(topic)}</span>
    </Link>
  )
}
