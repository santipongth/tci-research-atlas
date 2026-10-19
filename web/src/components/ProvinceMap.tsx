import { TH_PROVINCE_NAMES, TH_PROVINCE_PATHS, TH_VIEWBOX } from '../geo/thProvinces'
import { bucketOf, quantileBreaks } from '../lib/executive'
import { useI18n } from '../lib/i18n'

/**
 * Choropleth of Thailand's 77 provinces: 5 quantile classes of the sequential ramp (--seq-1…5), "no data" apart.
 * The figure's table view is the complete, accessible equivalent; each outline names its province and value on hover.
 */
export function ProvinceMap({ values, format, label, noData, range }: {
  values: ReadonlyMap<string, number | null>
  format: (v: number) => string
  label: string
  noData: string
  range: (from: string, to: string) => string
}) {
  const { lang } = useI18n()
  const known = [...values.values()].filter((v): v is number => v !== null && Number.isFinite(v))
  const breaks = quantileBreaks(known)
  const low = known.length ? Math.min(...known) : 0
  const name = (code: string) => {
    const n = TH_PROVINCE_NAMES[code]
    return n ? (lang === 'en' ? n[1] : n[0]) : code
  }
  return (
    <>
      <ul className="pkey">
        {breaks.map((b, i) => (
          <li key={b}>
            <span className={`sw sw-${i}`} aria-hidden="true" />
            {range(format(i === 0 ? low : breaks[i - 1]), format(b))}
          </li>
        ))}
        <li>
          <span className="sw sw-none" aria-hidden="true" />
          {noData}
        </li>
      </ul>
      <svg className="pmap" viewBox={TH_VIEWBOX} role="img" aria-label={label}>
        {Object.entries(TH_PROVINCE_PATHS).map(([code, d]) => {
          const v = values.get(code) ?? null
          const b = bucketOf(v, breaks)
          return (
            <path key={code} d={d} className={b < 0 ? 'pv-none' : `pv-${b}`}>
              <title>{`${name(code)}: ${v === null ? noData : format(v)}`}</title>
            </path>
          )
        })}
      </svg>
    </>
  )
}
