import { createContext, useContext, useEffect, useState } from 'react'
import type { AtlasRelease } from './release'
import type { DataError } from './source'
import type { TopicDetail } from './types'

export type AtlasState =
  | { status: 'loading' }
  | { status: 'ready'; release: AtlasRelease; detail: (id: string) => Promise<TopicDetail | null> }
  | { status: 'error'; error: DataError }

export const AtlasContext = createContext<AtlasState>({ status: 'loading' })

export function useAtlas(): AtlasState {
  return useContext(AtlasContext)
}

export function useRelease(): AtlasRelease | null {
  const state = useAtlas()
  return state.status === 'ready' ? state.release : null
}

export type DetailState = { status: 'loading' | 'missing' | 'error'; detail: null } | { status: 'ready'; detail: TopicDetail }

/** topics/<id>.json for one topic; state is keyed by id so a new id never shows the previous topic's detail. */
export function useTopicDetail(id: string | undefined): DetailState {
  const state = useAtlas()
  const loader = state.status === 'ready' ? state.detail : null
  const [entry, setEntry] = useState<{ id: string; result: DetailState } | null>(null)
  useEffect(() => {
    if (!id || !loader) return
    let alive = true
    loader(id).then(
      (detail) => {
        if (alive) setEntry({ id, result: detail ? { status: 'ready', detail } : { status: 'missing', detail: null } })
      },
      () => {
        if (alive) setEntry({ id, result: { status: 'error', detail: null } })
      },
    )
    return () => {
      alive = false
    }
  }, [id, loader])
  if (!id) return { status: 'missing', detail: null }
  return entry && entry.id === id ? entry.result : { status: 'loading', detail: null }
}
