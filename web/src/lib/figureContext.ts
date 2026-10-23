import { createContext, useContext } from 'react'

/** What a `Figure` already shows in its caption row, so a `DataTable` inside it does not repeat it. */
export interface FigureFrame {
  /** the caption row prints the table's numbered title: the table keeps its <caption> for screen readers only */
  titled: boolean
  /** the caption row has the CSV button: the table leaves its own out */
  csv: boolean
}

export const FigureContext = createContext<FigureFrame>({ titled: false, csv: false })

export function useFigureFrame(): FigureFrame {
  return useContext(FigureContext)
}
