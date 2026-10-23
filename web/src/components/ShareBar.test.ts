import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { ShareBar } from './ShareBar'

const html = (value: number | null) => renderToStaticMarkup(createElement(ShareBar, { value }))

describe('ShareBar', () => {
  it('prints a small real share as "<1%", never "0%"', () => {
    expect(html(0.004)).toContain('&lt;1%')
    expect(html(0)).toContain('>0%<')
    expect(html(0.25)).toContain('25%')
    expect(html(null)).toContain('–')
  })
})
