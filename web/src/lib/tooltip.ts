import { createContext, useContext, type ReactNode } from 'react'

/** Hover/focus tooltip. It only repeats what the page also shows in text or tables. */
export interface TooltipApi {
  show(content: ReactNode, x: number, y: number): void
  showAt(content: ReactNode, el: Element): void
  hide(): void
}

export const TooltipContext = createContext<TooltipApi>({ show() {}, showAt() {}, hide() {} })

export function useTooltip(): TooltipApi {
  return useContext(TooltipContext)
}
