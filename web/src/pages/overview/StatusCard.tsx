import { StatusDonut } from '../../charts/StatusDonut'
import { percentOf, waffleGroups } from '../../charts/infographic'
import { Card, SeeAll, type Span } from '../../components/dashboard/Card'
import type { AtlasRelease } from '../../data/release'
import { fmtInt } from '../../lib/format'
import { useI18n } from '../../lib/i18n'
import { statusName } from '../../lib/topicText'

/** Card: every topic by status as a ring with its list (count + share printed beside each status). */
export function StatusCard({ release, span }: { release: AtlasRelease; span: Span }) {
  const { t } = useI18n()
  const total = release.topics.length
  const groups = waffleGroups(release.topics)
  return (
    <Card span={span} className="card-center" title={t('ov.d.status')} action={<SeeAll to="/topics" label={t('dash.seeAll')} />}>
      <StatusDonut
        rows={groups.map((g) => ({ status: g.status, n: g.topics.length }))}
        total={fmtInt(total)}
        totalUnit={t('ov.d.statusUnit')}
        label={t('ov.d.statusLabel', { n: fmtInt(total) })}
        name={(s) => statusName(t, s)}
        pct={(n) => `${percentOf(n, total)}%`}
      />
    </Card>
  )
}
