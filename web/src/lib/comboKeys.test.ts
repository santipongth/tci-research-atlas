import { describe, expect, it } from 'vitest'
import { comboKey } from './comboKeys'

const base = { open: true, showList: true, active: 1, count: 4, hasQuery: true }

describe('comboKey', () => {
  it('does not pick with Enter when the list is closed (after Escape)', () => {
    expect(comboKey('Enter', { ...base, open: false, showList: false }).pick).toBe(false)
    expect(comboKey('Enter', base).pick).toBe(true)
    expect(comboKey('Enter', { ...base, hasQuery: false, showList: false }).pick).toBe(false)
  })
  it('reopens the list with ArrowUp as well as ArrowDown', () => {
    expect(comboKey('ArrowUp', { ...base, open: false, showList: false }).open).toBe(true)
    expect(comboKey('ArrowDown', { ...base, open: false, showList: false }).open).toBe(true)
    expect(comboKey('ArrowUp', base).active).toBe(0)
    expect(comboKey('ArrowDown', base).active).toBe(2)
  })
  it('ArrowDown on a closed list opens it on the first option', () => {
    expect(comboKey('ArrowDown', { ...base, open: false, showList: false, active: 2 })).toMatchObject({ open: true, active: 0 })
  })
  it('Escape closes an open list, then clears the query', () => {
    expect(comboKey('Escape', base)).toMatchObject({ open: false, clear: false })
    expect(comboKey('Escape', { ...base, open: false, showList: false })).toMatchObject({ clear: true })
  })
})
