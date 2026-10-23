import { useState } from 'react'

/** A long visual list cut to its first `limit` items with a "show all" switch (props for `ListMore`). The table view keeps every row. */
export function useCapped<T>(items: readonly T[], limit: number) {
  const [expanded, setExpanded] = useState(false)
  return {
    shown: expanded ? items : items.slice(0, limit),
    more: { total: items.length, limit, expanded, onToggle: () => setExpanded((e) => !e) },
  }
}
