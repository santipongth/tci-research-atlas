import { StoryLines, type StorySeries } from '../../charts/StoryLines'
import { Card, SeeAll } from '../../components/dashboard/Card'
import { RankRows } from '../../components/dashboard/RankRows'
import { Segmented } from '../../components/dashboard/Segmented'
import { StatusChip } from '../../components/StatusGlyph'
import type { AtlasRelease } from '../../data/release'
import type { Topic } from '../../data/types'
import { fmtInt, fmtSignedPct } from '../../lib/format'
import { useI18n } from '../../lib/i18n'
import { sortBy } from '../../lib/sort'
import { statusName } from '../../lib/topicText'

const seriesOf = (release: AtlasRelease, tp: Topic) => (release.series.topics[tp.id] ?? []).map((v) => (Number.isFinite(v) ? v : null))

/** Card: articles a year of the fastest-growing topics — the leader in TCI blue, the rest grey, focus on point/tab. */
export function RisingChartCard({ release, risers }: { release: AtlasRelease; risers: readonly Topic[] }) {
  const { t, name } = useI18n()
  const years = release.series.years
  // a large hot topic (hundreds of articles a year) would flatten the small risers into the axis: chart those without it
  const small = risers.filter((tp) => tp.status !== 'HOT')
  const shown = small.length >= 2 ? small : risers
  const leader = shown[0]
  const series: StorySeries[] = shown.map((tp) => ({ id: tp.id, label: name(tp), values: seriesOf(release, tp) }))
  if (!leader || series.length < 2) return null
  return (
    <Card span={8} title={t('ov.d.rising')} info={t('ov.story.fig', { n: fmtInt(series.length), a: years[0], b: years[years.length - 1] })}>
      <StoryLines
        years={years}
        series={series}
        initial={leader.id}
        height={340}
        format={(v) => fmtInt(v)}
        label={t('ov.story.label', { n: fmtInt(series.length), topic: name(leader) })}
        note={(s) => {
          // the rise over the last three years with articles, e.g. "จาก 18 เรื่องในปี 2022 เป็น 95 เรื่องในปี 2024"
          const last = s.values.reduce<number>((a, v, k) => (v !== null ? k : a), -1)
          let first = Math.max(0, last - 2)
          while (first < last && !((s.values[first] ?? 0) > 0)) first++
          return t('ov.story.note', { a: fmtInt(s.values[first]), y0: years[first], b: fmtInt(s.values[last]), y1: years[last] })
        }}
      />
    </Card>
  )
}

/** Card: the five topics moving most — rising (by how clearly they grow) or falling (by how fast they shrink) — each
 *  with its status, its growth a year and a small trend line of articles. */
export function MovesCard({ release, risers, move, onMove }: {
  release: AtlasRelease
  risers: readonly Topic[]
  move: 'up' | 'down'
  onMove: (m: 'up' | 'down') => void
}) {
  const { t, name } = useI18n()
  const fallers = sortBy(release.topics.filter((tp) => tp.status === 'DECLINING' && Number.isFinite(tp.metrics.share_growth)), (tp) => tp.metrics.share_growth, 'asc').slice(0, 5)
  const list = move === 'up' ? risers : fallers
  if (!risers.length && !fallers.length) return null
  return (
    <Card
      span={4}
      title={t('ov.d.moves')}
      info={t('ov.d.movesInfo')}
      action={<SeeAll to={move === 'down' ? '/topics?status=DECLINING' : '/topics'} label={t('dash.seeAll')} />}
    >
      <Segmented label={t('ov.d.movesSwitch')} value={move} onChange={onMove} options={[{ id: 'up', label: t('ov.d.up') }, { id: 'down', label: t('ov.d.down') }]} />
      {list.length ? (
        <RankRows
          label={t('ov.d.moves')}
          rows={list.map((tp) => ({
            key: tp.id,
            to: `/topics/${tp.id}`,
            name: name(tp),
            meta: <StatusChip status={tp.status} label={statusName(t, tp.status)} small />,
            value: <b className={move === 'up' ? 'rise-g' : 'rise-g is-down'}>{fmtSignedPct(tp.metrics.share_growth, 0)} {t('perYear')}</b>,
            trend: seriesOf(release, tp),
          }))}
        />
      ) : (
        <p className="card-empty">{t(move === 'up' ? 'ov.answerNone' : 'ov.d.noneDown')}</p>
      )}
    </Card>
  )
}
