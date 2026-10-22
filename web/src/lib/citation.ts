/**
 * RIS and BibTeX for article lists (R9, Ruling 10), written in the browser from search results, representative
 * articles and most-cited lists. Never an author: the Atlas publishes no person names (PDPA rule) — the DOI or the
 * ThaiJO link resolves the full citation. The Thai title is the main title when there is one; the other title goes to
 * RIS `TT` (translated title) and the BibTeX `note`. RIS `T2` is the journal, as reference managers expect for JOUR.
 */
export interface CiteRecord {
  id: string
  titleTh: string
  titleEn: string
  journal: string
  year: number | null
  doi: string | null
  url: string | null
}

const oneLine = (s: string | null | undefined) => (s ?? '').replace(/\s+/g, ' ').trim()

function titles(r: CiteRecord): [string, string] {
  const th = oneLine(r.titleTh)
  const en = oneLine(r.titleEn)
  return th ? [th, en] : [en, '']
}

const source = (release: string) => `Source: TCI Research Atlas ${release}`

/** RIS (CRLF line ends, one TY … ER record per article). */
export function toRis(records: readonly CiteRecord[], release: string): string {
  const lines: string[] = []
  const tag = (t: string, v: string | number | null | undefined) => {
    const s = oneLine(v === null || v === undefined ? '' : String(v))
    if (s) lines.push(`${t}  - ${s}`)
  }
  for (const r of records) {
    const [main, other] = titles(r)
    lines.push('TY  - JOUR')
    tag('ID', r.id)
    tag('TI', main)
    tag('TT', other)
    tag('T2', r.journal)
    tag('PY', r.year)
    tag('DO', r.doi)
    tag('UR', r.url)
    tag('N1', source(release))
    lines.push('ER  - ', '')
  }
  return lines.join('\r\n')
}

const BIB_SPECIAL: Record<string, string> = {
  '\\': '\\textbackslash{}', '{': '\\{', '}': '\\}', '&': '\\&', '%': '\\%', $: '\\$', '#': '\\#', _: '\\_', '^': '\\^{}', '~': '\\~{}',
}

/** A BibTeX field value: LaTeX special characters escaped, so braces always balance. */
export function bibEscape(s: string): string {
  return oneLine(s).replace(/[\\{}&%$#_^~]/g, (c) => BIB_SPECIAL[c])
}

/** DOI and URL fields are read verbatim: only characters that would break the braces or the line are encoded. */
const bibVerbatim = (s: string) => oneLine(s).replace(/[{}\\\s]/g, (c) => `%${c.charCodeAt(0).toString(16).toUpperCase().padStart(2, '0')}`)

function bibKey(id: string, used: Set<string>): string {
  const base = `tci:${id.replace(/[^A-Za-z0-9:._-]/g, '_')}`
  let key = base
  for (let n = 2; used.has(key); n++) key = `${base}-${n}`
  used.add(key)
  return key
}

/** BibTeX `@article` entries (UTF-8; Thai titles kept as they are). */
export function toBibtex(records: readonly CiteRecord[], release: string): string {
  const used = new Set<string>()
  return records
    .map((r) => {
      const [main, other] = titles(r)
      const fields: [string, string][] = [['title', bibEscape(main)]]
      if (r.journal) fields.push(['journal', bibEscape(r.journal)])
      if (r.year) fields.push(['year', String(r.year)])
      if (r.doi) fields.push(['doi', bibVerbatim(r.doi)])
      if (r.url) fields.push(['url', bibVerbatim(r.url)])
      fields.push(['note', bibEscape(other ? `${other}. ${source(release)}` : source(release))])
      return `@article{${bibKey(r.id, used)},\n${fields.map(([k, v]) => `  ${k} = {${v}},`).join('\n')}\n}\n`
    })
    .join('\n')
}

/** "Cite this atlas" (Ruling 10): the release as a data set — the organisation is the author, never a person. */
export interface AtlasCite {
  org: string
  title: string
  version: string
  kind: string
  year: number
  url: string | null
}

/** APA-like: Org. (Year). Title (Version) [Kind]. URL */
export function atlasCitation(c: AtlasCite): string {
  return `${oneLine(c.org)}. (${c.year}). ${oneLine(c.title)} (${oneLine(c.version)}) [${oneLine(c.kind)}].${c.url ? ` ${oneLine(c.url)}` : ''}`
}

/** BibTeX `@misc` for one release (English fields; the organisation in double braces so it is never split as a name). */
export function atlasBibtex(release: string, year: number, url: string | null, definitionVersion: number): string {
  const fields: [string, string][] = [
    ['author', `{${bibEscape('Thai-Journal Citation Index Centre (TCI)')}}`],
    ['title', `{TCI Research Atlas}: Thai research landscape, release ${bibEscape(release)}`],
    ['year', String(year)],
    ['version', bibEscape(release)],
    ['howpublished', 'Data set'],
  ]
  if (url) fields.push(['url', bibVerbatim(url)])
  fields.push(['note', bibEscape(`Status definition version ${definitionVersion}`)])
  return `@misc{tci-atlas-${release.toLowerCase().replace(/[^a-z0-9]/g, '')},\n${fields.map(([k, v]) => `  ${k} = {${v}},`).join('\n')}\n}\n`
}
