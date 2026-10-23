import { Link } from 'react-router'
import { EmptyState } from '../components/EmptyState'
import { HowNote } from '../components/HowNote'
import { PageHeader } from '../components/PageHeader'
import { RequireRelease } from '../components/RequireRelease'
import { Section } from '../components/Section'
import { StatusChip } from '../components/StatusGlyph'
import { TopicLink } from '../components/TopicLink'
import { useReleaseFile } from '../data/atlasContext'
import { groupName, hasModule, MODULE_FILES, type AtlasRelease } from '../data/release'
import type { GapsFile, Topic } from '../data/types'
import { windows } from '../lib/definition'
import { fmtInt, fmtSignedPct } from '../lib/format'
import { useI18n, useStrings } from '../lib/i18n'
import { pickIdeas, type Idea } from '../lib/ideas'
import { statusName } from '../lib/topicText'
import { ideasCodec } from '../lib/urlState'
import { useUrlState } from '../lib/useUrlState'
import { ideas as ID } from '../strings/ideas'

/** "หัวข้อน่าทำ": growing or under-studied topics by field, with a plain reason each, and topic pairs to join. */
export default function IdeasPage() {
  const s = useStrings(ID)
  return <RequireRelease title={s('id.title')}>{(release) => <Ideas release={release} />}</RequireRelease>
}

function Ideas({ release }: { release: AtlasRelease }) {
  const s = useStrings(ID)
  const { t, lang, name } = useI18n()
  const [state, update] = useUrlState(ideasCodec)
  const gapsFile = useReleaseFile<GapsFile>(hasModule(release, 'gaps') ? MODULE_FILES.gaps : null)
  const gaps = gapsFile.status === 'ready' ? gapsFile.data : null
  const few = new Map((gaps?.few_institutions ?? []).map((f) => [f.topic, f.institutions]))
  const groups = [...new Set(release.topics.map((tp) => tp.group))].sort((a, b) => groupName(release, a, lang).localeCompare(groupName(release, b, lang), lang))
  const group = groups.includes(state.g) ? state.g : ''
  const list = pickIdeas(release.topics, few, group || null)
  const R = windows(release.overview.last_complete_year).R
  const why = (i: Idea) => {
    const g = fmtSignedPct(i.topic.metrics.share_growth, 0)
    return i.kind === 'few' ? s('id.why.few', { k: fmtInt(i.institutions) }) : s(i.kind === 'emerging' ? 'id.why.emerging' : 'id.why.watch', { g })
  }
  const byId = (id: string): Topic | undefined => release.topicById.get(id)
  const bridges = (gaps?.bridges ?? []).filter((b) => byId(b.a) && byId(b.b) && (!group || byId(b.a)?.group === group || byId(b.b)?.group === group))
  return (
    <div className="container">
      <PageHeader title={s('id.title')} lede={s('id.lede')}>
        <p className="pv-pick">
          <label htmlFor="id-field">{s('id.field')}</label>
          <select id="id-field" value={group} onChange={(e) => update({ g: e.target.value })}>
            <option value="">{s('id.all')}</option>
            {groups.map((g) => (
              <option key={g} value={g}>{groupName(release, g, lang)}</option>
            ))}
          </select>
          <span className="hint">{s('id.list.count', { n: fmtInt(list.length) })}</span>
        </p>
      </PageHeader>
      <Section id="ideas" title={s('id.list.h')} intro={list[0] ? s('id.list.intro', { topic: name(list[0].topic), why: why(list[0]) }) : undefined}>
        {list.length ? (
          <ol className="ideas">
            {list.map((i) => {
              const m = i.topic.metrics
              return (
                <li key={i.topic.id} className="idea">
                  <h3><TopicLink topic={i.topic} /></h3>
                  <p className="idea-k">
                    <StatusChip status={i.topic.status} label={statusName(t, i.topic.status)} small /> {why(i)}
                  </p>
                  <p className="idea-f">
                    {s('id.facts', { n: fmtInt(m.count_recent), a: R[0], b: R[1], j: fmtInt(m.n_journals_R), o: fmtInt(m.n_orgs_R) })}
                    {i.institutions !== null && i.kind !== 'few' ? <> · {s('id.fewNote', { k: fmtInt(i.institutions) })}</> : null}
                  </p>
                  <p className="idea-go"><Link to={`/topics/${i.topic.id}`}>{s('id.open')}</Link></p>
                </li>
              )
            })}
          </ol>
        ) : (
          <EmptyState title={s('id.none')} />
        )}
        <HowNote>
          <p>{s('id.how', { k: fmtInt(gaps?.max_institutions ?? 5) })}</p>
        </HowNote>
      </Section>
      {bridges.length ? (
        <Section id="bridges" title={s('id.bridge.h')} intro={s('id.bridge.intro')}>
          <ul className="ideas-pairs">
            {bridges.map((b) => (
              <li key={`${b.a}-${b.b}`}>
                <span className="idea-pair">
                  <TopicLink topic={byId(b.a) as Topic} showStatus /> <span className="hint">{s('id.bridge.plus')}</span> <TopicLink topic={byId(b.b) as Topic} showStatus />
                </span>
                <span className="hint">{b.shared > 0 ? s('id.bridge.k', { k: fmtInt(b.shared) }) : s('id.bridge.none')}</span>
              </li>
            ))}
          </ul>
        </Section>
      ) : null}
      <p className="source">{t('source.line', { release: release.overview.release })}</p>
    </div>
  )
}
