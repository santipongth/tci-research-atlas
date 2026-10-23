import { useState } from 'react'

/** How many rows a list shows after `presses` presses of "แสดงเพิ่ม" (never more than `total`). */
export function pagedCount(total: number, step: number, presses: number): number {
  return Math.max(0, Math.min(total, step * (presses + 1)))
}

/**
 * A long list shown `step` rows at a time (the props of `MoreRows`). `resetKey` starts it over when the list itself
 * changes (another status, another sort), without an effect.
 */
export function usePaged<T>(items: readonly T[], step: number, resetKey = '') {
  const [state, setState] = useState({ key: resetKey, presses: 0 })
  const presses = state.key === resetKey ? state.presses : 0
  const n = pagedCount(items.length, step, presses)
  return {
    shown: items.slice(0, n),
    more: {
      total: items.length,
      shown: n,
      step,
      onMore: () => setState({ key: resetKey, presses: presses + 1 }),
      onReset: () => setState({ key: resetKey, presses: 0 }),
    },
  }
}
