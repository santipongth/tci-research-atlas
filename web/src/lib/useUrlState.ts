import { useCallback, useMemo } from 'react'
import { useSearchParams } from 'react-router'
import { mergeParams, type Codec } from './urlState'

/** Page state in the hash query (#/emerging?status=WATCH): shareable, survives reloads, defaults not written. */
export function useUrlState<T>(codec: Codec<T>): [T, (patch: Partial<T>) => void] {
  const [params, setParams] = useSearchParams()
  const state = useMemo(() => codec.parse(params), [codec, params])
  const update = useCallback(
    (patch: Partial<T>) => {
      setParams(
        (prev) => mergeParams(codec, prev, patch),
        { replace: true },
      )
    },
    [codec, setParams],
  )
  return [state, update]
}
