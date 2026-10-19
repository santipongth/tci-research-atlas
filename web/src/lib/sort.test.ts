import { describe, expect, it } from 'vitest'
import { nextSort } from './sort'

describe('nextSort', () => {
  it('starts text columns ascending and numeric columns descending', () => {
    expect(nextSort(null, 'name', 'asc')).toEqual({ key: 'name', dir: 'asc' })
    expect(nextSort(null, 'share', 'desc')).toEqual({ key: 'share', dir: 'desc' })
    expect(nextSort({ key: 'share', dir: 'asc' }, 'name', 'asc')).toEqual({ key: 'name', dir: 'asc' })
  })
  it('flips direction when the same column is chosen again', () => {
    expect(nextSort({ key: 'name', dir: 'asc' }, 'name', 'asc')).toEqual({ key: 'name', dir: 'desc' })
    expect(nextSort({ key: 'name', dir: 'desc' }, 'name', 'asc')).toEqual({ key: 'name', dir: 'asc' })
    expect(nextSort({ key: 'share', dir: 'desc' }, 'share', 'desc')).toEqual({ key: 'share', dir: 'asc' })
  })
})
