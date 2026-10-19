import { useEffect, useState, type ReactNode } from 'react'
import { AtlasContext, type AtlasState } from './atlasContext'
import { createDetailLoader, loadRelease } from './release'
import { toDataError, type DataSource } from './source'

export function AtlasProvider({ source, children }: { source: DataSource; children: ReactNode }) {
  const [state, setState] = useState<AtlasState>({ status: 'loading' })
  useEffect(() => {
    let alive = true
    loadRelease(source).then(
      (release) => {
        if (alive) setState({ status: 'ready', release, detail: createDetailLoader(source, release.latest.release) })
      },
      (e: unknown) => {
        if (alive) setState({ status: 'error', error: toDataError(e) })
      },
    )
    return () => {
      alive = false
    }
  }, [source])
  return <AtlasContext.Provider value={state}>{children}</AtlasContext.Provider>
}
