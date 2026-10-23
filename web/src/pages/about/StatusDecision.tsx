import { StatusChip } from '../../components/StatusGlyph'
import { Steps } from '../../components/Steps'
import { ruleVars } from '../../lib/definition'
import { useI18n } from '../../lib/i18n'
import { STATUS_STEPS } from '../../lib/statusSteps'
import { statusName } from '../../lib/topicText'

/** The status rule as a decision path: four checks in the order the definition applies them, each with the statuses it
 *  decides (the same steps as /emerging). Loaded on demand. */
export default function StatusDecision({ level }: { level: number }) {
  const { t } = useI18n()
  const vars = ruleVars(level)
  return (
    <div className="ab-tree">
      <p className="ab-tree-h">{t('steps.h')}</p>
      <Steps
        label={t('steps.label')}
        items={STATUS_STEPS.map((st) => ({
          title: t(`steps.${st.key}.t` as const),
          body: t(`steps.${st.key}.b` as const, vars),
          foot: st.outcomes.map((o) => (
            <span className="step-o" key={o}>
              <span>{t(`steps.o.${o}` as const, vars)}</span>
              <span aria-hidden="true">→</span>
              <StatusChip status={o} label={statusName(t, o)} small />
            </span>
          )),
        }))}
      />
    </div>
  )
}
