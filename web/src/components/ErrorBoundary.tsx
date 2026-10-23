import { Component, type ErrorInfo, type ReactNode } from 'react'
import { isChunkLoadError, shouldReloadOnce } from '../lib/chunkError'
import { ErrorFailure } from './ErrorFailure'

interface Props {
  children: ReactNode
  /** when this changes (the visitor went to another page or changed its query) a failure is forgotten and the page is tried again */
  resetKey?: string
  /** what replaces the failed part; default: the page-area failure (header and menu stay) */
  fallback?: (chunk: boolean) => ReactNode
}

/** No white page, whatever throws while rendering: a stale lazy chunk after a redeploy (reloads once), a data file
 *  in an unexpected shape, a missing string. Layout wraps the page area (header and menu stay); main.tsx wraps the
 *  whole app (the site chrome itself); App.tsx wraps the embeddable widgets with a compact failure. */
export class ErrorBoundary extends Component<Props, { error: unknown; failed: boolean }> {
  state = { error: null as unknown, failed: false }

  static getDerivedStateFromError(error: unknown) {
    return { error, failed: true }
  }

  componentDidCatch(error: unknown, info: ErrorInfo) {
    console.error(error, info.componentStack)
    if (isChunkLoadError(error)) {
      let storage: Storage | null = null
      try {
        storage = window.sessionStorage
      } catch {
        /* storage blocked: no automatic reload */
      }
      if (shouldReloadOnce(storage, Date.now())) window.location.reload()
    }
  }

  componentDidUpdate(prev: Props) {
    if (this.state.failed && prev.resetKey !== this.props.resetKey) this.setState({ error: null, failed: false })
  }

  render() {
    if (!this.state.failed) return this.props.children
    const chunk = isChunkLoadError(this.state.error)
    return this.props.fallback ? this.props.fallback(chunk) : <ErrorFailure chunk={chunk} />
  }
}
