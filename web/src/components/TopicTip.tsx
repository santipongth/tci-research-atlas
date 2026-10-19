import type { Topic } from '../data/types'
import { fmtInt, fmtPct } from '../lib/format'
import { useI18n } from '../lib/i18n'
import { ciText, growthText, statusName } from '../lib/topicText'
import { StatusChip } from './StatusGlyph'

export function TopicTip({ topic, ciLevel }: { topic: Topic; ciLevel: number }) {
  const { t, name, other, otherLang } = useI18n()
  const m = topic.metrics
  const ci = ciText(t, m, ciLevel)
  return (
    <>
      <div className="tip-title">{name(topic)}</div>
      <div className="tip-sub" lang={otherLang}>{other(topic)}</div>
      <div className="tip-row"><StatusChip status={topic.status} label={statusName(t, topic.status)} small /></div>
      <div className="tip-row"><strong>{growthText(t, m)}</strong>{ci ? <span className="tip-muted"> · {ci}</span> : null}</div>
      <div className="tip-row"><strong>{fmtPct(m.share_recent, 2)}</strong> <span className="tip-muted">{t('tip.ofRecent')}</span></div>
      <div className="tip-row tip-muted">{t('tip.breadth', { j: fmtInt(m.n_journals_R), o: fmtInt(m.n_orgs_R) })}</div>
      <div className="tip-hint">{t('tip.open')}</div>
    </>
  )
}
