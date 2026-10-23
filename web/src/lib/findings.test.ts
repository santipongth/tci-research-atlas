import { describe, expect, it } from 'vitest'
import { fmtPts } from './format'
import { articlesPer, perVars } from './findings'

describe('articlesPer', () => {
  it('counts per 100 articles from 10 %', () => {
    expect(articlesPer(0.12)).toEqual({ k: 12, per: 100 })
    expect(articlesPer(0.1)).toEqual({ k: 10, per: 100 })
  })

  it('counts per 1,000 from 0.15 % to 10 %, with no jump at 1.5 %', () => {
    expect(articlesPer(0.015)).toEqual({ k: 15, per: 1000 })
    expect(articlesPer(0.0149)).toEqual({ k: 15, per: 1000 })
    expect(articlesPer(0.004)).toEqual({ k: 4, per: 1000 })
    expect(articlesPer(0.099)).toEqual({ k: 99, per: 1000 })
  })

  it('counts per 10,000 below 0.15 %, never rounding 0.04 % up to 1 in 1,000', () => {
    expect(articlesPer(0.0004)).toEqual({ k: 4, per: 10000 })
    expect(articlesPer(0.0014)).toEqual({ k: 14, per: 10000 })
  })

  it('says at least 1 for a real share, 0 for none, and nothing for a missing or broken share', () => {
    expect(articlesPer(0.00001)).toEqual({ k: 1, per: 10000 })
    expect(articlesPer(0)).toEqual({ k: 0, per: 10000 })
    expect(articlesPer(Number.NaN)).toBeNull()
    expect(articlesPer(Number.POSITIVE_INFINITY)).toBeNull()
    expect(articlesPer(null)).toBeNull()
    expect(articlesPer(-0.1)).toBeNull()
  })

  it('formats the numbers for the sentence', () => {
    expect(perVars(0.004)).toEqual({ k: '4', per: '1,000' })
    expect(perVars(0.0004)).toEqual({ k: '4', per: '10,000' })
    expect(perVars(Number.NaN)).toBeNull()
  })
})

describe('fmtPts', () => {
  it('prints a dash for a change that is not a number', () => {
    expect(fmtPts(Number.NaN)).toBe('–')
    expect(fmtPts(0.031)).toBe('+3')
  })
})
