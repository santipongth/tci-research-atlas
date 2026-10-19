import type { Entry } from '../strings/define'
import { useI18n } from '../lib/i18n'

/** A topic's name in the UI language; a Thai name shown inside the English UI (no English name yet) carries lang="th". */
export function TopicName({ topic }: { topic: Entry }) {
  const { lang, name } = useI18n()
  return lang === 'en' && !topic.en ? <span lang="th">{name(topic)}</span> : <>{name(topic)}</>
}
