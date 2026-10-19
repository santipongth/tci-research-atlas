import { Link } from 'react-router'
import type { Topic } from '../data/types'
import { StatusGlyph } from './StatusGlyph'
import { TopicName } from './TopicName'

export function TopicLink({ topic, showStatus = false }: { topic: Topic; showStatus?: boolean }) {
  return (
    <Link to={`/topics/${topic.id}`} className="topic-link">
      {showStatus ? <StatusGlyph status={topic.status} size={12} /> : null}
      <span><TopicName topic={topic} /></span>
    </Link>
  )
}
