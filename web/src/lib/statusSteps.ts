import type { StatusId } from './status'

export type StepKey = 'enough' | 'fast' | 'large' | 'falling'

/**
 * How a topic gets its status, as four checks in the order the definition applies them (docs/EMERGING_SPEC.md):
 * enough data → small and growing fast (emerging, or watch when it comes from only a few sources) → large and still
 * growing (hot) → clearly shrinking (declining), and stable when none applies. Wording lives in strings (`steps.*`);
 * every threshold in it comes from `ruleVars`.
 */
export const STATUS_STEPS: readonly { key: StepKey; outcomes: readonly StatusId[] }[] = [
  { key: 'enough', outcomes: ['LOW_DATA'] },
  { key: 'fast', outcomes: ['EMERGING', 'WATCH'] },
  { key: 'large', outcomes: ['HOT'] },
  { key: 'falling', outcomes: ['DECLINING', 'STABLE'] },
]

/** The step (0–3) at which a status is decided. */
export function stepOf(status: StatusId): number {
  return Math.max(0, STATUS_STEPS.findIndex((s) => s.outcomes.includes(status)))
}
