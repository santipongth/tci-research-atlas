import type { ReactNode } from 'react'
import type { Topic } from '../data/types'
import { ruleVars } from '../lib/definition'
import { fmtInt } from '../lib/format'
import { useI18n } from '../lib/i18n'
import type { StatusId } from '../lib/status'
import { sortBy } from '../lib/sort'
import { statusName } from '../lib/topicText'
import { StatusChip } from './StatusGlyph'
import { TopicLink } from './TopicLink'

type Question = 'enough' | 'fast' | 'sources' | 'large' | 'falling'

/**
 * "สถานะมาจากไหน" as a decision diagram: one question per row down a spine; each answer that settles a status branches
 * to the right into that status, with how many topics got it this release and one real example. The rule and its
 * thresholds are the same `steps.*` strings and `ruleVars` the definition uses (lib/definition.ts).
 */
export function StatusFlowchart({ topics, level, current }: { topics: readonly Topic[]; level: number; current?: StatusId }) {
  const { t } = useI18n()
  const vars = ruleVars(level)
  const of = (st: StatusId) => sortBy(topics.filter((tp) => tp.status === st), (tp) => tp.score, 'desc')
  const outcome = (st: StatusId, when: string) => {
    const list = of(st)
    return (
      <div className={st === current ? 'sfc-out is-current' : 'sfc-out'}>
        <p className="sfc-when">{when}</p>
        <p className="sfc-st">
          <StatusChip status={st} label={statusName(t, st)} />
          {topics.length ? <span className="sfc-n">{t('flow.count', { n: fmtInt(list.length) })}</span> : null}
        </p>
        {list[0] ? <p className="sfc-eg">{t('flow.eg')} <TopicLink topic={list[0]} /></p> : null}
      </div>
    )
  }
  const row = (q: Question, title: string, body: string | null, outs: ReactNode, next: string | null) => (
    <li className="sfc-row" key={q}>
      <div className="sfc-q">
        <p className="sfc-qt">{title}</p>
        {body ? <p className="sfc-qb">{body}</p> : null}
        {next ? <p className="sfc-next" aria-hidden="true">{next}</p> : null}
      </div>
      <div className="sfc-outs">{outs}</div>
    </li>
  )
  return (
    <ol className="sfc" aria-label={t('steps.label')}>
      {row('enough', t('steps.enough.t'), t('steps.enough.b', vars), outcome('LOW_DATA', t('flow.no')), t('flow.yesNext'))}
      {row('fast', t('steps.fast.t'), t('steps.fast.b', vars), (
        <div className="sfc-sub">
          <p className="sfc-subq">{t('flow.yes')} — {t('flow.sources', vars)}</p>
          <div className="sfc-pair">
            {outcome('EMERGING', t('flow.yes'))}
            {outcome('WATCH', t('flow.notYet'))}
          </div>
        </div>
      ), t('flow.noNext'))}
      {row('large', t('steps.large.t'), t('steps.large.b', vars), outcome('HOT', t('flow.yes')), t('flow.noNext'))}
      {row('falling', t('steps.falling.t'), t('steps.falling.b', vars), (
        <div className="sfc-pair">
          {outcome('DECLINING', t('flow.yes'))}
          {outcome('STABLE', t('flow.no'))}
        </div>
      ), null)}
    </ol>
  )
}
