import type { Topic } from '../data/types'

/** Why a topic is worth starting on: growing from many sources, growing from few (room to join), or few institutions. */
export type IdeaKind = 'emerging' | 'watch' | 'few'

export interface Idea {
  topic: Topic
  kind: IdeaKind
  /** institutions working on it in the recent years, when the gaps module counted few */
  institutions: number | null
}

const ORDER: Record<IdeaKind, number> = { emerging: 0, watch: 1, few: 2 }

/**
 * Topics a student or advisor could start on: emerging (growing from many sources), watch (growing from few journals
 * or institutions) and any other rising topic that few institutions work on (`few`: topic id → institutions).
 * Low-data, stable and declining topics never appear. Ordered by kind, then signal score, then id; `group` narrows to
 * one field.
 */
export function pickIdeas(topics: readonly Topic[], few: ReadonlyMap<string, number>, group?: string | null): Idea[] {
  const out: Idea[] = []
  for (const tp of topics) {
    if (group && tp.group !== group) continue
    const n = few.get(tp.id) ?? null
    if (tp.status === 'EMERGING') out.push({ topic: tp, kind: 'emerging', institutions: n })
    else if (tp.status === 'WATCH') out.push({ topic: tp, kind: 'watch', institutions: n })
    else if (n !== null && tp.status === 'HOT') out.push({ topic: tp, kind: 'few', institutions: n })
  }
  return out.sort((a, b) => ORDER[a.kind] - ORDER[b.kind] || (b.topic.score ?? 0) - (a.topic.score ?? 0) || a.topic.id.localeCompare(b.topic.id))
}
