export interface ComboState {
  open: boolean
  showList: boolean
  active: number
  count: number
  hasQuery: boolean
}

export interface ComboAction {
  open?: boolean
  active?: number
  pick: boolean
  clear: boolean
  prevent: boolean
}

/** Keyboard behaviour of the topic-search combobox (ARIA 1.2), kept pure so it can be tested. */
export function comboKey(key: string, s: ComboState): ComboAction {
  const none: ComboAction = { pick: false, clear: false, prevent: false }
  const last = Math.max(s.count - 1, 0)
  switch (key) {
    case 'ArrowDown':
      // a closed list opens on its first option; an open one moves down
      return { ...none, prevent: true, open: true, active: s.showList ? Math.min(s.active + 1, last) : 0 }
    case 'ArrowUp':
      return { ...none, prevent: true, open: true, active: Math.max(s.active - 1, 0) }
    case 'Enter':
      return s.showList && s.hasQuery && s.active < s.count ? { ...none, prevent: true, pick: true } : none
    case 'Escape':
      return s.open ? { ...none, prevent: true, open: false } : { ...none, clear: true }
    default:
      return none
  }
}
