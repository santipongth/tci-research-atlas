import type { AtlasRelease, PreviousProblem } from '../data/release'
import type { StrKey } from '../strings'
import type { Vars } from './i18n'

const KEYS = { missing: 'prev.missing', offline: 'prev.offline', failed: 'prev.failed', damaged: 'prev.damaged' } as const satisfies Record<PreviousProblem, StrKey>

/** Why changes since the previous release are not shown, in words: not on this site, not in the one-release offline
 *  file, could not be loaded, or is damaged. null when the previous release was read (or there is none). */
export function previousNote(t: (key: StrKey, vars?: Vars) => string, release: Pick<AtlasRelease, 'previousMissing' | 'previousProblem'>): string | null {
  if (!release.previousMissing) return null
  return t(KEYS[release.previousProblem ?? 'missing'], { prev: release.previousMissing })
}
