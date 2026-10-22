/**
 * URLs for the embeddable widgets (Ruling 11) and the Atom feeds (Ruling 9).
 * The site uses a HashRouter, so a widget is `<site>#/embed/...`; the site URL is where this page is served from.
 */

/** The public address of this site (origin + path, no hash), or null in the offline file (file://) — a widget or a
 *  citation URL pointing at a file on someone's disk would be useless. */
export function siteUrl(loc: Pick<Location, 'protocol' | 'origin' | 'pathname'> = window.location): string | null {
  return loc.protocol === 'http:' || loc.protocol === 'https:' ? `${loc.origin}${loc.pathname}` : null
}

/** `<site>#/embed/<path>?lang=<lang>` */
export function embedSrc(site: string, path: string, lang: string): string {
  return `${site}#/embed/${path}?lang=${lang}`
}

const attr = (s: string) => s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

/** The copyable <iframe> code: fixed height, full width up to `width` px, no border, lazy, with a title for screen readers. */
export function iframeSnippet({ src, title, width, height }: { src: string; title: string; width: number; height: number }): string {
  return `<iframe src="${attr(src)}" title="${attr(title)}" width="${width}" height="${height}" style="width:100%;max-width:${width}px;border:0" loading="lazy"></iframe>`
}

/** A feed on this site, relative to the page like every data file (`data/feeds/…`). */
export function feedHref(rel: string): string {
  return `${import.meta.env.BASE_URL}data/feeds/${rel}`
}
