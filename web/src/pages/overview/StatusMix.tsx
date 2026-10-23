import { DataTable, type Column } from '../../components/DataTable'
import { Figure } from '../../components/Figure'
import { StatusChip } from '../../components/StatusGlyph'
import { TopicTip } from '../../components/TopicTip'
import { StatusWaffle } from '../../charts/StatusWaffle'
import { percentOf, waffleGroups, type WaffleGroup } from '../../charts/infographic'
import type { AtlasRelease } from '../../data/release'
import { fmtInt } from '../../lib/format'
import { useI18n } from '../../lib/i18n'
import { figureCsv } from '../../lib/tableCsv'
import { statusMeaning, statusName } from '../../lib/topicText'
import type { View } from '../../lib/urlState'

/** Every topic by status as a waffle (one square per topic), with the counts as its table. */
export function StatusMix({ release, number, tableNo, view, onView, compact = false, toggle }: {
  release: AtlasRelease
  number: number
  tableNo: number
  view: View
  onView: (v: View) => void
  compact?: boolean
  toggle?: 'tabs' | 'buttons'
}) {
  const { t } = useI18n()
  const total = release.topics.length
  const groups = waffleGroups(release.topics)
  const tableTitle = t('table.n', { n: tableNo, title: t('ov.wf.table') })
  const columns: Column<WaffleGroup>[] = [
    { key: 'status', csvHeader: 'status', header: t('col.status'), rowHeader: true, cell: (g) => <StatusChip status={g.status} label={statusName(t, g.status)} small />, csv: (g) => g.status },
    { key: 'meaning', csvHeader: 'meaning', header: t('col.meaning'), cell: (g) => statusMeaning(t, g.status), csv: (g) => statusMeaning(t, g.status) },
    { key: 'n', csvHeader: 'topics', header: t('col.topics'), numeric: true, cell: (g) => fmtInt(g.topics.length), sortValue: (g) => g.topics.length },
    { key: 'pct', csvHeader: 'share_of_topics', header: t('ov.wf.pct'), unit: t('unit.pct'), numeric: true, cell: (g) => String(percentOf(g.topics.length, total)), sortValue: (g) => g.topics.length, csv: (g) => (total ? g.topics.length / total : 0) },
  ]
  return (
    <Figure
      id="fig-statusmix"
      number={number}
      title={t('ov.wf.title', { n: fmtInt(total) })}
      tableTitle={tableTitle}
      csv={figureCsv(`atlas-${release.overview.release}-status-counts.csv`, groups, columns)}
      how={<p>{t('ov.wf.how')}</p>}
      source={t('source.line', { release: release.overview.release })}
      view={view}
      onView={onView}
      toggle={toggle}
      chart={
        <StatusWaffle
          groups={groups}
          total={total}
          statusLabel={(s) => statusName(t, s)}
          meaning={(s) => statusMeaning(t, s)}
          tipFor={(tp) => <TopicTip topic={tp} ciLevel={release.ciLevel} />}
          compact={compact}
        />
      }
      table={<DataTable caption={tableTitle} rows={groups} columns={columns} rowKey={(g) => g.status} stack={false} />}
    />
  )
}
