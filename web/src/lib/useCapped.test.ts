import { describe, expect, it } from 'vitest'
import { keepSelected } from './useCapped'

describe('keepSelected', () => {
  const items = Array.from({ length: 30 }, (_, i) => `t${i}`)
  const shown = items.slice(0, 20)
  it('adds the selected item when the cap hides it', () => {
    expect(keepSelected(shown, items, (x) => x === 't25')).toEqual([...shown, 't25'])
  })
  it('leaves the rows alone when the selection is shown, absent or empty', () => {
    expect(keepSelected(shown, items, (x) => x === 't3')).toBe(shown)
    expect(keepSelected(shown, items, (x) => x === 'other')).toBe(shown)
  })
})
