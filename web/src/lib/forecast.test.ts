import { describe, expect, it } from 'vitest'
import type { TopicForecast } from '../data/types'
import { forecastView } from './forecast'

const fc = (show: boolean, years = [2025, 2026]) => ({ show, years }) as unknown as TopicForecast

describe('forecastView', () => {
  it('shows a forecast only when the release shows one for a classified topic', () => {
    expect(forecastView('EMERGING', fc(true))).toBe('show')
    expect(forecastView('STABLE', fc(true, []))).toBe('none')
    expect(forecastView('STABLE', fc(false, []))).toBe('noSkill')
  })

  it('never draws a forecast band for LOW_DATA, even if the data carries one', () => {
    expect(forecastView('LOW_DATA', fc(true))).toBe('lowData')
    expect(forecastView('LOW_DATA', null)).toBe('lowData')
  })

  it('says "too few articles" only for LOW_DATA; other topics without a forecast get the neutral reason', () => {
    expect(forecastView('HOT', fc(false))).toBe('noSkill')
    expect(forecastView('HOT', null)).toBe('none')
    expect(forecastView('DECLINING', undefined)).toBe('none')
  })
})
