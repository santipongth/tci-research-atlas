import type { ReactNode } from 'react'
import { useMediaQuery } from '../lib/useMediaQuery'

/**
 * A section of supporting explanation (a step diagram) that folds into a closed disclosure on phones, so the page's
 * main content comes first; from 760 px it is an ordinary section with its h2.
 */
export function PhoneFold({ id, className, headingClass, heading, children }: {
  id: string
  className: string
  headingClass: string
  heading: ReactNode
  children: ReactNode
}) {
  const narrow = useMediaQuery('(max-width: 759px)')
  if (narrow) {
    return (
      <details className={`${className} fold`} aria-labelledby={id}>
        <summary>
          <h2 id={id} className={headingClass}>{heading}</h2>
        </summary>
        {children}
      </details>
    )
  }
  return (
    <section className={className} aria-labelledby={id}>
      <h2 id={id} className={headingClass}>{heading}</h2>
      {children}
    </section>
  )
}
