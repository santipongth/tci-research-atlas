import { describe, expect, it } from 'vitest'
import { translate } from './i18n'
import { previousNote } from './previous'

const t = (key: Parameters<typeof translate>[1], vars?: Record<string, string | number>) => translate('en', key, vars)

describe('previousNote', () => {
  it('says why changes are not shown, with "reload" only when the request failed', () => {
    expect(previousNote(t, { previousMissing: null, previousProblem: null })).toBeNull()
    expect(previousNote(t, { previousMissing: '2026Q3', previousProblem: 'failed' })).toContain('Reload')
    const damaged = previousNote(t, { previousMissing: '2026Q3', previousProblem: 'damaged' })
    expect(damaged).toContain('2026Q3')
    expect(damaged).not.toContain('Reload')
    expect(previousNote(t, { previousMissing: '2026Q3', previousProblem: 'offline' })).toContain('offline')
    expect(previousNote(t, { previousMissing: '2026Q3', previousProblem: null })).toContain('not on this site')
  })
})
