import type { ReactNode } from 'react'

/** A page section with an h2 that OnThisPage can scroll to. Render it only when its data exists (self-hiding). */
export function Section({ id, title, intro, children }: { id: string; title: string; intro?: ReactNode; children: ReactNode }) {
  return (
    <section className="sec" id={id} aria-labelledby={`${id}-h`}>
      <h2 id={`${id}-h`} tabIndex={-1}>{title}</h2>
      {intro ? <p className="intro">{intro}</p> : null}
      {children}
    </section>
  )
}
