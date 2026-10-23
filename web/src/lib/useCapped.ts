import { useState } from 'react'

/** A long visual list cut to its first `limit` items with a "show all" switch (props for `ListMore`). The table view keeps every row. */
export function useCapped<T>(items: readonly T[], limit: number) {
  const [expanded, setExpanded] = useState(false)
  return {
    shown: expanded ? items : items.slice(0, limit),
    more: { total: items.length, limit, expanded, onToggle: () => setExpanded((e) => !e) },
  }
}

/**
 * The capped rows plus the selected item when the cap hides it (appended after them, still in list order), so a pick
 * made elsewhere — a topic chosen on the map — always has its row, with its `aria-pressed`, in the list.
 */
export function keepSelected<T>(shown: readonly T[], items: readonly T[], isSelected: (item: T) => boolean): readonly T[] {
  if (shown.some(isSelected)) return shown
  const pick = items.find(isSelected)
  return pick === undefined ? shown : [...shown, pick]
}
