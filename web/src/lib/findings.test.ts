import { describe, expect, it } from 'vitest'
import { articlesPer, perVars } from './findings'

describe('articlesPer', () => {
  it('counts per 100 articles for a large share', () => {
    expect(articlesPer(0.12)).toEqual({ k: 12, per: 100 })
    expect(articlesPer(0.015)).toEqual({ k: 2, per: 100 })
  })

  it('counts per 1,000 for a small share, never rounding 0.4 % up to 1 in 100', () => {
    expect(articlesPer(0.004)).toEqual({ k: 4, per: 1000 })
    expect(articlesPer(0.0149)).toEqual({ k: 15, per: 1000 })
  })

  it('says at least 1', () => {
    expect(articlesPer(0.00004)).toEqual({ k: 1, per: 1000 })
    expect(articlesPer(0)).toEqual({ k: 1, per: 1000 })
  })

  it('formats the numbers for the sentence', () => {
    expect(perVars(0.004)).toEqual({ k: '4', per: '1,000' })
  })
})
