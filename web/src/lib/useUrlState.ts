import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router'
import type { Codec } from './urlState'

/** Page state in the hash query (#/emerging?status=WATCH): shareable, survives reloads, defaults not written. */
export function useUrlState<T>(codec: Codec<T>): [T, (patch: Partial<T>) => void] {
  const [params, setParams] = useSearchParams()
  const state = useMemo(() => codec.parse(params), [codec, params])
  const update = useCallback(
    (patch: Partial<T>) => {
      setParams(
        (prev) => {
          const next = codec.write({ ...codec.parse(prev), ...patch })
          const lang = prev.get('lang')
          if (lang) next.set('lang', lang)
          return next
        },
        { replace: true },
      )
    },
    [codec, setParams],
  )
  return [state, update]
}
