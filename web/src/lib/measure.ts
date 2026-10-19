let ctx: CanvasRenderingContext2D | null | undefined

/** Rendered width of a label in Sarabun (canvas measureText); a character estimate where no canvas exists. */
export function textWidth(text: string, px: number, weight = 600): number {
  if (ctx === undefined) ctx = typeof document !== 'undefined' ? document.createElement('canvas').getContext('2d') : null
  if (!ctx) return text.length * px * 0.58
  ctx.font = `${weight} ${px}px Sarabun, "Noto Sans Thai", system-ui, sans-serif`
  return ctx.measureText(text).width
}
