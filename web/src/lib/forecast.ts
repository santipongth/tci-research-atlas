import type { TopicForecast } from '../data/types'
import type { StatusId } from './status'

/** What the topic page says about a forecast: draw it, or which reason to give for "แนวโน้มไม่แน่นอน / Trend uncertain". */
export type ForecastView = 'show' | 'lowData' | 'noSkill' | 'none'

/**
 * LOW_DATA never gets a band (even if the data carries one) and is the only case told "too few articles";
 * a forecast the models could not beat the naive baseline with is "no skill"; any other missing forecast gets the neutral reason.
 */
export function forecastView(status: StatusId, fc: TopicForecast | null | undefined): ForecastView {
  if (status === 'LOW_DATA') return 'lowData'
  if (!fc) return 'none'
  if (fc.show === false) return 'noSkill'
  return fc.years.length === 0 ? 'none' : 'show'
}
