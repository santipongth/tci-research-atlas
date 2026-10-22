import { describe, expect, it } from 'vitest'
import { embedSrc, feedHref, iframeSnippet, siteUrl } from './embedUrl'

describe('embed URLs', () => {
  it('uses the served address and gives none in the offline file', () => {
    expect(siteUrl({ protocol: 'https:', origin: 'https://example.org', pathname: '/atlas/' })).toBe('https://example.org/atlas/')
    expect(siteUrl({ protocol: 'file:', origin: 'null', pathname: '/C:/atlas-offline.html' })).toBeNull()
  })

  it('builds a hash-router widget address and an escaped iframe', () => {
    const src = embedSrc('https://example.org/atlas/', 'topic/T000201', 'th')
    expect(src).toBe('https://example.org/atlas/#/embed/topic/T000201?lang=th')
    const html = iframeSnippet({ src, title: 'A "quoted" & <odd> title', width: 640, height: 480 })
    expect(html).toContain('src="https://example.org/atlas/#/embed/topic/T000201?lang=th"')
    expect(html).toContain('title="A &quot;quoted&quot; &amp; &lt;odd&gt; title"')
    expect(html).toContain('height="480"')
    expect(html.startsWith('<iframe ') && html.endsWith('</iframe>')).toBe(true)
  })

  it('points feeds at the site data folder', () => {
    expect(feedHref('releases.xml')).toMatch(/data\/feeds\/releases\.xml$/)
  })
})
