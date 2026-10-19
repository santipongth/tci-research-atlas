import { createContext, useContext, useEffect, useState } from 'react'
import type { AtlasRelease } from './release'
import type { DataError } from './source'
import type { TopicDetail } from './types'

export type AtlasState =
  | { status: 'loading' }
  | { status: 'ready'; release: AtlasRelease; detail: (id: string) => Promise<TopicDetail | null>; file: (path: string) => Promise<unknown> }
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

export type FileState<T> = { status: 'loading' | 'missing' | 'error'; data: null } | { status: 'ready'; data: T }

/** One optional file of the release (a P2 module file), keyed by path so a new path never shows the previous data.
 *  'missing' = the release (or the offline file) does not carry it; null path = nothing to load. */
export function useReleaseFile<T>(path: string | null): FileState<T> {
  const state = useAtlas()
  const loader = state.status === 'ready' ? state.file : null
  const [entry, setEntry] = useState<{ path: string; result: FileState<T> } | null>(null)
  useEffect(() => {
    if (!path || !loader) return
    let alive = true
    loader(path).then(
      (value) => {
        if (alive) setEntry({ path, result: value === null || value === undefined ? { status: 'missing', data: null } : { status: 'ready', data: value as T } })
      },
      () => {
        if (alive) setEntry({ path, result: { status: 'error', data: null } })
      },
    )
    return () => {
      alive = false
    }
  }, [path, loader])
  if (!path) return { status: 'missing', data: null }
  return entry && entry.path === path ? entry.result : { status: 'loading', data: null }
}
