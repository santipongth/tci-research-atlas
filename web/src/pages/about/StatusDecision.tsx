import { StatusFlowchart } from '../../components/StatusFlowchart'
import type { Topic } from '../../data/types'
import { useI18n } from '../../lib/i18n'

/** The status rule as the decision diagram /emerging shows, with this release's counts and examples. Loaded on demand. */
export default function StatusDecision({ level, topics }: { level: number; topics: readonly Topic[] }) {
  const { t } = useI18n()
  return (
    <div className="ab-tree">
      <p className="ab-tree-h">{t('steps.h')}</p>
      <StatusFlowchart topics={topics} level={level} />
    </div>
  )
}
